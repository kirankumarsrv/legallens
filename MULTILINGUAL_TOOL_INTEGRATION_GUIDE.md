# Multilingual LLM Tool Integration - Implementation Guide

## Architecture Overview

Instead of a simple translation layer, we've implemented an **LLM-as-Router with Tool Integration** architecture:

```
Hindi Legal Document
    ↓
Language Detection (in evidence_ingest_node)
    ↓
Evidence State: detected_language="hi", source_language_name="Hindi"
    ↓
Legal Analysis Node (with tools available)
    ↓
LLM Receives: "Here's a Hindi legal case. You have translation tools available."
    ↓
LLM Decides:
  Option A: "I understand Hindi. Let me analyze directly."
  Option B: "I need clarity on terminology. Calling translation tool."
  Option C: "I need to verify sections. Calling legal term extractor."
    ↓
Tool Execution (if called) → LLM Processes Result
    ↓
Final Analysis (with proper context)
```

---

## What Was Implemented

### 1. **Language Detection Module** 
📁 `workflows/lawyer_agent/nodes/language_detection.py`

```python
# Detects language with confidence
result = detect_language_with_confidence(text)
# Returns:
# {
#     "primary_language": "hi",
#     "primary_language_name": "Hindi", 
#     "confidence": 0.92,
#     "detected_languages": {"hi": 0.92, "mr": 0.05, "en": 0.03}
# }
```

**Features:**
- ✅ Multi-language detection (Hindi, Tamil, Marathi, Bengali, etc.)
- ✅ Confidence scoring
- ✅ Fallback handling
- ✅ LLM-friendly descriptions

### 2. **Legal Translator Tool**
📁 `workflows/lawyer_agent/tools/legal_translator.py`

```python
# Tool available to LLM
@tool
def legal_translator(text: str, source_language: str = "hi") -> str:
    """Translate legal text while preserving IPC sections, case numbers, etc."""
```

**Preserves:**
- IPC sections (354C, 406, etc.)
- CrPC provisions
- Case numbers (CS-123/2024)
- FIR numbers
- Dates (15/10/2024)
- Proper nouns

**Example:**
```
Input: "IPC धारा 354C के तहत शिकायत दर्ज की गई है।"
Output: "IPC Section 354C prosecution was registered.
         [Preserved legal terms: IPC धारा 354C]"
```

### 3. **Legal Term Extractor Tool**
📁 `workflows/lawyer_agent/tools/legal_term_extractor.py`

```python
# Tool available to LLM
@tool
def extract_legal_terms_tool(text: str, language: str = "en") -> str:
    """Extract legal terminology from document."""
```

**Extracts:**
- IPC sections
- CrPC sections
- Constitution articles
- Case/FIR numbers
- Court names
- Legal concepts in original language

**Example:**
```
Input: "IPC धारा 354C, CrPC 144, Constitution Article 21"
Output: "LEGAL TERMS EXTRACTED:
         IPC SECTIONS: 354C
         CRPC SECTIONS: 144
         CONSTITUTION ARTICLES: 21"
```

### 4. **Updated Evidence Ingestion**
📁 `workflows/lawyer_agent/nodes/evidence_ingest.py`

Now includes language detection:

```python
def evidence_ingest_node(state: LawyerState) -> LawyerState:
    # ... existing code ...
    
    # NEW: Detect language
    lang_result = detect_language_with_confidence(evidence_text)
    state["detected_language"] = lang_result["primary_language"]      # "hi"
    state["source_language_name"] = lang_result["primary_language_name"]  # "Hindi"
    
    # Track in audit trail
    state["reasoning_trace"].append(
        f"Language: {lang_name} ({detected_lang}, {confidence:.0%} confidence)"
    )
```

### 5. **Updated State Schema**
📁 `workflows/lawyer_agent/state.py`

Added fields:
```python
class LawyerState(TypedDict):
    detected_language: Optional[str]      # "hi", "ta", "en", etc.
    source_language_name: Optional[str]   # "Hindi", "Tamil", "English"
```

### 6. **Tools Module**
📁 `workflows/lawyer_agent/tools/__init__.py`

Centralized tool management:
```python
def get_all_lawyer_agent_tools():
    """Return all tools available to LLM"""
    return [
        get_legal_translator_tool(),
        get_legal_term_extractor_tool(),
    ]
```

---

## How It Works in the Workflow

### Phase 0: Evidence Ingestion
```
Input: ["sample_fir.txt" (in Hindi)]
    ↓
Parse evidence (OCR if needed)
    ↓
Detect language: "hi" (Hindi, 92% confidence)
    ↓
Output: state["detected_language"] = "hi"
        state["source_language_name"] = "Hindi"
        state["evidence_text"] = "[Hindi text]"
```

### Phase 1: Entity Extraction
```
Input: Hindi evidence_text
    ↓
Extract entities (regex + spaCy work on any language)
    ↓
Output: entities = {"persons": [...], "dates": [...], "sections": [...]}
```

