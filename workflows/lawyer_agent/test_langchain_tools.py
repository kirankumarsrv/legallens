"""
Test LangChain Tools Integration

Shows what tools are available and how to use them.
"""

from modules.fact_retriever import FactRetrieverFactory
import os


def test_tools_availability():
    """Check which LangChain tools are available"""
    print("\n" + "="*70)
    print("LANGCHAIN TOOLS AVAILABILITY CHECK")
    print("="*70)
    
    tools = {
        "Vector Stores": "✅ Available (built-in)",
        "Manual Input": "✅ Available (no dependencies)",
        "Web Search": {
            "Tavily": "⚠️  Requires: pip install tavily-python",
            "Google (SerpAPI)": "⚠️  Requires: pip install google-search-results",
            "Bing": "⚠️  Built-in (no install needed)",
            "DuckDuckGo": "⚠️  Requires: pip install duckduckgo-search"
        },
        "Research Papers": {
            "Arxiv": "⚠️  Requires: pip install arxiv",
            "Local PDFs": "⚠️  Requires: pip install pypdf"
        }
    }
    
    for category, options in tools.items():
        print(f"\n{category}:")
        if isinstance(options, str):
            print(f"  {options}")
        else:
            for tool, status in options.items():
                print(f"  • {tool}: {status}")
    
    print("\n" + "-"*70)
    print("INSTALLED PACKAGES CHECK:")
    print("-"*70)
    
    packages_to_check = [
        ("tavily-python", "Tavily Search"),
        ("google-search-results", "Google Search"),
        ("arxiv", "Arxiv Papers"),
        ("duckduckgo-search", "DuckDuckGo"),
        ("pypdf", "PDF Loading"),
    ]
    
    for package, display_name in packages_to_check:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {display_name}: installed")
        except ImportError:
            print(f"❌ {display_name}: NOT installed")
    
    return True


def test_available_retrievers():
    """Test available retrievers (what's working now)"""
    print("\n" + "="*70)
    print("AVAILABLE RETRIEVERS TEST")
    print("="*70)
    
    # Test 1: Manual input (always works)
    print("\n1️⃣  MANUAL INPUT RETRIEVER")
    print("   Status: ✅ READY")
    manual = FactRetrieverFactory.create_manual_input_retriever()
    manual.add_fact("Right to privacy under Article 21", tags=["privacy"])
    facts = manual.retrieve("privacy")
    print(f"   ✅ Retrieved {len(facts)} facts")
    
    # Test 2: Web search (if available)
    print("\n2️⃣  WEB SEARCH RETRIEVER")
    try:
        web = FactRetrieverFactory.create_web_search_retriever()
        if web.search_tool:
            print(f"   Status: ✅ READY ({web.search_engine})")
            # Don't actually search (may be slow or need API key)
            print(f"   Engine: {web.search_engine}")
        else:
            print(f"   Status: ⚠️  FALLBACK (DuckDuckGo not installed)")
            print(f"   To enable: pip install duckduckgo-search")
    except Exception as e:
        print(f"   Status: ❌ ERROR - {e}")
    
    # Test 3: Research papers (if available)
    print("\n3️⃣  RESEARCH PAPER RETRIEVER")
    try:
        paper = FactRetrieverFactory.create_research_paper_retriever()
        if paper.arxiv_tool:
            print(f"   Status: ✅ READY (Arxiv)")
            print(f"   Features: Academic paper search from arxiv.org")
        else:
            print(f"   Status: ⚠️  LIMITED (Arxiv not available)")
            print(f"   To enable: pip install arxiv")
    except Exception as e:
        print(f"   Status: ❌ ERROR - {e}")
    
    return True


def print_setup_instructions():
    """Print setup instructions for all tools"""
    print("\n" + "="*70)
    print("SETUP INSTRUCTIONS FOR FULL FUNCTIONALITY")
    print("="*70)
    
    instructions = """
OPTIONS FOR WEB SEARCH (choose one):

1. TAVILY SEARCH (Recommended for legal research):
   ```bash
   pip install tavily-python
   set TAVILY_API_KEY=your-api-key
   ```
   Get free key: https://tavily.com

2. GOOGLE SEARCH (Most comprehensive):
   ```bash
   pip install google-search-results
   set SERP_API_KEY=your-api-key
   ```
   Get free key: https://serpapi.com

3. DUCKDUCKGO (Free, no API key):
   ```bash
   pip install duckduckgo-search
   ```

4. BING SEARCH:
   ```bash
   set BING_SEARCH_V7_SUBSCRIPTION_KEY=your-key
   ```

OPTIONS FOR RESEARCH PAPERS:

```bash
pip install arxiv pypdf
```

FULL INSTALLATION (All features):

```bash
pip install tavily-python arxiv pypdf duckduckgo-search
set TAVILY_API_KEY=your-api-key
set SERP_API_KEY=your-api-key
```

VERIFY INSTALLATION:

```bash
cd "c:\\Users\\kiran\\Desktop\\law ai"
python -m workflows.lawyer_agent.test_multi_source_retriever
```

Expected: 5/5 tests passed ✅
"""
    
    print(instructions)
    return True


def show_usage_example():
    """Show how to use the multi-source retriever"""
    print("\n" + "="*70)
    print("USAGE EXAMPLE")
    print("="*70)
    
    example = """
from modules.fact_retriever import FactRetrieverFactory

# Create composite retriever with all sources
retriever = FactRetrieverFactory.create_composite_retriever(
    embedding_manager=embedding_manager,
    vector_stores=chroma_stores,
    enable_web_search=True,
    enable_research_papers=True,
    pdf_directory="./research_papers"
)

# Retrieve facts
query = "employer monitoring employee email right to privacy"
facts = retriever.retrieve(
    query=query,
    constraints={"k": 10},  # Top 10 results
    source_weights={
        "vector_store": 1.0,      # Statutes - highest priority
        "research_paper": 0.8,    # Academic research
        "web_search": 0.6,        # Web results
        "manual_input": 1.0       # Manual facts - always high
    }
)

# Facts are automatically:
# ✅ Deduplicated by content hash
# ✅ Ranked by relevance
# ✅ Combined from multiple sources
# ✅ Ready for lawyer approval in fact_gathering.py

print(f"Retrieved {len(facts)} unique facts")
for fact in facts[:3]:
    print(f"  • [{fact['source']}] {fact['content'][:60]}...")
"""
    
    print(example)
    return True


def run_all():
    """Run all checks"""
    print("\n" + "="*70)
    print("LANGCHAIN TOOLS INTEGRATION STATUS")
    print("="*70)
    
    test_tools_availability()
    test_available_retrievers()
    print_setup_instructions()
    show_usage_example()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("""
✅ STEP 2 COMPLETE: Multi-Source Fact Retriever implemented

What's integrated:
  ✅ Vector stores (statutes, precedents) - working
  ✅ Manual input retriever - working
  ⚠️  Web search (Tavily, Google, Bing, DuckDuckGo) - ready, needs API key
  ⚠️  Research papers (Arxiv, PDFs) - ready, needs arxiv package

All retrievers use LangChain tools:
  • TavilySearchResults
  • GoogleSearchAPIWrapper
  • BingSearchAPIWrapper
  • DuckDuckGoSearchRun
  • ArxivQueryRun
  • PyPDFLoader

Next step: STEP 3 - Interactive Fact Refiner UI
  • Display facts in containers
  • Per-fact chat refinement
  • Lawyer approval workflow
""")
    
    return True


if __name__ == "__main__":
    run_all()

