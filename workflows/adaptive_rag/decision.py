"""
Adaptive Decision Logic

Decides retrieval strategy based on question type.
This is the key decision point that routes the workflow.
"""


def adaptive_decision(question: str, llm) -> str:
    """
    Decide retrieval strategy for the given question.
    
    This is the core logic of Adaptive RAG.
    Answers ONE question: "Do I need retrieval to answer this?"
    
    Output modes:
        - NO_RETRIEVAL: General knowledge, definitions, no specific legal context needed
        - METADATA_ONLY: Needs summary-level info (years, case names, basic facts)
        - FULL_RAG: Needs detailed legal reasoning, evidence, full paragraph analysis

    Args:
        question (str): User's question
        llm: LLM manager instance

    Returns:
        str: One of ["NO_RETRIEVAL", "METADATA_ONLY", "FULL_RAG"]
    """

    prompt = f"""You are deciding how to answer a question about Indian law.

Question:
{question}

Analyze and decide ONE retrieval strategy:

1. NO_RETRIEVAL
   → General knowledge (e.g., "What is Article 21?")
   → Common definitions (e.g., "Define habeas corpus")
   → No specific case or document needed

2. METADATA_ONLY
   → Year/date information (e.g., "When was judgment X delivered?")
   → Case summary (e.g., "What was the case about?")
   → Can be answered from metadata summaries

3. FULL_RAG
   → Legal reasoning (e.g., "How was Article 21 interpreted after 2017?")
   → Evidence needed (e.g., "What did the court say about...?")
   → Requires detailed paragraphs from judgments

Output ONLY one word: NO_RETRIEVAL or METADATA_ONLY or FULL_RAG
"""

    decision = llm.generate(prompt).strip().upper()

    if "NO_RETRIEVAL" in decision:
        return "NO_RETRIEVAL"
    elif "METADATA_ONLY" in decision:
        return "METADATA_ONLY"
    else:
        return "FULL_RAG"
