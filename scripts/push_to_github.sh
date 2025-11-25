#!/bin/bash
# Quick push to GitHub

cd /Users/knewman/Downloads/slack-intelligence

echo "🔍 Checking git status..."
git status

echo ""
echo "📝 Staging any new files..."
git add -A

echo ""
echo "💾 Current commits ready to push:"
git log origin/main..HEAD --oneline

echo ""
echo "🚀 Ready to push 13 commits to GitHub"
echo ""
read -p "Enter your GitHub Personal Access Token (or press Ctrl+C to cancel): " TOKEN

if [ -z "$TOKEN" ]; then
    echo "❌ No token provided"
    exit 1
fi

echo ""
echo "Pushing to GitHub..."
git push https://$TOKEN@github.com/kylenewm/slack-automation.git main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Pushed to GitHub"
    echo ""
    echo "🚀 Next: Connect to Railway"
    echo "   1. Go to https://railway.app"
    echo "   2. Login with GitHub"
    echo "   3. Deploy from repo: kylenewm/slack-automation"
else
    echo ""
    echo "❌ Push failed. Check your token and try again."
fi

