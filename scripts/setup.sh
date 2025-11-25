#!/bin/bash
# Setup script for Slack Intelligence

set -e

echo "🚀 Setting up Slack Intelligence..."

python3 --version || { echo "❌ Python 3 not found"; exit 1; }

echo "📦 Creating virtual environment..."
python3 -m venv venv

echo "📥 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your tokens"
fi

echo "🗄️  Initializing database..."
cd backend
python -c "from database import init_db; init_db()"
cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Slack tokens and OpenAI API key"
echo "2. source venv/bin/activate"
echo "3. cd backend && python main.py"
echo "4. Visit http://localhost:8000/docs"
