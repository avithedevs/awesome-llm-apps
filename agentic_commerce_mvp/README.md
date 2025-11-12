# 🤖 Agentic Commerce MVP

A production-ready starter template for building AI-powered commerce platforms with autonomous agents. Built with FastAPI, supports multiple LLM providers, and implements the [Agentic Commerce Protocol](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol).

## ✨ Features

- **Multi-Agent Architecture**: Commerce, negotiation, support, and recommendation agents
- **Multi-Provider LLM Support**: OpenAI, Anthropic, Google Gemini with automatic fallback
- **Real-time Chat**: WebSocket support for bidirectional communication
- **Cost Optimized**: Intelligent model routing based on task complexity
- **Production Ready**: Error handling, retry logic, observability, and logging
- **Database Agnostic**: SQLAlchemy ORM with async support
- **Payment Integration**: Stripe integration ready
- **Type Safe**: Full Pydantic models and type hints

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ (or use Railway/Render free tier)
- Redis (optional, for session storage)
- API keys for at least one LLM provider

### Installation

1. **Clone and navigate to the project**

```bash
cd agentic_commerce_mvp
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. **Initialize database**

```bash
python -m app.models.database
```

6. **Run the server**

```bash
python main.py
# Or with uvicorn: uvicorn main:app --reload
```

7. **Access the API**

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 📁 Project Structure

```
agentic_commerce_mvp/
├── main.py                 # FastAPI app entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── app/
│   ├── agents/
│   │   └── commerce_agent.py    # Main commerce agent logic
│   ├── models/
│   │   └── database.py          # SQLAlchemy models
│   ├── routers/
│   │   ├── chat.py              # Chat endpoints
│   │   ├── products.py          # Product CRUD
│   │   ├── orders.py            # Order management
│   │   └── agents.py            # Agent config & metrics
│   └── database.py              # DB connection management
├── tests/
│   └── test_agents.py           # Agent unit tests
└── README.md
```

## 🎯 API Endpoints

### Chat

- `POST /api/v1/chat/message` - Send message to agent
- `WS /api/v1/chat/ws/{user_id}` - WebSocket chat connection
- `GET /api/v1/chat/session/{session_id}/history` - Get conversation history
- `DELETE /api/v1/chat/session/{session_id}` - End session

### Products

- `GET /api/v1/products` - List products (with filters)
- `GET /api/v1/products/{product_id}` - Get product details
- `POST /api/v1/products` - Create product
- `PUT /api/v1/products/{product_id}` - Update product
- `DELETE /api/v1/products/{product_id}` - Delete product
- `GET /api/v1/products/search/ai?query=...` - AI-powered search

### Orders

- `POST /api/v1/orders` - Create order
- `GET /api/v1/orders/{order_id}` - Get order details
- `GET /api/v1/orders/user/{user_id}` - Get user's orders
- `PATCH /api/v1/orders/{order_id}/status` - Update order status

### Agents

- `GET /api/v1/agents/metrics` - Get agent performance metrics
- `GET /api/v1/agents/config` - Get agent configuration
- `PUT /api/v1/agents/config` - Update agent configuration

## 💬 Usage Examples

### REST API

```python
import httpx

# Chat with the agent
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/chat/message",
        json={
            "message": "I'm looking for wireless headphones under $100",
            "user_id": "user_123",
            "session_id": "session_456",
            "task": "product_search",
            "provider": "openai"
        }
    )
    print(response.json())
```

### WebSocket

```python
import asyncio
import websockets
import json

async def chat():
    uri = "ws://localhost:8000/api/v1/chat/ws/user_123"
    async with websockets.connect(uri) as websocket:
        # Send message
        await websocket.send(json.dumps({
            "message": "Show me laptops under $1000",
            "task": "product_search"
        }))

        # Receive response
        response = await websocket.recv()
        print(json.loads(response))

asyncio.run(chat())
```

### JavaScript/TypeScript

```typescript
// Fetch API
const response = await fetch('http://localhost:8000/api/v1/chat/message', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Find me a MacBook Pro',
    user_id: 'user_123',
    task: 'product_search'
  })
});

const data = await response.json();
console.log(data.message);

// WebSocket
const ws = new WebSocket('ws://localhost:8000/api/v1/chat/ws/user_123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.message);
};

