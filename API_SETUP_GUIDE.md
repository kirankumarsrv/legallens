"""
API Keys & Setup Guide

Complete guide for setting up all external APIs and integrations.
"""

# ============================================================
# REQUIRED APIS
# ============================================================

## 1. GROQ API (Required - for LLM)
   
   Purpose: LLM provider for legal analysis
   Free tier: Yes (unlimited requests, rate limited)
   Setup time: 2 minutes
   
   Steps:
   1. Go to https://console.groq.com
   2. Sign up with GitHub or email
   3. Create API key
   4. Copy key to .env: GROQ_API_KEY=xxx
   5. Test: python -m workflows.lawyer_agent.run


# ============================================================
# OPTIONAL WEB SEARCH APIS (Choose at least one)
# ============================================================

## A. TAVILY SEARCH (Recommended for legal research)

   Purpose: Best search engine for legal documents, case law, statutes
   Free tier: Yes (30 requests/day)
   Setup time: 5 minutes
   Quality: ⭐⭐⭐⭐⭐ (Best for legal)
   
   Steps:
   1. Go to https://tavily.com
   2. Sign up (GitHub, Google, or email)
   3. Create API key in dashboard
   4. Copy key to .env: TAVILY_API_KEY=xxx
   5. Test: python -c "from modules.fact_retriever import FactRetrieverFactory; r = FactRetrieverFactory.create_web_search_retriever('tavily'); print(r.search_engine)"
   
   Pros:
   - Specialized for research and documentation
   - Returns structured results with URLs and snippets
   - Good for finding Indian case law and legal precedents
   
   Cons:
   - Limited free tier (30/day)
   - Paid plans start at $50/month


## B. GOOGLE SEARCH (Via SerpAPI)

   Purpose: Most comprehensive web search, can search any public source
   Free tier: Yes (100 requests/month)
   Setup time: 5 minutes
   Quality: ⭐⭐⭐⭐⭐ (Most comprehensive)
   
   Steps:
   1. Go to https://serpapi.com
   2. Sign up (email required)
   3. Get API key from dashboard
   4. Copy key to .env: SERP_API_KEY=xxx
   5. Test: python -c "from modules.fact_retriever import FactRetrieverFactory; r = FactRetrieverFactory.create_web_search_retriever('google'); print(r.search_engine)"
   
   Pros:
   - Most comprehensive search results
   - Includes all search types (web, scholar, news)
   - Works globally
   
   Cons:
   - Limited free tier (100/month)
   - Paid plans start at $50/month for 50k requests


## C. BING SEARCH

   Purpose: Alternative to Google, works in some restricted regions
   Free tier: Yes (limited)
   Setup time: 10 minutes
   Quality: ⭐⭐⭐⭐ (Good alternative)
   
   Steps:
   1. Go to https://www.bing.com/webmaster/tools/
   2. Sign in with Microsoft account
   3. Create search key in settings
   4. Copy key to .env: BING_SEARCH_V7_SUBSCRIPTION_KEY=xxx
   5. Test: python -c "from modules.fact_retriever import FactRetrieverFactory; r = FactRetrieverFactory.create_web_search_retriever('bing'); print(r.search_engine)"
   
   Pros:
   - Good alternative to Google in some regions
   - Reasonable free tier
   
   Cons:
   - Less comprehensive than Google
   - Interface can be confusing


## D. DUCKDUCKGO (Free, no API key needed)

   Purpose: Free alternative search, privacy-focused
   Free tier: Unlimited
   Setup time: 2 minutes (just install)
   Quality: ⭐⭐⭐ (Good fallback)
   
   Steps:
   1. pip install duckduckgo-search
   2. No API key needed
   3. Set DUCKDUCKGO_ENABLED=true in .env (optional)
   4. Test: python -c "from modules.fact_retriever import FactRetrieverFactory; r = FactRetrieverFactory.create_web_search_retriever('duckduckgo'); print(r.search_engine)"
   
   Pros:
   - Completely free, unlimited requests
   - No API key needed
   - Privacy-focused
   
   Cons:
   - Results less comprehensive
   - Less structured output
   - Sometimes blocked by rate limits


# ============================================================
# OPTIONAL RESEARCH PAPER APIS (Free)
# ============================================================

## A. ARXIV ACADEMIC PAPERS

   Purpose: Search 2+ million academic papers for legal research
   Free tier: Yes, completely free
   Setup time: 2 minutes
   Quality: ⭐⭐⭐⭐⭐ (Best for academic research)
   
   Steps:
   1. pip install arxiv
   2. Set ARXIV_ENABLED=true in .env
   3. No API key needed
   4. Test: python -c "from modules.fact_retriever import FactRetrieverFactory; r = FactRetrieverFactory.create_research_paper_retriever(); print('Arxiv ready' if r.arxiv_tool else 'Arxiv not available')"
   
   Pros:
   - Completely free, no API key
   - 2+ million papers available
   - Great for legal research, law review articles
   - No rate limits (be respectful)
   
   Cons:
   - Takes a moment to search
   - Results can include non-legal papers


