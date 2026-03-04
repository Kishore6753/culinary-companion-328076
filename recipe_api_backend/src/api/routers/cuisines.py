"""
Cuisines router: list and CRUD for cuisine types.

Flow: CuisineManagementFlow
Entrypoint: router (APIRouter mounted at /api/cuisines)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_admin
from src.api.database import get_db
from src.api.models import Cuisine
from src.api.schemas import CuisineCreate, CuisineOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cuisines", tags=["Cuisines"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=list[CuisineOut],
    summary="List all cuisines",
    description="Returns all cuisine types.",
)
def list_cuisines(db: Session = Depends(get_db)):
    """List all cuisines.

    Args:
        db: Database session.

    Returns:
        List of all cuisines.
    """
    return db.query(Cuisine).order_by(Cuisine.name).all()


# PUBLIC_INTERFACE
@router.get(
    "/{cuisine_id}",
    response_model=CuisineOut,
    summary="Get cuisine by ID",
    description="Returns a single cuisine by its ID.",
)
def get_cuisine(cuisine_id: int, db: Session = Depends(get_db)):
    """Get a single cuisine.

    Args:
        cuisine_id: The cuisine ID.
        db: Database session.

    Returns:
        Cuisine data.

    Raises:
        HTTPException 404: If cuisine not found.
    """
    cuisine = db.query(Cuisine).filter(Cuisine.id == cuisine_id).first()
    if not cuisine:
        raise HTTPException(status_code=404, detail="Cuisine not found")
    return cuisine


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=CuisineOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a cuisine (admin)",
    description="Creates a new cuisine type. Admin access required.",
)
def create_cuisine(
    payload: CuisineCreate,
    admin: None = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new cuisine (admin only).

    Args:
        payload: Cuisine creation data.
        admin: The authenticated admin user.
        db: Database session.

    Returns:
        The created cuisine.

    Raises:
        HTTPException 400: If cuisine name already exists.
    """
    if db.query(Cuisine).filter(Cuisine.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Cuisine name already exists")
    cuisine = Cuisine(name=payload.name, description=payload.description, image_url=payload.image_url)
    db.add(cuisine)
    db.commit()
    db.refresh(cuisine)
    logger.info("Cuisine created id=%d name='%s'", cuisine.id, cuisine.name)
    return cuisine


# PUBLIC_INTERFACE
@router.delete(
    "/{cuisine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a cuisine (admin)",
    description="Deletes a cuisine type. Admin access required.",
)
def delete_cuisine(
    cuisine_id: int,
    admin: None = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a cuisine (admin only).

    Args:
        cuisine_id: The cuisine ID.
        admin: The authenticated admin user.
        db: Database session.

    Raises:
        HTTPException 404: If cuisine not found.
    """
    cuisine = db.query(Cuisine).filter(Cuisine.id == cuisine_id).first()
    if not cuisine:
        raise HTTPException(status_code=404, detail="Cuisine not found")
    db.delete(cuisine)
    db.commit()
    logger.info("Cuisine deleted id=%d", cuisine_id)