ws.send(JSON.stringify({
  message: 'I need help choosing a laptop',
  task: 'product_search'
}));
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_agents.py
```

## 🚢 Deployment

### Railway.app (Recommended for MVP)

1. **Create Railway account** at https://railway.app
2. **Install Railway CLI**
```bash
npm install -g @railway/cli
```

3. **Login and initialize**
```bash
railway login
railway init
```

4. **Add PostgreSQL**
```bash
railway add postgresql
```

5. **Set environment variables** in Railway dashboard

6. **Deploy**
```bash
railway up
```

### Render.com

1. Create account at https://render.com
2. New Web Service → Connect GitHub repo
3. Add PostgreSQL database
4. Configure environment variables
5. Deploy!

### Docker (Self-hosted)

```bash
# Build
docker build -t agentic-commerce .

# Run
docker run -p 8000:8000 --env-file .env agentic-commerce
```

## 💰 Cost Optimization

### Model Selection Strategy

The agent automatically routes tasks to cost-effective models:

- **Simple tasks** (product search): Gemini Flash ($0.0001/1K tokens)
- **Medium complexity** (negotiation): GPT-4o-mini ($0.00015/1K tokens)
- **Complex reasoning** (order placement): GPT-4o ($0.0025/1K tokens)
- **Support conversations**: Claude 3.5 Sonnet ($0.003/1K tokens)

### Estimated Monthly Costs (500 users, 10 interactions/user/month)

```
Total Interactions: 5,000/month
Average tokens per interaction: 500 input + 300 output = 800 tokens

Cost Breakdown:
├─ Gemini Flash (60%): 3,000 × 0.8K × $0.0001 = $0.24
├─ GPT-4o-mini (25%): 1,250 × 0.8K × $0.0002 = $0.20
├─ GPT-4o (10%): 500 × 0.8K × $0.0025 = $1.00
└─ Claude (5%): 250 × 0.8K × $0.003 = $0.60

Total LLM Cost: ~$2.04/month
Hosting (Railway): $5/month
Total: ~$7/month for 500 users
```

## 🔐 Security Best Practices

- ✅ Environment variables for all secrets
- ✅ Input validation with Pydantic
- ✅ SQL injection prevention (parameterized queries)
- ✅ Rate limiting (implement with FastAPI Limiter)
- ✅ CORS configuration
- ⚠️ TODO: Add authentication (NextAuth, Clerk, or Auth0)
- ⚠️ TODO: Add HTTPS in production
- ⚠️ TODO: Implement request signing for API

## 📊 Monitoring & Observability

### Built-in Logging

Structured logging with `structlog`:

```python
logger.info(
    "agent_task_started",
    user_id=user.id,
    task="product_search",
    session_id=session.id
)
```

### Recommended Tools

- **Error Tracking**: Sentry (free tier)
- **Performance**: Langfuse or LangSmith
- **Analytics**: PostHog (free tier)
- **Uptime**: UptimeRobot (free tier)

## 🛠️ Customization

### Adding a New Agent Type

1. **Define task enum** in `commerce_agent.py`:
```python
class AgentTask(str, Enum):
    YOUR_NEW_TASK = "your_new_task"
```

2. **Add system prompt**:
```python
def _get_system_prompt(self, task: AgentTask):
    prompts = {
        AgentTask.YOUR_NEW_TASK: "Your custom prompt here..."
    }
```

3. **Configure model mapping**:
```python
self.task_model_map = {
    AgentTask.YOUR_NEW_TASK: ("gemini", "gemini-2.0-flash-exp")
}
```

### Adding Stripe Payments

See `docs/STRIPE_INTEGRATION.md` (TODO: Create this)

### Adding Vector Search

See `docs/VECTOR_SEARCH.md` (TODO: Create this)

## 📚 Resources

- [Agentic Commerce Protocol](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol)
- [Microsoft Agent Lightning](https://github.com/microsoft/agent-lightning)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI Agents SDK](https://github.com/openai/agents-sdk)
- [Anthropic Claude Docs](https://docs.anthropic.com/)

## 🤝 Contributing

Contributions welcome! Please read `CONTRIBUTING.md` first (TODO: Create this)

## 📄 License

MIT License - see LICENSE file

## 💡 Next Steps

After getting the MVP running, consider:

1. **Frontend**: Build a Next.js or React frontend
2. **Authentication**: Add user authentication (Clerk, Auth0)
3. **Payments**: Integrate Stripe checkout
4. **Vector Search**: Add semantic product search with embeddings
5. **Multi-Agent Patterns**: Implement agent swarms/teams
6. **Analytics**: Add product recommendations based on behavior
7. **Mobile**: Build mobile app (React Native, Flutter)

## 🆘 Support

- GitHub Issues: Report bugs or request features
- Discussions: Ask questions and share ideas
- Twitter: [@your_handle]

---

Built with ❤️ using Claude Code and vibe coding principles. Read `VIBE_CODING_GUIDE.md` for best practices.
