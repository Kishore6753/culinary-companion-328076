"""
Culinary Companion API - Main Application Entry Point.

FastAPI application with OpenAPI/Swagger documentation, CORS middleware,
and all domain routers registered.

Flow: ApplicationStartupFlow
Entrypoint: app (FastAPI instance)
"""
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Import routers after env is loaded so database config reads env vars
from src.api.routers.admin import router as admin_router  # noqa: E402
from src.api.routers.auth import router as auth_router  # noqa: E402
from src.api.routers.categories import router as categories_router  # noqa: E402
from src.api.routers.cuisines import router as cuisines_router  # noqa: E402
from src.api.routers.favorites import router as favorites_router  # noqa: E402
from src.api.routers.ratings import router as ratings_router  # noqa: E402
from src.api.routers.recipes import router as recipes_router  # noqa: E402
from src.api.routers.reviews import router as reviews_router  # noqa: E402
from src.api.routers.shopping_lists import router as shopping_lists_router  # noqa: E402

# OpenAPI tag metadata for organized Swagger docs
openapi_tags = [
    {"name": "Health", "description": "Health check endpoints"},
    {"name": "Authentication", "description": "User registration, login, and profile management"},
    {"name": "Recipes", "description": "Browse, search, create, update, and delete recipes"},
    {"name": "Categories", "description": "Recipe categories management"},
    {"name": "Cuisines", "description": "Cuisine types management"},
    {"name": "Favorites", "description": "User favorite recipes management"},
    {"name": "Ratings", "description": "Recipe ratings (1-5 stars)"},
    {"name": "Reviews", "description": "Recipe reviews and comments"},
    {"name": "Shopping Lists", "description": "Shopping list and item management"},
    {"name": "Admin / Moderation", "description": "Admin content moderation tools"},
]

app = FastAPI(
    title="Culinary Companion API",
    description=(
        "A fullstack food recipe application API featuring recipe browsing and search, "
        "organized by categories and cuisines, with detailed ingredients and steps, "
        "favoriting, shopping list management, user accounts, personal recipe creation/editing, "
        "ratings and reviews, and basic admin content moderation."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS configuration
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:4000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,PATCH,OPTIONS").split(","),
    allow_headers=os.getenv("ALLOWED_HEADERS", "Content-Type,Authorization,X-Requested-With").split(","),
    max_age=int(os.getenv("CORS_MAX_AGE", "3600")),
)

# Register all routers
app.include_router(auth_router)
app.include_router(recipes_router)
app.include_router(categories_router)
app.include_router(cuisines_router)
app.include_router(favorites_router)
app.include_router(ratings_router)
app.include_router(reviews_router)
app.include_router(shopping_lists_router)
app.include_router(admin_router)


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health check", description="Returns API health status.")
def health_check():
    """Health check endpoint.

    Returns:
        JSON with status message.
    """
    return {"status": "healthy", "service": "culinary-companion-api", "version": "1.0.0"}


# PUBLIC_INTERFACE
@app.get(
    "/healthz",
    tags=["Health"],
    summary="Kubernetes-style health check",
    description="Returns simple OK for liveness probes.",
)
def healthz():
    """Liveness probe endpoint.

    Returns:
        JSON with ok status.
    """
    return {"status": "ok"}


logger.info("Culinary Companion API initialized with %d routers", 9)
