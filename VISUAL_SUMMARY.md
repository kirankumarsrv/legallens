# Visual Summary: Multilingual Tool Integration

## The Three Approaches: Visual Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           YOUR THREE OPTIONS                                │
└─────────────────────────────────────────────────────────────────────────────┘

OPTION 1: Model Routing
═══════════════════════════════════════════════════════════════════════════════
                                                                      
    Hindi Document ──> Language Detected: "hi" ──> Route to Hindi Model?
                                                            │
                                                            ↓
                                                    ❌ GROQ HAS NO HINDI MODELS
                                                       All models English-only:
                                                       • llama-3.3-70b
                                                       • llama-3.1-70b
                                                       • mixtral-8x7b

VERDICT: ❌ NOT VIABLE


OPTION 2: Simple Translation
═══════════════════════════════════════════════════════════════════════════════
    
    Hindi Document ──> Google API ──> English ──> LLM Analyzes
         [Original]      [Translation]  [Context Lost]
    
    Problems:
    ❌ "शपथ" (legal oath) becomes generic "oath" (loses legal meaning)
    ❌ Extra API cost per request  
    ❌ Extra latency
    ❌ LLM has no context about original language
    ❌ Can't handle language-specific legal concepts

VERDICT: ❌ NOT IDEAL


OPTION 3: LLM + Tool Integration ✅ CHOSEN
═══════════════════════════════════════════════════════════════════════════════

    Hindi Document
         │
         ├──> Language Detection: "hi" (92% confidence)
         │
         ├──> Evidence Ingestion
         │    └──> state.detected_language = "hi"
         │
         ├──> LLM Receives:
         │    ├─ Evidence text (in Hindi)
         │    ├─ Facts extracted  
         │    └─ Tools available:
         │       ├─ legal_translator (Hindi → English, preserves terms)
         │       └─ extract_legal_terms (section references, case numbers)
         │
         ├──> LLM Routes Intelligently:
         │    ├─ "I understand Hindi. Analyzing directly."
         │    │  (No tool calls, natural analysis)
         │    │
         │    ├─ "I need clarity on terminology. Calling translator..."
         │    │  (Translates, preserves: "IPC 354C", "CS-123/2024")
         │    │
         │    └─ "Let me verify sections. Calling term extractor..."
         │       (Extracts: {ipc: [354C], case: [CS-123/2024]})
         │
         └──> Final Analysis
              (With proper legal context from original language)

BENEFITS:
✅ LLM stays intelligent (decides when/how to use tools)
✅ Legal terminology preserved 
✅ Selective tool use (costs only when needed)
✅ Works for all languages
✅ Audit trail (all tool calls logged)
✅ Extensible (add more tools as needed)

VERDICT: ✅ BEST APPROACH


┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPARISON TABLE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Aspect              │ Model Routing │ Translation │ Tools Integration       │
├─────────────────────┼───────────────┼─────────────┼────────────────────────┤
│ Works for all langs │      ❌       │      ✅     │        ✅              │
│ Available models    │      ❌       │      N/A    │        N/A             │
│ Legal accuracy      │      ⚠️       │      ❌     │        ✅              │
│ Cost efficiency     │      N/A      │      ❌     │        ✅              │
│ LLM intelligence    │      ⚠️       │      ❌     │        ✅              │
│ Control/routing     │      ❌       │      ❌     │        ✅              │
│ Extensible          │      ❌       │      ❌     │        ✅              │
│ Preserves terms     │      N/A      │      ❌     │        ✅              │
└─────────────────────┴───────────────┴─────────────┴────────────────────────┘
```

---

## Architecture Flow Diagram

```
MULTILINGUAL WORKFLOW ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

INPUT: Evidence File (Any Language)
           │
           ▼
┌─────────────────────────────────────────┐
│  PHASE 0: Evidence Ingestion (NEW)      │
├─────────────────────────────────────────┤
│  • Parse file (OCR if scanned)          │
│  • Detect language: "hi" ← NEW          │
│  • Store in state                       │
│  • confidence: 92%                      │
└─────────────────────────────────────────┘
           │ detected_language="hi"
           │ source_language_name="Hindi"
           ▼
