"""
Orders Router - Handle order creation and management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

router = APIRouter()


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    """Order line item"""
    product_id: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    total_price: float = Field(gt=0)


class Address(BaseModel):
    """Shipping/billing address"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str


class OrderCreate(BaseModel):
    """Order creation model"""
    user_id: str
    items: List[OrderItem]
    shipping_address: Address
    billing_address: Optional[Address] = None


class Order(BaseModel):
    """Order model"""
    id: str
    user_id: str
    status: OrderStatus
    items: List[OrderItem]
    subtotal: float
    tax: float
    shipping_cost: float
    total: float
    shipping_address: Address
    created_at: datetime
    updated_at: datetime


# Mock orders storage
mock_orders = []


@router.post("/", response_model=Order, status_code=201)
async def create_order(order: OrderCreate):
    """
    Create a new order

    Args:
        order: Order creation data

    Returns:
        Created order
    """
    # Calculate totals
    subtotal = sum(item.total_price for item in order.items)
    tax = subtotal * 0.08  # 8% tax
    shipping_cost = 9.99 if subtotal < 50 else 0.0  # Free shipping over $50
    total = subtotal + tax + shipping_cost

    new_order = {
        "id": f"ord_{len(mock_orders) + 1:05d}",
        "user_id": order.user_id,
        "status": OrderStatus.PENDING,
        "items": [item.model_dump() for item in order.items],
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "shipping_cost": round(shipping_cost, 2),
        "total": round(total, 2),
        "shipping_address": order.shipping_address.model_dump(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    mock_orders.append(new_order)
    return new_order


@router.get("/{order_id}", response_model=Order)
async def get_order(order_id: str):
    """
    Get order by ID

    Args:
        order_id: Order identifier

    Returns:
        Order details
    """
    order = next((o for o in mock_orders if o["id"] == order_id), None)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@router.get("/user/{user_id}", response_model=List[Order])
async def get_user_orders(user_id: str):
    """
    Get all orders for a user

    Args:
        user_id: User identifier

    Returns:
        List of user's orders
    """
    user_orders = [o for o in mock_orders if o["user_id"] == user_id]
    return user_orders


@router.patch("/{order_id}/status")
async def update_order_status(order_id: str, status: OrderStatus):
    """
    Update order status

    Args:
        order_id: Order identifier
        status: New order status

    Returns:
        Updated order
    """
    order = next((o for o in mock_orders if o["id"] == order_id), None)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order["status"] = status
    order["updated_at"] = datetime.utcnow()

    return order
