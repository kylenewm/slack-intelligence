#!/bin/bash
# Setup and test ngrok for Streamlit access

echo "=========================================================================="
echo "🌐 NGROK SETUP FOR STREAMLIT"
echo "=========================================================================="
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found. Installing..."
    echo ""
    
    # Check if Homebrew is available
    if command -v brew &> /dev/null; then
        echo "📦 Installing ngrok via Homebrew..."
        brew install ngrok
    else
        echo "💡 Please install ngrok manually:"
        echo "   1. Visit: https://ngrok.com/download"
        echo "   2. Download for macOS (ARM)"
        echo "   3. Unzip and move to /usr/local/bin/"
        echo "   4. Run this script again"
        exit 1
    fi
fi

echo "✅ ngrok is installed"
echo ""

# Check if Streamlit is running
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Streamlit is running on port 8501"
else
    echo "⚠️  Streamlit is NOT running on port 8501"
    echo ""
    read -p "Start Streamlit now? (y/n): " start_streamlit
    
    if [ "$start_streamlit" = "y" ]; then
        echo ""
        echo "🎨 Starting Streamlit in background..."
        cd /Users/knewman/Downloads/slack-intelligence
        source venv/bin/activate
        nohup streamlit run streamlit_dashboard.py --server.port 8501 > /tmp/streamlit.log 2>&1 &
        STREAMLIT_PID=$!
        echo "✅ Streamlit started (PID: $STREAMLIT_PID)"
        echo "📊 Logs: tail -f /tmp/streamlit.log"
        sleep 5
    else
        echo ""
        echo "💡 Start Streamlit in another terminal:"
        echo "   cd /Users/knewman/Downloads/slack-intelligence"
        echo "   source venv/bin/activate"
        echo "   streamlit run streamlit_dashboard.py --server.port 8501"
        echo ""
        read -p "Press Enter when Streamlit is running..."
    fi
fi

echo ""
echo "=========================================================================="
echo "🚀 STARTING NGROK TUNNEL"
echo "=========================================================================="
echo ""
echo "💡 Keep this terminal open to maintain the tunnel"
echo "📊 Your Streamlit dashboard will be accessible via the ngrok URL"
echo "🔗 Share this URL to access from anywhere (bypasses localhost restrictions)"
echo ""
echo "Starting ngrok..."
echo ""

ngrok http 8501