┌─────────────────────────────────────────┐
│  PHASE 1: Entity Extraction             │
├─────────────────────────────────────────┤
│  • Extract from Hindi text              │
│  • Works on any language                │
│  • Get: persons, dates, sections        │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  PHASE 1.3: Timeline Construction       │
├─────────────────────────────────────────┤
│  • Order events chronologically         │
│  • Uses extracted dates                 │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: Legal Analysis (WITH TOOLS) ← NEW                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LLM Receives:                                              │
│  ├─ Evidence text (in Hindi)                               │
│  ├─ Facts extracted                                         │
│  └─ TOOLS Available:                                        │
│     ├─ legal_translator()       ← Can call if needed       │
│     └─ extract_legal_terms()    ← Can call if needed       │
│                                                              │
│  LLM Routes (tool_choice="auto"):                          │
│  ├─ Option A: Direct analysis (no tools)                  │
│  ├─ Option B: Calls translator (for clarity)              │
│  └─ Option C: Calls term extractor (for verification)     │
│                                                              │
│  Tool Execution (if called):                              │
│  ├─ Input: Hindi text, source="hi"                        │
│  ├─ Process: Translate/Extract                            │
│  ├─ Preserve: "IPC 354C", "CS-123/2024", "15/10/2024"    │
│  └─ Output: Structured data for LLM                       │
│                                                              │
│  LLM Continues: Analysis with proper context              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  PHASE 3: Prediction                     │
├─────────────────────────────────────────┤
│  • Uses context-aware analysis          │
│  • Tools still available if needed       │
│  • Outcome prediction                   │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  PHASE 4: Drafting                       │
├─────────────────────────────────────────┤
│  • Generate legal document               │
│  • Bilingual where relevant              │
│  • Proper citations                      │
└─────────────────────────────────────────┘
           │
           ▼
        OUTPUT: Legal Analysis & Draft
```

---

## What Was Built: Component Diagram

```
MULTILINGUAL SUPPORT COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────────────────┐
│                  LANGUAGE DETECTION                              │
├──────────────────────────────────────────────────────────────────┤
│  📁 language_detection.py                                       │
│  ├─ detect_language(text) → "hi"                               │
│  └─ detect_language_with_confidence(text) →                    │
│     {primary: "hi", confidence: 0.92, ...}                    │
└──────────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴────────┐
                    ▼                ▼
        ┌────────────────────────────────────────┐
        │  EVIDENCE INGESTION NODE               │
        ├────────────────────────────────────────┤
        │  📁 evidence_ingest.py (UPDATED)      │
        │  ├─ Parse evidence                    │
        │  ├─ Detect language                   │
        │  └─ Store in state                    │
        │     detected_language="hi"            │
        │     source_language_name="Hindi"      │
        └────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌─────────────────────────┐  ┌──────────────────────────┐
│   TOOLS AVAILABLE       │  │  STATE SCHEMA (UPDATED)  │
├─────────────────────────┤  ├──────────────────────────┤
│  📁 tools/__init__.py   │  │  📁 state.py             │
│                         │  │                          │
│  get_all_lawyer_..()    │  │  + detected_language     │
│  ├─ legal_translator()  │  │  + source_language_name │
│  └─ extract_legal_..()  │  │                          │
│                         │  │  Flows through entire    │
│                         │  │  workflow                │
└─────────────────────────┘  └──────────────────────────┘
        │                           │
        │  Registered to:           │
        │                           │
        └──────────────┬────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  LLM (with tool support)     │
        ├──────────────────────────────┤
        │  Receives:                   │
        │  ├─ Evidence                 │
        │  ├─ Language context         │
        │  ├─ Available tools           │
        │  └─ Tool definitions          │
        │                              │
        │  Can call:                   │
        │  ├─ legal_translator         │
        │  └─ extract_legal_terms      │
        └──────────────────────────────┘
```

---

## Tool Interaction Diagram

```
LEGAL TRANSLATOR TOOL
═══════════════════════════════════════════════════════════════════════════════

Input:  "IPC धारा 354C के तहत शिकायत दर्ज की गई है।
         FIR No. 12345/2024"
        source_language="hi"

Process:
┌─────────────────────────────────────────┐
│ 1. Extract preserve tokens:             │
│    • "IPC धारा 354C" → __PRESERVE_0__   │
│    • "12345/2024" → __PRESERVE_1__      │
│    • Masked text → Send to Google API   │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│ 2. Translate masked text                │
│    (Google Translate API)               │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│ 3. Restore preserved tokens             │
│    • __PRESERVE_0__ → "IPC धारा 354C"   │
│    • __PRESERVE_1__ → "12345/2024"      │
└─────────────────────────────────────────┘

Output: "IPC Section 354C complaint was registered.
         FIR No. 12345/2024
         
         [Preserved terms: IPC धारा 354C, 12345/2024]"


