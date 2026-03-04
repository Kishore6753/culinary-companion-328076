"""
Ratings router: create, update, and view ratings for recipes.

Flow: RatingManagementFlow
Entrypoint: router (APIRouter mounted at /api/ratings)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.api.database import get_db
from src.api.models import Rating, Recipe, User
from src.api.schemas import RatingCreate, RatingOut, RecipeRatingSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ratings", tags=["Ratings"])


# PUBLIC_INTERFACE
@router.get(
    "/recipe/{recipe_id}",
    response_model=RecipeRatingSummary,
    summary="Get rating summary for a recipe",
    description="Returns the average score and total number of ratings for a recipe.",
)
def get_recipe_rating_summary(recipe_id: int, db: Session = Depends(get_db)):
    """Get aggregated rating summary for a recipe.

    Args:
        recipe_id: The recipe ID.
        db: Database session.

    Returns:
        Average score and total count.

    Raises:
        HTTPException 404: If recipe not found.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    result = db.query(
        func.coalesce(func.avg(Rating.score), 0).label("avg"),
        func.count(Rating.id).label("count"),
    ).filter(Rating.recipe_id == recipe_id).first()

    return RecipeRatingSummary(
        recipe_id=recipe_id,
        average_score=round(float(result.avg), 2),
        total_ratings=result.count,
    )


# PUBLIC_INTERFACE
@router.get(
    "/recipe/{recipe_id}/all",
    response_model=list[RatingOut],
    summary="List all ratings for a recipe",
    description="Returns all individual ratings for a given recipe.",
)
def list_recipe_ratings(recipe_id: int, db: Session = Depends(get_db)):
    """List all individual ratings for a recipe.

    Args:
        recipe_id: The recipe ID.
        db: Database session.

    Returns:
        List of rating entries.
    """
    return db.query(Rating).filter(Rating.recipe_id == recipe_id).order_by(Rating.created_at.desc()).all()


# PUBLIC_INTERFACE
@router.post(
    "/recipe/{recipe_id}",
    response_model=RatingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Rate a recipe",
    description="Creates or updates the authenticated user's rating for a recipe (1-5 stars).",
)
def rate_recipe(
    recipe_id: int,
    payload: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a rating for a recipe.

    If the user has already rated this recipe, the existing rating is updated.

    Args:
        recipe_id: The recipe ID.
        payload: Rating data (score 1-5).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created or updated rating.

    Raises:
        HTTPException 404: If recipe not found.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    existing = (
        db.query(Rating)
        .filter(Rating.user_id == current_user.id, Rating.recipe_id == recipe_id)
        .first()
    )
    if existing:
        existing.score = payload.score
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        logger.info("Rating updated user_id=%d recipe_id=%d score=%d", current_user.id, recipe_id, payload.score)
        return existing

    rating = Rating(
        user_id=current_user.id,
        recipe_id=recipe_id,
        score=payload.score,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    logger.info("Rating created user_id=%d recipe_id=%d score=%d", current_user.id, recipe_id, payload.score)
    return rating
