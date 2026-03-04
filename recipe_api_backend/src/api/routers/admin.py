"""
Admin moderation router: approve/reject/remove recipes and reviews.

Flow: AdminModerationFlow
Entrypoint: router (APIRouter mounted at /api/admin)
"""
import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_admin
from src.api.database import get_db
from src.api.models import ModerationLog, Recipe, Review, User
from src.api.schemas import ModerationAction, ModerationLogOut, RecipeListOut, ReviewOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin / Moderation"])

# Allowed target types and actions for validation
ALLOWED_TARGET_TYPES = {"recipe", "review"}
ALLOWED_ACTIONS = {"approve", "reject", "remove"}


# PUBLIC_INTERFACE
@router.post(
    "/moderate",
    response_model=ModerationLogOut,
    status_code=status.HTTP_201_CREATED,
    summary="Perform a moderation action",
    description="Approve, reject, or remove a recipe or review. Admin access required. "
    "target_type must be 'recipe' or 'review'. action must be 'approve', 'reject', or 'remove'.",
)
def moderate(
    payload: ModerationAction,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Execute a moderation action on a recipe or review.

    Contract:
      - Input: target_type ('recipe' or 'review'), target_id, action ('approve', 'reject', 'remove'), optional reason
      - Output: ModerationLog entry
      - Side effects: Updates is_approved/is_published on target, or deletes target
      - Errors: 400 for invalid type/action, 404 if target not found

    Args:
        payload: Moderation action data.
        admin: The authenticated admin user.
        db: Database session.

    Returns:
        The created moderation log entry.

    Raises:
        HTTPException 400: Invalid target_type or action.
        HTTPException 404: Target entity not found.
    """
    logger.info(
        "Moderation action: admin_id=%d target_type=%s target_id=%d action=%s",
        admin.id, payload.target_type, payload.target_id, payload.action,
    )

    if payload.target_type not in ALLOWED_TARGET_TYPES:
        raise HTTPException(status_code=400, detail=f"target_type must be one of {ALLOWED_TARGET_TYPES}")
    if payload.action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"action must be one of {ALLOWED_ACTIONS}")

    # Apply action to the target entity
    if payload.target_type == "recipe":
        recipe = db.query(Recipe).filter(Recipe.id == payload.target_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if payload.action == "approve":
            recipe.is_approved = True
            recipe.is_published = True
        elif payload.action == "reject":
            recipe.is_approved = False
            recipe.is_published = False
        elif payload.action == "remove":
            db.delete(recipe)

    elif payload.target_type == "review":
        review = db.query(Review).filter(Review.id == payload.target_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        if payload.action == "approve":
            review.is_approved = True
        elif payload.action == "reject":
            review.is_approved = False
        elif payload.action == "remove":
            db.delete(review)

    # Log the moderation action
    log_entry = ModerationLog(
        admin_id=admin.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        action=payload.action,
        reason=payload.reason,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    logger.info("Moderation log created id=%d", log_entry.id)
    return log_entry


# PUBLIC_INTERFACE
@router.get(
    "/moderation-log",
    response_model=dict,
    summary="List moderation logs",
    description="Returns paginated moderation action logs. Admin access required.",
)
def list_moderation_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all moderation log entries with pagination.

    Args:
        page: Page number.
        page_size: Items per page.
        admin: The authenticated admin user.
        db: Database session.

    Returns:
        Paginated moderation log entries.
    """
    query = db.query(ModerationLog)
    total = query.count()
    logs = query.order_by(ModerationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [ModerationLogOut.model_validate(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 0,
    }


# PUBLIC_INTERFACE
@router.get(
    "/pending-recipes",
    response_model=dict,
    summary="List recipes pending approval",
    description="Returns paginated recipes that are not yet approved. Admin access required.",
)
def list_pending_recipes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List recipes that are pending moderation approval.

    Args:
        page: Page number.
        page_size: Items per page.
        admin: The authenticated admin user.
        db: Database session.

    Returns:
        Paginated list of unapproved recipes.
    """
    query = db.query(Recipe).filter(Recipe.is_approved.is_(False))
    total = query.count()
    recipes = query.order_by(Recipe.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [RecipeListOut.model_validate(r) for r in recipes],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 0,
    }


# PUBLIC_INTERFACE
@router.get(
    "/pending-reviews",
    response_model=dict,
    summary="List reviews pending approval",
    description="Returns paginated reviews that are not yet approved. Admin access required.",
)
def list_pending_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List reviews that are pending moderation approval.

    Args:
        page: Page number.
        page_size: Items per page.
        admin: The authenticated admin user.
        db: Database session.

    Returns:
        Paginated list of unapproved reviews.
    """
    query = db.query(Review).filter(Review.is_approved.is_(False))
    total = query.count()
    reviews = query.order_by(Review.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [ReviewOut.model_validate(r) for r in reviews],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 0,
    }
