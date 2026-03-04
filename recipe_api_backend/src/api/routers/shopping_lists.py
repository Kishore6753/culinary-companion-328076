"""
Shopping lists router: CRUD for shopping lists and their items.

Flow: ShoppingListManagementFlow
Entrypoint: router (APIRouter mounted at /api/shopping-lists)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from src.api.auth import get_current_user
from src.api.database import get_db
from src.api.models import Ingredient, Recipe, ShoppingList, ShoppingListItem, User
from src.api.schemas import (
    ShoppingListCreate,
    ShoppingListItemCreate,
    ShoppingListItemOut,
    ShoppingListItemUpdate,
    ShoppingListOut,
    ShoppingListUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/shopping-lists", tags=["Shopping Lists"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=list[ShoppingListOut],
    summary="List user's shopping lists",
    description="Returns all shopping lists for the authenticated user, with items.",
)
def list_shopping_lists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all shopping lists for the current user.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of shopping lists with their items.
    """
    return (
        db.query(ShoppingList)
        .options(joinedload(ShoppingList.items))
        .filter(ShoppingList.user_id == current_user.id)
        .order_by(ShoppingList.updated_at.desc())
        .all()
    )


# PUBLIC_INTERFACE
@router.get(
    "/{list_id}",
    response_model=ShoppingListOut,
    summary="Get a shopping list by ID",
    description="Returns a single shopping list with its items.",
)
def get_shopping_list(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific shopping list.

    Args:
        list_id: The shopping list ID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Shopping list with items.

    Raises:
        HTTPException 404: If list not found or not owned by user.
    """
    shopping_list = (
        db.query(ShoppingList)
        .options(joinedload(ShoppingList.items))
        .filter(ShoppingList.id == list_id, ShoppingList.user_id == current_user.id)
        .first()
    )
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return shopping_list


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=ShoppingListOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shopping list",
    description="Creates a new shopping list for the authenticated user.",
)
def create_shopping_list(
    payload: ShoppingListCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new shopping list.

    Args:
        payload: Shopping list creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created shopping list.
    """
    shopping_list = ShoppingList(
        user_id=current_user.id,
        name=payload.name,
    )
    db.add(shopping_list)
    db.commit()
    db.refresh(shopping_list)
    logger.info("Shopping list created id=%d user_id=%d", shopping_list.id, current_user.id)
    return shopping_list


# PUBLIC_INTERFACE
@router.put(
    "/{list_id}",
    response_model=ShoppingListOut,
    summary="Update a shopping list",
    description="Updates the name of a shopping list.",
)
def update_shopping_list(
    list_id: int,
    payload: ShoppingListUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a shopping list name.

    Args:
        list_id: The shopping list ID.
        payload: Updated data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated shopping list.

    Raises:
        HTTPException 404: If list not found or not owned by user.
    """
    shopping_list = (
        db.query(ShoppingList)
        .filter(ShoppingList.id == list_id, ShoppingList.user_id == current_user.id)
        .first()
    )
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    shopping_list.name = payload.name
    shopping_list.updated_at = datetime.now(timezone.utc)
    db.commit()
    shopping_list = (
        db.query(ShoppingList)
        .options(joinedload(ShoppingList.items))
        .filter(ShoppingList.id == list_id)
        .first()
    )
    logger.info("Shopping list updated id=%d", list_id)
    return shopping_list


# PUBLIC_INTERFACE
@router.delete(
    "/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shopping list",
    description="Deletes a shopping list and all its items.",
)
def delete_shopping_list(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a shopping list.

    Args:
        list_id: The shopping list ID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If list not found or not owned by user.
    """
    shopping_list = (
        db.query(ShoppingList)
        .filter(ShoppingList.id == list_id, ShoppingList.user_id == current_user.id)
        .first()
    )
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    db.delete(shopping_list)
    db.commit()
    logger.info("Shopping list deleted id=%d", list_id)


# ─── Shopping List Items ─────────────────────────────────────────────────────


# PUBLIC_INTERFACE
@router.post(
    "/{list_id}/items",
    response_model=ShoppingListItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to a shopping list",
    description="Adds a new item to the specified shopping list.",
)
def add_shopping_list_item(
    list_id: int,
    payload: ShoppingListItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add an item to a shopping list.

    Args:
        list_id: The shopping list ID.
        payload: Item data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created shopping list item.

    Raises:
        HTTPException 404: If shopping list not found or not owned by user.
    """
    shopping_list = (
        db.query(ShoppingList)
        .filter(ShoppingList.id == list_id, ShoppingList.user_id == current_user.id)
        .first()
    )
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    item = ShoppingListItem(
        shopping_list_id=list_id,
        ingredient_name=payload.ingredient_name,
        quantity=payload.quantity,
        unit=payload.unit,
        recipe_id=payload.recipe_id,
    )
    db.add(item)
    shopping_list.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    logger.info("Item added to shopping list id=%d", list_id)
    return item


# PUBLIC_INTERFACE
@router.post(
    "/{list_id}/add-recipe/{recipe_id}",
    response_model=ShoppingListOut,
    summary="Add all ingredients from a recipe to a shopping list",
    description="Adds all ingredients from a recipe to the shopping list.",
)
def add_recipe_ingredients_to_list(
    list_id: int,
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add all ingredients from a recipe to a shopping list.

    Args:
        list_id: The shopping list ID.
        recipe_id: The recipe ID whose ingredients to add.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated shopping list with all items.

    Raises:
        HTTPException 404: If shopping list or recipe not found.
    """
    shopping_list = (
        db.query(ShoppingList)
        .filter(ShoppingList.id == list_id, ShoppingList.user_id == current_user.id)
        .first()
    )
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    ingredients = db.query(Ingredient).filter(Ingredient.recipe_id == recipe_id).order_by(Ingredient.order_index).all()
    for ing in ingredients:
        item = ShoppingListItem(
            shopping_list_id=list_id,
            ingredient_name=ing.name,
            quantity=ing.quantity,
            unit=ing.unit,
            recipe_id=recipe_id,
        )
        db.add(item)

    shopping_list.updated_at = datetime.now(timezone.utc)
    db.commit()

    result = (
        db.query(ShoppingList)
        .options(joinedload(ShoppingList.items))
        .filter(ShoppingList.id == list_id)
        .first()
    )
    logger.info("Recipe id=%d ingredients added to shopping list id=%d", recipe_id, list_id)
    return result


# PUBLIC_INTERFACE
@router.put(
    "/{list_id}/items/{item_id}",
    response_model=ShoppingListItemOut,
    summary="Update a shopping list item",
    description="Updates an item in a shopping list (name, quantity, unit, checked status).",
)
def update_shopping_list_item(
    list_id: int,
    item_id: int,
    payload: ShoppingListItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a shopping list item.

    Args:
        list_id: The shopping list ID.
        item_id: The item ID.
        payload: Fields to update.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated item.

    Raises:
        HTTPException 404: If list or item not found.
    """
    shopping_list = (
        db.query(ShoppingList)
        .filter(ShoppingList.id == list_id, ShoppingList.user_id == current_user.id)
        .first()
    )
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    item = (
        db.query(ShoppingListItem)
        .filter(ShoppingListItem.id == item_id, ShoppingListItem.shopping_list_id == list_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if payload.ingredient_name is not None:
        item.ingredient_name = payload.ingredient_name
    if payload.quantity is not None:
        item.quantity = payload.quantity
    if payload.unit is not None:
        item.unit = payload.unit
    if payload.is_checked is not None:
        item.is_checked = payload.is_checked

    shopping_list.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


# PUBLIC_INTERFACE
@router.delete(
    "/{list_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item from a shopping list",
    description="Removes a specific item from a shopping list.",
)
def delete_shopping_list_item(
    list_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove an item from a shopping list.

    Args:
        list_id: The shopping list ID.
        item_id: The item ID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If list or item not found.
    """
    shopping_list = (
        db.query(ShoppingList)
        .filter(ShoppingList.id == list_id, ShoppingList.user_id == current_user.id)
        .first()
    )
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    item = (
        db.query(ShoppingListItem)
        .filter(ShoppingListItem.id == item_id, ShoppingListItem.shopping_list_id == list_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    logger.info("Item id=%d removed from shopping list id=%d", item_id, list_id)
