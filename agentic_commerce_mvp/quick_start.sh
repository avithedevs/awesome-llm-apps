#!/bin/bash

# Agentic Commerce MVP - Quick Start Script
# This script helps you get up and running quickly

set -e  # Exit on error

echo "🚀 Agentic Commerce MVP - Quick Start"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10+ first."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "🔐 Please edit .env and add your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - GOOGLE_API_KEY"
    echo "   - DATABASE_URL"
    echo ""
    read -p "Press Enter when you've added your API keys to .env..."
else
    echo "✅ .env file found"
fi

# Check if required env vars are set
echo "🔍 Checking environment variables..."
source .env

if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  Warning: No LLM API keys found. Please add at least one:"
    echo "   - OPENAI_API_KEY"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - GOOGLE_API_KEY"
fi

# Ask about database setup
echo ""
echo "📊 Database Setup"
echo "-----------------"
echo "Do you want to use Docker for PostgreSQL?"
echo "1) Yes - Start PostgreSQL with Docker Compose"
echo "2) No - I'll use my own PostgreSQL instance"
read -p "Enter your choice (1 or 2): " db_choice

if [ "$db_choice" == "1" ]; then
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi

    echo "🐳 Starting PostgreSQL with Docker..."
    docker-compose up -d db redis

    echo "⏳ Waiting for database to be ready..."
    sleep 5

    # Update .env with Docker database URL
    sed -i.bak 's|DATABASE_URL=.*|DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentic_commerce|g' .env
    echo "✅ Database URL updated in .env"
else
    echo "ℹ️  Make sure your DATABASE_URL in .env points to your PostgreSQL instance"
fi

# Initialize database
echo ""
echo "🗄️  Initializing database tables..."
python -m app.models.database

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "   1. Review your .env file and ensure all API keys are set"
echo "   2. Run the server: python main.py"
echo "   3. Open http://localhost:8000/docs in your browser"
echo "   4. Start building your agentic commerce platform!"
echo ""
echo "📚 Resources:"
echo "   - README.md - Full documentation"
echo "   - VIBE_CODING_GUIDE.md - Best practices and tips"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "Happy coding! 🚀"
