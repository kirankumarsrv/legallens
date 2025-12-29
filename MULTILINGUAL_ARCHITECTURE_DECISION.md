# Multilingual Architecture Decision Framework

## Problem
Hindi/Marathi/Tamil legal documents are extracted via OCR but remain untranslated → LLM struggles with non-English content.

---

## Three Architectural Approaches

### 1️⃣ **Simple Translation Layer** ❌ NOT RECOMMENDED
```
Hindi Document → Google Translate API → English → LLM Analysis
```
**Pros:**
- Simple to implement
- Works for any language

**Cons:**
- ❌ **Legal terminology lost** (शपथ ≠ "oath" in legal context)
- ❌ **Extra API costs** (Google/Azure per-request)
- ❌ **Latency overhead** (round-trip translation)
- ❌ **No semantic awareness** (translator doesn't know IPC context)

---

### 2️⃣ **Language-Aware Model Routing** ⚠️ POSSIBLE BUT LIMITED
```
Language Detected (Hindi)
    ↓
Route to Groq Model Selection
    ├─ English: llama-3.3-70b-versatile ✓ (native)
    ├─ Hindi: ??? ❌ NOT AVAILABLE
    └─ Tamil: ??? ❌ NOT AVAILABLE
```

**Available Groq Models:**
- `llama-3.3-70b-versatile` (English only)
- `llama-3.1-70b-versatile` (English only)
- `mixtral-8x7b-32768` (English only)

**Verdict:** ❌ **Groq doesn't offer multilingual models. All are English-focused.**

---

### 3️⃣ **LLM-as-Router with Tool Integration** ✅ RECOMMENDED
```
Hindi Document Detected
    ↓
Send to LLM Router: "Analyze this legal document. It's in Hindi."
    ↓
LLM Decides:
    Option A: "I can work with this. Here's my analysis with Hindi terms noted."
    Option B: "I need translation tool."
    Option C: "I need specialized legal translator tool."
    ↓
LLM Calls Tool if Needed (with awareness)
    ├─ TRANSLATE_LEGAL(text, source_lang="hi", target_lang="en")
    ├─ EXTRACT_LEGAL_TERMS(text, language="hi")  ← preserve terminology
    └─ LOOKUP_IPC_HINDI(section_number)
    ↓
LLM Processes Result → Analysis
```

**Pros:**
- ✅ **LLM stays aware** of original language throughout
- ✅ **Selective translation** (only when LLM decides it's needed)
- ✅ **Tools can be domain-specific** (legal translator, not generic)
- ✅ **Preserves semantic context** (LLM knows it's Hindi law)
- ✅ **Extensible** (add tools for any language)

---

## Recommended Architecture: **Hybrid Approach**

Combine **Language Detection + Tool Integration + LLM Routing**

```
PHASE 0: Evidence Ingestion
├─ OCR extract text (Hindi/Marathi/Tamil/English)
├─ Detect language: "hi", "mr", "ta", "en"
└─ Store language metadata in state

PHASE 1: Entity Extraction (Unchanged)
├─ Extract entities (works on any language)
└─ Timeline built (dates are universal)

PHASE 2: Legal Analysis (NEW - WITH TOOLS)
├─ Send to LLM: 
│  "This is a Hindi legal case. Here's the evidence: [text]"
│  "Available tools: TRANSLATE_LEGAL, EXTRACT_LEGAL_TERMS, LOOKUP_IPC_HINDI"
├─ LLM routes:
│  ├─ If "needs clarification" → calls TRANSLATE_LEGAL
│  ├─ If "extract terms" → calls EXTRACT_LEGAL_TERMS
│  └─ If "verify section" → calls LOOKUP_IPC_HINDI
└─ LLM reasons: "Here's the analysis (referencing original Hindi terminology)"

PHASE 3-4: Prediction & Drafting
└─ Output bilingual where possible
```

---

## Implementation Roadmap

### Step 1: Add Language to State
```python
# workflows/lawyer_agent/state.py
class LawyerState(TypedDict):
    # ... existing fields ...
    detected_language: str  # "hi", "en", "mr", "ta", etc.
    source_language_name: str  # "Hindi", "English", "Marathi"
```

### Step 2: Detect Language in Evidence Ingest
```python
# workflows/lawyer_agent/nodes/evidence_ingest.py
detected_lang = detect_language(evidence_text)  # Returns "hi", "ta", etc.
state["detected_language"] = detected_lang
state["source_language_name"] = LANG_NAMES.get(detected_lang, "Unknown")
```

### Step 3: Create Tool Suite
```python
# workflows/lawyer_agent/tools/
├── legal_translator.py          # Translates preserving legal terms
├── legal_term_extractor.py      # Extracts Hindi/Tamil IPC terms
└── ipc_statute_lookup.py        # Looks up sections in original language
```

### Step 4: Give Tools to LLM
```python
# workflows/lawyer_agent/nodes/legal_analysis.py
tools = [
    translate_legal_tool,
    extract_legal_terms_tool,
    ipc_statute_lookup_tool,
    search_precedents_tool,
]

response = llm.invoke(
    prompt="Analyze this case in Hindi...",
    tools=tools,
    tool_choice="auto"  # LLM decides if/when to use tools
)
```

### Step 5: Process Tool Calls
```python
# LangChain handles tool calling automatically
# LLM response includes:
# {
#   "reasoning": "Original Hindi is clearer; translating for clarity",
#   "tool_calls": [
#       {"tool": "translate_legal", "args": {...}},
#       {"tool": "search_precedents", "args": {...}}
#   ],
#   "analysis": "Based on translation and precedents..."
# }
```

---

## Tool Specification Examples

### Tool 1: Legal Translator
```python
@tool
def translate_legal(text: str, source_lang: str, target_lang: str = "en") -> str:
    """
    Translate legal text preserving terminology.
    
    Uses Google Translate API with legal context.
    Preserves: Section numbers, case citations, proper nouns.
    
    Example:
        translate_legal(
            "IPC धारा 354C के तहत अभियोजन",
            source_lang="hi"
        )
        → "IPC Section 354C prosecution under"
    """
```

### Tool 2: Legal Term Extractor
```python
@tool
def extract_legal_terms(text: str, language: str) -> dict:
    """
    Extract legal terminology in source language.
    
    Returns:
    {
        "ipc_sections": ["354C", "406"],
        "crpc_sections": ["144"],
        "entities": {"persons": [...], "courts": [...]},
        "legal_terms": {"निर्णय": "judgment", ...}
    }
    """
```

### Tool 3: IPC Statute Lookup
```python
@tool
def lookup_ipc_statute(section: str, language: str = "en") -> str:
    """
    Look up IPC section in original language.
    
    Example:
        lookup_ipc_statute("354C", language="hi")
        → "IPC धारा 354C: महिलाओं के साथ व्यभिचारी आचरण"
    """
```

---

## Why This Approach Wins

| Aspect | Translation Layer | Model Routing | Tool Integration |
|--------|-------------------|---------------|-----------------|
| **Language Support** | ✅ All | ❌ None | ✅ All |
| **Semantic Awareness** | ❌ | ✅ | ✅✅ |
| **Cost** | ❌ High (per-request) | ✅ None | ⚠️ Medium (only when used) |
| **Latency** | ❌ High | ✅ None | ✅ Low (selective) |
| **Legal Accuracy** | ❌ Poor | ⚠️ Limited | ✅✅ Excellent |
| **Extensibility** | ❌ | ❌ | ✅ Easy (add tools) |
| **LLM Control** | ❌ Passive | ⚠️ Routed | ✅ Active (tool-use) |

---

## Next Steps

1. **Update state** to track detected language
2. **Create tool implementations** (use Google Translate API for now)
3. **Integrate with LLM** via LangChain tool_use
4. **Test with Hindi FIR** → see LLM decide when to use tools
5. **Expand tools** as needed (Tamil, Marathi, regional variations)

