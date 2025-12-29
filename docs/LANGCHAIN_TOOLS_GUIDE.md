"""
Multi-Source Fact Retriever - LangChain Tools Integration

This document explains the LangChain tools integrated into the fact retriever.

==========================================
1. VECTOR STORE RETRIEVER
==========================================
Source: Chroma/FAISS vector databases
Features:
- Statutes (constitution, IPC, CrPC)
- Precedents (yearwise, 1950-2025)
- Semantic similarity search
- Filtered by statute type, year, section

Status: ✅ Fully integrated
No additional setup needed (uses existing vector stores)


==========================================
2. WEB SEARCH RETRIEVER
==========================================
Options available:

A. TAVILY SEARCH (Recommended for legal research)
   - Best for legal documents and case law
   - Returns structured results with sources
   - Fast and reliable
   
   Setup:
   ```bash
   pip install tavily-python
   export TAVILY_API_KEY="your-api-key"
   ```
   Get API key: https://tavily.com
   
   Usage:
   ```python
   retriever = FactRetrieverFactory.create_web_search_retriever(
       search_engine="tavily"
   )
   ```

B. GOOGLE SEARCH (Via SerpAPI)
   - Comprehensive web results
   - Access to any public legal resource
   - Structured results with rankings
   
   Setup:
   ```bash
   pip install google-search-results
   export SERP_API_KEY="your-api-key"
   ```
   Get API key: https://serpapi.com
   
   Usage:
   ```python
   retriever = FactRetrieverFactory.create_web_search_retriever(
       search_engine="google"
   )
   ```

C. BING SEARCH
   - Comprehensive alternative to Google
   - Works in regions where Google is restricted
   
   Setup:
   ```bash
   export BING_SEARCH_V7_SUBSCRIPTION_KEY="your-key"
   ```
   Get API key: https://www.bing.com/webmaster/tools/
   
   Usage:
   ```python
   retriever = FactRetrieverFactory.create_web_search_retriever(
       search_engine="bing"
   )
   ```

D. DUCKDUCKGO SEARCH (Free, no API key needed)
   - Privacy-focused, no tracking
   - Works offline with some limitations
   - Fallback option
   
   Setup:
   ```bash
   pip install duckduckgo-search
   ```
   
   Usage:
   ```python
   retriever = FactRetrieverFactory.create_web_search_retriever(
       search_engine="duckduckgo"
   )
   ```

Status: ✅ Fully integrated
Just set your preferred API key in environment variables


==========================================
3. RESEARCH PAPER RETRIEVER
==========================================
Options available:

A. ARXIV ACADEMIC PAPER SEARCH (Recommended)
   - 2+ million academic papers
   - Legal research papers, law review articles
   - Case studies and empirical research
   - Free, no API key needed
   
   Setup:
   ```bash
   pip install arxiv
   ```
   
   Usage:
   ```python
   retriever = FactRetrieverFactory.create_research_paper_retriever(
       use_arxiv=True
   )
   facts = retriever.retrieve("right to privacy constitutional law")
   ```

B. LOCAL PDF SEMANTIC SEARCH
   - Search over uploaded PDFs
   - Custom research documents
   - Legislation drafts, whitepapers
   
   Setup:
   ```python
   retriever = FactRetrieverFactory.create_research_paper_retriever(
       pdf_directory="./research_papers",
       embedding_manager=embedding_manager
   )
   ```

Status: ✅ Fully integrated
Arxiv requires: pip install arxiv
Local PDFs require: pip install pypdf


==========================================
4. MANUAL INPUT RETRIEVER
==========================================
Features:
- Lawyer manually enters facts
- Highest confidence (1.0 relevance)
- Tagged for easy retrieval
- Quick reference

Status: ✅ Fully integrated
No setup needed (all in-memory)


==========================================
COMPOSITE RETRIEVER (Multi-Source Aggregation)
==========================================
Combines all retrievers with:
- Deduplication by fact hash
- Configurable source weighting
- Relevance-based ranking
- Automatic fallback

Usage:
```python
from modules.fact_retriever import FactRetrieverFactory

# Create composite with all sources
retriever = FactRetrieverFactory.create_composite_retriever(
    embedding_manager=embedding_manager,
    vector_stores=chroma_stores,
    enable_web_search=True,          # Requires API key
    enable_research_papers=True,     # Requires arxiv
    pdf_directory="./research_papers"
)

# Retrieve with optional weighting
facts = retriever.retrieve(
    query="right to privacy employment",
    constraints={"k": 10},
    source_weights={
        "vector_store": 1.0,         # Highest priority
        "web_search": 0.7,
        "research_paper": 0.8,
        "manual_input": 1.0          # Manual input always high
    }
)
```


==========================================
SETUP INSTRUCTIONS (QUICK START)
==========================================

1. For Vector Stores only (no external APIs):
   ```bash
   # Already working - no setup needed
   ```

2. For Web Search (any option):
   ```bash
   # For Tavily (recommended)
   pip install tavily-python
   export TAVILY_API_KEY="your-key"
   
   # OR for Google
   pip install google-search-results
   export SERP_API_KEY="your-key"
   
   # OR for DuckDuckGo (free, no API)
   pip install duckduckgo-search
   ```

3. For Research Papers:
   ```bash
   pip install arxiv
   pip install pypdf
   ```

4. For full functionality:
   ```bash
   pip install tavily-python arxiv pypdf
   export TAVILY_API_KEY="your-key"
   ```


==========================================
TESTING
==========================================

Run tests to verify all retrievers:
```bash
cd "c:\Users\kiran\Desktop\law ai"
python -m workflows.lawyer_agent.test_multi_source_retriever
```

Expected output:
✅ PASS: manual_input
✅ PASS: factory
✅ PASS: composite
✅ PASS: deduplication
✅ PASS: weighting
5/5 tests passed


==========================================
FACT STORAGE & USAGE
==========================================

Facts from all sources are stored in FactStorage with:
- content: The actual text
- source: Source retriever name
- source_type: vector_store | web_search | research_paper | manual_input
- relevance_score: 0-1 confidence
- source_details: Metadata (URL, year, file, etc.)
- fact_hash: MD5 hash for deduplication

Example fact structure:
{
    "id": "uuid-123",
    "content": "Article 21 protects right to privacy...",
    "source": "VectorStoreRetriever",
    "source_type": "vector_store",
    "relevance_score": 0.92,
    "source_details": {
        "statute_section": "Article 21",
        "statute_type": "Constitution",
        "year": 1950
    },
    "status": "pending",  # pending | approved | rejected | approved_locked
    "created_at": "2025-12-29T...",
    "phases_used_in": ["legal_analysis"]
}


==========================================
NEXT STEPS
==========================================

STEP 3: Interactive Fact Refiner UI
- Node: display_facts_node → format for containers
- Node: per_fact_chat_node → edit/delete/approve per fact
- Node: fact_approval_node → lock approved facts

STEP 4: Update Legal Analysis
- Input: Problem + Approved facts (no re-retrieval)
- Retrieve only precedents (not statutes)
- Output: Legal arguments with citations

STEP 5: Interactive Argument Refiner
- Similar to STEP 3 but for legal arguments
- Per-argument chat refinement
- Approval workflow

"""
