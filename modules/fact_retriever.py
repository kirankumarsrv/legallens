"""
Multi-Source Fact Retriever Module

Retrieves legal facts from multiple sources:
- Vector stores (statutes, precedents)
- Web search (Google, case databases, legal websites)
- Research papers (PDF semantic search)
- Manual input (lawyer uploads)
- LangChain integrations (APIs, custom tools)

Architecture:
- BaseRetriever: Abstract base class
- VectorStoreRetriever: Chroma/FAISS for statutes & precedents
- WebSearchRetriever: Tavily Search, Google Search, Bing Search
- ResearchPaperRetriever: Semantic search over PDF corpus
- ManualInputRetriever: Lawyer-provided facts
- CompositeRetriever: Aggregates all sources with ranking
"""

import os
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
from enum import Enum
from dotenv import load_dotenv

# Load .env file for API keys
load_dotenv()


class SourceType(Enum):
    """Fact source types"""
    VECTOR_STORE = "vector_store"
    WEB_SEARCH = "web_search"
    RESEARCH_PAPER = "research_paper"
    MANUAL_INPUT = "manual_input"
    API = "api"
    PRECEDENT = "precedent"
    STATUTE = "statute"


class BaseRetriever(ABC):
    """Abstract base class for fact retrievers"""
    
    def __init__(self, source_type: SourceType, config: Dict[str, Any] = None):
        """
        Initialize retriever.
        
        Args:
            source_type: Type of source
            config: Retriever configuration
        """
        self.source_type = source_type
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def retrieve(self, query: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Retrieve facts matching query.
        
        Returns:
            List of facts with keys: content, source, source_type, relevance_score, 
            source_details, metadata
        """
        pass
    
    def _create_fact(
        self,
        content: str,
        relevance_score: float = 0.5,
        source_details: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create standardized fact dict."""
        return {
            "content": content,
            "source": self.name,
            "source_type": self.source_type.value,
            "relevance_score": min(1.0, max(0.0, relevance_score)),
            "source_details": source_details or {},
            "metadata": metadata or {},
            "retrieved_at": datetime.now().isoformat(),
            "fact_hash": hashlib.md5(content.encode()).hexdigest()
        }


class VectorStoreRetriever(BaseRetriever):
    """Retrieve from vector stores (Chroma, FAISS)"""
    
    def __init__(self, embedding_manager, vector_stores: Dict[str, Any] = None):
        """
        Initialize vector store retriever.
        
        Args:
            embedding_manager: EmbeddingManager instance
            vector_stores: Dict mapping store names to store instances
                          e.g., {"statutes": chroma_store, "precedents": faiss_store}
        """
        super().__init__(SourceType.VECTOR_STORE)
        self.embedding_manager = embedding_manager
        self.vector_stores = vector_stores or {}
    
    def retrieve(self, query: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve from vector stores with optional constraints."""
        constraints = constraints or {}
        facts = []
        
        for store_name, store in self.vector_stores.items():
            try:
                # Query the store
                results = store.similarity_search(query, k=constraints.get("k", 5))
                
                for result in results:
                    fact = self._create_fact(
                        content=result.page_content,
                        relevance_score=0.8,  # Vector search confidence
                        source_details={
                            "store": store_name,
                            "doc_id": result.metadata.get("id"),
                            "year": result.metadata.get("year"),
                            "statute_section": result.metadata.get("statute_section")
                        },
                        metadata=result.metadata
                    )
                    facts.append(fact)
            
            except Exception as e:
                print(f"⚠️  Vector store retrieval failed for {store_name}: {e}")
        
        return facts


class WebSearchRetriever(BaseRetriever):
    """Retrieve from web search (Tavily, Google, Bing)"""
    
    def __init__(self, search_engine: str = "tavily", api_key: str = None):
        """
        Initialize web search retriever.
        
        Args:
            search_engine: "tavily", "google", "bing", "duckduckgo"
            api_key: Optional API key (overrides env var)
        """
        super().__init__(SourceType.WEB_SEARCH)
        self.search_engine = search_engine
        self.api_key = api_key
        self.search_tool = None
        
        # Initialize search tool
        self._init_search_tool()
    
    def _init_search_tool(self):
        """Initialize LangChain search tool"""
        try:
            if self.search_engine == "tavily":
                self._init_tavily()
            elif self.search_engine == "google":
                self._init_google()
            elif self.search_engine == "bing":
                self._init_bing()
            else:
                self._init_duckduckgo()
        except Exception as e:
            print(f"⚠️  Search tool initialization failed: {e}")
            # Fallback to DuckDuckGo
            try:
                self._init_duckduckgo()
            except:
                self.search_tool = None
    
    def _init_tavily(self):
        """Initialize Tavily Search (best for legal research)"""
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            
            api_key = self.api_key or os.getenv("TAVILY_API_KEY")
            if not api_key:
                print("⚠️  TAVILY_API_KEY not found. Set via env var or parameter.")
                return
            
            self.search_tool = TavilySearchResults(
                api_key=api_key,
                max_results=5
            )
            self.search_engine = "tavily"
            print("✅ Tavily Search initialized (best for legal research)")
        except ImportError:
            print("⚠️  TavilySearchResults not available. Install: pip install tavily-python")
        except Exception as e:
            print(f"⚠️  Tavily initialization failed: {e}")
    
    def _init_google(self):
        """Initialize Google Search via SerpAPI"""
        try:
            from langchain_community.tools.google_search import GoogleSearchAPIWrapper
            
            api_key = self.api_key or os.getenv("SERP_API_KEY")
            if not api_key:
                print("⚠️  SERP_API_KEY not found. Get from https://serpapi.com")
                return
            
            self.search_tool = GoogleSearchAPIWrapper(serpapi_api_key=api_key)
            self.search_engine = "google"
            print("✅ Google Search initialized (via SerpAPI)")
        except ImportError:
            print("⚠️  GoogleSearchAPIWrapper not available")
        except Exception as e:
            print(f"⚠️  Google Search initialization failed: {e}")
    
    def _init_bing(self):
        """Initialize Bing Search"""
        try:
            from langchain_community.tools.bing_search import BingSearchAPIWrapper
            
            api_key = self.api_key or os.getenv("BING_SEARCH_V7_SUBSCRIPTION_KEY")
            if not api_key:
                print("⚠️  BING_SEARCH_V7_SUBSCRIPTION_KEY not found")
                return
            
            self.search_tool = BingSearchAPIWrapper(bing_search_v7_subscription_key=api_key)
            self.search_engine = "bing"
            print("✅ Bing Search initialized")
        except ImportError:
            print("⚠️  BingSearchAPIWrapper not available")
        except Exception as e:
            print(f"⚠️  Bing Search initialization failed: {e}")
    
    def _init_duckduckgo(self):
        """Initialize DuckDuckGo Search (free, no API key needed)"""
        try:
            from langchain_community.tools import DuckDuckGoSearchRun
            self.search_tool = DuckDuckGoSearchRun()
            self.search_engine = "duckduckgo"
            print("✅ DuckDuckGo Search initialized (free, no API key needed)")
        except ImportError:
            print("⚠️  DuckDuckGoSearchRun not available. Install: pip install duckduckgo-search")
            self.search_tool = None
        except Exception as e:
            print(f"⚠️  DuckDuckGo initialization failed: {e}")
    
    def retrieve(self, query: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve from web search."""
        if not self.search_tool:
            return []
        
        constraints = constraints or {}
        facts = []
        
        try:
            # Append legal context to query
            legal_query = f"{query} Indian law legal case precedent"
            
            # Execute search
            results = self.search_tool.invoke(legal_query)
            
            # Parse results based on tool type
            if isinstance(results, list):
                parsed_results = results
            else:
                # If single string result, parse it
                parsed_results = self._parse_search_results(results)
            
            for idx, result in enumerate(parsed_results[:constraints.get("k", 5)]):
                content = result.get("snippet", result.get("content", str(result)))
                
                fact = self._create_fact(
                    content=content[:500],  # Limit length
                    relevance_score=0.6,  # Web search generally lower confidence
                    source_details={
                        "engine": self.search_engine,
                        "url": result.get("link", result.get("url", "")),
                        "title": result.get("title", "")
                    },
                    metadata={
                        "search_rank": idx + 1,
                        "source": "web"
                    }
                )
                facts.append(fact)
        
        except Exception as e:
            print(f"⚠️  Web search retrieval failed: {e}")
        
        return facts
    
    def _parse_search_results(self, results: str) -> List[Dict[str, Any]]:
        """Parse web search results string into structured format."""
        parsed = []
        
        # Simple parsing of web results
        if isinstance(results, str):
            # Split by common delimiters
            snippets = results.split("\n\n")
            for snippet in snippets:
                if snippet.strip():
                    parsed.append({
                        "content": snippet.strip(),
                        "snippet": snippet.strip()[:200]
                    })
        
        return parsed


class ResearchPaperRetriever(BaseRetriever):
    """Retrieve from research papers (Arxiv, PDFs, academic databases)"""
    
    def __init__(
        self,
        pdf_directory: str = None,
        embedding_manager=None,
        use_arxiv: bool = True,
        arxiv_query_tool=None
    ):
        """
        Initialize research paper retriever.
        
        Args:
            pdf_directory: Directory containing PDF files
            embedding_manager: For semantic search over PDFs
            use_arxiv: Enable Arxiv academic paper search
            arxiv_query_tool: Optional pre-configured ArxivAPIWrapper
        """
        super().__init__(SourceType.RESEARCH_PAPER)
        self.pdf_directory = pdf_directory
        self.embedding_manager = embedding_manager
        self.documents = []
        self.arxiv_tool = arxiv_query_tool
        
        # Initialize Arxiv if not provided
        if use_arxiv and not arxiv_query_tool:
            self._init_arxiv()
        
        if pdf_directory and os.path.exists(pdf_directory):
            self._load_pdfs()
    
    def _init_arxiv(self):
        """Initialize Arxiv academic paper search tool"""
        try:
            from langchain_community.tools import ArxivQueryRun
            from langchain_community.utilities import ArxivAPIWrapper
            
            arxiv_wrapper = ArxivAPIWrapper()
            self.arxiv_tool = ArxivQueryRun(api_wrapper=arxiv_wrapper)
            print("✅ Arxiv academic paper search initialized")
        except ImportError:
            print("⚠️  ArxivQueryRun not available. Install: pip install arxiv")
        except Exception as e:
            print(f"⚠️  Arxiv initialization failed: {e}")
    
    def _load_pdfs(self):
        """Load and index PDF documents"""
        try:
            from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
            
            loader = DirectoryLoader(
                self.pdf_directory,
                glob="**/*.pdf",
                loader_cls=PyPDFLoader
            )
            self.documents = loader.load()
            print(f"✅ Loaded {len(self.documents)} PDF documents from {self.pdf_directory}")
        
        except ImportError:
            print("⚠️  PyPDFLoader not available. Install: pip install pypdf")
        except Exception as e:
            print(f"⚠️  PDF loading failed: {e}")
    
    def retrieve(self, query: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve from research papers using Arxiv + local PDFs"""
        constraints = constraints or {}
        facts = []
        
        # ============================================================
        # STEP 1: Try Arxiv for academic papers
        # ============================================================
        if self.arxiv_tool:
            try:
                # Query Arxiv with legal/research focus
                arxiv_query = f"{query} law legal regulation"
                arxiv_results = self.arxiv_tool.run(arxiv_query)
                
                if arxiv_results and isinstance(arxiv_results, str):
                    # Parse Arxiv results
                    arxiv_facts = self._parse_arxiv_results(arxiv_results, query)
                    facts.extend(arxiv_facts[:constraints.get("k", 3)])
            
            except Exception as e:
                print(f"⚠️  Arxiv retrieval failed: {e}")
        
        # ============================================================
        # STEP 2: Local PDF semantic search (if embedding_manager available)
        # ============================================================
        if self.documents and self.embedding_manager:
            try:
                query_embedding = self.embedding_manager.embed_text(query)
                
                scored_docs = []
                for doc in self.documents:
                    doc_embedding = self.embedding_manager.embed_text(doc.page_content)
                    score = self._cosine_similarity(query_embedding, doc_embedding)
                    scored_docs.append((doc, score))
                
                scored_docs.sort(key=lambda x: x[1], reverse=True)
                
                for doc, score in scored_docs[:constraints.get("k", 3)]:
                    if score > 0.3:  # Relevance threshold
                        fact = self._create_fact(
                            content=doc.page_content[:500],
                            relevance_score=score,
                            source_details={
                                "file": doc.metadata.get("source", ""),
                                "page": doc.metadata.get("page", 0),
                                "source_type": "local_pdf"
                            },
                            metadata={
                                "document_type": "research_paper",
                                "similarity_score": score
                            }
                        )
                        facts.append(fact)
            
            except Exception as e:
                print(f"⚠️  PDF semantic search failed: {e}")
        
        return facts
    
    def _parse_arxiv_results(self, arxiv_output: str, query: str) -> List[Dict[str, Any]]:
        """Parse Arxiv API results into standardized facts"""
        facts = []
        
        try:
            # Parse Arxiv results (typically includes title, authors, abstract, url)
            lines = arxiv_output.split("\n")
            
            for line in lines:
                if line.strip() and len(line) > 50:  # Skip short lines
                    fact = self._create_fact(
                        content=line[:500],
                        relevance_score=0.7,
                        source_details={
                            "source": "arxiv",
                            "query": query,
                            "database": "arxiv.org"
                        },
                        metadata={
                            "document_type": "academic_paper",
                            "source": "arxiv"
                        }
                    )
                    facts.append(fact)
        
        except Exception as e:
            print(f"⚠️  Arxiv parsing failed: {e}")
        
        return facts
    
    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
        except:
            return 0.0


class ManualInputRetriever(BaseRetriever):
    """Handle lawyer-provided facts"""
    
    def __init__(self):
        """Initialize manual input retriever"""
        super().__init__(SourceType.MANUAL_INPUT)
        self.manual_facts = []
    
    def add_fact(self, content: str, tags: List[str] = None):
        """
        Add manually entered fact.
        
        Args:
            content: Fact text
            tags: Optional tags for categorization
        """
        fact = self._create_fact(
            content=content,
            relevance_score=1.0,  # Manual input has highest confidence
            source_details={"tags": tags or []},
            metadata={"input_type": "manual", "tags": tags or []}
        )
        self.manual_facts.append(fact)
        return fact
    
    def retrieve(self, query: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve manually added facts matching query"""
        constraints = constraints or {}
        query_lower = query.lower()
        
        matching_facts = [
            fact for fact in self.manual_facts
            if query_lower in fact["content"].lower() or 
               any(tag.lower() in query_lower for tag in fact["metadata"].get("tags", []))
        ]
        
        # Sort by relevance (manual input first)
        matching_facts.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return matching_facts[:constraints.get("k", 10)]
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all manually added facts"""
        return self.manual_facts
    
    def clear(self):
        """Clear all manual facts"""
        self.manual_facts.clear()


class CompositeRetriever(BaseRetriever):
    """Aggregates multiple retrievers with ranking and deduplication"""
    
    def __init__(self, retrievers: List[BaseRetriever] = None):
        """
        Initialize composite retriever.
        
        Args:
            retrievers: List of retriever instances
        """
        super().__init__(SourceType.VECTOR_STORE)
        self.retrievers = retrievers or []
    
    def add_retriever(self, retriever: BaseRetriever):
        """Add a retriever to the composite"""
        self.retrievers.append(retriever)
    
    def retrieve(
        self,
        query: str,
        constraints: Dict[str, Any] = None,
        source_weights: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve from all retrievers and aggregate results.
        
        Args:
            query: Search query
            constraints: Query constraints (k, filters, etc.)
            source_weights: Weight for each source type
                           e.g., {"vector_store": 1.0, "web_search": 0.7}
        
        Returns:
            Ranked list of unique facts
        """
        constraints = constraints or {}
        source_weights = source_weights or {}
        all_facts = []
        
        # Retrieve from each source
        for retriever in self.retrievers:
            try:
                source_key = retriever.source_type.value
                weight = source_weights.get(source_key, 1.0)
                
                facts = retriever.retrieve(query, constraints)
                
                # Apply source weight
                for fact in facts:
                    fact["weighted_score"] = fact.get("relevance_score", 0.5) * weight
                
                all_facts.extend(facts)
            
            except Exception as e:
                print(f"⚠️  Retriever {retriever.name} failed: {e}")
        
        # Deduplicate by fact hash
        seen_hashes = set()
        unique_facts = []
        for fact in all_facts:
            fact_hash = fact.get("fact_hash")
            if fact_hash not in seen_hashes:
                seen_hashes.add(fact_hash)
                unique_facts.append(fact)
        
        # Sort by weighted score
        unique_facts.sort(key=lambda x: x.get("weighted_score", 0), reverse=True)
        
        # Return top k
        return unique_facts[:constraints.get("k", 10)]
    
    def retrieve_by_source(
        self,
        query: str,
        source_type: SourceType,
        constraints: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve from a specific source type only"""
        constraints = constraints or {}
        
        for retriever in self.retrievers:
            if retriever.source_type == source_type:
                return retriever.retrieve(query, constraints)
        
        return []


class FactRetrieverFactory:
    """Factory for creating retrievers"""
    
    @staticmethod
    def create_vector_store_retriever(
        embedding_manager,
        vector_stores: Dict[str, Any] = None
    ) -> VectorStoreRetriever:
        """Create vector store retriever"""
        return VectorStoreRetriever(embedding_manager, vector_stores)
    
    @staticmethod
    def create_web_search_retriever(
        search_tool=None,
        search_engine: str = "tavily"
    ) -> WebSearchRetriever:
        """Create web search retriever"""
        return WebSearchRetriever(search_tool, search_engine)
    
    @staticmethod
    def create_research_paper_retriever(
        pdf_directory: str = None,
        embedding_manager=None
    ) -> ResearchPaperRetriever:
        """Create research paper retriever"""
        return ResearchPaperRetriever(pdf_directory, embedding_manager)
    
    @staticmethod
    def create_manual_input_retriever() -> ManualInputRetriever:
        """Create manual input retriever"""
        return ManualInputRetriever()
    
    @staticmethod
    def create_composite_retriever(
        embedding_manager,
        vector_stores: Dict[str, Any] = None,
        enable_web_search: bool = True,
        enable_research_papers: bool = False,
        pdf_directory: str = None
    ) -> CompositeRetriever:
        """
        Create a composite retriever with all available sources.
        
        Args:
            embedding_manager: For embeddings
            vector_stores: Vector store instances
            enable_web_search: Include web search
            enable_research_papers: Include research papers
            pdf_directory: Directory with PDFs
        
        Returns:
            CompositeRetriever with all configured sources
        """
        composite = CompositeRetriever()
        
        # Add vector store retriever (always included)
        vs_retriever = FactRetrieverFactory.create_vector_store_retriever(
            embedding_manager,
            vector_stores
        )
        composite.add_retriever(vs_retriever)
        
        # Add web search if enabled
        if enable_web_search:
            web_retriever = FactRetrieverFactory.create_web_search_retriever()
            composite.add_retriever(web_retriever)
        
        # Add research paper retriever if enabled
        if enable_research_papers and pdf_directory:
            paper_retriever = FactRetrieverFactory.create_research_paper_retriever(
                pdf_directory,
                embedding_manager
            )
            composite.add_retriever(paper_retriever)
        
        # Add manual input retriever
        manual_retriever = FactRetrieverFactory.create_manual_input_retriever()
        composite.add_retriever(manual_retriever)
        
        return composite


class GoogleScholarRetriever(BaseRetriever):
    """Retrieve from Google Scholar for legal citations and academic papers"""
    
    def __init__(self):
        super().__init__(SourceType.WEB_SEARCH)
        self.name = "GoogleScholarRetriever"
    
    def retrieve(self, query: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve from Google Scholar"""
        constraints = constraints or {}
        facts = []
        
        try:
            # Use scholarly library if available
            try:
                from scholarly import scholarly
                search_query = scholarly.search_pubs(query)
                
                for idx, pub in enumerate(search_query):
                    if idx >= constraints.get("k", 3):
                        break
                    
                    title = pub.get('bib', {}).get('title', 'Unknown')
                    abstract = pub.get('bib', {}).get('abstract', '')
                    authors = ', '.join(pub.get('bib', {}).get('author', []))
                    year = pub.get('bib', {}).get('pub_year', '')
                    url = pub.get('pub_url', '')
                    
                    content = f"Title: {title}\nAuthors: {authors}\nYear: {year}\nAbstract: {abstract[:500]}"
                    
                    fact = self._create_fact(
                        content=content,
                        relevance_score=0.7,
                        source_details={
                            "title": title,
                            "authors": authors,
                            "year": year,
                            "url": url,
                            "abstract": abstract[:500]
                        },
                        metadata={"source": "google_scholar", "rank": idx + 1}
                    )
                    facts.append(fact)
            except ImportError:
                print("   ℹ️  scholarly library not installed. Install: pip install scholarly")
        except Exception as e:
            print(f"   ⚠️  Google Scholar search failed: {e}")
        
        return facts


class ArxivRetriever(BaseRetriever):
    """Retrieve from ArXiv for legal research papers"""
    
    def __init__(self):
        super().__init__(SourceType.RESEARCH_PAPER)
        self.name = "ArxivRetriever"
    
    def retrieve(self, query: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve from ArXiv"""
        constraints = constraints or {}
        facts = []
        
        try:
            import arxiv
            
            # Search ArXiv
            search = arxiv.Search(
                query=query,
                max_results=constraints.get("k", 2),
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            for idx, result in enumerate(search.results()):
                content = f"Title: {result.title}\nAuthors: {', '.join([a.name for a in result.authors])}\nPublished: {result.published}\nSummary: {result.summary[:500]}"
                
                fact = self._create_fact(
                    content=content,
                    relevance_score=0.65,
                    source_details={
                        "title": result.title,
                        "authors": [a.name for a in result.authors],
                        "published": str(result.published),
                        "url": result.entry_id,
                        "pdf_url": result.pdf_url,
                        "summary": result.summary[:500]
                    },
                    metadata={"source": "arxiv", "rank": idx + 1}
                )
                facts.append(fact)
        except ImportError:
            print("   ℹ️  arxiv library not installed. Install: pip install arxiv")
        except Exception as e:
            print(f"   ⚠️  ArXiv search failed: {e}")
        
        return facts


class IndianLegalDBRetriever(BaseRetriever):
    """Retrieve from Indian legal databases (IndianKanoon, etc.)"""
    
    def __init__(self):
        super().__init__(SourceType.WEB_SEARCH)
        self.name = "IndianLegalDBRetriever"
    
    def retrieve(self, query: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve from Indian legal databases via web scraping/API"""
        constraints = constraints or {}
        facts = []
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # IndianKanoon search
            search_url = "https://indiankanoon.org/search/"
            params = {"formInput": query}
            
            try:
                response = requests.get(search_url, params=params, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    results = soup.find_all('div', class_='result', limit=constraints.get("k", 4))
                    
                    for idx, result in enumerate(results):
                        title_elem = result.find('a', class_='result_title')
                        snippet_elem = result.find('div', class_='snippet')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            url = "https://indiankanoon.org" + title_elem.get('href', '')
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                            
                            content = f"Case: {title}\nExcerpt: {snippet[:500]}"
                            
                            fact = self._create_fact(
                                content=content,
                                relevance_score=0.8,
                                source_details={
                                    "case_name": title,
                                    "url": url,
                                    "snippet": snippet[:500],
                                    "database": "IndianKanoon"
                                },
                                metadata={"source": "indian_kanoon", "rank": idx + 1}
                            )
                            facts.append(fact)
            except requests.RequestException as e:
                print(f"   ⚠️  IndianKanoon request failed: {e}")
                
        except ImportError:
            print("   ℹ️  beautifulsoup4 not installed. Install: pip install beautifulsoup4 requests")
        except Exception as e:
            print(f"   ⚠️  Indian legal DB search failed: {e}")
        
        return facts
