"""
Categories router: list and CRUD for recipe categories.

Flow: CategoryManagementFlow
Entrypoint: router (APIRouter mounted at /api/categories)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_admin
from src.api.database import get_db
from src.api.models import Category
from src.api.schemas import CategoryCreate, CategoryOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/categories", tags=["Categories"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=list[CategoryOut],
    summary="List all categories",
    description="Returns all recipe categories.",
)
def list_categories(db: Session = Depends(get_db)):
    """List all recipe categories.

    Args:
        db: Database session.

    Returns:
        List of all categories.
    """
    return db.query(Category).order_by(Category.name).all()


# PUBLIC_INTERFACE
@router.get(
    "/{category_id}",
    response_model=CategoryOut,
    summary="Get category by ID",
    description="Returns a single category by its ID.",
)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a single category.

    Args:
        category_id: The category ID.
        db: Database session.

    Returns:
        Category data.

    Raises:
        HTTPException 404: If category not found.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category (admin)",
    description="Creates a new category. Admin access required.",
)
def create_category(
    payload: CategoryCreate,
    admin: None = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new category (admin only).

    Args:
        payload: Category creation data.
        admin: The authenticated admin user.
        db: Database session.

    Returns:
        The created category.

    Raises:
        HTTPException 400: If category name already exists.
    """
    if db.query(Category).filter(Category.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Category name already exists")
    category = Category(name=payload.name, description=payload.description, image_url=payload.image_url)
    db.add(category)
    db.commit()
    db.refresh(category)
    logger.info("Category created id=%d name='%s'", category.id, category.name)
    return category


# PUBLIC_INTERFACE
@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category (admin)",
    description="Deletes a category. Admin access required.",
)
def delete_category(
    category_id: int,
    admin: None = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a category (admin only).

    Args:
        category_id: The category ID.
        admin: The authenticated admin user.
        db: Database session.

    Raises:
        HTTPException 404: If category not found.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
    logger.info("Category deleted id=%d", category_id)