## B. LOCAL PDF SEMANTIC SEARCH

   Purpose: Search your own uploaded research PDFs
   Free tier: Yes (uses local embeddings)
   Setup time: 5 minutes
   Quality: ⭐⭐⭐⭐ (Depends on your PDFs)
   
   Steps:
   1. pip install pypdf
   2. Create directory: mkdir research_papers
   3. Add PDF files to research_papers/
   4. Set PDF_RESEARCH_DIRECTORY=./research_papers in .env
   5. Test: python -c "from modules.fact_retriever import FactRetrieverFactory; r = FactRetrieverFactory.create_research_paper_retriever('./research_papers'); print(f'Loaded {len(r.documents)} documents')"
   
   Pros:
   - Completely free
   - Control over content
   - Fast semantic search
   
   Cons:
   - Only searches PDFs you provide
   - Requires good embedding model


# ============================================================
# RECOMMENDED SETUP PLANS
# ============================================================

## PLAN 1: MINIMAL (Budget-friendly)
   - GROQ_API_KEY ✅ (required)
   - DUCKDUCKGO (free web search)
   - ARXIV (free papers)
   Total cost: $0/month
   Time: 10 minutes
   
   For: Testing and development

## PLAN 2: OPTIMAL (Recommended for development)
   - GROQ_API_KEY ✅ (required)
   - TAVILY_API_KEY (best for legal, 30/day free)
   - ARXIV (free papers)
   Total cost: $0/month (within free tier)
   Time: 10 minutes
   
   For: Development and testing with good legal search

## PLAN 3: COMPREHENSIVE (Production-ready)
   - GROQ_API_KEY ✅ (required)
   - TAVILY_API_KEY (30 legal searches/day)
   - SERP_API_KEY (100 Google searches/month)
   - ARXIV (unlimited free papers)
   - Local PDF search (free)
   Total cost: $0/month (within free tiers)
   Time: 20 minutes
   
   For: Production use with multiple search options

## PLAN 4: ENTERPRISE (Unlimited)
   - All APIs with paid plans
   - PostgreSQL for multi-user support
   - Advanced authentication
   Total cost: $150-500/month
   Time: Setup varies
   
   For: Multi-user production system


# ============================================================
# QUICK START CHECKLIST
# ============================================================

STEP 1: Get Required Key
- [ ] Get GROQ_API_KEY from https://console.groq.com
- [ ] Copy key to .env

STEP 2: Get Recommended Key
- [ ] Get TAVILY_API_KEY from https://tavily.com (optional)
- [ ] Copy key to .env

STEP 3: Install Packages
bash
cp .env.example .env
pip install -r requirements.txt
pip install tavily-python arxiv

STEP 4: Fill .env File
- [ ] Add GROQ_API_KEY
- [ ] Add TAVILY_API_KEY (if you got it)
- [ ] Set ARXIV_ENABLED=true

STEP 5: Test
bash
python -m workflows.lawyer_agent.test_langchain_tools

STEP 6: Run Application
bash
python -m workflows.lawyer_agent.run


# ============================================================
# ENVIRONMENT VARIABLES EXPLAINED
# ============================================================

Search Engine Priority (Auto-fallback):
If Tavily not configured → Try Google (SerpAPI)
If Google not configured → Try Bing
If Bing not configured → Use DuckDuckGo
If DuckDuckGo not installed → No web search

Research Papers:
If Arxiv enabled and installed → Use Arxiv
If local PDFs configured → Search local PDFs
If both disabled → No paper search


# ============================================================
# TROUBLESHOOTING
# ============================================================

Q: "TAVILY_API_KEY not found"
A: Set in .env or environment variable, then restart app

Q: "Could not import duckduckgo_search"
A: pip install duckduckgo-search

Q: "ArxivQueryRun not available"
A: pip install arxiv

Q: "Web search returns no results"
A: Check API key validity, verify API quota not exceeded

Q: "Slow performance on first search"
A: First search loads models, subsequent searches are faster


# ============================================================
# PRODUCTION DEPLOYMENT
# ============================================================

For hosting on cloud (AWS, Azure, GCP, Heroku):

1. DON'T commit .env - use secret management:
   - AWS Secrets Manager
   - Azure Key Vault
   - Heroku Config Vars
   - GitHub Secrets (for CI/CD)

2. Set environment variables in platform:
   export GROQ_API_KEY="xxx"
   export TAVILY_API_KEY="xxx"
   etc.

3. Update .gitignore to exclude .env:
   echo ".env" >> .gitignore

4. For production databases:
   export SESSION_STORAGE_TYPE=postgresql
   export POSTGRESQL_HOST="your-db-host"
   etc.


# ============================================================
# GETTING HELP
# ============================================================

API Support:
- Groq: https://console.groq.com/docs
- Tavily: https://tavily.com/docs
- SerpAPI: https://serpapi.com/docs
- Bing: https://www.bing.com/webmaster/help/webmaster-help-center-f8de0d4d
- Arxiv: https://arxiv.org/help/api/basics

"""
