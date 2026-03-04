"""
Reviews router: create, list, update, and delete reviews for recipes.

Flow: ReviewManagementFlow
Entrypoint: router (APIRouter mounted at /api/reviews)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from src.api.auth import get_current_user
from src.api.database import get_db
from src.api.models import Recipe, Review, User
from src.api.schemas import ReviewCreate, ReviewOut, ReviewUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


# PUBLIC_INTERFACE
@router.get(
    "/recipe/{recipe_id}",
    response_model=list[ReviewOut],
    summary="List approved reviews for a recipe",
    description="Returns all approved reviews for a recipe, with user info.",
)
def list_recipe_reviews(
    recipe_id: int,
    db: Session = Depends(get_db),
):
    """List approved reviews for a recipe.

    Args:
        recipe_id: The recipe ID.
        db: Database session.

    Returns:
        List of approved reviews with user details.
    """
    reviews = (
        db.query(Review)
        .options(joinedload(Review.user))
        .filter(Review.recipe_id == recipe_id, Review.is_approved.is_(True))
        .order_by(Review.created_at.desc())
        .all()
    )
    return reviews


# PUBLIC_INTERFACE
@router.post(
    "/recipe/{recipe_id}",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a review for a recipe",
    description="Creates a review for the specified recipe. Requires authentication.",
)
def create_review(
    recipe_id: int,
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new review for a recipe.

    Args:
        recipe_id: The recipe ID.
        payload: Review data (comment text).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created review.

    Raises:
        HTTPException 404: If recipe not found.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    review = Review(
        user_id=current_user.id,
        recipe_id=recipe_id,
        comment=payload.comment,
        is_approved=True,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    # Re-fetch with user relationship
    review = db.query(Review).options(joinedload(Review.user)).filter(Review.id == review.id).first()
    logger.info("Review created id=%d user_id=%d recipe_id=%d", review.id, current_user.id, recipe_id)
    return review


# PUBLIC_INTERFACE
@router.put(
    "/{review_id}",
    response_model=ReviewOut,
    summary="Update a review",
    description="Updates a review comment. Only the review author can update.",
)
def update_review(
    review_id: int,
    payload: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing review.

    Args:
        review_id: The review ID.
        payload: Updated review data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated review.

    Raises:
        HTTPException 404: If review not found.
        HTTPException 403: If user is not the review author.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this review")

    review.comment = payload.comment
    review.updated_at = datetime.now(timezone.utc)
    db.commit()
    review = db.query(Review).options(joinedload(Review.user)).filter(Review.id == review.id).first()
    logger.info("Review updated id=%d", review_id)
    return review


# PUBLIC_INTERFACE
@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a review",
    description="Deletes a review. Only the author or an admin can delete.",
)
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a review.

    Args:
        review_id: The review ID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If review not found.
        HTTPException 403: If user is not the author or admin.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this review")

    db.delete(review)
    db.commit()
    logger.info("Review deleted id=%d by user id=%d", review_id, current_user.id)
