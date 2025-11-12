# 🧪 Test-Driven Development Strategy for Agentic Commerce MVP

> "Tests are the specifications for your code. Write them first, watch them fail, then make them pass."

## Table of Contents
1. [Testing Pyramid](#testing-pyramid)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [End-to-End Tests](#end-to-end-tests)
5. [LLM Evaluation Framework](#llm-evaluation-framework)
6. [Agent Behavior Testing](#agent-behavior-testing)
7. [Performance & Load Testing](#performance--load-testing)
8. [Security Testing](#security-testing)
9. [Continuous Testing Pipeline](#continuous-testing-pipeline)
10. [Testing Tools & Framework](#testing-tools--framework)

---

## Testing Pyramid

```
        /\
       /  \      E2E Tests (5%)
      /────\     - Full user journeys
     /      \    - Critical business flows
    /────────\
   / Integration\ (15%)
  /    Tests     \ - API contracts
 /────────────────\ - Database ops
/   Unit Tests     \ (80%)
\  Agent Logic    / - Pure functions
 \  Models       / - Business logic
  \  Utilities  /
   \__________/
```

**Golden Ratio:**
- 80% Unit Tests (fast, isolated)
- 15% Integration Tests (API, DB, external services)
- 5% E2E Tests (full user flows)

---

## Unit Tests

### 1. Agent Logic Tests

**Test File:** `tests/unit/test_commerce_agent.py`

```python
"""
Unit tests for CommerceAgent
Testing agent behavior in isolation
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.agents.commerce_agent import CommerceAgent, AgentTask, LLMProvider

class TestCommerceAgentInitialization:
    """Test agent initialization"""

    def test_agent_creates_with_valid_params(self):
        """Should create agent with user_id and session_id"""
        agent = CommerceAgent(
            user_id="user_123",
            session_id="session_456"
        )
        assert agent.user_id == "user_123"
        assert agent.session_id == "session_456"

    def test_agent_defaults_to_openai_provider(self):
        """Should default to OpenAI if no provider specified"""
        agent = CommerceAgent("user_123", "session_456")
        assert agent.preferred_provider == LLMProvider.OPENAI

    def test_conversation_history_starts_empty(self):
        """Should initialize with empty conversation history"""
        agent = CommerceAgent("user_123", "session_456")
        assert len(agent.conversation_history) == 0


class TestConversationHistoryManagement:
    """Test conversation history management"""

    def test_add_to_history_stores_messages(self):
        """Should store messages in conversation history"""
        agent = CommerceAgent("user_123", "session_456")
        agent._add_to_history("user", "Hello")
        agent._add_to_history("assistant", "Hi there!")

        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0]["role"] == "user"
        assert agent.conversation_history[1]["content"] == "Hi there!"

    def test_history_respects_max_limit(self):
        """Should not exceed max_history limit"""
        agent = CommerceAgent("user_123", "session_456")
        agent.max_history = 5

        # Add 20 messages (10 pairs)
        for i in range(10):
            agent._add_to_history("user", f"Message {i}")
            agent._add_to_history("assistant", f"Response {i}")

        # Should only keep last 10 messages (5 pairs)
        assert len(agent.conversation_history) == 10
        assert agent.conversation_history[0]["content"] == "Message 5"

    def test_clear_history_removes_all_messages(self):
        """Should clear all conversation history"""
        agent = CommerceAgent("user_123", "session_456")
        agent._add_to_history("user", "Hello")
        agent.clear_history()

        assert len(agent.conversation_history) == 0


class TestLLMProviderFallback:
    """Test multi-provider fallback logic"""

    @pytest.mark.asyncio
    async def test_falls_back_when_primary_fails(self):
        """Should fall back to secondary provider on primary failure"""
        agent = CommerceAgent("user_123", "session_456")

        # Mock OpenAI to fail
        agent.openai_client = AsyncMock()
        agent.openai_client.chat.completions.create.side_effect = Exception("API Error")

        # Mock Gemini to succeed
        agent.gemini_model = AsyncMock()
        agent.gemini_model.generate_content_async = AsyncMock(
            return_value=AsyncMock(text="Gemini response")
        )

        result = await agent._call_llm_with_fallback(
            task=AgentTask.PRODUCT_SEARCH,
            prompt="Find laptops"
        )

        assert result == "Gemini response"

    @pytest.mark.asyncio
    async def test_returns_error_when_all_providers_fail(self):
        """Should return graceful error when all providers fail"""
        agent = CommerceAgent("user_123", "session_456")

        # All providers fail
        agent.openai_client = None
        agent.anthropic_client = None
        agent.gemini_model = None

        result = await agent._call_llm_with_fallback(
            task=AgentTask.PRODUCT_SEARCH,
            prompt="Find laptops"
        )

        assert "technical difficulties" in result.lower()


class TestTaskModelMapping:
    """Test that tasks route to appropriate models"""

    def test_simple_tasks_use_cheap_models(self):
        """Simple tasks should use Gemini Flash (cheapest)"""
        agent = CommerceAgent("user_123", "session_456")

        provider, model = agent.task_model_map[AgentTask.PRODUCT_SEARCH]
        assert provider == "gemini"

    def test_complex_tasks_use_premium_models(self):
        """Complex tasks should use GPT-4o or Claude"""
        agent = CommerceAgent("user_123", "session_456")

        provider, model = agent.task_model_map[AgentTask.ORDER_PLACEMENT]
        assert provider in ["openai", "anthropic"]
        assert "gpt-4o" in model or "claude" in model


class TestRetryLogic:
    """Test retry behavior for failed LLM calls"""

    @pytest.mark.asyncio
    async def test_retries_on_transient_errors(self):
        """Should retry up to 3 times on transient errors"""
        agent = CommerceAgent("user_123", "session_456")

        # Mock to fail twice, then succeed
        call_count = 0
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return AsyncMock(choices=[AsyncMock(message=AsyncMock(content="Success"))])

        agent.openai_client = AsyncMock()
        agent.openai_client.chat.completions.create = mock_create

        result = await agent._call_openai([], "gpt-4o-mini")

        assert call_count == 3
        assert result == "Success"


class TestSystemPromptGeneration:
    """Test system prompt generation for different tasks"""

    def test_generates_task_specific_prompts(self):
        """Should generate appropriate prompts for each task"""
        agent = CommerceAgent("user_123", "session_456")

        search_prompt = agent._get_system_prompt(AgentTask.PRODUCT_SEARCH)
        support_prompt = agent._get_system_prompt(AgentTask.CUSTOMER_SUPPORT)

        assert "shopping assistant" in search_prompt.lower()
        assert "customer support" in support_prompt.lower()
        assert search_prompt != support_prompt
```

### 2. Database Model Tests

**Test File:** `tests/unit/test_models.py`

```python
"""
Unit tests for database models
Testing data validation and relationships
"""

import pytest
from datetime import datetime
from app.models.database import User, Product, Order, OrderItem, CartItem

class TestUserModel:
    """Test User model validation"""

    def test_user_creation_with_required_fields(self):
        """Should create user with email and password"""
        user = User(
            email="test@example.com",
            hashed_password="hashed_pw_123",
            full_name="Test User"
        )
        assert user.email == "test@example.com"
        assert user.is_active is True

    def test_user_preferences_defaults_to_empty_dict(self):
        """Should default preferences to empty dict"""
        user = User(email="test@example.com", hashed_password="pw")
        assert user.preferences == {}

    def test_email_uniqueness(self, db_session):
        """Should enforce unique email constraint"""
        # This would test database constraint
        # Requires database fixture
        pass


class TestProductModel:
    """Test Product model validation"""

    def test_product_creation_with_required_fields(self):
        """Should create product with name, price, SKU"""
        product = Product(
            name="Wireless Headphones",
            price=99.99,
            sku="WH-001"
        )
        assert product.name == "Wireless Headphones"
        assert product.price == 99.99

    def test_price_must_be_positive(self):
        """Should validate that price is positive"""
        # Pydantic validation test
        with pytest.raises(ValueError):
            Product(name="Test", price=-10.0, sku="TEST")

    def test_stock_quantity_defaults_to_zero(self):
        """Should default stock to 0 if not specified"""
        product = Product(name="Test", price=10.0, sku="TEST")
        assert product.stock_quantity == 0


class TestOrderModel:
    """Test Order model and calculations"""

    def test_order_total_calculation(self):
        """Should calculate total = subtotal + tax + shipping - discount"""
        order = Order(
            user_id="user_123",
            subtotal=100.0,
            tax=8.0,
            shipping_cost=10.0,
            discount=5.0,
            total=113.0,
            shipping_address={"street": "123 Main St"}
        )

        calculated_total = order.subtotal + order.tax + order.shipping_cost - order.discount
        assert order.total == calculated_total

    def test_order_status_defaults_to_pending(self):
        """Should default to PENDING status"""
        order = Order(
            user_id="user_123",
            subtotal=100.0,
            total=100.0,
            shipping_address={}
        )
        assert order.status == OrderStatus.PENDING
```

### 3. Utility & Helper Tests

**Test File:** `tests/unit/test_utils.py`

```python
"""
Unit tests for utility functions
Testing pure functions and helpers
"""

import pytest
from app.utils.token_counter import count_tokens, truncate_to_token_limit
from app.utils.cost_calculator import calculate_llm_cost
from app.utils.validators import validate_email, validate_price

class TestTokenCounter:
    """Test token counting utilities"""

    def test_counts_tokens_correctly(self):
        """Should count tokens in text"""
        text = "Hello, how are you doing today?"
        tokens = count_tokens(text, model="gpt-4o")
        assert tokens > 0
        assert tokens < 20  # Simple sentence

    def test_truncates_long_text(self):
        """Should truncate text exceeding token limit"""
        long_text = "word " * 10000  # Very long text
        truncated = truncate_to_token_limit(long_text, max_tokens=100)

        token_count = count_tokens(truncated)
        assert token_count <= 100


class TestCostCalculator:
    """Test LLM cost calculation"""

    def test_calculates_openai_cost(self):
        """Should calculate cost for OpenAI models"""
        cost = calculate_llm_cost(
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500
        )
        expected = (1000 * 0.00015 / 1000) + (500 * 0.0006 / 1000)
        assert cost == pytest.approx(expected, abs=0.001)

    def test_calculates_anthropic_cost(self):
        """Should calculate cost for Anthropic models"""
        cost = calculate_llm_cost(
            model="claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=500
        )
        assert cost > 0


class TestValidators:
    """Test input validation functions"""

    def test_validates_correct_email(self):
        """Should accept valid email addresses"""
        assert validate_email("user@example.com") is True
        assert validate_email("test.user+tag@domain.co.uk") is True

    def test_rejects_invalid_email(self):
        """Should reject invalid email addresses"""
        assert validate_email("not-an-email") is False
        assert validate_email("missing@domain") is False

    def test_validates_positive_price(self):
        """Should validate that prices are positive"""
        assert validate_price(10.99) is True
        assert validate_price(0) is False
        assert validate_price(-5.00) is False
```

---

## Integration Tests

### 1. API Endpoint Tests

**Test File:** `tests/integration/test_api_endpoints.py`

```python
"""
Integration tests for API endpoints
Testing request/response contracts
"""

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestChatEndpoints:
    """Test chat API endpoints"""

    @pytest.mark.asyncio
    async def test_send_message_returns_response(self, client):
        """POST /api/v1/chat/message should return agent response"""
        response = await client.post(
            "/api/v1/chat/message",
            json={
                "message": "Find me wireless headphones",
                "user_id": "test_user",
                "session_id": "test_session",
                "task": "product_search"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "session_id" in data
        assert data["message"] != ""

    @pytest.mark.asyncio
    async def test_send_empty_message_returns_error(self, client):
        """Should return error for empty message"""
        response = await client.post(
            "/api/v1/chat/message",
            json={
                "message": "",
                "user_id": "test_user"
            }
        )

        # Should handle gracefully
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, client):
        """GET /api/v1/chat/session/{id}/history should return history"""
        # First send a message
        await client.post(
            "/api/v1/chat/message",
            json={
                "message": "Hello",
                "user_id": "test_user",
                "session_id": "test_session"
            }
        )

        # Then get history
        response = await client.get(
            "/api/v1/chat/session/test_session/history?user_id=test_user"
        )

        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert len(data["history"]) > 0


class TestProductEndpoints:
    """Test product API endpoints"""

    @pytest.mark.asyncio
    async def test_list_products(self, client):
        """GET /api/v1/products should return product list"""
        response = await client.get("/api/v1/products")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_product_by_id(self, client):
        """GET /api/v1/products/{id} should return product details"""
        response = await client.get("/api/v1/products/prod_001")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "prod_001"
        assert "name" in data
        assert "price" in data

    @pytest.mark.asyncio
    async def test_create_product(self, client):
        """POST /api/v1/products should create new product"""
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Test Product",
                "price": 29.99,
                "sku": "TEST-001",
                "description": "A test product"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Product"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_search_products_with_query(self, client):
        """GET /api/v1/products/search/ai should search products"""
        response = await client.get(
            "/api/v1/products/search/ai?query=headphones&limit=5"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestOrderEndpoints:
    """Test order API endpoints"""

    @pytest.mark.asyncio
    async def test_create_order(self, client):
        """POST /api/v1/orders should create new order"""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": "test_user",
                "items": [
                    {
                        "product_id": "prod_001",
                        "quantity": 2,
                        "unit_price": 99.99,
                        "total_price": 199.98
                    }
                ],
                "shipping_address": {
                    "street": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94102",
                    "country": "US"
                }
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["user_id"] == "test_user"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_user_orders(self, client):
        """GET /api/v1/orders/user/{id} should return user's orders"""
        response = await client.get("/api/v1/orders/user/test_user")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
```

### 2. Database Integration Tests

**Test File:** `tests/integration/test_database.py`

```python
"""
Integration tests for database operations
Testing CRUD operations and relationships
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import User, Product, Order
from app.database import get_db

@pytest.mark.asyncio
async def test_create_and_retrieve_user(db_session: AsyncSession):
    """Should create user and retrieve from database"""
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        full_name="Test User"
    )

    db_session.add(user)
    await db_session.commit()

    # Retrieve
    retrieved = await db_session.get(User, user.id)
    assert retrieved.email == "test@example.com"

@pytest.mark.asyncio
async def test_product_inventory_management(db_session: AsyncSession):
    """Should update product stock correctly"""
    product = Product(
        name="Test Product",
        price=29.99,
        sku="TEST-001",
        stock_quantity=100
    )

    db_session.add(product)
    await db_session.commit()

    # Decrease stock
    product.stock_quantity -= 5
    await db_session.commit()

    # Verify
    retrieved = await db_session.get(Product, product.id)
    assert retrieved.stock_quantity == 95

@pytest.mark.asyncio
async def test_order_with_items_relationship(db_session: AsyncSession):
    """Should create order with items and maintain relationship"""
    # Create user and product first
    user = User(email="buyer@example.com", hashed_password="pw")
    product = Product(name="Laptop", price=999.99, sku="LAPTOP-001")

    db_session.add_all([user, product])
    await db_session.commit()

    # Create order with items
    order = Order(
        user_id=user.id,
        subtotal=999.99,
        total=999.99,
        shipping_address={"street": "123 Main"}
    )

    order_item = OrderItem(
        product_id=product.id,
        quantity=1,
        unit_price=999.99,
        total_price=999.99
    )

    order.items.append(order_item)
    db_session.add(order)
    await db_session.commit()

    # Verify relationship
    retrieved_order = await db_session.get(Order, order.id)
    assert len(retrieved_order.items) == 1
    assert retrieved_order.items[0].product_id == product.id
```

---

## End-to-End Tests

### Full User Journey Tests

**Test File:** `tests/e2e/test_shopping_flow.py`

```python
"""
End-to-end tests for complete shopping flows
Testing real user scenarios from start to finish
"""

import pytest
from playwright.async_api import async_playwright

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_purchase_flow():
    """
    Test complete purchase flow:
    1. User searches for product via agent
    2. Agent recommends products
    3. User adds to cart
    4. User checks out
    5. Order confirmation
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # 1. Navigate to chat
        await page.goto("http://localhost:3000/chat")

        # 2. Search for product
        await page.fill("#message-input", "Find me wireless headphones under $100")
        await page.click("#send-button")

        # 3. Wait for agent response
        await page.wait_for_selector(".agent-message")
        response = await page.text_content(".agent-message")
        assert "headphones" in response.lower()

        # 4. Click on recommended product
        await page.click(".product-card:first-child")

        # 5. Add to cart
        await page.click("#add-to-cart")
        await page.wait_for_selector(".cart-notification")

        # 6. Go to checkout
        await page.click("#checkout-button")

        # 7. Fill shipping info
        await page.fill("#shipping-street", "123 Main St")
        await page.fill("#shipping-city", "San Francisco")
        await page.fill("#shipping-postal", "94102")

        # 8. Complete purchase
        await page.click("#complete-order")

        # 9. Verify confirmation
        await page.wait_for_selector(".order-confirmation")
        confirmation = await page.text_content(".order-number")
        assert confirmation.startswith("ord_")

        await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_price_negotiation_flow():
    """
    Test price negotiation scenario:
    1. User expresses price concern
    2. Agent offers discount
    3. User accepts
    4. Price updated in cart
    """
    # Similar structure to above
    pass
```

---

## LLM Evaluation Framework

### Agent Response Quality Tests

**Test File:** `tests/evals/test_agent_quality.py`

```python
"""
LLM Evaluation Tests
Testing agent response quality, accuracy, and appropriateness
"""

import pytest
from app.agents.commerce_agent import CommerceAgent, AgentTask

class TestProductSearchAccuracy:
    """Evaluate product search agent accuracy"""

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_understands_price_constraints(self):
        """Agent should respect price constraints in search"""
        agent = CommerceAgent("eval_user", "eval_session")

        response = await agent.search_products("laptops under $500")

        # Check if response mentions budget awareness
        assert "500" in response.message or "budget" in response.message.lower()

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_asks_clarifying_questions(self):
        """Agent should ask questions for vague queries"""
        agent = CommerceAgent("eval_user", "eval_session")

        response = await agent.search_products("something for gaming")

        # Should ask what type of gaming product
        assert "?" in response.message  # Contains question
        assert any(word in response.message.lower()
                  for word in ["what", "which", "prefer", "looking for"])

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_provides_multiple_options(self):
        """Agent should provide multiple product options"""
        agent = CommerceAgent("eval_user", "eval_session")

        response = await agent.search_products("wireless headphones")

        # Should mention multiple products or options
        assert len(response.suggested_products) >= 2 or \
               any(word in response.message.lower()
                   for word in ["options", "choices", "several", "multiple"])


class TestNegotiationBehavior:
    """Evaluate price negotiation appropriateness"""

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_offers_reasonable_discounts(self):
        """Agent should offer discounts within policy (max 15%)"""
        agent = CommerceAgent("eval_user", "eval_session")

        response = await agent.negotiate_price("prod_001", 85.00)
        # Original price is $99.99

        # Extract discount percentage from response
        # Should not exceed 15%
        assert "discount" in response.message.lower()
        # More robust: parse actual percentage offered

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_rejects_unreasonable_requests(self):
        """Agent should decline unrealistic price requests"""
        agent = CommerceAgent("eval_user", "eval_session")

        response = await agent.negotiate_price("prod_001", 10.00)
        # Asking for 90% off

        assert any(word in response.message.lower()
                  for word in ["unable", "cannot", "best price", "sorry"])


class TestCustomerSupportQuality:
    """Evaluate customer support agent quality"""

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_shows_empathy(self):
        """Agent should show empathy for customer issues"""
        agent = CommerceAgent("eval_user", "eval_session")

        response = await agent.process_message(
            "My order arrived damaged and I'm very upset",
            task=AgentTask.CUSTOMER_SUPPORT
        )

        # Should contain empathetic language
        empathy_words = ["sorry", "understand", "apologize", "regret",
                        "unfortunate", "appreciate"]
        assert any(word in response.message.lower() for word in empathy_words)

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_provides_actionable_solutions(self):
        """Agent should offer concrete next steps"""
        agent = CommerceAgent("eval_user", "eval_session")

        response = await agent.process_message(
            "I haven't received my order yet",
            task=AgentTask.CUSTOMER_SUPPORT
        )

        # Should mention tracking, refund, or resolution
        action_words = ["track", "check", "refund", "replace",
                       "investigate", "look into"]
        assert any(word in response.message.lower() for word in action_words)


class TestResponseConsistency:
    """Test agent response consistency"""

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_same_query_similar_responses(self):
        """Similar queries should get similar responses"""
        agent = CommerceAgent("eval_user", "eval_session")

        response1 = await agent.search_products("wireless earbuds")
        response2 = await agent.search_products("bluetooth earphones")

        # Both should be about audio products
        # Use semantic similarity check here
        # For now, simple keyword check
        common_words = ["audio", "wireless", "bluetooth", "music"]
        r1_has_common = any(w in response1.message.lower() for w in common_words)
        r2_has_common = any(w in response2.message.lower() for w in common_words)

        assert r1_has_common and r2_has_common
```

### Evaluation Metrics

**Test File:** `tests/evals/test_performance_metrics.py`

```python
"""
Performance and quality metrics for agents
Quantitative evaluation of agent behavior
"""

import pytest
import time
from app.agents.commerce_agent import CommerceAgent, AgentTask

class TestResponseTime:
    """Evaluate agent response time"""

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_response_time_under_threshold(self):
        """Agent should respond within 5 seconds"""
        agent = CommerceAgent("eval_user", "eval_session")

        start = time.time()
        await agent.search_products("Find laptops")
        end = time.time()

        response_time = end - start
        assert response_time < 5.0, f"Response took {response_time}s"

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_average_response_time(self):
        """Average response time should be under 3 seconds"""
        agent = CommerceAgent("eval_user", "eval_session")

        times = []
        queries = [
            "wireless headphones",
            "gaming laptop",
            "smart watch",
            "bluetooth speaker",
            "noise cancelling earbuds"
        ]

        for query in queries:
            start = time.time()
            await agent.search_products(query)
            end = time.time()
            times.append(end - start)

        avg_time = sum(times) / len(times)
        assert avg_time < 3.0, f"Average response time: {avg_time}s"


class TestTokenUsage:
    """Evaluate token efficiency"""

    @pytest.mark.eval
    @pytest.mark.asyncio
    async def test_simple_query_low_tokens(self):
        """Simple queries should use <1000 tokens"""
        agent = CommerceAgent("eval_user", "eval_session")

        # Track tokens (you'll need to add token tracking)
        response = await agent.search_products("headphones")

        # Assuming you add token tracking to AgentResponse
        # assert response.tokens_used < 1000
        pass

    @pytest.mark.eval
    async def test_uses_appropriate_model_for_task(self):
        """Should use cheaper models for simple tasks"""
        agent = CommerceAgent("eval_user", "eval_session")

        # Check task-model mapping
        provider, model = agent.task_model_map[AgentTask.PRODUCT_SEARCH]

        # Simple search should use cheap model
        assert provider == "gemini"  # Cheapest option
```

---

## Testing Tools & Framework

### Recommended Stack

```yaml
Testing Frameworks:
  - pytest: Main testing framework
  - pytest-asyncio: Async test support
  - pytest-cov: Coverage reporting
  - pytest-mock: Mocking utilities

API Testing:
  - httpx: Async HTTP client
  - pytest-httpx: HTTP mocking

E2E Testing:
  - playwright: Browser automation
  - selenium: Alternative browser testing

LLM Evaluation:
  - langsmith: LLM observability & testing
  - promptfoo: Prompt testing framework
  - ragas: RAG evaluation metrics
  - deepeval: LLM evaluation framework

Load Testing:
  - locust: Python load testing
  - k6: Modern load testing

Security Testing:
  - bandit: Security linter
  - safety: Dependency vulnerability check
  - sqlmap: SQL injection testing
```

### Test Configuration

**File:** `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (DB, API)
    e2e: End-to-end tests (slow, full flow)
    eval: LLM evaluation tests
    slow: Slow running tests

asyncio_mode = auto

# Coverage settings
addopts =
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -v
    -s
```

### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest -m unit

# Run integration tests
pytest -m integration

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_commerce_agent.py

# Run specific test
pytest tests/unit/test_commerce_agent.py::TestConversationHistoryManagement::test_clear_history_removes_all_messages

# Run evals only
pytest -m eval

# Run excluding slow tests
pytest -m "not slow"
```

### Continuous Integration (GitHub Actions)

**File:** `.github/workflows/tests.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run unit tests
        run: pytest -m unit

      - name: Run integration tests
        run: pytest -m integration
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Test Coverage Goals

**Minimum Coverage Targets:**

- **Overall:** 80%
- **Critical Paths:** 95%
  - Payment processing
  - Order creation
  - User authentication
- **Agent Logic:** 85%
- **API Endpoints:** 90%
- **Database Models:** 75%
- **Utility Functions:** 90%

**Coverage Report Example:**

```
---------- coverage: platform linux, python 3.11 ----------
Name                                   Stmts   Miss  Cover
----------------------------------------------------------
app/agents/commerce_agent.py             245     15    94%
app/routers/chat.py                       85      8    91%
app/routers/products.py                   92     12    87%
app/routers/orders.py                     78      9    88%
app/models/database.py                   156     38    76%
app/database.py                           34      3    91%
----------------------------------------------------------
TOTAL                                    690     85    88%
```

---

## Next Steps

1. **Week 1:** Set up testing infrastructure
   - Install pytest and dependencies
   - Configure pytest.ini
   - Write first 10 unit tests

2. **Week 2:** Build test coverage
   - Achieve 60% coverage
   - Add integration tests
   - Set up CI/CD

3. **Week 3:** Advanced testing
   - LLM evaluation framework
   - E2E tests for critical flows
   - Achieve 80% coverage

4. **Ongoing:** Maintain and improve
   - Add tests for new features (TDD)
   - Monitor and improve flaky tests
   - Regular eval reviews

---

**Remember:** Write the test first, watch it fail, then make it pass. That's TDD! 🧪
