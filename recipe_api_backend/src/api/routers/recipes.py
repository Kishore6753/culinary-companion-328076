"""
Recipes router: CRUD, search, and filtering for recipes.

Flow: RecipeManagementFlow
Entrypoint: router (APIRouter mounted at /api/recipes)
"""
import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.api.auth import get_current_user, get_optional_current_user
from src.api.database import get_db
from src.api.models import Ingredient, Recipe, RecipeStep, User
from src.api.schemas import RecipeCreate, RecipeListOut, RecipeOut, RecipeUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recipes", tags=["Recipes"])


def _build_recipe_query(db: Session, published_only: bool = True):
    """Build base recipe query with eager-loaded relationships."""
    query = db.query(Recipe).options(
        joinedload(Recipe.ingredients),
        joinedload(Recipe.steps),
        joinedload(Recipe.author),
        joinedload(Recipe.category),
        joinedload(Recipe.cuisine),
    )
    if published_only:
        query = query.filter(Recipe.is_published.is_(True), Recipe.is_approved.is_(True))
    return query


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=dict,
    summary="List recipes with pagination, search, and filtering",
    description="Returns a paginated list of published/approved recipes. "
    "Supports search by title, filtering by category_id, cuisine_id, and difficulty.",
)
def list_recipes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search recipes by title"),
    category_id: int | None = Query(None, description="Filter by category"),
    cuisine_id: int | None = Query(None, description="Filter by cuisine"),
    difficulty: str | None = Query(None, description="Filter by difficulty"),
    author_id: int | None = Query(None, description="Filter by author"),
    db: Session = Depends(get_db),
):
    """List recipes with pagination and optional filters.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        search: Optional title search term.
        category_id: Optional category filter.
        cuisine_id: Optional cuisine filter.
        difficulty: Optional difficulty filter.
        author_id: Optional author filter.
        db: Database session.

    Returns:
        Paginated response with recipe list items.
    """
    logger.info("Listing recipes page=%d size=%d search=%s", page, page_size, search)
    query = db.query(Recipe).filter(Recipe.is_published.is_(True), Recipe.is_approved.is_(True))

    if search:
        query = query.filter(Recipe.title.ilike(f"%{search}%"))
    if category_id is not None:
        query = query.filter(Recipe.category_id == category_id)
    if cuisine_id is not None:
        query = query.filter(Recipe.cuisine_id == cuisine_id)
    if difficulty:
        query = query.filter(Recipe.difficulty == difficulty)
    if author_id is not None:
        query = query.filter(Recipe.author_id == author_id)

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
    "/{recipe_id}",
    response_model=RecipeOut,
    summary="Get recipe detail",
    description="Returns the full recipe including ingredients, steps, author, category, and cuisine.",
)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Get a single recipe by ID with all nested details.

    Args:
        recipe_id: The recipe ID.
        db: Database session.

    Returns:
        Full recipe data.

    Raises:
        HTTPException 404: If recipe not found.
    """
    recipe = _build_recipe_query(db, published_only=False).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=RecipeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recipe",
    description="Creates a recipe with ingredients and steps. Requires authentication.",
)
def create_recipe(
    payload: RecipeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new recipe owned by the authenticated user.

    Args:
        payload: Recipe data including ingredients and steps.
        current_user: The authenticated user (author).
        db: Database session.

    Returns:
        The created recipe with all details.
    """
    logger.info("Creating recipe title='%s' by user id=%d", payload.title, current_user.id)
    recipe = Recipe(
        title=payload.title,
        description=payload.description,
        instructions=payload.instructions,
        prep_time_minutes=payload.prep_time_minutes,
        cook_time_minutes=payload.cook_time_minutes,
        total_time_minutes=payload.total_time_minutes,
        servings=payload.servings,
        difficulty=payload.difficulty,
        image_url=payload.image_url,
        category_id=payload.category_id,
        cuisine_id=payload.cuisine_id,
        author_id=current_user.id,
        is_published=True,
        is_approved=True,
    )
    db.add(recipe)
    db.flush()  # Get recipe.id before adding children

    for ing_data in payload.ingredients:
        ingredient = Ingredient(
            recipe_id=recipe.id,
            name=ing_data.name,
            quantity=ing_data.quantity,
            unit=ing_data.unit,
            order_index=ing_data.order_index,
        )
        db.add(ingredient)

    for step_data in payload.steps:
        step = RecipeStep(
            recipe_id=recipe.id,
            step_number=step_data.step_number,
            instruction=step_data.instruction,
            image_url=step_data.image_url,
        )
        db.add(step)

    db.commit()
    # Re-fetch with all relationships
    full_recipe = _build_recipe_query(db, published_only=False).filter(Recipe.id == recipe.id).first()
    logger.info("Recipe created id=%d", recipe.id)
    return full_recipe


# PUBLIC_INTERFACE
@router.put(
    "/{recipe_id}",
    response_model=RecipeOut,
    summary="Update a recipe",
    description="Updates a recipe. Only the author or an admin can update.",
)
def update_recipe(
    recipe_id: int,
    payload: RecipeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing recipe.

    Args:
        recipe_id: The recipe ID to update.
        payload: Fields to update.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated recipe.

    Raises:
        HTTPException 404: If recipe not found.
        HTTPException 403: If user is not the author or admin.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this recipe")

    # Update scalar fields
    update_fields = ["title", "description", "instructions", "prep_time_minutes",
                     "cook_time_minutes", "total_time_minutes", "servings",
                     "difficulty", "image_url", "is_published", "category_id", "cuisine_id"]
    for field in update_fields:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(recipe, field, value)

    # Replace ingredients if provided
    if payload.ingredients is not None:
        db.query(Ingredient).filter(Ingredient.recipe_id == recipe_id).delete()
        for ing_data in payload.ingredients:
            db.add(Ingredient(
                recipe_id=recipe_id,
                name=ing_data.name,
                quantity=ing_data.quantity,
                unit=ing_data.unit,
                order_index=ing_data.order_index,
            ))

    # Replace steps if provided
    if payload.steps is not None:
        db.query(RecipeStep).filter(RecipeStep.recipe_id == recipe_id).delete()
        for step_data in payload.steps:
            db.add(RecipeStep(
                recipe_id=recipe_id,
                step_number=step_data.step_number,
                instruction=step_data.instruction,
                image_url=step_data.image_url,
            ))

    recipe.updated_at = datetime.now(timezone.utc)
    db.commit()
    full_recipe = _build_recipe_query(db, published_only=False).filter(Recipe.id == recipe.id).first()
    logger.info("Recipe updated id=%d by user id=%d", recipe_id, current_user.id)
    return full_recipe


# PUBLIC_INTERFACE
@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recipe",
    description="Deletes a recipe. Only the author or an admin can delete.",
)
def delete_recipe(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a recipe by ID.

    Args:
        recipe_id: The recipe ID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If recipe not found.
        HTTPException 403: If user is not the author or admin.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this recipe")

    db.delete(recipe)
    db.commit()
    logger.info("Recipe deleted id=%d by user id=%d", recipe_id, current_user.id)
