#!/bin/bash
# Quick start script for Slack Intelligence with new production features

echo "=========================================================================="
echo "🚀 SLACK INTELLIGENCE - QUICK START"
echo "=========================================================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "💡 Copy .env.example to .env and configure your API keys"
    exit 1
fi

# Check if venv exists
if [ ! -d venv ]; then
    echo "❌ Error: Virtual environment not found"
    echo "💡 Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
python -c "import apscheduler" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Installing missing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "=========================================================================="
echo "✅ READY TO START"
echo "=========================================================================="
echo ""
echo "Choose what to run:"
echo ""
echo "1. Start FastAPI backend (with auto-sync)"
echo "2. Start Streamlit dashboard"
echo "3. Run production features test"
echo "4. Run manual sync once"
echo "5. Start ngrok for Streamlit (port 8501)"
echo "6. Start everything (API + Streamlit)"
echo ""
read -p "Enter choice (1-6): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting FastAPI backend..."
        echo "💡 Auto-sync will run every 15 minutes if enabled in .env"
        echo "📊 View API docs: http://localhost:8000/docs"
        echo ""
        uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    2)
        echo ""
        echo "🎨 Starting Streamlit dashboard..."
        echo "📊 Dashboard: http://localhost:8501"
        echo "💡 If localhost blocked, use ngrok (option 5)"
        echo ""
        streamlit run streamlit_dashboard.py --server.port 8501
        ;;
    3)
        echo ""
        echo "🧪 Running production features test..."
        echo ""
        python scripts/test_production_features.py
        ;;
    4)
        echo ""
        echo "🔄 Running manual sync..."
        echo ""
        python scripts/sync_once.py
        ;;
    5)
        echo ""
        echo "🌐 Starting ngrok tunnel..."
        echo "💡 Make sure Streamlit is running (option 2) in another terminal"
        echo ""
        if command -v ngrok &> /dev/null; then
            ngrok http 8501
        else
            echo "❌ ngrok not installed"
            echo "💡 Install: brew install ngrok (or download from ngrok.com)"
        fi
        ;;
    6)
        echo ""
        echo "🚀 Starting both API and Streamlit..."
        echo ""
        echo "📊 FastAPI: http://localhost:8000"
        echo "📊 Streamlit: http://localhost:8501"
        echo "💡 Use ngrok for Streamlit if localhost is blocked"
        echo ""
        
        # Start API in background
        uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
        API_PID=$!
        
        # Wait a bit for API to start
        sleep 3
        
        # Start Streamlit
        streamlit run streamlit_dashboard.py --server.port 8501
        
        # Kill API when Streamlit exits
        kill $API_PID
        ;;
    *)
        echo ""
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

