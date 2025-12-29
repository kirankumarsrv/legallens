# Integration Code: How to Enable Tools in Legal Analysis

This file shows the exact code needed to integrate the new tools into the legal analysis node.

---

## Current Code (Before Integration)

📁 `workflows/lawyer_agent/nodes/legal_analysis.py`

```python
# Current structure (simplified)
def legal_analysis_node(state: LawyerState, ...) -> LawyerState:
    """
    Phase 2: Legal Analysis
    - Retrieves relevant statutes from vector DB
    - Generates legal reasoning
    """
    
    # ... existing code ...
    
    # Retrieve statutes
    relevant_statutes = retrieve_relevant_statutes(...)
    
    # Call LLM with statutes
    analysis = llm.invoke(
        prompt=f"Analyze this case based on statutes: {relevant_statutes}"
    )
    
    state["analysis"] = analysis
    return state
```

**Problem:** No language awareness, no tools available to LLM

---

## Updated Code (After Integration)

```python
def legal_analysis_node(state: LawyerState, ...) -> LawyerState:
    """
    Phase 2: Legal Analysis (WITH MULTILINGUAL TOOL SUPPORT)
    - Retrieves relevant statutes from vector DB
    - Makes translation tools available to LLM
    - LLM can call tools intelligently based on language
    """
    
    print("\n📋 PHASE 2: LEGAL ANALYSIS")
    
    # ... existing code ...
    
    # NEW: Get tools available to LLM
    from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools
    tools = get_all_lawyer_agent_tools()
    print(f"   📦 Tools available: {', '.join([t.name for t in tools])}")
    
    # Retrieve statutes
    relevant_statutes = retrieve_relevant_statutes(...)
    
    # NEW: Build language-aware prompt
    base_prompt = f"Analyze this case based on statutes: {relevant_statutes}"
    
    # Add language context if not English
    if state.get("detected_language") and state["detected_language"] != "en":
        language_name = state.get("source_language_name", "Unknown")
        base_prompt += (
            f"\n\n⚠️ IMPORTANT: The original evidence is in {language_name}. "
            f"Use the translation tool if you need clarification on terminology. "
            f"The tool preserves legal references (IPC sections, case numbers, etc.)."
        )
    
    # NEW: Call LLM with tools
    try:
        response = llm.invoke(
            prompt=base_prompt,
            tools=tools,           # ← PASS TOOLS
            tool_choice="auto",    # ← LLM DECIDES WHEN TO USE
        )
        
        analysis = response.content
        
        # NEW: Log tool usage if any
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"   🔧 LLM used tools: {[tc['name'] for tc in response.tool_calls]}")
            if state.get("reasoning_trace") is None:
                state["reasoning_trace"] = []
            for tool_call in response.tool_calls:
                state["reasoning_trace"].append(
                    f"LEGAL ANALYSIS: Called tool '{tool_call['name']}'"
                )
    
    except Exception as e:
        print(f"   ❌ Error in analysis: {str(e)}")
        analysis = f"Analysis failed: {str(e)}"
    
    state["analysis"] = analysis
    return state
```

---

## Minimal Change Version

If you want minimal changes to existing code:

```python
# Option: Minimal integration (just add tools)

def legal_analysis_node(state: LawyerState, ...) -> LawyerState:
    # ... all existing code ...
    
    # ADD JUST THESE LINES:
    from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools
    tools = get_all_lawyer_agent_tools()
    
    # MODIFY EXISTING LLM CALL:
    # OLD:
    # analysis = llm.invoke(prompt=prompt)
    
    # NEW:
    analysis = llm.invoke(prompt=prompt, tools=tools, tool_choice="auto")
    
    # Continue with rest of function
    state["analysis"] = analysis
    return state
```

---

## Before & After Comparison

### Before (Current)
```python
# No language awareness
# No tools available to LLM
# One-size-fits-all analysis

analysis = llm.invoke(prompt=prompt)
```

