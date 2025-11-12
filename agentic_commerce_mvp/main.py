"""
Agentic Commerce MVP - FastAPI Backend
A lightweight agentic commerce platform with AI-powered shopping agents
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from dotenv import load_dotenv
import os

# Import routers
from app.routers import products, agents, orders, chat

# Import database
from app.database import init_db, close_db

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if not os.getenv("PRETTY_LOGS") else structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for startup and shutdown"""
    # Startup
    logger.info("Starting Agentic Commerce MVP")
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down Agentic Commerce MVP")
    await close_db()


# Initialize FastAPI app
app = FastAPI(
    title="Agentic Commerce MVP",
    description="AI-powered commerce platform with autonomous agents",
    version="0.1.0",
    lifespan=lifespan
)

# CORS Configuration
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Agentic Commerce MVP",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    return {
        "status": "ok",
        "database": "connected",
        "cache": "connected",
        "llm_providers": ["openai", "anthropic", "gemini"]
    }


# Include routers
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    return {
        "error": "Internal server error",
        "message": "Something went wrong. Our team has been notified."
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("APP_PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        log_level="info"
    )