LEGAL TERM EXTRACTOR TOOL
═══════════════════════════════════════════════════════════════════════════════

Input:  "IPC धारा 354C, CrPC 144, Constitution Article 21"
        language="hi"

Process:
┌───────────────────────────────────────────────────────────┐
│ 1. Regex patterns for:                                    │
│    • IPC sections (354C)                                  │
│    • CrPC sections (144)                                  │
│    • Constitution articles (21)                           │
│    • Case numbers, FIR numbers                            │
│    • Legal concepts in Hindi                              │
└───────────────────────────────────────────────────────────┘
                    │
┌───────────────────────────────────────────────────────────┐
│ 2. Structure results                                      │
└───────────────────────────────────────────────────────────┘

Output: {
          "ipc_sections": ["354C"],
          "crpc_sections": ["144"],
          "constitution_articles": ["21"],
          "legal_concepts": ["शपथ", "निर्णय"]
        }
```

---

## Data Flow: Complete Journey

```
                    Hindi FIR
                       │
                       ▼
        ┌──────────────────────────┐
        │ Evidence Ingest (Phase 0)│
        ├──────────────────────────┤
        │ language_detection.py    │
        │ Result: detected_lang=hi │
        │        confidence=92%    │
        └──────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
   state object              tools registry
   detected_lang="hi"   ┌──→ legal_translator
   source_lang="Hindi"  │    extract_legal_terms
                        │
        ┌───────────────┴────────────┐
        ▼                            ▼
   Entity Extraction          LLM Analysis
   persons, dates,            (tools available)
   sections, FIRs
                               LLM decides:
        │                      ├─ Direct analysis
        ├─────────┬─────────┬──┤ OR
        │          │         │  ├─ Call translator
        ▼          ▼         ▼  │
   Timeline  Facts  Entities │  └─ Call extractor
   Building  Summary Export  │
                             ▼
                      Tools execute (if called)
                      ├─ Translate (preserve terms)
                      └─ Extract (structure data)
                             │
                             ▼
                      Analysis generation
                      (with full context)
                             │
        ┌────────────────────┴────────────────┐
        ▼                                      ▼
   Prediction                            Drafting
   (using analysis)                    (final document)
```

---

## Status Dashboard

```
╔═══════════════════════════════════════════════════════════════╗
║              MULTILINGUAL INTEGRATION STATUS                  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ✅ INFRASTRUCTURE COMPLETE                                  ║
║  ├─ Language detection module      [READY]                  ║
║  ├─ Legal translator tool          [READY]                  ║
║  ├─ Legal term extractor tool      [READY]                  ║
║  ├─ Tool registry                  [READY]                  ║
║  ├─ State schema updated           [READY]                  ║
║  └─ Evidence ingestion updated     [READY]                  ║
║                                                               ║
║  ⏳ AWAITING: Legal Analysis Node Integration                 ║
║  ├─ Add tools to llm.invoke()      [TODO: 5 min]            ║
║  └─ Add language context to prompt [TODO: 2 min]            ║
║                                                               ║
║  📚 DOCUMENTATION COMPLETE                                   ║
║  ├─ Architecture decision          [✅ 400 lines]            ║
║  ├─ Implementation guide           [✅ 500 lines]            ║
║  ├─ Integration code guide         [✅ 400 lines]            ║
║  ├─ Quick reference                [✅ 2 pages]             ║
║  └─ This visual summary            [✅ NOW]                 ║
║                                                               ║
╠═══════════════════════════════════════════════════════════════╣
║  ESTIMATE: 5 minutes to full integration                      ║
║  EFFORT: Change legal_analysis_node (3 lines)                ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Next Action

```
┌──────────────────────────────────────────────────────┐
│  STEP 1: Read                                        │
│  📖 QUICK_REFERENCE.md (5 min)                      │
│                                                       │
│  STEP 2: Integrate                                   │
│  📝 INTEGRATION_CODE_GUIDE.md                       │
│     → Copy 3 lines to legal_analysis_node           │
│                                                       │
│  STEP 3: Test                                        │
│  🧪 python -m workflows.lawyer_agent.run            │
│     → Language will auto-detect                      │
│     → Tools available to LLM                         │
│                                                       │
│  ⏱️  Total Time: ~10 minutes                         │
└──────────────────────────────────────────────────────┘
```

---

**Architecture**: LLM + Tool Integration ✅
**Status**: Infrastructure Complete, Ready to Integrate
**Next**: 5-minute integration in legal_analysis_node
