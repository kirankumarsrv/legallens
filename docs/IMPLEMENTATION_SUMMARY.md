# Multilingual Integration: Decision & Implementation Summary

## Your Question
> Instead of translation layer, use other groq model automatically? Give decision to llm, language detected then put that language to llm to decide which llm to use. Or integrate tools to llm that one tool might be a translator.

## Our Answer: Hybrid Approach ✅

We chose **Option 3: LLM with Tool Integration** because:

1. ❌ **Model Routing (Option 1)** - Groq doesn't have multilingual models
2. ⚠️ **Simple Translation (Option 2)** - Loses legal context & costs per request
3. ✅ **Tool Integration (Option 3)** - LLM stays intelligent, decides when to use tools

---

## What Was Built

### Files Created

```
workflows/lawyer_agent/
├── tools/
│   ├── __init__.py                 # Tool registry
│   ├── legal_translator.py         # Translation tool
│   └── legal_term_extractor.py     # Term extraction tool
├── nodes/
│   └── language_detection.py       # Language detection module
```

### Files Modified

```
workflows/lawyer_agent/
├── state.py                        # Added: detected_language, source_language_name
├── nodes/evidence_ingest.py        # Added: Language detection after parsing
```

### Documentation

```
MULTILINGUAL_ARCHITECTURE_DECISION.md      # Full comparison of 3 approaches
MULTILINGUAL_TOOL_INTEGRATION_GUIDE.md    # Implementation details & usage
```

---

## How It Works

### Phase 0: Evidence Ingestion (Automatic)
```
Input: Hindi FIR PDF
    ↓
OCR Extract Text
    ↓
Detect Language: "hi" (Hindi, 92% confidence) ← NEW
    ↓
Store in state: 
  detected_language = "hi"
  source_language_name = "Hindi"
```

### Phase 2: Legal Analysis (LLM + Tools)
```
LLM Receives:
  "This is a HINDI case. Available tools: translation, term extraction"
    ↓
LLM Decides:
  ├─ "I understand. Analyzing directly."
  ├─ "I need translation for clarity." → Calls tool
  └─ "Let me verify sections." → Calls term extractor
    ↓
Tool Executes (if called):
  legal_translator("IPC धारा 354C के तहत...", source="hi", target="en")
  Returns: "IPC Section 354C prosecution..."
           [Preserved terms: IPC धारा 354C]
    ↓
LLM Continues with translation + context
```

---

## Key Components

### 1. Language Detection
```python
# In evidence_ingest_node
from workflows.lawyer_agent.nodes.language_detection import detect_language_with_confidence

result = detect_language_with_confidence(evidence_text)
# {
#   "primary_language": "hi",
#   "primary_language_name": "Hindi",
#   "confidence": 0.92
# }

state["detected_language"] = result["primary_language"]
state["source_language_name"] = result["primary_language_name"]
```

### 2. Legal Translator Tool
```python
# LLM can call this
@tool
def legal_translator(text: str, source_language: str = "hi") -> str:
    """Translate legal text, preserving IPC sections, case numbers, dates."""
    # Uses Google Translate API (or fallback)
    # Preserves: "IPC 354C", "CS-123/2024", "15/10/2024"
```

### 3. Legal Term Extractor Tool
```python
# LLM can call this
@tool
def extract_legal_terms_tool(text: str, language: str = "en") -> str:
    """Extract IPC/CrPC sections, case numbers, legal concepts."""
    # Returns structured: {ipc_sections: [...], crpc_sections: [...], ...}
```

### 4. Updated State
```python
class LawyerState(TypedDict):
    # ... existing fields ...
    detected_language: Optional[str]        # "hi", "ta", "en"
    source_language_name: Optional[str]     # "Hindi", "Tamil", "English"
```

---

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Multilingual Support** | ❌ None | ✅ Hindi, Tamil, Marathi, etc. |
| **Automatic Detection** | ❌ Manual | ✅ Automatic in evidence_ingest |
| **Translation** | ❌ No | ✅ Available as tool (LLM decides) |
| **Legal Accuracy** | ❌ | ✅ LLM aware of language context |
| **Cost** | N/A | ✅ Selective (only when LLM uses) |
| **Control** | N/A | ✅ LLM decides when/how to use tools |
| **Transparency** | N/A | ✅ Tool calls logged in reasoning_trace |

---

## Architecture Advantages

### Why Tool Integration Over Simple Translation

