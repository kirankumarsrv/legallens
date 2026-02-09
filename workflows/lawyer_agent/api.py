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
from typing import List, Optional, Dict, Any
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


class ArgumentResponse(BaseModel):
    """Response model for an argument."""
    id: str
    content: str
    legal_basis: str
    relevance_score: float
    status: str
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
    created_at: Optional[str]
    updated_at: Optional[str]
    status: str = "in_progress"


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

@app.get("/cases", response_model=List[str])
def list_cases():
    """List all case IDs in the database."""
    try:
        cases = CaseSessionStorage.get_all_cases(DB_PATH)
        return cases
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases", response_model=CaseInfo)
def create_case(request: CreateCaseRequest):
    """Create a new case. Expects JSON body with `case_name` and optional `case_type`."""
    try:
        # Generate a unique case_id (UUID4 hex)
        case_id = uuid.uuid4().hex
        storage = CaseSessionStorage(case_id, DB_PATH)
        storage.set_case_status("in_progress")
        # Optionally, we could store case metadata; keep minimal for now
        now = datetime.now(timezone.utc).isoformat()
        return CaseInfo(
            case_id=case_id,
            created_at=now,
            updated_at=now,
            status="in_progress"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cases/{case_id}", response_model=CaseInfo)
def get_case(case_id: str):
    """Get case metadata."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        status = storage.get_case_status() or "in_progress"
        return CaseInfo(
            case_id=case_id,
            status=status
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
            legal_basis=argument.legal_basis
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
    enable_indian_legal_db: bool = Query(True)
):
    """Stream compute progress (SSE style) for a case. This reads persisted problem statement and evidence metadata if available.

    This endpoint returns `text/event-stream` events with JSON payloads in `data:` lines.
    """
    def sse_event(data: str):
        return f"data: {data}\n\n"

    def generator():
        try:
            storage = CaseSessionStorage(case_id, DB_PATH)

            # Build initial state using persisted flags
            state = {
                "question": storage.get_state_flag("problem_statement") or "",
                "evidence_files": storage.get_state_flag("evidence_files") or None,
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

            yield sse_event("{\"phase\": \"start\", \"message\": \"Compute started\"}")

            # Phase 0: Evidence ingest
            yield sse_event('{"phase": "evidence_ingest", "message": "Starting evidence ingestion"}')
            state = evidence_ingest_node(state)
            yield sse_event('{"phase": "evidence_ingest", "message": "Evidence ingestion complete"}')

            # Persist any evidence paths into flags (already done by upload endpoint)

            # Phase 1: Fact gathering
            yield sse_event('{"phase": "fact_gathering", "message": "Starting fact gathering"}')
            # Initialize dependencies (cached by get_dependencies) so Phase1 can use embeddings/FAISS
            try:
                deps = get_dependencies()
                _chroma = deps.get("chroma_stores")
                _emb = deps.get("embedding_model")
                _faiss = deps.get("faiss_store")
                _llm = deps.get("llm")
            except Exception:
                _chroma = {}
                _emb = None
                _faiss = None
                _llm = None

            state = fact_gathering_node(
                state=state,
                chroma_stores=_chroma,
                embedding_model=_emb,
                faiss_store=_faiss,
                llm=_llm,
                enable_web_search=enable_web_search,
                enable_research_papers=enable_research_papers,
                enable_google_scholar=enable_google_scholar,
                enable_arxiv=enable_arxiv,
                enable_indian_legal_db=enable_indian_legal_db,
            )
            # Save facts
            try:
                if state.get("fact_storage"):
                    storage.save_facts(state["fact_storage"].to_dict())
                    storage.set_state_flag("facts_edited", True)
            except Exception:
                pass
            yield sse_event('{"phase": "fact_gathering", "message": "Fact gathering complete"}')

            # Phase 2: Legal analysis
            yield sse_event('{"phase": "legal_analysis", "message": "Starting legal analysis"}')
            deps = get_dependencies()
            llm = deps.get("llm")
            embedding_model = deps.get("embedding_model")
            chroma_stores = deps.get("chroma_stores")
            faiss_store = deps.get("faiss_store")

            if llm is None:
                class SimpleLLM:
                    def generate(self, prompt, *a, **k):
                        return "(placeholder LLM) Analysis unavailable"
                llm = SimpleLLM()

            state = legal_analysis_node(state=state, chroma_stores=chroma_stores, embedding_model=embedding_model, faiss_store=faiss_store, llm=llm)
            # Save arguments
            try:
                if state.get("argument_storage"):
                    storage.save_arguments(state["argument_storage"].to_dict())
                    storage.set_state_flag("arguments_edited", True)
            except Exception:
                pass
            yield sse_event('{"phase": "legal_analysis", "message": "Legal analysis complete"}')

            # Phase 3: Prediction
            yield sse_event('{"phase": "prediction", "message": "Starting prediction"}')
            state = prediction_node(state=state, faiss_store=None, llm=llm, embedding_model=None)
            # Save prediction history
            try:
                if state.get("prediction_history"):
                    storage.save_prediction_history(state["prediction_history"])
            except Exception:
                pass
            yield sse_event('{"phase": "prediction", "message": "Prediction complete"}')

            # Phase 4: Draft generation
            yield sse_event('{"phase": "draft_generation", "message": "Starting draft generation"}')
            state = draft_generation_node(state=state, llm=llm)
            yield sse_event('{"phase": "draft_generation", "message": "Draft generation complete"}')

            # Final state summary
            summary = {
                "phase": "done",
                "message": "Compute finished",
                "analysis": state.get("analysis", ""),
                "arguments_count": len(getattr(state.get("argument_storage"), "arguments", {})) if state.get("argument_storage") else 0,
                "prediction": state.get("prediction"),
                "prediction_confidence": state.get("prediction_confidence"),
                "draft": state.get("draft", ""),
                "reasoning_trace": state.get("reasoning_trace", [])
            }
            yield sse_event(json.dumps(summary))

        except Exception as e:
            yield sse_event(json.dumps({"phase": "error", "message": str(e)}))

    return StreamingResponse(generator(), media_type='text/event-stream')



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
