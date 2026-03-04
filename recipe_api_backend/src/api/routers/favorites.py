"""
Favorites router: add, remove, and list user favorites.

Flow: FavoritesManagementFlow
Entrypoint: router (APIRouter mounted at /api/favorites)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.api.database import get_db
from src.api.models import Favorite, Recipe, User
from src.api.schemas import FavoriteOut, RecipeListOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/favorites", tags=["Favorites"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=list[FavoriteOut],
    summary="List current user's favorites",
    description="Returns all favorite entries for the authenticated user.",
)
def list_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all favorites for the current user.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of favorite entries.
    """
    return db.query(Favorite).filter(Favorite.user_id == current_user.id).order_by(Favorite.created_at.desc()).all()


# PUBLIC_INTERFACE
@router.get(
    "/recipes",
    response_model=list[RecipeListOut],
    summary="List favorited recipes",
    description="Returns the actual recipe objects that the user has favorited.",
)
def list_favorite_recipes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List full recipe data for the user's favorites.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of recipe summaries.
    """
    favorites = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    recipe_ids = [f.recipe_id for f in favorites]
    if not recipe_ids:
        return []
    recipes = db.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
    return recipes


# PUBLIC_INTERFACE
@router.post(
    "/{recipe_id}",
    response_model=FavoriteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a recipe to favorites",
    description="Adds the specified recipe to the authenticated user's favorites.",
)
def add_favorite(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a recipe to the user's favorites.

    Args:
        recipe_id: The recipe ID to favorite.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created favorite entry.

    Raises:
        HTTPException 404: If recipe not found.
        HTTPException 400: If already favorited.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    existing = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.recipe_id == recipe_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Recipe already in favorites")

    favorite = Favorite(user_id=current_user.id, recipe_id=recipe_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    logger.info("Favorite added user_id=%d recipe_id=%d", current_user.id, recipe_id)
    return favorite


# PUBLIC_INTERFACE
@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a recipe from favorites",
    description="Removes the specified recipe from the authenticated user's favorites.",
)
def remove_favorite(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a recipe from the user's favorites.

    Args:
        recipe_id: The recipe ID to unfavorite.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If favorite not found.
    """
    favorite = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.recipe_id == recipe_id)
        .first()
    )
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(favorite)
    db.commit()
    logger.info("Favorite removed user_id=%d recipe_id=%d", current_user.id, recipe_id)
