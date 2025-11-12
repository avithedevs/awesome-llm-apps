"""
Database Models for Agentic Commerce MVP
SQLAlchemy ORM models for PostgreSQL
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
import uuid

Base = declarative_base()


def generate_uuid():
    """Generate UUID for primary keys"""
    return str(uuid.uuid4())


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Preferences
    preferences = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    orders = relationship("Order", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")
    agent_sessions = relationship("AgentSession", back_populates="user")


class Product(Base):
    """Product catalog model"""
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    compare_at_price = Column(Float, nullable=True)  # Original price for discounts

    # Inventory
    sku = Column(String, unique=True, nullable=False, index=True)
    stock_quantity = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)

    # Categorization
    category = Column(String, nullable=True, index=True)
    tags = Column(JSON, default=list)  # ["electronics", "headphones"]

    # Media
    images = Column(JSON, default=list)  # List of image URLs

    # Metadata
    metadata = Column(JSON, default=dict)  # Flexible field for additional data

    # SEO
    slug = Column(String, unique=True, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")
    cart_items = relationship("CartItem", back_populates="product")


class Order(Base):
    """Order model"""
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Order details
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, index=True)
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    total = Column(Float, nullable=False)

    # Shipping information
    shipping_address = Column(JSON, nullable=False)
    billing_address = Column(JSON, nullable=True)

    # Payment
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_method = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True, unique=True)

    # Agent information
    agent_session_id = Column(String, ForeignKey("agent_sessions.id"), nullable=True)
    agent_notes = Column(JSON, default=dict)  # Store agent interactions/decisions

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    agent_session = relationship("AgentSession", back_populates="orders")


class OrderItem(Base):
    """Order line items"""
    __tablename__ = "order_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)

    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)  # Price at time of purchase
    total_price = Column(Float, nullable=False)

    # Snapshot of product details at purchase time
    product_snapshot = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class CartItem(Base):
    """Shopping cart items"""
    __tablename__ = "cart_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)

    quantity = Column(Integer, nullable=False, default=1)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")


class AgentSession(Base):
    """Agent interaction session tracking"""
    __tablename__ = "agent_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Session metadata
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # Agent information
    agent_type = Column(String, nullable=False)  # "commerce", "support", etc.
    provider_used = Column(String, nullable=True)  # "openai", "anthropic", etc.

    # Conversation
    conversation_history = Column(JSON, default=list)
    total_messages = Column(Integer, default=0)

    # Performance metrics
    total_tokens_used = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    # Outcomes
    tasks_completed = Column(JSON, default=list)
    products_viewed = Column(JSON, default=list)
    satisfaction_score = Column(Float, nullable=True)  # 0-5 rating

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="agent_sessions")
    orders = relationship("Order", back_populates="agent_session")


class AgentLog(Base):
    """Detailed logging of agent actions for debugging and optimization"""
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("agent_sessions.id"), nullable=False)

    # Log details
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String, nullable=False, index=True)  # "llm_call", "tool_use", "error"

    # Event data
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Performance
    execution_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)

    # Provider info
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)


# Database initialization helper
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

def get_database_url():
    """Get database URL from environment"""
    return os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/agentic_commerce")


def create_tables():
    """Create all tables in the database"""
    database_url = get_database_url()
    engine = create_engine(database_url, echo=True)
    Base.metadata.create_all(engine)
    print("All tables created successfully!")


if __name__ == "__main__":
    # Create tables when run directly
    create_tables()
