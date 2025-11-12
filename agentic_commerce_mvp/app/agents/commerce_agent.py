"""
Commerce Agent - Core AI agent for handling shopping interactions
Supports multiple LLM providers with fallback strategies
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from enum import Enum

# LLM Clients
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai

logger = structlog.get_logger()


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class AgentTask(str, Enum):
    PRODUCT_SEARCH = "product_search"
    PRICE_NEGOTIATION = "price_negotiation"
    ORDER_PLACEMENT = "order_placement"
    CUSTOMER_SUPPORT = "customer_support"
    RECOMMENDATION = "recommendation"


class AgentResponse(BaseModel):
    """Structured response from the agent"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    suggested_products: List[Dict[str, Any]] = Field(default_factory=list)
    next_action: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class CommerceAgent:
    """
    Main commerce agent that handles user interactions and delegates to specialized sub-agents
    """

    def __init__(
        self,
        user_id: str,
        session_id: str,
        preferred_provider: LLMProvider = LLMProvider.OPENAI
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.preferred_provider = preferred_provider
        self.conversation_history = []
        self.max_history = 10

        # Initialize LLM clients
        self._init_llm_clients()

        # Task to model mapping (cost optimization)
        self.task_model_map = {
            AgentTask.PRODUCT_SEARCH: ("gemini", "gemini-2.0-flash-exp"),
            AgentTask.PRICE_NEGOTIATION: ("openai", "gpt-4o-mini"),
            AgentTask.ORDER_PLACEMENT: ("openai", "gpt-4o"),
            AgentTask.CUSTOMER_SUPPORT: ("anthropic", "claude-3-5-sonnet-20241022"),
            AgentTask.RECOMMENDATION: ("gemini", "gemini-2.0-flash-exp")
        }

        logger.info(
            "commerce_agent_initialized",
            user_id=user_id,
            session_id=session_id,
            provider=preferred_provider.value
        )

    def _init_llm_clients(self):
        """Initialize all available LLM provider clients"""
        try:
            self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            logger.warning("OpenAI client initialization failed", error=str(e))
            self.openai_client = None

        try:
            self.anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        except Exception as e:
            logger.warning("Anthropic client initialization failed", error=str(e))
            self.anthropic_client = None

        try:
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        except Exception as e:
            logger.warning("Gemini client initialization failed", error=str(e))
            self.gemini_model = None

    def _add_to_history(self, role: str, content: str):
        """Add message to conversation history with size limit"""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > self.max_history * 2:  # user + assistant pairs
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_openai(self, messages: List[Dict], model: str = "gpt-4o-mini") -> str:
        """Call OpenAI with retry logic"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                timeout=30
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("openai_call_failed", error=str(e), model=model)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_anthropic(self, messages: List[Dict], model: str = "claude-3-5-sonnet-20241022") -> str:
        """Call Anthropic with retry logic"""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")

        try:
            # Convert messages format for Anthropic
            system_message = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_messages = [m for m in messages if m["role"] != "system"]

            response = await self.anthropic_client.messages.create(
                model=model,
                system=system_message,
                messages=user_messages,
                max_tokens=1000,
                temperature=0.7,
                timeout=30
            )
            return response.content[0].text
        except Exception as e:
            logger.error("anthropic_call_failed", error=str(e), model=model)
            raise

    async def _call_gemini(self, prompt: str, model_name: str = "gemini-2.0-flash-exp") -> str:
        """Call Gemini with retry logic"""
        if not self.gemini_model:
            raise ValueError("Gemini client not initialized")

        try:
            response = await self.gemini_model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error("gemini_call_failed", error=str(e))
            raise

    async def _call_llm_with_fallback(
        self,
        task: AgentTask,
        prompt: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        Call LLM with intelligent fallback strategy
        1. Try preferred provider for the task
        2. Fall back to alternative providers
        3. Return graceful error message if all fail
        """
        provider, model = self.task_model_map.get(task, ("openai", "gpt-4o-mini"))

        # Build messages
        system_message = self._get_system_prompt(task)
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]

        # Try providers in order
        providers_to_try = [
            (provider, model),
            ("openai", "gpt-4o-mini"),
            ("gemini", "gemini-2.0-flash-exp"),
            ("anthropic", "claude-3-5-sonnet-20241022")
        ]

        for prov, mdl in providers_to_try:
            try:
                if prov == "openai" and self.openai_client:
                    return await self._call_openai(messages, mdl)
                elif prov == "anthropic" and self.anthropic_client:
                    return await self._call_anthropic(messages, mdl)
                elif prov == "gemini" and self.gemini_model:
                    full_prompt = f"{system_message}\n\n{prompt}"
                    return await self._call_gemini(full_prompt)
            except Exception as e:
                logger.warning(
                    "llm_provider_failed",
                    provider=prov,
                    model=mdl,
                    task=task.value,
                    error=str(e)
                )
                continue

        # All providers failed
        logger.error("all_llm_providers_failed", task=task.value)
        return "I'm experiencing technical difficulties. Please try again in a moment."

    def _get_system_prompt(self, task: AgentTask) -> str:
        """Get system prompt based on task type"""
        prompts = {
            AgentTask.PRODUCT_SEARCH: (
                "You are a helpful shopping assistant. Help users find products that match their needs. "
                "Ask clarifying questions when needed. Be concise and friendly."
            ),
            AgentTask.PRICE_NEGOTIATION: (
                "You are a pricing negotiation agent. You can offer discounts up to 15% based on "
                "customer loyalty, bulk purchases, or special circumstances. Be fair but firm."
            ),
            AgentTask.ORDER_PLACEMENT: (
                "You are an order fulfillment agent. Ensure all order details are correct before "
                "confirming. Handle payment processing and provide order confirmation."
            ),
            AgentTask.CUSTOMER_SUPPORT: (
                "You are a customer support agent. Help resolve issues with orders, returns, "
                "and general inquiries. Be empathetic and solution-oriented."
            ),
            AgentTask.RECOMMENDATION: (
                "You are a product recommendation agent. Suggest products based on user preferences, "
                "browsing history, and current trends. Explain why you recommend each product."
            )
        }
        return prompts.get(task, "You are a helpful AI assistant.")

    async def process_message(
        self,
        user_message: str,
        task: AgentTask = AgentTask.PRODUCT_SEARCH
    ) -> AgentResponse:
        """
        Main entry point for processing user messages

        Args:
            user_message: The user's input message
            task: The type of task to perform

        Returns:
            AgentResponse with the agent's reply and any structured data
        """
        logger.info(
            "agent_processing_message",
            user_id=self.user_id,
            session_id=self.session_id,
            task=task.value,
            message_length=len(user_message)
        )

        # Add to conversation history
        self._add_to_history("user", user_message)

        try:
            # Call LLM with fallback
            response_text = await self._call_llm_with_fallback(
                task=task,
                prompt=user_message,
                context={"history": self.conversation_history[-6:]}  # Last 3 exchanges
            )

            # Add response to history
            self._add_to_history("assistant", response_text)

            # TODO: Parse structured data from response (products, prices, etc.)
            # This would involve additional LLM calls or structured output parsing

            return AgentResponse(
                success=True,
                message=response_text,
                data={"task": task.value},
                confidence=0.85
            )

        except Exception as e:
            logger.error(
                "agent_processing_failed",
                user_id=self.user_id,
                error=str(e),
                task=task.value
            )
            return AgentResponse(
                success=False,
                message="I'm having trouble processing your request. Please try again.",
                confidence=0.0
            )

    async def search_products(self, query: str) -> AgentResponse:
        """Specialized method for product search"""
        return await self.process_message(
            user_message=f"Help me find: {query}",
            task=AgentTask.PRODUCT_SEARCH
        )

    async def negotiate_price(self, product_id: str, desired_price: float) -> AgentResponse:
        """Specialized method for price negotiation"""
        return await self.process_message(
            user_message=f"I'd like to negotiate the price for product {product_id}. Can you offer it for ${desired_price}?",
            task=AgentTask.PRICE_NEGOTIATION
        )

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("conversation_history_cleared", user_id=self.user_id)


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        agent = CommerceAgent(
            user_id="user_123",
            session_id="session_456",
            preferred_provider=LLMProvider.OPENAI
        )

        # Test product search
        response = await agent.search_products("wireless headphones under $100")
        print(f"Agent: {response.message}")

        # Test negotiation
        response = await agent.negotiate_price("prod_789", 79.99)
        print(f"Agent: {response.message}")

    asyncio.run(main())
