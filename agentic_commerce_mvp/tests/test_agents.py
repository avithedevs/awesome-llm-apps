"""
Unit tests for Commerce Agent
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.commerce_agent import CommerceAgent, AgentTask, LLMProvider, AgentResponse


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-123")


@pytest.fixture
def commerce_agent(mock_env_vars):
    """Create a commerce agent instance for testing"""
    return CommerceAgent(
        user_id="test_user",
        session_id="test_session",
        preferred_provider=LLMProvider.OPENAI
    )


@pytest.mark.asyncio
async def test_agent_initialization(commerce_agent):
    """Test that agent initializes correctly"""
    assert commerce_agent.user_id == "test_user"
    assert commerce_agent.session_id == "test_session"
    assert commerce_agent.preferred_provider == LLMProvider.OPENAI
    assert len(commerce_agent.conversation_history) == 0


@pytest.mark.asyncio
async def test_conversation_history_limit(commerce_agent):
    """Test that conversation history is limited to max_history"""
    # Add many messages
    for i in range(15):
        commerce_agent._add_to_history("user", f"Message {i}")
        commerce_agent._add_to_history("assistant", f"Response {i}")

    # Should only keep last max_history * 2 messages
    assert len(commerce_agent.conversation_history) <= commerce_agent.max_history * 2


@pytest.mark.asyncio
@patch('app.agents.commerce_agent.AsyncOpenAI')
async def test_product_search(mock_openai, commerce_agent):
    """Test product search functionality"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I found some great wireless headphones for you!"

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    commerce_agent.openai_client = mock_client

    # Test product search
    result = await commerce_agent.search_products("wireless headphones")

    assert result.success is True
    assert "headphones" in result.message.lower()
    assert len(commerce_agent.conversation_history) == 2  # user + assistant


@pytest.mark.asyncio
@patch('app.agents.commerce_agent.AsyncOpenAI')
async def test_llm_fallback_strategy(mock_openai, commerce_agent):
    """Test that agent falls back to alternative providers on failure"""
    # Make OpenAI fail
    commerce_agent.openai_client.chat.completions.create = AsyncMock(
        side_effect=Exception("OpenAI API error")
    )

    # Mock Gemini to succeed
    mock_gemini = AsyncMock()
    mock_gemini.generate_content_async = AsyncMock(
        return_value=MagicMock(text="Gemini response")
    )
    commerce_agent.gemini_model = mock_gemini

    result = await commerce_agent.process_message(
        "Find me a laptop",
        task=AgentTask.PRODUCT_SEARCH
    )

    # Should succeed with fallback
    assert result.success is True


@pytest.mark.asyncio
async def test_clear_history(commerce_agent):
    """Test clearing conversation history"""
    # Add some messages
    commerce_agent._add_to_history("user", "Hello")
    commerce_agent._add_to_history("assistant", "Hi there!")

    assert len(commerce_agent.conversation_history) == 2

    # Clear history
    commerce_agent.clear_history()

    assert len(commerce_agent.conversation_history) == 0


@pytest.mark.asyncio
@patch('app.agents.commerce_agent.AsyncOpenAI')
async def test_negotiation_task(mock_openai, commerce_agent):
    """Test price negotiation functionality"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I can offer you a 10% discount on this product."

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    commerce_agent.openai_client = mock_client

    result = await commerce_agent.negotiate_price("prod_123", 89.99)

    assert result.success is True
    assert "discount" in result.message.lower()


def test_system_prompt_generation(commerce_agent):
    """Test system prompt generation for different tasks"""
    search_prompt = commerce_agent._get_system_prompt(AgentTask.PRODUCT_SEARCH)
    negotiation_prompt = commerce_agent._get_system_prompt(AgentTask.PRICE_NEGOTIATION)

    assert "shopping assistant" in search_prompt.lower()
    assert "negotiation" in negotiation_prompt.lower()
    assert search_prompt != negotiation_prompt


@pytest.mark.asyncio
@patch('app.agents.commerce_agent.AsyncOpenAI')
async def test_error_handling(mock_openai, commerce_agent):
    """Test that errors are handled gracefully"""
    # Make all providers fail
    commerce_agent.openai_client = None
    commerce_agent.anthropic_client = None
    commerce_agent.gemini_model = None

    result = await commerce_agent.process_message(
        "Find products",
        task=AgentTask.PRODUCT_SEARCH
    )

    # Should return graceful error message
    assert result.success is False
    assert "trouble" in result.message.lower() or "error" in result.message.lower()


@pytest.mark.asyncio
async def test_task_model_mapping(commerce_agent):
    """Test that different tasks map to appropriate models"""
    # Check that task model mapping is configured
    assert AgentTask.PRODUCT_SEARCH in commerce_agent.task_model_map
    assert AgentTask.PRICE_NEGOTIATION in commerce_agent.task_model_map

    # Verify cheap models for simple tasks
    search_provider, search_model = commerce_agent.task_model_map[AgentTask.PRODUCT_SEARCH]
    assert search_provider == "gemini"  # Cheaper model


@pytest.mark.asyncio
@patch('app.agents.commerce_agent.tenacity.retry')
async def test_retry_logic(mock_retry, commerce_agent):
    """Test that retry logic is applied to LLM calls"""
    # This test verifies that the retry decorator is applied
    # In production, the agent will retry up to 3 times with exponential backoff
    assert hasattr(commerce_agent._call_openai, '__wrapped__')