### Phase 2: Legal Analysis (WITH TOOLS)
```
Input: Hindi evidence + extracted entities + available tools
    ↓
LLM Prompt:
"You are analyzing a HINDI legal case. Here's the evidence:
[Hindi text summary]

Available tools:
1. legal_translator - Translate Hindi to English (preserves legal terms)
2. extract_legal_terms - Extract sections, case numbers, etc.

Analyze this case. Use tools if you need clarification."
    ↓
LLM Routes:
  Case 1: "I understand Hindi. Proceeding with analysis."
          → Analyzes directly
  
  Case 2: "I need the specific English meaning. Calling translator."
          → Calls: legal_translator(evidence_text, "hi", "en")
          → Receives: translated text with preserved terms
          → Analyzes translated + original
  
  Case 3: "Let me verify the legal references."
          → Calls: extract_legal_terms_tool(evidence_text, "hi")
          → Receives: structured terms
          → Uses in analysis
    ↓
Output: analysis with proper Hindi/English context
```

### Phase 3-4: Prediction & Drafting
```
Input: Analysis + precedents + tools (still available)
    ↓
LLM can still use tools if needed
    ↓
Output: Draft (in English, with Hindi terms noted where relevant)
```

---

## Usage Examples

### Example 1: Processing Hindi FIR

```python
from workflows.lawyer_agent.run import run_lawyer_agent, setup_dependencies

# Setup
dependencies = setup_dependencies()

# Hindi case
hindi_case = """
FIR संख्या: 12345/2024
प्रथमिकी दर्ज की गई है IPC धारा 354C के तहत।
शिकायतकर्ता: राजेश कुमार
अभियुक्त: विक्रम शर्मा
तारीख: 15/10/2024
"""

# Run workflow
run_lawyer_agent(
    question="Is this a valid FIR under IPC 354C?",
    dependencies=dependencies,
    evidence_files=["sample_hindi_fir.txt"]
)

# What happens:
# 1. evidence_ingest_node detects: detected_language="hi", source_language_name="Hindi"
# 2. entity_extraction extracts: sections, dates, persons
# 3. legal_analysis calls tools if needed
# 4. LLM generates analysis aware of Hindi context
```

### Example 2: Multilingual Evidence

```python
# Mixed Hindi + Tamil evidence
mixed_case = """
Hindi Section:
IPC धारा 354C के तहत प्रथमिकी दर्ज की गई है।

Tamil Section:
வழக்கு எண்: 456/2024
"""

# Workflow:
# 1. detection identifies: primarily Hindi (80%), some Tamil (15%)
# 2. LLM can use translation tool for Tamil portions
# 3. Analysis preserves both language contexts
```

---

## Benefits Over Simple Translation

| Aspect | Simple Translation | LLM with Tools |
|--------|-------------------|-----------------|
| **Legal Accuracy** | ❌ Lost in translation | ✅ LLM aware of context |
| **Cost** | ❌ Per-request API calls | ✅ Selective tool use |
| **Control** | ❌ No | ✅ LLM decides when/how to use |
| **Transparency** | ❌ Black box | ✅ Audit trail of tool calls |
| **Adaptability** | ❌ One approach | ✅ Different for each case |
| **Preservation** | ❌ Terminology lost | ✅ Legal terms preserved |

---

## Configuration & Settings

### Enable Tools in Legal Analysis Node

Update `workflows/lawyer_agent/nodes/legal_analysis.py`:

```python
from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools

def legal_analysis_node(state: LawyerState, ...) -> LawyerState:
    # Get available tools
    tools = get_all_lawyer_agent_tools()
    
    # Create prompt with language info
    language_note = ""
    if state.get("detected_language") != "en":
        language_note = f"This case is in {state['source_language_name']}. "
        language_note += "Use translation tools if needed for clarity."
    
    # Call LLM with tools
    response = llm.invoke(
        prompt=f"{language_note}\n{prompt_text}",
        tools=tools,
        tool_choice="auto"  # LLM decides
    )
    
    # Process tool calls and continue
```

### Environment Variables (if using Google Translate)

```bash
# .env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_TRANSLATE_API_KEY=your-api-key
```

### Requirements

Add to `requirements.txt`:

```
langdetect  # For language detection
google-cloud-translate  # For translation (optional, add if using Google API)
```

---

## Testing

### Test Language Detection

```python
python -c "
from workflows.lawyer_agent.nodes.language_detection import detect_language_with_confidence

hindi = 'IPC धारा 354C के तहत शिकायत दर्ज की गई है।'
result = detect_language_with_confidence(hindi)
print(f'Detected: {result[\"primary_language_name\"]} ({result[\"confidence\"]:.0%})')
"
```

### Test Tools

```python
from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools

tools = get_all_lawyer_agent_tools()
print(f"Available {len(tools)} tools:")
for tool in tools:
    print(f"  - {tool.name}")
```

---

## Future Enhancements

1. **Caching** - Cache translations for repeated sections
2. **Domain-specific Models** - Use specialized legal translation models
3. **Terminology DB** - Build knowledge base of legal terms per language
4. **Multi-step Analysis** - Different tools for different phases
5. **Bilingual Output** - Generate drafts with both languages
6. **Regional Variations** - Handle regional IPC/CrPC variations

---

## Troubleshooting

**Q: Language detection failing?**
- A: Ensure `langdetect` is installed: `pip install langdetect`
- Provide more text (>100 chars) for better detection

**Q: Tool not being called?**
- A: Check LLM model supports tool use (Groq models do)
- Verify tool is properly registered in `get_all_lawyer_agent_tools()`

**Q: Translation preserving sections?**
- A: Check `PRESERVE_PATTERNS` in `legal_translator.py` covers your use case