```
Simple Translation:              LLM with Tools:
Hindi → Google API → English    Hindi → LLM Says:
          ↓                         ├─ "I understand, analyzing directly"
        Loss of context            ├─ "I need clarity → Calls translator"
        Extra latency              └─ "I need verification → Calls extractor"
        Costs per request                    ↓
        No LLM awareness          Smart routing + context preservation
```

### Why Not Model Routing

```
Language Detected (Hindi)
    ↓
Route to Hindi-capable Groq Model?
    ↓
❌ Groq has NO Hindi models
   All models are English-focused:
   - llama-3.3-70b-versatile
   - llama-3.1-70b-versatile
   - mixtral-8x7b-32768
```

---

## Next Steps to Activate

### Step 1: Install Dependencies
```bash
pip install langdetect google-cloud-translate
```

### Step 2: Update Legal Analysis Node
Modify `workflows/lawyer_agent/nodes/legal_analysis.py`:
```python
from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools

def legal_analysis_node(state, ...):
    tools = get_all_lawyer_agent_tools()
    
    # Add language context to prompt
    if state.get("detected_language") != "en":
        prompt += f"Note: This case is in {state['source_language_name']}. "
        prompt += "Use translation tools if needed."
    
    # Call LLM with tools
    response = llm.invoke(prompt, tools=tools, tool_choice="auto")
```

### Step 3: Test with Hindi Case
```python
from workflows.lawyer_agent.run import run_lawyer_agent, setup_dependencies

dependencies = setup_dependencies()

# Your existing test case (already in Hindi)
run_lawyer_agent(
    question="Does this case violate privacy rights?",
    dependencies=dependencies,
    evidence_files=["evidence_samples/sample_fir.txt"]  # Already has Hindi content
)

# Expected behavior:
# 1. Language detected as Hindi
# 2. LLM receives tools
# 3. Workflow completes with proper context
```

---

## Current Status

### ✅ Completed
- [x] Language detection module (`language_detection.py`)
- [x] Legal translator tool (`legal_translator.py`)
- [x] Legal term extractor tool (`legal_term_extractor.py`)
- [x] Tool registry (`tools/__init__.py`)
- [x] State schema updated (detected_language, source_language_name)
- [x] Evidence ingestion updated (language detection)
- [x] Complete documentation

### ⏳ To Do (Integration)
- [ ] Update `legal_analysis_node` to pass tools to LLM
- [ ] Configure LLM to support tool_use
- [ ] Test with sample Hindi FIR
- [ ] Configure Google Translate API (if using cloud)
- [ ] Add bilingual output support (optional)

---

## File Summary

### New Files
| File | Purpose |
|------|---------|
| `tools/legal_translator.py` | Translate preserving legal terms |
| `tools/legal_term_extractor.py` | Extract sections, case numbers |
| `tools/__init__.py` | Tool registry & management |
| `nodes/language_detection.py` | Detect language with confidence |

### Modified Files
| File | Changes |
|------|---------|
| `state.py` | Added detected_language, source_language_name |
| `nodes/evidence_ingest.py` | Added language detection after parsing |

### Documentation
| File | Purpose |
|------|---------|
| `MULTILINGUAL_ARCHITECTURE_DECISION.md` | Architecture comparison (3 approaches) |
| `MULTILINGUAL_TOOL_INTEGRATION_GUIDE.md` | Complete implementation guide |

---

## Key Insights

1. **Language Detection is Automatic** - Happens in evidence_ingest, no user input needed
2. **Tools are Optional** - LLM decides when/if to use them
3. **Preserves Context** - Legal terms stay intact during translation
4. **Audit Trail** - All tool calls logged in reasoning_trace
5. **Extensible** - Easy to add more tools (legal DB lookup, precedent search, etc.)

---

## Testing Commands

```bash
# Test language detection
python -c "from workflows.lawyer_agent.nodes.language_detection import detect_language_with_confidence; print(detect_language_with_confidence('IPC धारा 354C'))"

# Test tools available
python -c "from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools; tools = get_all_lawyer_agent_tools(); print(f'Tools: {[t.name for t in tools]}')"

# Run workflow (will auto-detect language)
python -m workflows.lawyer_agent.run
```

---

## Questions?

See detailed docs:
- **Architecture**: `MULTILINGUAL_ARCHITECTURE_DECISION.md`
- **Implementation**: `MULTILINGUAL_TOOL_INTEGRATION_GUIDE.md`
- **Code**: `workflows/lawyer_agent/tools/` and `nodes/language_detection.py`
