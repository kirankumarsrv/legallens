"""
FastAPI REST API backend for lawyer agent case workflow.

Exposes endpoints for:
- Case management (create, list, delete)
- Facts (list, get, create, update, approve, reject, lock)
- Arguments (list, get, create, update, approve, reject, lock)
- Predictions (list, get, restore)
- Workflow state flags (get, set, clear)

Run:
    uvicorn workflows.lawyer_agent.api:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
import uuid
import json

from modules.case_session_storage import CaseSessionStorage
from modules.fact_storage import FactStorage
from modules.argument_storage import ArgumentStorage
from modules.llm_manager import LLMManager
import os
from dotenv import load_dotenv

# Workflow nodes
from workflows.lawyer_agent.nodes.evidence_ingest import evidence_ingest_node
from workflows.lawyer_agent.nodes.fact_gathering import fact_gathering_node
from workflows.lawyer_agent.nodes.legal_analysis import legal_analysis_node
from workflows.lawyer_agent.nodes.prediction import prediction_node
from workflows.lawyer_agent.nodes.draft_generation import draft_generation_node
from modules.embedding_manager import EmbeddingManager
try:
    from langchain_chroma import Chroma
except Exception:
    Chroma = None
try:
    from modules.vector_store.FAISS_vector_store import FAISSVectorStore
except Exception:
    FAISSVectorStore = None

# Cached dependencies
_DEPENDENCIES = None

# Ensure environment variables from .env are loaded when the app imports this module
try:
    load_dotenv()
except Exception:
    pass


def get_dependencies():
    """Initialize and return shared dependencies (llm, embedding_model, chroma_stores, faiss_store).

    Reads environment variables for configuration. Caches result in-module for reuse.
    """
    global _DEPENDENCIES
    if _DEPENDENCIES is not None:
        return _DEPENDENCIES

    print("\n" + "="*80)
    print("DEPENDENCY INITIALIZATION AT STARTUP")
    print("="*80)
    
    # Embedding model
    emb_model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
    emb_device = os.getenv("EMBEDDING_DEVICE", None)
    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HUGGINGFACE_API_TOKEN")
    
    print(f"\n📦 EMBEDDING MODEL CONFIG:")
    print(f"   Model Name (EMBEDDING_MODEL): {emb_model_name}")
    print(f"   Device (EMBEDDING_DEVICE): {emb_device or 'auto'}")
    print(f"   HuggingFace Token Present: {'✅ YES' if hf_token else '❌ NO'}")
    
    try:
        print(f"   Attempting to initialize EmbeddingManager...")
        embedding_model = EmbeddingManager(model_name=emb_model_name, device=emb_device)
        print(f"   ✅ EmbeddingManager initialized successfully")
    except Exception as e:
        print(f"   ❌ FAILED to initialize EmbeddingManager('{emb_model_name}'):")
        print(f"      Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        embedding_model = None

    # LLM
    llm_provider = os.getenv("LLM_PROVIDER", "groq")
    llm_model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    try:
        llm = LLMManager(provider=llm_provider, model_name=llm_model)
    except Exception:
        llm = None

    # Chroma stores (statutory collections)
    chroma_stores = {}
    if Chroma and embedding_model:
        try:
            chroma_stores["constitution"] = Chroma(collection_name="constitution", persist_directory="vector_db/chroma/constitution", embedding_function=embedding_model)
        except Exception as e:
            print(f"WARNING: failed to init Chroma 'constitution' store: {e}")
        try:
            chroma_stores["ipc"] = Chroma(collection_name="ipc", persist_directory="vector_db/chroma/ipc", embedding_function=embedding_model)
        except Exception as e:
            print(f"WARNING: failed to init Chroma 'ipc' store: {e}")
        try:
            chroma_stores["crpc"] = Chroma(collection_name="crpc", persist_directory="vector_db/chroma/crpc", embedding_function=embedding_model)
        except Exception as e:
            print(f"WARNING: failed to init Chroma 'crpc' store: {e}")
    else:
        if not Chroma:
            print("INFO: Chroma library not available (Chroma=None)")
        if not embedding_model:
            print("INFO: embedding_model not initialized; skipping Chroma stores")

    # FAISS store for precedents
    faiss_store = None
    if FAISSVectorStore and embedding_model:
        try:
            faiss_store = FAISSVectorStore(embedding_model=embedding_model)
        except Exception:
            print("WARNING: failed to initialize FAISSVectorStore")
            faiss_store = None
    else:
        if not FAISSVectorStore:
            print("INFO: FAISSVectorStore class not available")
        if not embedding_model:
            print("INFO: embedding_model not initialized; skipping FAISS store")

    _DEPENDENCIES = {
        "llm": llm,
        "embedding_model": embedding_model,
        "chroma_stores": chroma_stores,
        "faiss_store": faiss_store,
    }
    return _DEPENDENCIES

# ============================================================================
# Pydantic Models
# ============================================================================

class FactRequest(BaseModel):
    """Request model for creating/updating a fact."""
    content: str
    source: str = "manual"
    source_details: Optional[Dict[str, Any]] = None
    relevance_score: float = 0.5


class FactResponse(BaseModel):
    """Response model for a fact."""
    id: str
    content: str
    source: str
    source_details: Optional[Dict[str, Any]] = None
    llm_summary: Optional[str] = None
    case_reference: Optional[str] = None  # New field for detailed case info (case name, id, year)
    relevance_score: float
    status: str
    created_at: Optional[str] = None
    approved_at: Optional[str] = None


class ArgumentRequest(BaseModel):
    """Request model for creating/updating an argument."""
    content: str
    legal_basis: str = ""
    relevance_score: float = 0.5
    fact_ids: List[str] = []


class ArgumentResponse(BaseModel):
    """Response model for an argument."""
    id: str
    content: str
    legal_basis: str
    relevance_score: float
    status: str
    fact_ids: List[str] = []
    created_at: Optional[str] = None
    approved_at: Optional[str] = None


class PredictionHistoryItem(BaseModel):
    """A prediction history entry."""
    timestamp: str
    prediction: str
    prediction_confidence: float
    similar_cases: List[Dict[str, Any]]
    analysis_snapshot: str
    facts_snapshot: List[Dict[str, Any]]


class CaseInfo(BaseModel):
    """Case metadata."""
    case_id: str
    case_name: str
    status: str = "in_progress"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    fact_count: int = 0
    argument_count: int = 0


class CreateCaseRequest(BaseModel):
    """Request model for creating a case via POST /cases."""
    case_name: str
    case_type: Optional[str] = None


class StateFlags(BaseModel):
    """Workflow state flags."""
    facts_edited: bool = False
    arguments_edited: bool = False
    recompute_prediction: bool = False
    restore_prediction_index: Optional[int] = None


class ComputeRequest(BaseModel):
    question: str
    evidence_files: Optional[List[str]] = None
    enable_web_search: bool = False
    enable_research_papers: bool = False
    enable_google_scholar: bool = True
    enable_arxiv: bool = True
    enable_indian_legal_db: bool = True
    pdf_directory: Optional[str] = None


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Lawyer Agent API",
    description="REST API for case workflow management",
    version="1.0.0"
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (configure for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "case_sessions.db"
EVIDENCE_UPLOAD_DIR = "evidence_uploads"


# ============================================================================
# Case Management Endpoints
# ============================================================================

@app.get("/cases", response_model=List[CaseInfo])
def list_cases():
    """List all cases with their metadata."""
    try:
        case_ids = CaseSessionStorage.get_all_cases(DB_PATH)
        if not case_ids:
            return []
        
        cases = []
        for case_id in case_ids:
            try:
                storage = CaseSessionStorage(case_id, DB_PATH)
                state_flags = storage.get_all_state_flags()
                
                # Get case metadata from state flags
                case_name = state_flags.get("case_name", case_id)
                status = storage.get_case_status() or "in_progress"
                
                # Count facts and arguments
                facts_data = storage.load_facts()
                args_data = storage.load_arguments()
                fact_count = len(facts_data.get("facts", [])) if facts_data else 0
                arg_count = len(args_data.get("arguments", [])) if args_data else 0
                
                # Get timestamps with fallback
                now = datetime.now(timezone.utc).isoformat()
                created_at = state_flags.get("created_at", now)
                updated_at = state_flags.get("updated_at", now)
                
                cases.append(CaseInfo(
                    case_id=case_id,
                    case_name=case_name,
                    status=status,
                    created_at=created_at,
                    updated_at=updated_at,
                    fact_count=fact_count,
                    argument_count=arg_count
                ))
            except Exception as case_err:
                print(f"Error loading case {case_id}: {case_err}")
                continue
        
        return cases
    except Exception as e:
        print(f"Error in list_cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases", response_model=CaseInfo)
def create_case(request: CreateCaseRequest):
    """Create a new case. Expects JSON body with `case_name` and optional `case_type`."""
    try:
        # Generate a unique case_id (UUID4 hex)
        case_id = uuid.uuid4().hex
        storage = CaseSessionStorage(case_id, DB_PATH)
        
        # Ensure case session exists in database
        storage.set_case_status("in_progress")
        
        # Store case metadata
        now = datetime.now(timezone.utc).isoformat()
        case_name = request.case_name if request.case_name else f"Case {case_id[:8]}"
        
        storage.set_state_flag("case_name", case_name)
        storage.set_state_flag("case_type", request.case_type or "")
        storage.set_state_flag("created_at", now)
        storage.set_state_flag("updated_at", now)
        
        # Verify case was saved to database
        all_cases = CaseSessionStorage.get_all_cases(DB_PATH)
        if case_id not in all_cases:
            print(f"⚠️  WARNING: Case {case_id} was not saved to database!")
            raise HTTPException(status_code=500, detail="Case could not be saved to database")
        
        print(f"✅ Case created and saved to database: {case_id} (name: {case_name})")
        
        return CaseInfo(
            case_id=case_id,
            case_name=case_name,
            created_at=now,
            updated_at=now,
            status="in_progress",
            fact_count=0,
            argument_count=0
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cases/{case_id}", response_model=CaseInfo)
def get_case(case_id: str):
    """Get case metadata."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        state_flags = storage.get_all_state_flags()
        status = storage.get_case_status() or "in_progress"
        
        # Get case metadata from state flags
        case_name = state_flags.get("case_name", case_id)
        now = datetime.now(timezone.utc).isoformat()
        created_at = state_flags.get("created_at", now)
        updated_at = state_flags.get("updated_at", now)
        
        # Count facts and arguments
        facts_data = storage.load_facts()
        args_data = storage.load_arguments()
        fact_count = len(facts_data.get("facts", [])) if facts_data else 0
        arg_count = len(args_data.get("arguments", [])) if args_data else 0
        
        return CaseInfo(
            case_id=case_id,
            case_name=case_name,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            fact_count=fact_count,
            argument_count=arg_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/cases/{case_id}")
def delete_case(case_id: str):
    """Delete a case and all its data."""
    try:
        CaseSessionStorage.delete_case(case_id, DB_PATH)
        return {"status": "deleted", "case_id": case_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Facts Endpoints
# ============================================================================

@app.get("/cases/{case_id}/facts", response_model=List[FactResponse])
def list_facts(case_id: str):
    """List all facts for a case."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        facts_data = storage.load_facts()
        if not facts_data:
            return []
        fs = FactStorage.from_dict(facts_data)
        facts = fs.get_all_facts()
        # Populate top-level llm_summary and case_reference from source_details if present
        for f in facts:
            if not f.get("llm_summary") and f.get("source_details"):
                f["llm_summary"] = f["source_details"].get("llm_summary")
            if not f.get("case_reference") and f.get("source_details"):
                f["case_reference"] = f["source_details"].get("case_reference")
        return [FactResponse(**f) for f in facts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cases/{case_id}/facts/{fact_id}", response_model=FactResponse)
def get_fact(case_id: str, fact_id: str):
    """Get a specific fact."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        facts_data = storage.load_facts()
        if not facts_data:
            raise HTTPException(status_code=404, detail="Fact not found")
        fs = FactStorage.from_dict(facts_data)
        fact = fs.get_fact(fact_id)
        if not fact:
            raise HTTPException(status_code=404, detail="Fact not found")
        # expose llm_summary and case_reference at top-level for frontend convenience
        if not fact.get("llm_summary") and fact.get("source_details"):
            fact["llm_summary"] = fact["source_details"].get("llm_summary")
        if not fact.get("case_reference") and fact.get("source_details"):
            fact["case_reference"] = fact["source_details"].get("case_reference")
        return FactResponse(**fact)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/facts", response_model=FactResponse)
def create_fact(case_id: str, fact: FactRequest):
    """Create a new fact."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        fs = FactStorage()
        facts_data = storage.load_facts()
        if facts_data:
            fs = FactStorage.from_dict(facts_data)
        
        fact_id = fs.add_fact(
            content=fact.content,
            source=fact.source,
            source_details=fact.source_details,
            relevance_score=fact.relevance_score
        )
        
        storage.save_facts(fs.to_dict())
        created_fact = fs.get_fact(fact_id)
        if not created_fact.get("llm_summary") and created_fact.get("source_details"):
            created_fact["llm_summary"] = created_fact["source_details"].get("llm_summary")
        return FactResponse(**created_fact)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/cases/{case_id}/facts/{fact_id}", response_model=FactResponse)
def update_fact(case_id: str, fact_id: str, fact: FactRequest):
    """Update a fact."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        facts_data = storage.load_facts()
        if not facts_data:
            raise HTTPException(status_code=404, detail="Fact not found")
        fs = FactStorage.from_dict(facts_data)
        
        fs.update_fact(fact_id, content=fact.content)
        storage.save_facts(fs.to_dict())
        
        updated_fact = fs.get_fact(fact_id)
        if not updated_fact.get("llm_summary") and updated_fact.get("source_details"):
            updated_fact["llm_summary"] = updated_fact["source_details"].get("llm_summary")
        return FactResponse(**updated_fact)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/facts/{fact_id}/approve")
def approve_fact(case_id: str, fact_id: str):
    """Approve a fact."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        facts_data = storage.load_facts()
        if not facts_data:
            raise HTTPException(status_code=404, detail="Fact not found")
        fs = FactStorage.from_dict(facts_data)
        
        fs.approve_fact(fact_id)
        storage.save_facts(fs.to_dict())
        storage.set_state_flag("facts_edited", True)
        
        updated_fact = fs.get_fact(fact_id)
        if not updated_fact.get("llm_summary") and updated_fact.get("source_details"):
            updated_fact["llm_summary"] = updated_fact["source_details"].get("llm_summary")
        return FactResponse(**updated_fact)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/facts/{fact_id}/reject")
def reject_fact(case_id: str, fact_id: str):
    """Reject a fact."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        facts_data = storage.load_facts()
        if not facts_data:
            raise HTTPException(status_code=404, detail="Fact not found")
        fs = FactStorage.from_dict(facts_data)
        
        fs.reject_fact(fact_id)
        storage.save_facts(fs.to_dict())
        storage.set_state_flag("facts_edited", True)
        
        updated_fact = fs.get_fact(fact_id)
        if not updated_fact.get("llm_summary") and updated_fact.get("source_details"):
            updated_fact["llm_summary"] = updated_fact["source_details"].get("llm_summary")
        return FactResponse(**updated_fact)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/facts/lock")
def lock_approved_facts(case_id: str):
    """Lock all approved facts."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        facts_data = storage.load_facts()
        if not facts_data:
            return {"status": "no_facts"}
        fs = FactStorage.from_dict(facts_data)
        
        fs.lock_approved_facts()
        storage.save_facts(fs.to_dict())
        storage.set_state_flag("facts_edited", True)
        # Mark facts as approved and locked so subsequent compute runs skip re-retrieval
        storage.set_state_flag("facts_approved_and_locked", True)
        
        return {"status": "locked", "count": len(fs.approved_fact_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/facts/{fact_id}/lock")
def lock_single_fact(case_id: str, fact_id: str):
    """Lock a single approved fact (adds approved_locked status).

    This supports frontend flows that try to lock an individual fact.
    If the fact is not yet approved, it will be approved and then locked.
    If all approved facts become locked, the case state flag `facts_approved_and_locked`
    will be set to True so future compute runs can skip re-retrieval.
    """
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        facts_data = storage.load_facts()
        if not facts_data:
            return {"status": "no_facts"}
        fs = FactStorage.from_dict(facts_data)

        fact = fs.get_fact(fact_id)
        if not fact:
            raise HTTPException(status_code=404, detail="Fact not found")

        # Ensure fact is approved, then mark as locked
        fs.approve_fact(fact_id)
        if fact_id in fs.facts:
            fs.facts[fact_id]["status"] = "approved_locked"
            fs.facts[fact_id]["updated_at"] = datetime.now().isoformat()

        storage.save_facts(fs.to_dict())
        storage.set_state_flag("facts_edited", True)

        # If all approved facts are locked, set the global flag
        if fs.is_facts_approved_and_locked():
            storage.set_state_flag("facts_approved_and_locked", True)

        return {"status": "locked", "fact_id": fact_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Arguments Endpoints
# ============================================================================

@app.get("/cases/{case_id}/arguments", response_model=List[ArgumentResponse])
def list_arguments(case_id: str):
    """List all arguments for a case."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        args_data = storage.load_arguments()
        if not args_data:
            return []
        arg_store = ArgumentStorage.from_dict(args_data)
        args = arg_store.get_all_arguments()
        return [ArgumentResponse(**a) for a in args]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cases/{case_id}/arguments/{arg_id}", response_model=ArgumentResponse)
def get_argument(case_id: str, arg_id: str):
    """Get a specific argument."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        args_data = storage.load_arguments()
        if not args_data:
            raise HTTPException(status_code=404, detail="Argument not found")
        arg_store = ArgumentStorage.from_dict(args_data)
        arg = arg_store.get_argument(arg_id)
        if not arg:
            raise HTTPException(status_code=404, detail="Argument not found")
        return ArgumentResponse(**arg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/arguments", response_model=ArgumentResponse)
def create_argument(case_id: str, argument: ArgumentRequest):
    """Create a new argument."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        arg_store = ArgumentStorage()
        args_data = storage.load_arguments()
        if args_data:
            arg_store = ArgumentStorage.from_dict(args_data)
        
        arg_id = arg_store.add_argument(
            content=argument.content,
            legal_basis=argument.legal_basis,
            fact_ids=argument.fact_ids
        )
        
        storage.save_arguments(arg_store.to_dict())
        created_arg = arg_store.get_argument(arg_id)
        return ArgumentResponse(**created_arg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/cases/{case_id}/arguments/{arg_id}", response_model=ArgumentResponse)
def update_argument(case_id: str, arg_id: str, argument: ArgumentRequest):
    """Update an argument."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        args_data = storage.load_arguments()
        if not args_data:
            raise HTTPException(status_code=404, detail="Argument not found")
        arg_store = ArgumentStorage.from_dict(args_data)
        
        arg_store.update_argument(arg_id, content=argument.content)
        # Update fact_ids manually since update_argument doesn't have fact_ids parameter
        if arg_id in arg_store.arguments:
            arg_store.arguments[arg_id]["fact_ids"] = argument.fact_ids
            arg_store.arguments[arg_id]["updated_at"] = datetime.now().isoformat()
        storage.save_arguments(arg_store.to_dict())
        storage.set_state_flag("arguments_edited", True)
        
        updated_arg = arg_store.get_argument(arg_id)
        return ArgumentResponse(**updated_arg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/arguments/{arg_id}/approve")
def approve_argument(case_id: str, arg_id: str):
    """Approve an argument."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        args_data = storage.load_arguments()
        if not args_data:
            raise HTTPException(status_code=404, detail="Argument not found")
        arg_store = ArgumentStorage.from_dict(args_data)
        
        arg_store.approve_argument(arg_id)
        storage.save_arguments(arg_store.to_dict())
        storage.set_state_flag("arguments_edited", True)
        
        updated_arg = arg_store.get_argument(arg_id)
        return ArgumentResponse(**updated_arg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/arguments/{arg_id}/reject")
def reject_argument(case_id: str, arg_id: str):
    """Reject an argument."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        args_data = storage.load_arguments()
        if not args_data:
            raise HTTPException(status_code=404, detail="Argument not found")
        arg_store = ArgumentStorage.from_dict(args_data)
        
        arg_store.reject_argument(arg_id)
        storage.save_arguments(arg_store.to_dict())
        storage.set_state_flag("arguments_edited", True)
        
        updated_arg = arg_store.get_argument(arg_id)
        return ArgumentResponse(**updated_arg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/arguments/lock")
def lock_approved_arguments(case_id: str):
    """Lock all approved arguments."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        args_data = storage.load_arguments()
        if not args_data:
            return {"status": "no_arguments"}
        arg_store = ArgumentStorage.from_dict(args_data)
        
        arg_store.lock_approved_arguments()
        storage.save_arguments(arg_store.to_dict())
        storage.set_state_flag("arguments_edited", True)
        
        return {"status": "locked", "count": len(arg_store.approved_arg_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Prediction Endpoints
# ============================================================================

@app.get("/cases/{case_id}/predictions", response_model=List[PredictionHistoryItem])
def list_predictions(case_id: str):
    """List prediction history for a case."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        history = storage.load_prediction_history()
        return [PredictionHistoryItem(**item) for item in history]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/predictions/restore/{index}")
def restore_prediction(case_id: str, index: int):
    """Restore a prediction from history by index."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        history = storage.load_prediction_history()
        if index < 0 or index >= len(history):
            raise HTTPException(status_code=404, detail="Prediction index out of range")
        
        storage.set_state_flag("restore_prediction_index", index)
        return {"status": "restore_queued", "index": index}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# State Flags Endpoints
# ============================================================================

@app.get("/cases/{case_id}/state", response_model=StateFlags)
def get_state(case_id: str):
    """Get all workflow state flags for a case."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        flags = storage.get_all_state_flags()
        return StateFlags(
            facts_edited=flags.get("facts_edited", False),
            arguments_edited=flags.get("arguments_edited", False),
            recompute_prediction=flags.get("recompute_prediction", False),
            restore_prediction_index=flags.get("restore_prediction_index")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/state/{flag_key}")
def set_state_flag(case_id: str, flag_key: str, value: Any):
    """Set a state flag."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        storage.set_state_flag(flag_key, value)
        return {"flag": flag_key, "value": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/cases/{case_id}/state/{flag_key}")
def clear_state_flag(case_id: str, flag_key: str):
    """Clear a state flag."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        storage.clear_state_flag(flag_key)
        return {"status": "cleared", "flag": flag_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/draft")
def generate_draft(case_id: str):
    """Generate a legal draft/memorandum from the current case analysis, arguments, and prediction.
    
    Requires that legal_analysis and prediction phases have already been completed.
    """
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        
        # Load current state
        state = {
            "question": storage.get_state_flag("problem_statement") or "",
            "analysis": None,
            "prediction": None,
            "fact_storage": None,
            "argument_storage": None,
            "statutes": None,
            "precedents": None,
            "draft": None,
            "reasoning_trace": []
        }
        
        # Load facts if available
        facts_data = storage.load_facts()
        if facts_data:
            try:
                state["fact_storage"] = FactStorage.from_dict(facts_data)
            except Exception:
                pass
        
        # Load arguments if available
        args_data = storage.load_arguments()
        if args_data:
            try:
                from modules.argument_storage import ArgumentStorage as ArgStore
                state["argument_storage"] = ArgStore.from_dict(args_data)
            except Exception:
                pass
        
        # Get LLM
        deps = get_dependencies()
        llm = deps.get("llm")
        if llm is None:
            class SimpleLLM:
                def generate(self, prompt, *a, **k):
                    return "(placeholder LLM) Draft generation unavailable — configure LLM provider."
            llm = SimpleLLM()
        
        # Run draft generation
        state = draft_generation_node(state=state, llm=llm)
        
        return {
            "status": "ok",
            "draft": state.get("draft"),
            "case_id": case_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



def compute_case(case_id: str, request: ComputeRequest):
    """Run the synchronous compute pipeline for a single case.

    Steps executed (synchronously):
      0. Evidence ingest
      1. Fact gathering (multi-source retrieval)
      2. Legal analysis (uses approved facts when locked)
      3. Prediction (with history/backtrack support)

    This endpoint is designed for the UI to trigger the full workflow and
    receive the updated state as response for interactive display.
    """
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)

        # Initialize state
        storage = CaseSessionStorage(case_id, DB_PATH)

        # If request.question is empty, fall back to persisted problem_statement
        question_text = request.question or storage.get_state_flag("problem_statement") or ""

        state = {
            "question": question_text,
            "evidence_files": request.evidence_files or None,
            "evidence_text": None,
            "detected_language": None,
            "source_language_name": None,
            "entities": None,
            "timeline": None,
            "facts": None,
            "facts_raw": None,
            "fact_storage": None,
            "facts_approved_and_locked": storage.get_state_flag("facts_approved_and_locked", False),
            "analysis": None,
            "statutes": None,
            "precedents": None,
            "prediction": None,
            "similar_cases": None,
            "prediction_confidence": None,
            "draft": None,
            "approved_phase": None,
            "user_feedback": None,
            "reasoning_trace": []
        }

        # If facts/arguments were already persisted, load them
        facts_data = storage.load_facts()
        if facts_data:
            try:
                state["fact_storage"] = FactStorage.from_dict(facts_data)
                state["facts_raw"] = [f.get("content") for f in state["fact_storage"].get_all_facts()]
            except Exception:
                state["fact_storage"] = None

        args_data = storage.load_arguments()
        if args_data:
            try:
                from modules.argument_storage import ArgumentStorage as ArgStore
                state["argument_storage"] = ArgStore.from_dict(args_data)
            except Exception:
                state["argument_storage"] = None

        # Prepare real connectors from environment via get_dependencies()
        deps = get_dependencies()
        chroma_stores = deps.get("chroma_stores")
        embedding_model = deps.get("embedding_model")
        faiss_store = deps.get("faiss_store")
        llm = deps.get("llm")

        # Fallback simple LLM if real LLM not available
        if llm is None:
            class SimpleLLM:
                def generate(self, prompt, *a, **k):
                    return "(placeholder LLM) Analysis/prediction unavailable — configure LLM provider."
            llm = SimpleLLM()

        # Phase 0: Evidence ingestion
        state = evidence_ingest_node(state)

        # Phase 1: Fact gathering (multi-source)
        # Skip retrieval if facts already approved & locked
        if not storage.get_state_flag("facts_approved_and_locked", False):
            state = fact_gathering_node(
                state=state,
                chroma_stores=chroma_stores,
                embedding_model=embedding_model,
                faiss_store=faiss_store,
                llm=llm,
                enable_web_search=request.enable_web_search,
                enable_research_papers=request.enable_research_papers,
                enable_google_scholar=request.enable_google_scholar,
                enable_arxiv=request.enable_arxiv,
                enable_indian_legal_db=request.enable_indian_legal_db,
                pdf_directory=request.pdf_directory,
            )
        else:
            state["reasoning_trace"].append("PHASE 1: Skipped fact gathering (facts already approved and locked)")

        # Persist facts to storage
        try:
            if state.get("fact_storage"):
                storage.save_facts(state["fact_storage"].to_dict())
                storage.set_state_flag("facts_edited", True)
        except Exception:
            pass

        # Phase 2: Legal analysis
        state = legal_analysis_node(state=state, chroma_stores=chroma_stores, embedding_model=embedding_model, faiss_store=faiss_store, llm=llm)

        # Persist arguments if generated
        try:
            if state.get("argument_storage"):
                storage.save_arguments(state["argument_storage"].to_dict())
                storage.set_state_flag("arguments_edited", True)
        except Exception:
            pass

        # Phase 3: Prediction
        state = prediction_node(state=state, faiss_store=faiss_store, llm=llm, embedding_model=embedding_model)

        # Persist prediction history (if available)
        try:
            if state.get("prediction_history"):
                storage.save_prediction_history(state["prediction_history"])
        except Exception:
            pass

        # Phase 4: Draft generation
        state = draft_generation_node(state=state, llm=llm)

        # Update overall case status
        try:
            storage.set_case_status("in_progress")
        except Exception:
            pass

        # Return the updated state (serialize limited keys)
        safe_state = {
            "question": state.get("question"),
            "detected_language": state.get("detected_language"),
            "facts_count": len(state.get("facts_raw") or []),
            "analysis": state.get("analysis"),
            "arguments_count": len(getattr(state.get("argument_storage"), "arguments", []) or []) if state.get("argument_storage") else 0,
            "prediction": state.get("prediction"),
            "prediction_confidence": state.get("prediction_confidence"),
            "draft": state.get("draft"),
            "reasoning_trace": state.get("reasoning_trace", [])
        }

        return safe_state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check & Info
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "lawyer_agent_api"}


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "Lawyer Agent REST API",
        "version": "1.0.0",
        "docs": "/docs"
    }



@app.post("/cases/{case_id}/evidence")
async def upload_evidence(case_id: str, files: List[UploadFile] = File(...)):
    """Upload one or more evidence files for a case. Files are stored under `evidence_uploads/{case_id}` and
    returned as server-side paths that can be passed to the compute pipeline.
    """
    try:
        store_dir = os.path.join(EVIDENCE_UPLOAD_DIR, case_id)
        os.makedirs(store_dir, exist_ok=True)

        saved_paths = []
        for upload in files:
            # sanitize filename - use basename to avoid path fragments
            filename = os.path.basename(upload.filename)
            # prefix with uuid to avoid collisions
            out_name = f"{uuid.uuid4().hex}_{filename}"
            out_path = os.path.join(store_dir, out_name)

            content = await upload.read()
            with open(out_path, "wb") as f:
                f.write(content)

            saved_paths.append(out_path)

            # persist metadata record
            try:
                storage = CaseSessionStorage(case_id, DB_PATH)
                # upload.content_type available
                mime = upload.content_type or 'application/octet-stream'
                storage.add_evidence_record(file_path=os.path.relpath(out_path), file_name=filename, mime_type=mime, size_bytes=len(content), uploader='anonymous')
            except Exception:
                pass

        # Persist evidence file paths (relative) to case session storage for later compute runs
        try:
            storage = CaseSessionStorage(case_id, DB_PATH)
            rel_paths = [os.path.relpath(p) for p in saved_paths]
            storage.set_state_flag("evidence_files", rel_paths)
            storage.set_state_flag("evidence_uploaded_at", datetime.utcnow().isoformat())
        except Exception:
            # Non-fatal: log and continue returning saved paths
            pass

        return {"status": "ok", "saved": saved_paths}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/cases/{case_id}/compute/stream")
def compute_case_stream(
    case_id: str, 
    enable_web_search: bool = Query(False), 
    enable_research_papers: bool = Query(False),
    enable_google_scholar: bool = Query(True),
    enable_arxiv: bool = Query(True),
    enable_indian_legal_db: bool = Query(True),
    workflow: str = Query("fact_retrieval")  # Which workflow to run
):
    """
    Stream compute progress (SSE style) for a case.
    
    Workflows:
    - fact_retrieval: ONLY retrieve and summarize facts (Workflow 1)
    - argument_generation: ONLY generate arguments from locked facts (Workflow 2)
    - prediction: ONLY generate prediction (Workflow 3)
    - draft_generation: ONLY generate draft (Workflow 4)
    """
    def sse_event(data: str):
        return f"data: {data}\n\n"

    def generator():
        try:
            storage = CaseSessionStorage(case_id, DB_PATH)

            # Load problem statement from state flags
            problem_statement = storage.get_state_flag("problem_statement") or ""
            
            # Debug: Show if problem statement was loaded
            if problem_statement:
                ps_preview = problem_statement[:100] + "..." if len(problem_statement) > 100 else problem_statement
                print(f"\n✅ PROBLEM STATEMENT LOADED ({len(problem_statement)} chars): {ps_preview}")
            else:
                print("\n⚠️  WARNING: No problem statement found! Please click 'Save Problem' before 'Run Compute'")

            # Build initial state
            state = {
                "question": problem_statement,
                "evidence_files": storage.get_state_flag("evidence_files") or None,
                "evidence_text": None,
                "detected_language": None,
                "source_language_name": None,
                "entities": None,
                "timeline": None,
                "facts": None,
                "facts_raw": None,
                "fact_storage": None,
                "argument_storage": None,
                "facts_approved_and_locked": storage.get_state_flag("facts_approved_and_locked", False),
                "analysis": None,
                "statutes": None,
                "precedents": None,
                "prediction": None,
                "prediction_history": [],
                "similar_cases": None,
                "prediction_confidence": None,
                "draft": None,
                "approved_phase": None,
                "user_feedback": None,
                "reasoning_trace": []
            }

            yield sse_event("{\"phase\": \"start\", \"message\": \"Compute started\"}")

            # Get dependencies
            try:
                deps = get_dependencies()
                _chroma = deps.get("chroma_stores") or {}
                _emb = deps.get("embedding_model")
                _faiss = deps.get("faiss_store")
                _llm = deps.get("llm")
            except Exception as e:
                print(f"Warning: Failed to get dependencies: {e}")
                _chroma = {}
                _emb = None
                _faiss = None
                _llm = None

            if workflow == "fact_retrieval":
                # ========== TWO-PHASE WORKFLOW: ENTITY EXTRACTION → RAG RETRIEVAL ==========
                from workflows.lawyer_agent.workflow_1_fact_retrieval import (
                    create_entity_extraction_workflow,
                    create_fact_gathering_workflow
                )
                
                # Check if entities already extracted and clarifications answered
                existing_clarifications = storage.get_state_flag("entity_clarifications") or []
                unanswered_clarifications = [c for c in existing_clarifications if not c.get("answered", False)]
                
                if not existing_clarifications:
                    # === PHASE 1: ENTITY EXTRACTION & ANOMALY DETECTION ===
                    print("\n" + "="*80)
                    print("PHASE 1: ENTITY EXTRACTION & ANOMALY DETECTION")
                    print("="*80)
                    
                    yield sse_event('{"phase": "start", "message": "Phase 1: Entity Extraction & Anomaly Detection"}')
                    
                    # Run entity extraction workflow ONLY
                    entity_workflow = create_entity_extraction_workflow(
                        llm=_llm,
                        auto_resolve_conflicts=False,
                        similarity_threshold=0.85
                    )
                    
                    state = entity_workflow.invoke(state)
                    
                    # Save entity extraction results
                    try:
                        if state.get("normalized_entities"):
                            storage.set_state_flag("normalized_entities", state["normalized_entities"])
                        if state.get("entity_canonical_map"):
                            storage.set_state_flag("entity_canonical_map", state["entity_canonical_map"])
                        if state.get("entity_conflicts"):
                            storage.set_state_flag("entity_conflicts", state["entity_conflicts"])
                        if state.get("entity_clarifications"):
                            storage.set_state_flag("entity_clarifications", state["entity_clarifications"])
                        if state.get("entity_summary"):
                            storage.set_state_flag("entity_summary", state["entity_summary"])
                        
                        clarifications = state.get("entity_clarifications", [])
                        if clarifications:
                            print(f"\n⏸️  WORKFLOW STOPPED: {len(clarifications)} clarification(s) required")
                            print("   Please review the 🏷️ Entities & Conflicts tab and answer questions")
                            yield sse_event('{{"phase": "paused", "message": "⏸️  Workflow paused - {} clarification(s) needed from lawyer", "clarifications_count": {}}}' .format(len(clarifications), len(clarifications)))
                        else:
                            print("\n✅ No clarifications needed, ready for Phase 2")
                            yield sse_event('{"phase": "phase1_complete", "message": "✅ Entity extraction complete - no clarifications needed"}')
                    
                    except Exception as e:
                        print(f"Warning: Failed to save entity data: {e}")
                    
                    yield sse_event('{"phase": "done", "message": "Phase 1 complete - Review entities before continuing"}')
                
                elif unanswered_clarifications:
                    # === CLARIFICATIONS STILL PENDING ===
                    print(f"\n⚠️  {len(unanswered_clarifications)} clarification(s) still unanswered")
                    print("   Please answer all questions in the 🏷️ Entities & Conflicts tab before continuing")
                    yield sse_event('{{"phase": "waiting", "message": "⚠️  {} clarification(s) still need answers", "clarifications_count": {}}}' .format(len(unanswered_clarifications), len(unanswered_clarifications)))
                    yield sse_event('{"phase": "done", "message": "Please answer clarification questions before continuing"}')
                
                else:
                    # === PHASE 2: RAG RETRIEVAL WITH CLEAN ENTITIES ===
                    print("\n" + "="*80)
                    print("PHASE 2: RAG RETRIEVAL WITH VERIFIED ENTITIES")
                    print("="*80)
                    
                    yield sse_event('{"phase": "start", "message": "Phase 2: RAG Retrieval with verified entities"}')
                    
                    # Load verified entities from state flags
                    state["normalized_entities"] = storage.get_state_flag("normalized_entities")
                    state["entity_canonical_map"] = storage.get_state_flag("entity_canonical_map")
                    
                    # Load existing facts if any
                    facts_data = storage.load_facts()
                    if facts_data:
                        try:
                            state["fact_storage"] = FactStorage.from_dict(facts_data)
                        except Exception:
                            pass
                    
                    # Run fact gathering workflow with clean entities
                    fact_workflow = create_fact_gathering_workflow(
                        chroma_stores=_chroma,
                        embedding_model=_emb,
                        faiss_store=_faiss,
                        llm=_llm,
                        enable_web_search=enable_web_search,
                        enable_research_papers=enable_research_papers,
                        enable_google_scholar=enable_google_scholar,
                        enable_arxiv=enable_arxiv,
                        enable_indian_legal_db=enable_indian_legal_db
                    )
                    
                    state = fact_workflow.invoke(state)
                    
                    # Save facts
                    try:
                        if state.get("fact_storage"):
                            storage.save_facts(state["fact_storage"].to_dict())
                            storage.set_state_flag("facts_edited", True)
                    except Exception as e:
                        print(f"Warning: Failed to save facts: {e}")
                    
                    print("\n✅ RAG retrieval complete with verified entities")
                    yield sse_event('{"phase": "done", "message": "✅ Phase 2 complete - Facts retrieved with clean entities"}')


            elif workflow == "argument_generation":
                # ========== WORKFLOW 2: ARGUMENT GENERATION ONLY ==========
                yield sse_event('{"phase": "legal_analysis", "message": "Starting argument generation"}')
                
                # Load facts and arguments from database
                facts_data = storage.load_facts()
                if facts_data:
                    try:
                        state["fact_storage"] = FactStorage.from_dict(facts_data)
                    except Exception:
                        pass
                
                args_data = storage.load_arguments()
                if args_data:
                    try:
                        from modules.argument_storage import ArgumentStorage as ArgStore
                        state["argument_storage"] = ArgStore.from_dict(args_data)
                    except Exception:
                        pass
                
                # Validate locked facts exist
                if not state.get("fact_storage"):
                    raise ValueError("No facts found. Please run fact retrieval first.")
                
                locked_facts = state["fact_storage"].get_locked_facts()
                if not locked_facts:
                    raise ValueError("No locked facts found. Please approve and lock facts first.")
                
                state["facts"] = locked_facts
                state["facts_approved_and_locked"] = True
                
                if _llm is None:
                    class SimpleLLM:
                        def generate(self, prompt, *a, **k):
                            return "(placeholder LLM) Analysis unavailable"
                    _llm = SimpleLLM()
                
                state = legal_analysis_node(
                    state=state,
                    chroma_stores=_chroma,
                    embedding_model=_emb,
                    faiss_store=_faiss,
                    llm=_llm
                )
                
                # Save arguments and analysis
                try:
                    if state.get("argument_storage"):
                        storage.save_arguments(state["argument_storage"].to_dict())
                        storage.set_state_flag("arguments_edited", True)
                    if state.get("analysis"):
                        storage.save_state("analysis", state["analysis"])
                except Exception as e:
                    print(f"Warning: Failed to save arguments/analysis: {e}")
                
                analysis_text = state.get("analysis", "")
                yield sse_event(json.dumps({
                    "phase": "legal_analysis", 
                    "message": "Argument generation complete"
                }))
                yield sse_event(json.dumps({
                    "phase": "done", 
                    "message": "Argument generation complete",
                    "analysis": analysis_text
                }))

            elif workflow == "prediction":
                # ========== WORKFLOW 3: PREDICTION ONLY ==========
                yield sse_event('{"phase": "prediction", "message": "Starting prediction"}')
                
                # Load arguments from database
                args_data = storage.load_arguments()
                if args_data:
                    try:
                        from modules.argument_storage import ArgumentStorage as ArgStore
                        state["argument_storage"] = ArgStore.from_dict(args_data)
                    except Exception:
                        pass
                
                # Validate arguments exist
                if not state.get("argument_storage"):
                    raise ValueError("No arguments found. Please run argument generation first.")
                
                if _llm is None:
                    class SimpleLLM:
                        def generate(self, prompt, *a, **k):
                            return "(placeholder LLM) Prediction unavailable"
                    _llm = SimpleLLM()
                
                state = prediction_node(state=state, faiss_store=_faiss, llm=_llm, embedding_model=_emb)
                
                # Save prediction history
                try:
                    if state.get("prediction_history"):
                        storage.save_prediction_history(state["prediction_history"])
                except Exception as e:
                    print(f"Warning: Failed to save prediction: {e}")
                
                yield sse_event('{"phase": "prediction", "message": "Prediction complete"}')
                yield sse_event(json.dumps({
                    "phase": "done",
                    "message": "Prediction complete",
                    "prediction": state.get("prediction"),
                    "prediction_confidence": state.get("prediction_confidence")
                }))

            elif workflow == "draft_generation":
                # ========== WORKFLOW 4: DRAFT GENERATION ONLY ==========
                yield sse_event('{"phase": "draft_generation", "message": "Starting draft generation"}')
                
                # Load all context from database
                facts_data = storage.load_facts()
                if facts_data:
                    try:
                        state["fact_storage"] = FactStorage.from_dict(facts_data)
                    except Exception:
                        pass
                
                args_data = storage.load_arguments()
                if args_data:
                    try:
                        from modules.argument_storage import ArgumentStorage as ArgStore
                        state["argument_storage"] = ArgStore.from_dict(args_data)
                    except Exception:
                        pass
                
                # Load prediction if available
                try:
                    pred_history = storage.load_prediction_history()
                    if pred_history:
                        state["prediction_history"] = pred_history
                        if pred_history:
                            latest = pred_history[-1]
                            state["prediction"] = latest.get("prediction")
                            state["prediction_confidence"] = latest.get("confidence")
                except Exception:
                    pass
                
                # Validate required context
                if not state.get("fact_storage"):
                    raise ValueError("No facts found. Cannot generate draft.")
                if not state.get("argument_storage"):
                    raise ValueError("No arguments found. Cannot generate draft.")
                
                if _llm is None:
                    class SimpleLLM:
                        def generate(self, prompt, *a, **k):
                            return "(placeholder LLM) Draft unavailable"
                    _llm = SimpleLLM()
                
                state = draft_generation_node(state=state, llm=_llm)
                
                yield sse_event('{"phase": "draft_generation", "message": "Draft generation complete"}')
                yield sse_event(json.dumps({
                    "phase": "done",
                    "message": "Draft generation complete",
                    "draft": state.get("draft", "")
                }))

            else:
                raise ValueError(f"Unknown workflow: {workflow}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield sse_event(json.dumps({"phase": "error", "message": str(e)}))

    return StreamingResponse(generator(), media_type='text/event-stream')


# ============ ENTITY EXTRACTION & CONFLICT RESOLUTION ENDPOINTS ============

@app.get("/cases/{case_id}/entities")
def get_entities(case_id: str):
    """Returns all extracted entities (persons, dates, organizations, etc.) from workflow_1."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        
        # Get entities from state flags
        normalized_entities = storage.get_state_flag("normalized_entities", {}) or {}
        entity_canonical_map = storage.get_state_flag("entity_canonical_map", {}) or {}
        
        return {
            "case_id": case_id,
            "normalized_entities": normalized_entities,
            "canonical_map": entity_canonical_map,
            "total_entities": len(normalized_entities),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        # Return empty data on any error instead of 500
        return {
            "case_id": case_id,
            "normalized_entities": {},
            "canonical_map": {},
            "total_entities": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@app.get("/cases/{case_id}/entities/conflicts")
def get_entity_conflicts(case_id: str):
    """Returns detected entity conflicts (e.g., same person in multiple roles)."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        
        # Get conflicts from state flags
        entity_conflicts = storage.get_state_flag("entity_conflicts", []) or []
        entity_summary = storage.get_state_flag("entity_summary", "") or ""
        
        return {
            "case_id": case_id,
            "conflicts": entity_conflicts,
            "conflict_count": len(entity_conflicts),
            "summary": entity_summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        # Return empty data on any error instead of 500
        return {
            "case_id": case_id,
            "conflicts": [],
            "conflict_count": 0,
            "summary": "",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@app.get("/cases/{case_id}/entities/clarifications")
def get_entity_clarifications(case_id: str):
    """Returns LLM-generated clarification questions for ambiguous entities/conflicts."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        
        # Get clarifications from state flags
        entity_clarifications = storage.get_state_flag("entity_clarifications", []) or []
        
        return {
            "case_id": case_id,
            "clarifications": entity_clarifications,
            "pending_count": len([c for c in entity_clarifications if not c.get("resolved", False)]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        # Return empty data on any error instead of 500
        return {
            "case_id": case_id,
            "clarifications": [],
            "pending_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class ClarificationAnswerRequest(BaseModel):
    """Lawyer's response to an entity clarification question."""
    clarification_id: Union[int, str]  # Accept both int and str for backwards compatibility
    answer: str
    resolution: Optional[str] = None
    notes: Optional[str] = None


@app.post("/cases/{case_id}/entities/answer")
def submit_clarification_answer(case_id: str, request: ClarificationAnswerRequest):
    """Accept lawyer's answer to clarification questions and resolve conflicts."""
    try:
        print(f"\n📝 CLARIFICATION ANSWER RECEIVED:")
        print(f"   Case ID: {case_id}")
        print(f"   Clarification ID: {request.clarification_id} (type: {type(request.clarification_id).__name__})")
        print(f"   Answer: {request.answer[:100]}...")
        
        storage = CaseSessionStorage(case_id, DB_PATH)
        
        # Get clarifications from state flags
        entity_clarifications = storage.get_state_flag("entity_clarifications", []) or []
        
        # Find and update the clarification
        updated = False
        for clarification in entity_clarifications:
            # Compare as strings to handle both int and string IDs
            if str(clarification.get("id")) == str(request.clarification_id):
                clarification["answered"] = True
                clarification["resolved"] = True
                clarification["lawyer_answer"] = request.answer
                clarification["resolution"] = request.resolution
                clarification["notes"] = request.notes
                clarification["resolved_at"] = datetime.now(timezone.utc).isoformat()
                updated = True
                break
        
        if not updated:
            raise HTTPException(status_code=404, detail=f"Clarification {request.clarification_id} not found")
        
        # Update state
        storage.set_state_flag("entity_clarifications", entity_clarifications)
        
        # Count remaining unanswered (use 'answered' field to match workflow check)
        unanswered = len([c for c in entity_clarifications if not c.get("answered", False)])
        
        return {
            "status": "answered",
            "case_id": case_id,
            "clarification_id": request.clarification_id,
            "lawyer_answer": request.answer,
            "remaining_unanswered": unanswered,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/problem")
def save_problem_statement(case_id: str, payload: Dict[str, str]):
    """Persist the problem statement text into CaseSessionStorage under the flag `problem_statement`."""
    try:
        ps = payload.get("problem_statement")
        if ps is None:
            raise HTTPException(status_code=400, detail="Missing 'problem_statement' in body")

        storage = CaseSessionStorage(case_id, DB_PATH)
        storage.set_state_flag("problem_statement", ps)
        storage.set_state_flag("problem_statement_saved_at", datetime.utcnow().isoformat())
        return {"status": "ok", "problem_statement": ps}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
