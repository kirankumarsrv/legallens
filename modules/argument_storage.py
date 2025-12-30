"""
Argument Storage Module

Stores generated legal arguments with status tracking similar to FactStorage.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional


class ArgumentStorage:
    def __init__(self, case_id: str = None):
        self.case_id = case_id or str(uuid.uuid4())
        self.arguments: Dict[str, Dict[str, Any]] = {}
        self.approved_arg_ids: List[str] = []
        self.rejected_arg_ids: List[str] = []

    def add_argument(self, content: str, legal_basis: str = None, relevance_score: float = 0.5) -> str:
        arg_id = str(uuid.uuid4())
        self.arguments[arg_id] = {
            "id": arg_id,
            "content": content,
            "legal_basis": legal_basis or "",
            "relevance_score": relevance_score,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        return arg_id

    def add_arguments_batch(self, args_list: List[Dict[str, Any]]) -> List[str]:
        ids = []
        for a in args_list:
            ids.append(self.add_argument(a.get("content", ""), a.get("legal_basis"), a.get("relevance_score", 0.5)))
        return ids

    def approve_argument(self, arg_id: str) -> bool:
        if arg_id not in self.arguments:
            return False
        self.arguments[arg_id]["status"] = "approved"
        self.arguments[arg_id]["updated_at"] = datetime.now().isoformat()
        if arg_id not in self.approved_arg_ids:
            self.approved_arg_ids.append(arg_id)
        return True

    def reject_argument(self, arg_id: str) -> bool:
        if arg_id not in self.arguments:
            return False
        self.arguments[arg_id]["status"] = "rejected"
        self.arguments[arg_id]["updated_at"] = datetime.now().isoformat()
        if arg_id not in self.rejected_arg_ids:
            self.rejected_arg_ids.append(arg_id)
        return True

    def update_argument(self, arg_id: str, content: str = None, relevance_score: float = None) -> bool:
        if arg_id not in self.arguments:
            return False
        if content is not None:
            self.arguments[arg_id]["content"] = content
        if relevance_score is not None:
            self.arguments[arg_id]["relevance_score"] = relevance_score
        self.arguments[arg_id]["updated_at"] = datetime.now().isoformat()
        return True

    def delete_argument(self, arg_id: str) -> bool:
        if arg_id not in self.arguments:
            return False
        del self.arguments[arg_id]
        self.approved_arg_ids = [i for i in self.approved_arg_ids if i != arg_id]
        self.rejected_arg_ids = [i for i in self.rejected_arg_ids if i != arg_id]
        return True

    def get_pending_arguments(self) -> List[Dict[str, Any]]:
        return [a for a in self.arguments.values() if a["status"] == "pending"]

    def get_approved_arguments(self) -> List[Dict[str, Any]]:
        return [self.arguments[i] for i in self.approved_arg_ids if i in self.arguments]

    def get_all_arguments(self) -> List[Dict[str, Any]]:
        return list(self.arguments.values())

    def lock_approved_arguments(self) -> List[Dict[str, Any]]:
        for aid in self.approved_arg_ids:
            if aid in self.arguments:
                self.arguments[aid]["status"] = "approved_locked"
        return self.get_approved_arguments()

    def to_dict(self) -> Dict[str, Any]:
        return {"case_id": self.case_id, "arguments": self.arguments, "approved_arg_ids": self.approved_arg_ids, "rejected_arg_ids": self.rejected_arg_ids}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArgumentStorage":
        store = cls(case_id=data.get("case_id"))
        store.arguments = data.get("arguments", {})
        store.approved_arg_ids = data.get("approved_arg_ids", [])
        store.rejected_arg_ids = data.get("rejected_arg_ids", [])
        return store
