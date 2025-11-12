"""
Products Router - CRUD operations for products
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter()


class Product(BaseModel):
    """Product model"""
    id: str
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0)
    compare_at_price: Optional[float] = None
    sku: str
    stock_quantity: int = Field(ge=0)
    is_available: bool = True
    category: Optional[str] = None
    tags: List[str] = []
    images: List[str] = []
    created_at: datetime


class ProductCreate(BaseModel):
    """Product creation model"""
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0)
    compare_at_price: Optional[float] = None
    sku: str
    stock_quantity: int = Field(ge=0, default=0)
    category: Optional[str] = None
    tags: List[str] = []
    images: List[str] = []


# Mock data (in production, query from database)
mock_products = [
    {
        "id": "prod_001",
        "name": "Wireless Headphones Pro",
        "description": "Premium noise-cancelling wireless headphones",
        "price": 299.99,
        "compare_at_price": 399.99,
        "sku": "WHP-001",
        "stock_quantity": 50,
        "is_available": True,
        "category": "Electronics",
        "tags": ["audio", "wireless", "noise-cancelling"],
        "images": ["https://example.com/headphones.jpg"],
        "created_at": datetime.utcnow()
    },
    {
        "id": "prod_002",
        "name": "Smart Watch Ultra",
        "description": "Advanced fitness tracking smartwatch",
        "price": 449.99,
        "sku": "SWU-001",
        "stock_quantity": 30,
        "is_available": True,
        "category": "Electronics",
        "tags": ["wearable", "fitness", "smart"],
        "images": ["https://example.com/smartwatch.jpg"],
        "created_at": datetime.utcnow()
    }
]


@router.get("/", response_model=List[Product])
async def list_products(
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    List all products with optional filtering

    Args:
        category: Filter by category
        min_price: Minimum price filter
        max_price: Maximum price filter
        in_stock: Filter by stock availability
        search: Search in name and description
        skip: Number of items to skip
        limit: Number of items to return

    Returns:
        List of products
    """
    filtered_products = mock_products

    # Apply filters
    if category:
        filtered_products = [p for p in filtered_products if p.get("category") == category]

    if min_price is not None:
        filtered_products = [p for p in filtered_products if p.get("price", 0) >= min_price]

    if max_price is not None:
        filtered_products = [p for p in filtered_products if p.get("price", 0) <= max_price]

    if in_stock is not None:
        filtered_products = [
            p for p in filtered_products
            if p.get("is_available") and p.get("stock_quantity", 0) > 0
        ]

    if search:
        search_lower = search.lower()
        filtered_products = [
            p for p in filtered_products
            if search_lower in p.get("name", "").lower() or
               search_lower in p.get("description", "").lower()
        ]

    # Pagination
    return filtered_products[skip:skip + limit]


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """
    Get a single product by ID

    Args:
        product_id: Product identifier

    Returns:
        Product details
    """
    product = next((p for p in mock_products if p["id"] == product_id), None)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.post("/", response_model=Product, status_code=201)
async def create_product(product: ProductCreate):
    """
    Create a new product

    Args:
        product: Product creation data

    Returns:
        Created product
    """
    # In production, save to database
    new_product = {
        "id": f"prod_{len(mock_products) + 1:03d}",
        **product.model_dump(),
        "is_available": True,
        "created_at": datetime.utcnow()
    }

    mock_products.append(new_product)
    return new_product


@router.put("/{product_id}", response_model=Product)
async def update_product(product_id: str, product: ProductCreate):
    """
    Update an existing product

    Args:
        product_id: Product identifier
        product: Updated product data

    Returns:
        Updated product
    """
    existing_product = next((p for p in mock_products if p["id"] == product_id), None)

    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update fields
    for key, value in product.model_dump().items():
        existing_product[key] = value

    return existing_product


@router.delete("/{product_id}")
async def delete_product(product_id: str):
    """
    Delete a product

    Args:
        product_id: Product identifier

    Returns:
        Success message
    """
    global mock_products
    initial_length = len(mock_products)
    mock_products = [p for p in mock_products if p["id"] != product_id]

    if len(mock_products) == initial_length:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"status": "success", "message": "Product deleted"}


@router.get("/search/ai", response_model=List[Product])
async def ai_powered_search(query: str, limit: int = Query(5, ge=1, le=20)):
    """
    AI-powered semantic product search

    Args:
        query: Natural language search query
        limit: Maximum number of results

    Returns:
        Matching products
    """
    # TODO: Implement vector similarity search with embeddings
    # For now, use simple keyword matching
    query_lower = query.lower()
    results = [
        p for p in mock_products
        if query_lower in p.get("name", "").lower() or
           query_lower in p.get("description", "").lower() or
           any(query_lower in tag.lower() for tag in p.get("tags", []))
    ]

    return results[:limit]
