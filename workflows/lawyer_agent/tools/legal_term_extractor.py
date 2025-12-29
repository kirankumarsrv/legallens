"""
Legal Term Extractor

Extracts domain-specific legal terms while preserving original language.
Identifies: IPC sections, CrPC provisions, case references, legal concepts.
"""

import re
from typing import Dict, List, Optional
from collections import defaultdict


def extract_legal_terms(text: str, language: str = "en") -> Dict:
    """
    Extract legal terminology from text.
    
    Args:
        text: Legal document text
        language: Language code (hi, en, ta, mr, etc.)
    
    Returns:
        {
            "ipc_sections": ["354C", "406"],
            "crpc_sections": ["144"],
            "constitution_articles": ["21"],
            "case_numbers": ["CS-123/2024"],
            "fir_numbers": ["12345/2024"],
            "legal_concepts": ["शपथ", "निर्णय"],
            "authorities": ["Police Station", "District Court"],
        }
    """
    
    if not text:
        return {}
    
    result = defaultdict(list)
    
    # IPC Sections (Indian Penal Code)
    ipc_pattern = r'\b(?:IPC|Indian\s+Penal\s+Code)\s+(?:Section|Sec\.?|S\.?|धारा|अनुभाग)\s*[:\-]?\s*(\d{1,4}[A-Za-z]*)'
    for match in re.finditer(ipc_pattern, text, re.IGNORECASE):
        section = match.group(1).strip()
        if section not in result["ipc_sections"]:
            result["ipc_sections"].append(section)
    
    # CrPC Sections (Criminal Procedure Code)
    crpc_pattern = r'\b(?:CrPC|Cr\.P\.C|Criminal\s+Procedure\s+Code)\s+(?:Section|Sec\.?|S\.?|धारा)\s*[:\-]?\s*(\d{1,4}[A-Za-z]*)'
    for match in re.finditer(crpc_pattern, text, re.IGNORECASE):
        section = match.group(1).strip()
        if section not in result["crpc_sections"]:
            result["crpc_sections"].append(section)
    
    # Constitution Articles
    constitution_pattern = r'\b(?:Constitution|Article)\s+(?:of\s+India)?\s*[:\-]?\s*(\d{1,3}[A-Za-z]*)'
    for match in re.finditer(constitution_pattern, text, re.IGNORECASE):
        article = match.group(1).strip()
        if article not in result["constitution_articles"]:
            result["constitution_articles"].append(article)
    
    # Case Numbers
    case_pattern = r'\b(?:Case|Charge\s+Sheet|CS|WP)\b\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d+[/\-]\d{2,4})'
    for match in re.finditer(case_pattern, text, re.IGNORECASE):
        case_num = match.group(1).strip()
        if case_num not in result["case_numbers"]:
            result["case_numbers"].append(case_num)
    
    # FIR Numbers
    fir_pattern = r'\bFIR\b\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d+[/\-]\d{2,4})'
    for match in re.finditer(fir_pattern, text, re.IGNORECASE):
        fir_num = match.group(1).strip()
        if fir_num not in result["fir_numbers"]:
            result["fir_numbers"].append(fir_num)
    
    # Authorities (Police Station, Court, etc.)
    authority_pattern = r'(?:Police\s+Station|Court|Magistrate|Commissioner)\s*[:\-]?\s*([A-Z][A-Za-z\s,&.]*?)(?:\n|State|District|$)'
    for match in re.finditer(authority_pattern, text, re.IGNORECASE):
        authority = match.group(1).strip()
        if authority and len(authority) > 2:
            if authority not in result["authorities"]:
                result["authorities"].append(authority)
    
    # Legal Concepts (language-specific)
    legal_concepts = _extract_legal_concepts(text, language)
    result["legal_concepts"] = legal_concepts
    
    return {k: v for k, v in result.items() if v}  # Remove empty keys


def _extract_legal_concepts(text: str, language: str) -> List[str]:
    """
    Extract legal concepts specific to language.
    
    Hindi legal concepts, Tamil legal terms, etc.
    """
    
    concepts = {
        "hi": {
            "शपथ": "oath/affidavit",
            "निर्णय": "judgment/decision",
            "अभियोजन": "prosecution",
            "प्रतिवादी": "defendant",
            "अभियुक्त": "accused",
            "याचिकाकर्ता": "petitioner",
            "अधिकार": "right/authority",
            "दायित्व": "liability/responsibility",
            "क्षति": "damage",
            "मुआवजा": "compensation",
        },
        "ta": {
            "மனுவு": "petition",
            "தீர்ப்பு": "judgment",
            "வழக்கு": "case",
            "பொறுப்பு": "responsibility",
            "ஆதாரம்": "evidence",
        },
        "mr": {
            "शपथ": "oath",
            "निर्णय": "judgment",
            "केस": "case",
            "साक्ष्य": "evidence",
        },
    }
    
    concept_dict = concepts.get(language, {})
    found = []
    
    for concept, meaning in concept_dict.items():
        if concept in text:
            found.append(concept)
    
    return found


def get_legal_term_extractor_tool():
    """Return LangChain tool for legal term extraction."""
    from langchain_core.tools import tool
    
    @tool
    def extract_legal_terms_tool(
        text: str,
        language: str = "en",
    ) -> str:
        """
        Extract legal terminology from a document.
        
        Identifies and categorizes:
        - IPC/CrPC section references
        - Constitution article references
        - Case and FIR numbers
        - Court/Authority names
        - Legal concepts in source language
        
        Args:
            text: The legal document text
            language: Language code (hi, ta, en, mr, etc.)
        
        Returns:
            Formatted list of extracted legal terms
        
        Example:
            extract_legal_terms_tool(
                "IPC 354C के तहत केस CS-123/2024",
                language="hi"
            )
        """
        terms = extract_legal_terms(text, language)
        
        if not terms:
            return "No legal terms extracted."
        
        output = "Extracted Legal Terms:\n"
        for category, items in terms.items():
            output += f"\n{category.upper().replace('_', ' ')}:\n"
            for item in items:
                output += f"  • {item}\n"
        
        return output
    
    return extract_legal_terms_tool


if __name__ == "__main__":
    # Test
    test_hindi = """
    IPC धारा 354C के तहत शिकायत दर्ज की गई है।
    CrPC धारा 144 लागू किया गया।
    Constitution Article 21 का उल्लंघन।
    केस नंबर: CS-12345/2024
    FIR: 98765/2024
    """
    
    terms = extract_legal_terms(test_hindi, language="hi")
    print("Extracted Legal Terms:")
    for category, items in terms.items():
        print(f"\n{category.upper()}:")
        for item in items:
            print(f"  - {item}")
