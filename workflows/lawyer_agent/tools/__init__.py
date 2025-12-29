"""
Lawyer Agent Tools

Collection of tools available to the LLM for multilingual legal analysis.
Tools are called by LLM when needed (via tool_use mechanism).
"""

from workflows.lawyer_agent.tools.legal_translator import get_legal_translator_tool
from workflows.lawyer_agent.tools.legal_term_extractor import get_legal_term_extractor_tool


def get_all_lawyer_agent_tools():
    """
    Get all tools available to the lawyer agent LLM.
    
    Returns:
        List of LangChain Tool objects
    """
    tools = [
        get_legal_translator_tool(),
        get_legal_term_extractor_tool(),
    ]
    return tools


def get_tool_descriptions():
    """
    Get human-readable descriptions of all tools.
    
    Used in system prompts to tell LLM what tools are available.
    """
    return {
        "legal_translator": {
            "name": "Translate Legal Document",
            "description": "Translate legal text while preserving IPC sections, case numbers, and legal terminology.",
        },
        "extract_legal_terms": {
            "name": "Extract Legal Terms",
            "description": "Extract and categorize legal terminology (sections, case numbers, legal concepts) from text.",
        },
    }


if __name__ == "__main__":
    tools = get_all_lawyer_agent_tools()
    print(f"Available tools: {len(tools)}")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
