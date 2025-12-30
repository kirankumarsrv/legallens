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

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from modules.case_session_storage import CaseSessionStorage
from modules.fact_storage import FactStorage
from modules.argument_storage import ArgumentStorage

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
    source_details: Optional[Dict[str, Any]]
    relevance_score: float
    status: str
    created_at: Optional[str]
    approved_at: Optional[str]


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
    created_at: Optional[str]
    approved_at: Optional[str]


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


class StateFlags(BaseModel):
    """Workflow state flags."""
    facts_edited: bool = False
    arguments_edited: bool = False
    recompute_prediction: bool = False
    restore_prediction_index: Optional[int] = None


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
def create_case(case_id: str):
    """Create a new case."""
    try:
        storage = CaseSessionStorage(case_id, DB_PATH)
        storage.set_case_status("in_progress")
        return CaseInfo(
            case_id=case_id,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
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
        
        return {"status": "locked", "count": len(fs.approved_fact_ids)}
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
