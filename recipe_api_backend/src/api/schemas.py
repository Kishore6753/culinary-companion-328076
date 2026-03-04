"""
Pydantic schemas for request/response validation.

Organized by domain: Auth, User, Category, Cuisine, Recipe (with ingredients
and steps), Favorite, Rating, Review, ShoppingList, ShoppingListItem,
ModerationLog.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ─── Auth Schemas ────────────────────────────────────────────────────────────


class UserRegister(BaseModel):
    """Schema for user registration."""

    username: str = Field(..., min_length=3, max_length=100, description="Unique username")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    display_name: Optional[str] = Field(None, max_length=150, description="Display name")


class UserLogin(BaseModel):
    """Schema for user login."""

    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


# ─── User Schemas ────────────────────────────────────────────────────────────


class UserOut(BaseModel):
    """Public user information."""

    id: int
    username: str
    email: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    display_name: Optional[str] = Field(None, max_length=150)
    bio: Optional[str] = None
    avatar_url: Optional[str] = Field(None, max_length=500)


# ─── Category Schemas ────────────────────────────────────────────────────────


class CategoryCreate(BaseModel):
    """Schema for creating a category."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)


class CategoryOut(BaseModel):
    """Category response schema."""

    id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Cuisine Schemas ─────────────────────────────────────────────────────────


class CuisineCreate(BaseModel):
    """Schema for creating a cuisine."""

    name: str = Field(..., min_length=1, max_length=100, description="Cuisine name")
    description: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)


class CuisineOut(BaseModel):
    """Cuisine response schema."""

    id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Ingredient Schemas ──────────────────────────────────────────────────────


class IngredientCreate(BaseModel):
    """Schema for creating an ingredient within a recipe."""

    name: str = Field(..., min_length=1, max_length=200, description="Ingredient name")
    quantity: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=50)
    order_index: int = Field(default=0, description="Display order")


class IngredientOut(BaseModel):
    """Ingredient response schema."""

    id: int
    recipe_id: int
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    order_index: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Recipe Step Schemas ─────────────────────────────────────────────────────


class RecipeStepCreate(BaseModel):
    """Schema for creating a recipe step."""

    step_number: int = Field(..., ge=1, description="Step sequence number")
    instruction: str = Field(..., min_length=1, description="Step instruction text")
    image_url: Optional[str] = Field(None, max_length=500)


class RecipeStepOut(BaseModel):
    """Recipe step response schema."""

    id: int
    recipe_id: int
    step_number: int
    instruction: str
    image_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Recipe Schemas ──────────────────────────────────────────────────────────


class RecipeCreate(BaseModel):
    """Schema for creating a recipe with ingredients and steps."""

    title: str = Field(..., min_length=1, max_length=255, description="Recipe title")
    description: Optional[str] = None
    instructions: str = Field(..., min_length=1, description="Cooking instructions")
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    total_time_minutes: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    difficulty: Optional[str] = Field("medium", description="easy, medium, or hard")
    image_url: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = None
    cuisine_id: Optional[int] = None
    ingredients: List[IngredientCreate] = Field(default_factory=list)
    steps: List[RecipeStepCreate] = Field(default_factory=list)


class RecipeUpdate(BaseModel):
    """Schema for updating a recipe."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    total_time_minutes: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    difficulty: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    is_published: Optional[bool] = None
    category_id: Optional[int] = None
    cuisine_id: Optional[int] = None
    ingredients: Optional[List[IngredientCreate]] = None
    steps: Optional[List[RecipeStepCreate]] = None


class RecipeOut(BaseModel):
    """Full recipe response schema with nested relations."""

    id: int
    title: str
    description: Optional[str] = None
    instructions: str
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    total_time_minutes: Optional[int] = None
    servings: Optional[int] = None
    difficulty: Optional[str] = None
    image_url: Optional[str] = None
    is_published: bool
    is_approved: bool
    author_id: int
    category_id: Optional[int] = None
    cuisine_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    ingredients: List[IngredientOut] = []
    steps: List[RecipeStepOut] = []
    author: Optional[UserOut] = None
    category: Optional[CategoryOut] = None
    cuisine: Optional[CuisineOut] = None

    model_config = {"from_attributes": True}


class RecipeListOut(BaseModel):
    """Lightweight recipe listing (no nested ingredients/steps)."""

    id: int
    title: str
    description: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    total_time_minutes: Optional[int] = None
    servings: Optional[int] = None
    difficulty: Optional[str] = None
    image_url: Optional[str] = None
    is_published: bool
    is_approved: bool
    author_id: int
    category_id: Optional[int] = None
    cuisine_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Favorite Schemas ────────────────────────────────────────────────────────


class FavoriteOut(BaseModel):
    """Favorite response schema."""

    id: int
    user_id: int
    recipe_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Rating Schemas ──────────────────────────────────────────────────────────


class RatingCreate(BaseModel):
    """Schema for creating/updating a rating."""

    score: int = Field(..., ge=1, le=5, description="Rating score 1-5")


class RatingOut(BaseModel):
    """Rating response schema."""

    id: int
    user_id: int
    recipe_id: int
    score: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecipeRatingSummary(BaseModel):
    """Aggregated rating summary for a recipe."""

    recipe_id: int
    average_score: float
    total_ratings: int


# ─── Review Schemas ──────────────────────────────────────────────────────────


class ReviewCreate(BaseModel):
    """Schema for creating a review."""

    comment: str = Field(..., min_length=1, description="Review text")


class ReviewUpdate(BaseModel):
    """Schema for updating a review."""

    comment: str = Field(..., min_length=1, description="Updated review text")


class ReviewOut(BaseModel):
    """Review response schema."""

    id: int
    user_id: int
    recipe_id: int
    comment: str
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    user: Optional[UserOut] = None

    model_config = {"from_attributes": True}


# ─── Shopping List Schemas ───────────────────────────────────────────────────


class ShoppingListCreate(BaseModel):
    """Schema for creating a shopping list."""

    name: str = Field(default="My Shopping List", max_length=200)


class ShoppingListUpdate(BaseModel):
    """Schema for updating a shopping list."""

    name: str = Field(..., min_length=1, max_length=200)


class ShoppingListItemCreate(BaseModel):
    """Schema for adding an item to a shopping list."""

    ingredient_name: str = Field(..., min_length=1, max_length=200)
    quantity: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=50)
    recipe_id: Optional[int] = None


class ShoppingListItemUpdate(BaseModel):
    """Schema for updating a shopping list item."""

    ingredient_name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=50)
    is_checked: Optional[bool] = None


class ShoppingListItemOut(BaseModel):
    """Shopping list item response schema."""

    id: int
    shopping_list_id: int
    ingredient_name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    is_checked: bool
    recipe_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ShoppingListOut(BaseModel):
    """Shopping list response with items."""

    id: int
    user_id: int
    name: str
    created_at: datetime
    updated_at: datetime
    items: List[ShoppingListItemOut] = []

    model_config = {"from_attributes": True}


# ─── Moderation Schemas ──────────────────────────────────────────────────────


class ModerationAction(BaseModel):
    """Schema for performing a moderation action."""

    target_type: str = Field(..., description="'recipe' or 'review'")
    target_id: int = Field(..., description="ID of the target entity")
    action: str = Field(..., description="approve, reject, remove")
    reason: Optional[str] = None


class ModerationLogOut(BaseModel):
    """Moderation log response schema."""

    id: int
    admin_id: int
    target_type: str
    target_id: int
    action: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Pagination ──────────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: list
    total: int
    page: int
    page_size: int
    pages: int
