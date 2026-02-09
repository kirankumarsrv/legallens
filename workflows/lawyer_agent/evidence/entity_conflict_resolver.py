"""
LLM-based Entity Conflict Resolution

Resolves ambiguous entities using:
1. LLM analysis of context
2. Evidence document analysis
3. Interactive clarification (returns questions for lawyer)
"""

from typing import Dict, List, Any, Optional


def resolve_conflicts_with_llm(
    conflicts: List[Dict[str, Any]],
    evidence_text: str,
    question: str,
    llm,
    auto_resolve: bool = False
) -> Dict[str, Any]:
    """
    Use LLM to resolve entity conflicts by analyzing context.
    
    Args:
        conflicts: List of conflicts from detect_role_conflicts
        evidence_text: Full evidence text for context
        question: Legal question being analyzed
        llm: LLM instance
        auto_resolve: If False, generate questions for lawyer
    
    Returns:
        {
            "resolved": [resolved entities],
            "unresolved": [conflicts needing human input],
            "clarification_questions": [questions for lawyer],
            "confidence": float
        }
    """
    if not conflicts:
        return {
            "resolved": [],
            "unresolved": [],
            "clarification_questions": [],
            "confidence": 1.0
        }
    
    resolved = []
    unresolved = []
    clarification_questions = []
    
    for conflict in conflicts:
        person = conflict["person"]
        roles = conflict["roles"]
        contexts = conflict.get("contexts", [])
        
        # Build LLM prompt for analysis
        context_text = "\n".join([f"- {ctx['context']}" for ctx in contexts[:5]])
        
        prompt = f"""Analyze this entity conflict in a legal case:

**PERSON NAME:** {person}

**CONFLICTING ROLES:** {', '.join(roles)}

**CONTEXTS WHERE PERSON APPEARS:**
{context_text}

**FULL EVIDENCE (first 1000 chars):**
{evidence_text[:1000]}

**LEGAL QUESTION:**
{question}

**TASK:**
Determine the ACTUAL role of "{person}" in this case. Consider:
1. Is this the same person in different roles (unlikely but possible)?
2. Are these different people with same/similar names?
3. Is there OCR error or spelling variation?
4. What is the most likely interpretation based on legal context?

**OUTPUT FORMAT:**
Provide your analysis in this format:
RESOLUTION: [same_person/different_persons/unclear]
ACTUAL_ROLE: [the actual role - police/accused/victim/witness/other]
CONFIDENCE: [high/medium/low]
REASONING: [brief explanation]
CLARIFICATION_NEEDED: [YES/NO]
QUESTION_FOR_LAWYER: [if clarification needed, what to ask]
"""

        try:
            # Call LLM
            if hasattr(llm, 'generate'):
                response = llm.generate(prompt, temperature=0.0, max_tokens=300)
            elif hasattr(llm, 'call'):
                response = llm.call(prompt)
            else:
                response = "LLM unavailable"
            
            # Parse LLM response
            resolution_data = _parse_llm_resolution(response, person, roles)
            
            # If high confidence and auto_resolve, mark as resolved
            if resolution_data["confidence"] == "high" and auto_resolve:
                resolved.append({
                    "person": person,
                    "resolved_role": resolution_data["actual_role"],
                    "resolution": resolution_data["resolution"],
                    "reasoning": resolution_data["reasoning"],
                    "confidence": "high"
                })
            else:
                # Need clarification
                unresolved.append(conflict)
                if resolution_data.get("question_for_lawyer"):
                    clarification_questions.append({
                        "person": person,
                        "question": resolution_data["question_for_lawyer"],
                        "context": context_text,
                        "suggested_resolution": resolution_data
                    })
        
        except Exception as e:
            print(f"   ⚠️  LLM resolution failed for {person}: {e}")
            unresolved.append(conflict)
            clarification_questions.append({
                "person": person,
                "question": f"Please clarify: Is '{person}' the {' or '.join(roles)}? Found in multiple roles.",
                "context": context_text
            })
    
    return {
        "resolved": resolved,
        "unresolved": unresolved,
        "clarification_questions": clarification_questions,
        "confidence": len(resolved) / len(conflicts) if conflicts else 1.0
    }


def _parse_llm_resolution(response: str, person: str, roles: List[str]) -> Dict[str, Any]:
    """Parse LLM response into structured format"""
    
    # Default values
    result = {
        "resolution": "unclear",
        "actual_role": roles[0] if roles else "unknown",
        "confidence": "low",
        "reasoning": "",
        "clarification_needed": True,
        "question_for_lawyer": f"Please clarify the role of '{person}' - found as: {', '.join(roles)}"
    }
    
    if not response or response == "LLM unavailable":
        return result
    
    # Simple parsing (can be improved with structured output)
    lines = response.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith("RESOLUTION:"):
            result["resolution"] = line.split(":", 1)[1].strip().lower()
        elif line.startswith("ACTUAL_ROLE:"):
            result["actual_role"] = line.split(":", 1)[1].strip().lower()
        elif line.startswith("CONFIDENCE:"):
            result["confidence"] = line.split(":", 1)[1].strip().lower()
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.split(":", 1)[1].strip()
        elif line.startswith("CLARIFICATION_NEEDED:"):
            result["clarification_needed"] = "yes" in line.lower()
        elif line.startswith("QUESTION_FOR_LAWYER:"):
            result["question_for_lawyer"] = line.split(":", 1)[1].strip()
    
    return result


def generate_clarification_summary(
    normalization_result: Dict[str, Any],
    conflict_resolution: Dict[str, Any]
) -> str:
    """
    Generate human-readable summary of entity issues.
    
    Returns markdown-formatted summary for lawyer review.
    """
    summary = []
    
    summary.append("# Entity Analysis Summary\n")
    
    # Name variations found
    duplicates = normalization_result.get("duplicates_found", [])
    if duplicates:
        summary.append(f"## Name Variations Detected ({len(duplicates)})\n")
        summary.append("The following names appear to be the same person:\n")
        for orig, canonical in duplicates[:10]:
            summary.append(f"- **{orig}** → normalized to **{canonical}**")
        summary.append("")
    
    # Conflicts requiring clarification
    questions = conflict_resolution.get("clarification_questions", [])
    if questions:
        summary.append(f"## ⚠️ Conflicts Requiring Clarification ({len(questions)})\n")
        for i, q in enumerate(questions, 1):
            summary.append(f"### {i}. {q['person']}")
            summary.append(f"**Question:** {q['question']}")
            summary.append(f"**Context:** {q['context'][:200]}...")
            summary.append("")
    
    # Auto-resolved conflicts
    resolved = conflict_resolution.get("resolved", [])
    if resolved:
        summary.append(f"## ✅ Auto-Resolved ({len(resolved)})\n")
        for r in resolved:
            summary.append(f"- **{r['person']}**: {r['resolved_role']} ({r['confidence']} confidence)")
            summary.append(f"  - {r['reasoning'][:150]}")
        summary.append("")
    
    return "\n".join(summary)
