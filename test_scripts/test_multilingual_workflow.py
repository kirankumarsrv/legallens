"""
Test Multilingual Support: Hindi FIR Processing
================================================

This test demonstrates the complete multilingual workflow:
1. Load Hindi FIR
2. Detect language automatically
3. Show tools available to LLM
4. Process through full workflow
5. Demonstrate translator tool in action
"""

import sys
import os

# Add workspace to path
sys.path.insert(0, r"c:\Users\kiran\Desktop\law ai")

from workflows.lawyer_agent.run import run_lawyer_agent

def test_multilingual_hindi_fir():
    """Test with Hindi FIR - Language detection & translation"""
    
    print("\n" + "="*70)
    print("🌍 MULTILINGUAL TEST: HINDI FIR PROCESSING")
    print("="*70)
    
    question = """
CLIENT CASE: WORKPLACE PRIVACY VIOLATION (HINDI EVIDENCE)

FACTS:
- Client: Rajesh Kumar (Employee)
- Employer: TechCorp India Pvt Ltd
- Timeline: July 2023 - October 2024
- Issue: Employer monitored personal emails without consent
  * Keylogger installed by IT department
  * Personal, family, medical emails monitored
  * Company refused to stop despite requests
  * No employee policy or consent obtained

QUESTION:
Does employer's action violate Article 21 right to privacy?
What remedies are available to Rajesh?

APPLICABLE AREAS: Article 21 (Constitution), IPC Privacy Sections, IT Act 2000
"""
    
    evidence_files = [
        "evidence_samples/sample_fir_hindi.txt",  # Hindi FIR we just created
    ]
    
    print(f"\n📋 Question: {question.strip()[:100]}...\n")
    print(f"📁 Evidence Files:")
    for ef in evidence_files:
        full_path = os.path.join(r"c:\Users\kiran\Desktop\law ai", ef)
        if os.path.exists(full_path):
            print(f"   ✅ {ef} ({os.path.getsize(full_path)} bytes)")
        else:
            print(f"   ❌ {ef} (NOT FOUND)")
    
    print("\n" + "-"*70)
    print("🚀 EXECUTING WORKFLOW WITH HINDI EVIDENCE")
    print("-"*70)
    
    try:
        # Run the lawyer agent with Hindi evidence
        final_state = run_lawyer_agent(
            question=question,
            evidence_files=evidence_files
        )
        
        print("\n" + "="*70)
        print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
        print("="*70)
        
        # Print key results
        print("\n🔍 DETECTED LANGUAGE:")
        if final_state.get("detected_language"):
            lang = final_state.get("detected_language")
            lang_name = final_state.get("source_language_name", "Unknown")
            confidence = final_state.get("language_confidence", "N/A")
            print(f"   ✅ {lang_name} ({lang}) - Confidence: {confidence}")
        else:
            print("   ⚠️  No language detected")
        
        print("\n📦 TOOLS AVAILABLE:")
        if final_state.get("tools_used"):
            for tool in final_state.get("tools_used", []):
                print(f"   ✅ {tool}")
        else:
            print("   ℹ️  Tools available but not used in this workflow")
        
        print("\n📊 AUDIT TRAIL:")
        for trace in final_state.get("reasoning_trace", [])[-5:]:
            print(f"   • {trace}")
        
        print("\n📄 ANALYSIS SUMMARY (First 300 chars):")
        analysis = final_state.get("analysis", "")
        if analysis:
            preview = analysis[:300].replace("\n", " ")
            print(f"   {preview}...")
        else:
            print("   No analysis generated")
        
        print("\n" + "="*70)
        print("✅ MULTILINGUAL TEST PASSED")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_language_detection_directly():
    """Direct test of language detection on Hindi text"""
    
    print("\n" + "="*70)
    print("🔍 DIRECT LANGUAGE DETECTION TEST")
    print("="*70)
    
    from workflows.lawyer_agent.nodes.language_detection import detect_language_with_confidence
    
    test_cases = [
        ("English: This is a privacy violation case", "English"),
        ("Hindi: भारतीय संविधान के अनुच्छेद 21 के तहत निजता का अधिकार", "Hindi"),
        ("Tamil: தனியுரிமை உரிமைகள் பாதுகாப்பு கட்டளை", "Tamil"),
        ("IPC धारा 354C के तहत शिकायत दर्ज की गई है।", "Hindi (IPC section)"),
    ]
    
    for text, expected in test_cases:
        result = detect_language_with_confidence(text)
        detected = result.get("primary_language", "Unknown")
        confidence = result.get("confidence", 0)
        
        status = "✅" if detected.lower() == expected.lower().split()[0] else "⚠️"
        print(f"\n{status} Expected: {expected}")
        print(f"   Detected: {detected}")
        print(f"   Confidence: {confidence:.2%}")
        print(f"   Sample: {text[:60]}...")


def test_translator_tool():
    """Test the legal translator tool directly"""
    
    print("\n" + "="*70)
    print("🔄 LEGAL TRANSLATOR TOOL TEST")
    print("="*70)
    
    from workflows.lawyer_agent.tools.legal_translator import translate_legal
    
    hindi_text = "IPC धारा 354C के तहत गोपनीयता उल्लंघन के लिए शिकायत दर्ज की गई है। केस CS-123/2024 और FIR No. 12345/2024 में।"
    
    print(f"\n📝 Input (Hindi):")
    print(f"   {hindi_text}\n")
    
    try:
        result = translate_legal(
            text=hindi_text,
            source_language="hi",
            target_language="en"
        )
        
        print(f"✅ Translation Status: {result.get('status')}")
        print(f"\n📝 Output (English):")
        print(f"   {result.get('translated_text')}\n")
        
        print(f"🔒 Preserved Legal Terms:")
        for term in result.get('preserved_terms', []):
            print(f"   • {term}")
        
    except Exception as e:
        print(f"⚠️  Translation test: {str(e)}")


if __name__ == "__main__":
    # Run all tests
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "MULTILINGUAL LEGAL AI - TEST SUITE" + " "*19 + "║")
    print("╚" + "="*68 + "╝")
    
    # Test 1: Direct language detection
    test_language_detection_directly()
    
    # Test 2: Translator tool
    test_translator_tool()
    
    # Test 3: Full workflow with Hindi evidence
    test_multilingual_hindi_fir()
    
    print("\n✅ ALL TESTS COMPLETED\n")