### After (New)
```python
# Language-aware prompting
# Tools available when needed
# Intelligent routing by LLM

if state.get("detected_language") != "en":
    prompt += f"\nNote: This is in {state['source_language_name']}. Tools available."

analysis = llm.invoke(
    prompt=prompt,
    tools=get_all_lawyer_agent_tools(),
    tool_choice="auto"
)
```

---

## Complete Example with Full Context

```python
"""
Legal Analysis Node - With Multilingual Tool Support
"""

from workflows.lawyer_agent.state import LawyerState
from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools
from workflows.lawyer_agent.nodes.language_detection import LANGUAGE_NAMES

def legal_analysis_node(
    state: LawyerState,
    chroma_stores: dict,
    embedding_model,
    faiss_store,
    llm
) -> LawyerState:
    """
    Phase 2: Legal Analysis
    
    Analyzes facts against statutes and precedents.
    Now with multilingual support via tools.
    """
    
    print("\n📋 PHASE 2: LEGAL ANALYSIS")
    print("   (Retrieve statutes, generate reasoning)\n")
    
    # Get tools for this LLM
    tools = get_all_lawyer_agent_tools()
    
    # Build retrieval query from facts
    facts_summary = "\n".join([f"• {fact['fact']}" for fact in state.get("facts", [])])
    
    # Retrieve relevant statutes from vector DB
    relevant_statutes = []
    for store_name, store in chroma_stores.items():
        results = store.similarity_search(facts_summary, k=3)
        relevant_statutes.extend([
            {"source": store_name, "content": doc.page_content}
            for doc in results
        ])
    
    # Build statute summary
    statute_text = "\n\n".join([
        f"[{s['source'].upper()}]\n{s['content'][:500]}"
        for s in relevant_statutes
    ])
    
    # Build base analysis prompt
    analysis_prompt = f"""You are a legal analyst. Analyze the following case:

FACTS:
{facts_summary}

RELEVANT STATUTES:
{statute_text}

Provide legal analysis considering:
1. Applicable statutes and their provisions
2. Previous precedents in similar cases
3. Strength of arguments for both sides
4. Potential legal remedies and liabilities

Be specific, cite sections, and provide reasoned conclusions."""
    
    # Add language context
    if state.get("detected_language") and state["detected_language"] != "en":
        language_name = state.get("source_language_name", "Unknown")
        analysis_prompt += (
            f"\n\nNOTE: The original evidence is in {language_name}. "
            f"Tools are available if you need to translate or extract legal terms."
        )
    
    # Call LLM with tools
    print("   📞 Calling LLM with tools available...")
    try:
        response = llm.invoke(
            analysis_prompt,
            tools=tools,
            tool_choice="auto"  # Let LLM decide when to use tools
        )
        
        analysis_text = response.content if hasattr(response, 'content') else str(response)
        
        # Track tool usage
        tool_calls = []
        if hasattr(response, 'tool_calls'):
            tool_calls = response.tool_calls
            for call in tool_calls:
                tool_name = call.get('name', 'unknown')
                print(f"   🔧 LLM called: {tool_name}")
        
        state["analysis"] = analysis_text
        
        # Store statutes used
        state["statutes"] = relevant_statutes
        
        # Audit trail
        if state.get("reasoning_trace") is None:
            state["reasoning_trace"] = []
        
        trace_entry = f"LEGAL ANALYSIS: Generated reasoning"
        if tool_calls:
            trace_entry += f" (used {len(tool_calls)} tool(s))"
        state["reasoning_trace"].append(trace_entry)
        
        print(f"   ✅ Analysis complete\n")
        
    except Exception as e:
        print(f"   ❌ Analysis failed: {str(e)}\n")
        state["analysis"] = f"Error during legal analysis: {str(e)}"
        raise
    
    return state
```

---

## Testing the Integration

### Test 1: Verify Tools Are Available

