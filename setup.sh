#!/bin/bash
# Setup script to install all dependencies and configure APIs

echo "=================================="
echo "Legal AI - Setup Script"
echo "=================================="
echo ""

# Step 1: Install Python packages
echo "STEP 1: Installing Python packages..."
pip install -r requirements.txt

echo ""
echo "STEP 2: Checking API tools..."

# Check web search tools
echo "Web search tools:"
python -c "
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    print('  ✅ Tavily available')
except:
    print('  ❌ Tavily not installed (optional): pip install tavily-python')

try:
    from langchain_community.tools.google_search import GoogleSearchAPIWrapper
    print('  ✅ Google Search available')
except:
    print('  ❌ Google Search not installed (optional): pip install google-search-results')

try:
    from langchain_community.tools import DuckDuckGoSearchRun
    print('  ✅ DuckDuckGo available')
except:
    print('  ❌ DuckDuckGo not installed (optional): pip install duckduckgo-search')
" 2>/dev/null

# Check research paper tools
echo ""
echo "Research paper tools:"
python -c "
try:
    from langchain_community.tools import ArxivQueryRun
    print('  ✅ Arxiv available')
except:
    print('  ❌ Arxiv not installed (optional): pip install arxiv')
" 2>/dev/null

echo ""
echo "STEP 3: Checking configuration..."

if [ -f .env ]; then
    echo "✅ .env file exists"
else
    echo "⚠️  Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env created - fill in your API keys!"
fi

echo ""
echo "STEP 4: Testing installation..."
python -m workflows.lawyer_agent.test_langchain_tools 2>/dev/null | grep -E "Status:|tests passed"

echo ""
echo "=================================="
echo "Setup complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. For Groq: https://console.groq.com"
echo "3. For Tavily (recommended): https://tavily.com"
echo "4. For Arxiv: No key needed, already free"
echo ""
echo "Run the application:"
echo "  python -m workflows.lawyer_agent.run"
echo ""
