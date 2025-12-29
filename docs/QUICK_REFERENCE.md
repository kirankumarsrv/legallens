# Quick Reference: Multilingual Tool Integration

## The Three Approaches Compared

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR OPTIONS                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ 1️⃣ MODEL ROUTING                                            │
│    "Use different Groq models per language"                 │
│    ❌ Problem: Groq has NO multilingual models             │
│       All models are English-optimized                       │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ 2️⃣ SIMPLE TRANSLATION                                       │
│    "Google Translate API → then LLM"                        │
│    ❌ Problems:                                              │
│       • Legal terminology lost (शपथ ≠ "oath")             │
│       • Extra cost per request                               │
│       • Extra latency                                        │
│       • No context preservation                              │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ 3️⃣ LLM + TOOL INTEGRATION ✅ CHOSEN                         │
│    "Give LLM tools, let it decide"                          │
│    ✅ Benefits:                                              │
│       • LLM stays aware of language                          │
│       • Selective tool use (costs only when needed)         │
│       • Intelligent routing                                  │
│       • Legal terms preserved                                │
│       • Extensible (add more tools)                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture at a Glance

```
HINDI LEGAL DOCUMENT
        ↓
    [PHASE 0: EVIDENCE INGESTION]
    ├─ Parse (OCR if scanned)
    └─ Detect Language: "hi" ← NEW
        ↓ state.detected_language = "hi"
        ↓ state.source_language_name = "Hindi"
        ↓
    [PHASE 1: ENTITY EXTRACTION]
    └─ Extract entities (works in any language)
        ↓
    [PHASE 2: LEGAL ANALYSIS] ← WITH TOOLS
    ├─ LLM receives tools:
    │  ├─ legal_translator()      (if needs English clarity)
    │  └─ extract_legal_terms()   (if needs to verify sections)
    ├─ LLM routes intelligently
    └─ Tools preserve "IPC 354C", "CS-123/2024", etc.
        ↓
    [PHASE 3-4: PREDICTION & DRAFT]
    └─ Analysis with proper Hindi context
```

---

## What Got Built

### 📁 Files Created (New)
```
workflows/lawyer_agent/
├── tools/
│   ├── __init__.py                 # Registry: get_all_lawyer_agent_tools()
│   ├── legal_translator.py         # @tool: Translate Hindi→English
│   └── legal_term_extractor.py     # @tool: Extract IPC/CrPC/case refs
├── nodes/
│   └── language_detection.py       # Detect language + confidence
```

### 📝 Files Modified
```
state.py
  + detected_language: Optional[str]        # "hi", "ta", "en"
  + source_language_name: Optional[str]     # "Hindi", "Tamil"

nodes/evidence_ingest.py
  + Language detection after parsing
  + Store in state
  + Audit trail updated
```

### 📚 Documentation Created
```
MULTILINGUAL_ARCHITECTURE_DECISION.md      ← Full analysis
MULTILINGUAL_TOOL_INTEGRATION_GUIDE.md    ← How to use
IMPLEMENTATION_SUMMARY.md                  ← This summary
```

---

## The Tools (Available to LLM)

### Tool 1: Legal Translator
```python
legal_translator(text: str, source_language: str = "hi") → str
```
**Preserves:** IPC 354C, CS-123/2024, 15/10/2024, proper nouns
**Example:**
```
Input: "IPC धारा 354C के तहत शिकायत"
Output: "IPC Section 354C complaint
         [Preserved: IPC धारा 354C]"
```

### Tool 2: Legal Term Extractor
```python
extract_legal_terms_tool(text: str, language: str) → str
```
**Extracts:** IPC sections, CrPC sections, Constitution articles, case numbers
**Example:**
```
Input: "IPC 354C, CrPC 144, Constitution 21, Case CS-123/2024"
Output: "IPC SECTIONS: 354C
        CRPC SECTIONS: 144
        CONSTITUTION ARTICLES: 21
        CASE NUMBERS: CS-123/2024"
```

---

## How LLM Uses Tools

```
LLM Receives Prompt:
"This is a HINDI case. Here's the evidence: [...]
Available tools: legal_translator, extract_legal_terms
Analyze and use tools if needed."

LLM Routes:
├─ Option A: "I understand Hindi. Direct analysis."
│           → Analyzes without tools
│
├─ Option B: "I need clarity on terminology."
│           → Calls: legal_translator(evidence, source="hi")
│           → Receives: translated text (terms preserved)
│           → Uses in analysis
│
└─ Option C: "Let me verify sections."
           → Calls: extract_legal_terms_tool(evidence, language="hi")
           → Receives: {ipc_sections: [...], ...}
           → Uses in analysis
```

---

## Key State Fields (NEW)

```python
state["detected_language"]      # "hi", "ta", "mr", "en", etc.
state["source_language_name"]   # "Hindi", "Tamil", "Marathi", "English"
```

These flow through the entire workflow, so every node knows the language context.

---

## Testing (After Integration)

### Test 1: Language Detection
```bash
python -c "
from workflows.lawyer_agent.nodes.language_detection import detect_language_with_confidence
result = detect_language_with_confidence('IPC धारा 354C')
print(f'{result[\"primary_language_name\"]}: {result[\"confidence\"]:.0%}')
"
# Output: Hindi: 92%
```

### Test 2: Tools Available
```bash
python -c "
from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools
tools = get_all_lawyer_agent_tools()
print(f'Tools: {[t.name for t in tools]}')
"
# Output: Tools: ['legal_translator', 'extract_legal_terms']
```

### Test 3: Full Workflow
```bash
python -m workflows.lawyer_agent.run
# Will auto-detect language of sample evidence
# LLM will have tools available
```

---

## Integration Checklist

- [x] Language detection module
- [x] Legal translator tool
- [x] Legal term extractor tool
- [x] Tool registry
- [x] State schema updated
- [x] Evidence ingestion updated
- [ ] **Legal analysis node updated** (TO DO)
  - Pass tools to LLM
  - Add language context to prompt
  - Configure tool_choice="auto"
- [ ] **Test with Hindi evidence** (TO DO)
- [ ] **Configure Google Translate** (if using API) (Optional)

---

## Why This Approach Wins

```
❌ MODEL ROUTING
   Groq doesn't have Hindi models
   
❌ SIMPLE TRANSLATION  
   Legal context lost
   Extra costs & latency
   
✅ TOOL INTEGRATION
   ✅ LLM stays intelligent
   ✅ Selective tool use
   ✅ Preserves legal terms
   ✅ Audit trail
   ✅ Extensible
   ✅ Cost efficient
```

---

## Next Step: One Code Change

Update `workflows/lawyer_agent/nodes/legal_analysis.py`:

```python
# Add at top
from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools

# In function
tools = get_all_lawyer_agent_tools()

# Add to prompt if not English
if state.get("detected_language") != "en":
    prompt += f"\n\nIMPORTANT: This case is in {state['source_language_name']}. "
    prompt += "Use translation tools for clarification if needed."

# Call with tools
response = llm.invoke(
    prompt=prompt,
    tools=tools,          # ← ADD THIS
    tool_choice="auto"    # ← ADD THIS
)
```

Then test: `python -m workflows.lawyer_agent.run`

---

## Support Files

- 📖 **Full Guide**: `MULTILINGUAL_TOOL_INTEGRATION_GUIDE.md`
- 🏗️ **Architecture**: `MULTILINGUAL_ARCHITECTURE_DECISION.md`
- 🔧 **Implementation**: `IMPLEMENTATION_SUMMARY.md` (this file)

---

**Status**: ✅ Complete infrastructure built. Awaiting legal_analysis node integration.