```bash
python -c "
from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools
tools = get_all_lawyer_agent_tools()
print(f'✅ {len(tools)} tools ready:')
for tool in tools:
    print(f'   - {tool.name}')
"
```

Expected output:
```
✅ 2 tools ready:
   - legal_translator
   - extract_legal_terms
```

### Test 2: Test Language Detection in Evidence

```bash
python -c "
from workflows.lawyer_agent.nodes.evidence_ingest import evidence_ingest_node
from workflows.lawyer_agent.state import LawyerState

state = LawyerState(
    question='Test',
    evidence_files=['evidence_samples/sample_fir.txt'],
    evidence_text=None,
    detected_language=None,
    source_language_name=None,
    entities=None,
    timeline=None,
    contradictions=None,
    facts=None,
    facts_raw=None,
    analysis=None,
    statutes=None,
    precedents=None,
    prediction=None,
    similar_cases=None,
    prediction_confidence=None,
    draft=None,
    templates=None,
    citations=None,
    approved_phase=None,
    user_feedback=None,
    reasoning_trace=None
)

# This will load evidence and detect language
state_after = evidence_ingest_node(state)

print(f'Detected language: {state_after[\"detected_language\"]}')
print(f'Language name: {state_after[\"source_language_name\"]}')
"
```

### Test 3: Run Full Workflow

```bash
python -m workflows.lawyer_agent.run

# Should show:
# ✅ Tools available: legal_translator, extract_legal_terms
# 🌐 Detecting language...
# ✅ Language detected: Hindi (hi) - 92% confidence
# ... rest of workflow ...
```

---

## Handling Tool Responses

After LLM calls a tool, you need to handle the response:

```python
# If LLM calls tool, response might look like:
# {
#     "type": "tool_use",
#     "tool": "legal_translator",
#     "args": {"text": "...", "source_language": "hi"},
#     "result": "Translated text..."
# }

# LangChain handles this automatically, but if needed:
if hasattr(response, 'tool_calls'):
    for tool_call in response.tool_calls:
        tool_name = tool_call['name']
        tool_args = tool_call['arguments']
        
        # Execute tool
        if tool_name == "legal_translator":
            # Tool already executed by LLM
            result = tool_call.get('result')
        # ... handle other tools
```

---

## Common Integration Issues

### Issue 1: Groq model doesn't support tool_choice
**Solution:** Ensure you're using a Groq model that supports tool use.
- ✅ `llama-3.3-70b-versatile` - supports tool use
- ✅ `llama-3.1-70b-versatile` - supports tool use
- ❌ Older models may not support it

### Issue 2: Tools not being called
**Solution:** 
1. Check tools are properly registered
2. Ensure LLM prompt mentions tools exist
3. Try explicit tool_choice="force_tool" for testing

### Issue 3: Tool errors
**Solution:**
1. Check Google Translate API credentials (if using)
2. Ensure langdetect is installed
3. Review tool implementation in `tools/`

---

## Optional: Add Tool Usage Logging

```python
# Enhanced logging for debugging

def log_tool_usage(response, state):
    """Log tool calls for audit trail"""
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for call in response.tool_calls:
            tool_name = call['name']
            tool_args = call.get('arguments', {})
            
            log_entry = f"TOOL CALL: {tool_name}"
            if 'source_language' in tool_args:
                log_entry += f" (source: {tool_args['source_language']})"
            
            if state.get("reasoning_trace") is None:
                state["reasoning_trace"] = []
            state["reasoning_trace"].append(log_entry)
            
            print(f"   📝 {log_entry}")
```

---

## Summary

**Key changes needed:**

1. ✅ Import tools: `from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools`
2. ✅ Get tools: `tools = get_all_lawyer_agent_tools()`
3. ✅ Add language context to prompt (optional but recommended)
4. ✅ Pass to LLM: `llm.invoke(prompt, tools=tools, tool_choice="auto")`
5. ✅ Handle tool calls in response (LangChain does this automatically)

That's it! The infrastructure is already built.
