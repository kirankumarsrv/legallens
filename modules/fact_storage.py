"""
Fact Storage Module

Manages fact persistence across workflow phases.
Prevents duplicate retrieval and maintains fact approval status.

Data Model:
    Fact = {
        "id": str (uuid),
        "content": str,
        "source": str (vector_db | web_search | research_papers | manual),
        "source_details": dict (year, statute_section, url, etc.),
        "relevance_score": float (0-1),
        "status": str (pending | approved | rejected),
        "created_at": datetime,
        "updated_at": datetime
    }
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional


class FactStorage:
    """In-memory fact storage with optional persistence."""
    
    def __init__(self, case_id: str = None):
        """
        Initialize fact storage for a case.
        
        Args:
            case_id: Optional case identifier for persistence
        """
        self.case_id = case_id or str(uuid.uuid4())
        self.facts: Dict[str, Dict[str, Any]] = {}
        self.approved_fact_ids: List[str] = []
        self.rejected_fact_ids: List[str] = []
    
    def add_fact(
        self, 
        content: str, 
        source: str, 
        source_details: Dict[str, Any] = None,
        relevance_score: float = 0.5
    ) -> str:
        """
        Add a new fact to storage.
        
        Args:
            content: Fact content/text
            source: Source (vector_db | web_search | research_papers | manual)
            source_details: Metadata about fact source
            relevance_score: Relevance to case (0-1)
        
        Returns:
            Fact ID (uuid)
        """
        fact_id = str(uuid.uuid4())
        
        self.facts[fact_id] = {
            "id": fact_id,
            "content": content,
            "source": source,
            "source_details": source_details or {},
            "relevance_score": relevance_score,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        return fact_id
    
    def add_facts_batch(self, facts_list: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple facts at once.
        
        Args:
            facts_list: List of dicts with keys: content, source, source_details, relevance_score
        
        Returns:
            List of fact IDs
        """
        fact_ids = []
        for fact in facts_list:
            fact_id = self.add_fact(
                content=fact.get("content", ""),
                source=fact.get("source", "unknown"),
                source_details=fact.get("source_details"),
                relevance_score=fact.get("relevance_score", 0.5)
            )
            fact_ids.append(fact_id)
        
        return fact_ids
    
    def approve_fact(self, fact_id: str) -> bool:
        """Approve a fact (lock it for analysis phase)."""
        if fact_id not in self.facts:
            return False
        
        self.facts[fact_id]["status"] = "approved"
        self.facts[fact_id]["updated_at"] = datetime.now().isoformat()
        
        if fact_id not in self.approved_fact_ids:
            self.approved_fact_ids.append(fact_id)
        
        return True
    
    def reject_fact(self, fact_id: str) -> bool:
        """Reject a fact (remove from consideration)."""
        if fact_id not in self.facts:
            return False
        
        self.facts[fact_id]["status"] = "rejected"
        self.facts[fact_id]["updated_at"] = datetime.now().isoformat()
        
        if fact_id not in self.rejected_fact_ids:
            self.rejected_fact_ids.append(fact_id)
        
        return True
    
    def update_fact(self, fact_id: str, content: str = None, relevance_score: float = None) -> bool:
        """Update fact content or relevance score."""
        if fact_id not in self.facts:
            return False
        
        if content is not None:
            self.facts[fact_id]["content"] = content
        
        if relevance_score is not None:
            self.facts[fact_id]["relevance_score"] = relevance_score
        
        self.facts[fact_id]["updated_at"] = datetime.now().isoformat()
        return True
    
    def delete_fact(self, fact_id: str) -> bool:
        """Delete a fact."""
        if fact_id not in self.facts:
            return False
        
        del self.facts[fact_id]
        self.approved_fact_ids = [fid for fid in self.approved_fact_ids if fid != fact_id]
        self.rejected_fact_ids = [fid for fid in self.rejected_fact_ids if fid != fact_id]
        
        return True
    
    def get_approved_facts(self) -> List[Dict[str, Any]]:
        """Get all approved facts (for legal analysis phase)."""
        return [
            self.facts[fid] 
            for fid in self.approved_fact_ids 
            if fid in self.facts
        ]
    
    def get_approved_facts_content(self) -> str:
        """Get approved facts as concatenated text (for LLM context)."""
        approved = self.get_approved_facts()
        return "\n\n".join([f["content"] for f in approved])
    
    def get_pending_facts(self) -> List[Dict[str, Any]]:
        """Get facts pending approval."""
        return [
            fact 
            for fact in self.facts.values() 
            if fact["status"] == "pending"
        ]
    
    def get_rejected_facts(self) -> List[Dict[str, Any]]:
        """Get facts marked as rejected."""
        return [
            fact 
            for fact in self.facts.values() 
            if fact["status"] == "rejected"
        ]
    
    def get_all_facts(self) -> List[Dict[str, Any]]:
        """Get all facts with their current status."""
        return list(self.facts.values())
    
    def get_fact_by_id(self, fact_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific fact by ID."""
        return self.facts.get(fact_id)
    
    def lock_approved_facts(self) -> List[Dict[str, Any]]:
        """
        Lock all approved facts (prevent re-retrieval).
        Returns the locked facts for use in downstream phases.
        """
        # Mark all approved facts as locked
        for fact_id in self.approved_fact_ids:
            if fact_id in self.facts:
                self.facts[fact_id]["status"] = "approved_locked"
        
        return self.get_approved_facts()
    
    def mark_fact_used_in_phase(self, fact_id: str, phase: str) -> bool:
        """Record that a fact was used in a specific phase for audit trail."""
        if fact_id not in self.facts:
            return False
        
        if "phases_used_in" not in self.facts[fact_id]:
            self.facts[fact_id]["phases_used_in"] = []
        
        if phase not in self.facts[fact_id]["phases_used_in"]:
            self.facts[fact_id]["phases_used_in"].append(phase)
            self.facts[fact_id]["updated_at"] = datetime.now().isoformat()
        
        return True
    
    def is_facts_approved_and_locked(self) -> bool:
        """Check if facts have been approved and locked."""
        if not self.approved_fact_ids:
            return False
        
        for fact_id in self.approved_fact_ids:
            if fact_id in self.facts and self.facts[fact_id]["status"] != "approved_locked":
                return False
        
        return True
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        return {
            "total_facts": len(self.facts),
            "approved_facts": len(self.approved_fact_ids),
            "pending_facts": len(self.get_pending_facts()),
            "rejected_facts": len(self.get_rejected_facts()),
            "sources": list(set(f.get("source", "unknown") for f in self.facts.values())),
            "avg_relevance": (
                sum(f.get("relevance_score", 0) for f in self.facts.values()) / len(self.facts)
                if self.facts else 0
            )
        }
    
    def clear(self):
        """Clear all stored facts."""
        self.facts.clear()
        self.approved_fact_ids.clear()
        self.rejected_fact_ids.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (for session storage)."""
        return {
            "case_id": self.case_id,
            "facts": self.facts,
            "approved_fact_ids": self.approved_fact_ids,
            "rejected_fact_ids": self.rejected_fact_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactStorage":
        """Deserialize from dict."""
        storage = cls(case_id=data.get("case_id"))
        storage.facts = data.get("facts", {})
        storage.approved_fact_ids = data.get("approved_fact_ids", [])
        storage.rejected_fact_ids = data.get("rejected_fact_ids", [])
        return storage
