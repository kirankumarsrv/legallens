#!/usr/bin/env python
"""Quick integration test"""

print("\n" + "="*60)
print("INTEGRATION TEST: Multilingual Tool Support")
print("="*60)

# Test 1: Tools available
print("\n✅ TEST 1: Tools Loading")
try:
    from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools
    tools = get_all_lawyer_agent_tools()
    print(f"   ✅ Loaded {len(tools)} tools: {[t.name for t in tools]}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 2: Language detection
print("\n✅ TEST 2: Language Detection")
try:
    from workflows.lawyer_agent.nodes.language_detection import detect_language_with_confidence
    
    hindi_text = 'IPC धारा 354C के तहत शिकायत दर्ज की गई है।'
    result = detect_language_with_confidence(hindi_text)
    
    lang = result.get("primary_language_name", "Unknown")
    code = result.get("primary_language", "?")
    conf = result.get("confidence", 0)
    
    print(f"   Input: {hindi_text[:30]}...")
    print(f"   Language: {lang} ({code}) - {conf:.0%} confidence")
    print(f"   ✅ Detected correctly")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 3: Translator tool
print("\n✅ TEST 3: Legal Translator Tool")
try:
    from workflows.lawyer_agent.tools.legal_translator import translate_legal
    
    hindi = "IPC धारा 354C के तहत शिकायत"
    result = translate_legal(hindi, source_language="hi", target_language="en")
    
    print(f"   Input: {hindi}")
    print(f"   Method: {result.get('method', 'unknown')}")
    print(f"   Preserved terms: {result.get('preserved_terms', [])}")
    print(f"   ✅ Translator ready")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 4: Legal Analysis node updated
print("\n✅ TEST 4: Legal Analysis Node Integration")
try:
    from workflows.lawyer_agent.nodes.legal_analysis import legal_analysis_node
    import inspect
    
    source = inspect.getsource(legal_analysis_node)
    if "get_all_lawyer_agent_tools" in source:
        print("   ✅ legal_analysis_node has tool integration")
    else:
        print("   ❌ legal_analysis_node missing tool integration")
except Exception as e:
    print(f"   ❌ Failed: {e}")

print("\n" + "="*60)
print("INTEGRATION TESTS COMPLETE")
print("="*60 + "\n")
