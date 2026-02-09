================================================================================
TEST CASE WITH ANOMALIES - COMPLETE PACKAGE
================================================================================

CASE NAME: State vs. Munjappa - Theft Case
CASE TYPE: Criminal Theft (High-Value Electronics)
TEST PURPOSE: Entity Extraction & Anomaly Detection
TOTAL FILES PROVIDED: 5 Documents

================================================================================
FILES IN THIS PACKAGE
================================================================================

1. TEST_CASE_NER_ANOMALIES.txt (MAIN PROBLEM STATEMENT)
   - Complete problem statement for the case
   - Contains intentional anomalies for testing
   - Describes expected system behavior
   - Instructions on how to test in frontend
   - File Size: ~12 KB

2. TEST_FIR_BNG_2025_78945.txt (FIRST INFORMATION REPORT)
   - Official police FIR document
   - Contains suspect details, timeline, charges
   - Legal sections referenced (IPC 379, 380, 406)
   - Investigating officer report
   - File Size: ~8 KB
   
3. TEST_MEDICAL_REPORT.txt (HOSPITAL MEDICAL EXAMINATION)
   - Medical examination from Apollo Hospital
   - Injury assessment of accused
   - Custody fitness report
   - Doctor's certification
   - File Size: ~6 KB

4. TEST_WITNESS_STATEMENTS.txt (WITNESS TESTIMONIES)
   - 4 witness statements recorded
   - Includes Complainant, Security, CCTV Operator, Manager
   - Timeline verification from witnesses
   - Anomaly flags embedded in document
   - File Size: ~7 KB

5. TEST_CCTV_REPORT.txt (VIDEO SURVEILLANCE ANALYSIS)
   - Frame-by-frame timeline analysis
   - Key moments with timestamps
   - Technical details of CCTV system
   - Evidence preservation information
   - File Size: ~8 KB

================================================================================
KEY ANOMALIES IN THIS TEST CASE
================================================================================

ANOMALY #1: NAME VARIATION (Fuzzy Matching Test)
Expected Detection:
  - "Munjappa" appears 6 times (Primary name)
  - "Munyappa" appears 3 times (Alternate spelling)
  - System should recognize 88%+ similarity
  - Should suggest consolidation to canonical form: "MUNJAPPA"

Status in Files:
  ✓ Present in all documents
  ✓ Inconsistently used (intentional)
  ✓ Test for fuzzy matching capability

---

ANOMALY #2: ROLE CONFLICT (HIGH SEVERITY)
Expected Detection:
  - "Arun Kumar" appears as TWO DIFFERENT PEOPLE:
    * Arun Kumar Singh = Complainant (Shop Owner, Age 38)
    * Arun Kumar = Police Officer (Constable, ID: DL-2025-CSI-4521)
  - Same first/last name but DIFFERENT ROLES and AGES
  - System should flag as HIGH severity conflict
  - Requires clarification: Are they same person or different?

Status in Files:
  ✓ Present in all documents
  ✓ Clearly marked in anomaly detection sections
  ✓ Test for role conflict detection

---

ANOMALY #3: NAME AMBIGUITY (MEDIUM SEVERITY)
Expected Detection:
  - "Priya" appears as TWO DIFFERENT PEOPLE:
    * Priya Sharma (Age 45, Security Officer)
    * Priya (Age 28, CCTV Operator)
  - Different ages, roles, and last names
  - System should flag as MEDIUM severity (potential duplicates)
  - Require lawyer clarification: Are these separate individuals?

Status in Files:
  ✓ Present in all documents  
  ✓ Marked with [ANOMALY FLAGGED] notes
  ✓ Test for name ambiguity detection

---

ANOMALY #4: PERSON CONSOLIDATION (Simple Matching)
Expected Detection:
  - "Rajesh Kumar" appears consistently (Age 55, Manager)
  - Role and age CONSISTENT across mentions
  - System should recognize as SAME PERSON
  - Should consolidate into single entity
  - No clarification needed

Status in Files:
  ✓ Present in all documents
  ✓ Consistent attributes
  ✓ Test for successful consolidation

================================================================================
HOW TO USE THIS TEST CASE
================================================================================

STEP 1: PREPARE THE PROBLEM STATEMENT
- Open TEST_CASE_NER_ANOMALIES.txt
- Copy the "Problem Statement" section (lines 5-40)

STEP 2: CREATE A NEW CASE IN FRONTEND
- Open http://localhost:5173/
- Click "Create New Case"
- Enter Case Name: "State vs. Munjappa"
- Click "Create"

STEP 3: ENTER PROBLEM STATEMENT
- Go to "Case Workflow" tab
- Paste problem statement into the textarea
- Click "Save Problem"

STEP 4: UPLOAD EVIDENCE FILES (OPTIONAL)
- Click "Upload Files" in Evidence section
- Select these files to upload:
  * TEST_FIR_BNG_2025_78945.txt
  * TEST_MEDICAL_REPORT.txt
  * TEST_WITNESS_STATEMENTS.txt
  * TEST_CCTV_REPORT.txt
- Click "Upload Files"

STEP 5: RUN COMPUTE
- Click "🔧 Run Compute" button
- This will trigger:
  ✓ Entity Extraction (NER)
  ✓ Entity Normalization
  ✓ Anomaly Detection
  ✓ Conflict Identification
  ✓ Clarification Question Generation

STEP 6: VIEW RESULTS
- Wait for computation to complete (~2-5 minutes)
- Click "🏷️ Entities & Conflicts" tab
- Review:
  ✓ Entity Summary (Should show 6 persons → 5 after consolidation)
  ✓ Conflicts Panel (Should show 2 conflicts)
  ✓ Clarification Questions (Should show 3+ questions)
  ✓ Entity Mapping (Should show normalization)

STEP 7: VERIFY ANOMALY DETECTION
Expected System Output:

PERSONS EXTRACTED:
  1. Munjappa/Munyappa → [CONSOLIDATED TO: "Munjappa"]
  2. Arun Kumar Singh
  3. Arun Kumar [CONFLICT FLAG: Also appears as complainant?]
  4. Priya Sharma
  5. Priya [CONFLICT FLAG: Different from Priya Sharma? Age mismatch]
  6. Rajesh Kumar

CONFLICTS:
  ✓ HIGH: "Arun Kumar" role confusion (Complainant vs Police Officer)
  ✓ MEDIUM: "Priya" name ambiguity (Different ages & roles)
  ✓ NAME VARIATION: "Munjappa" ↔ "Munyappa" (RESOLVED)

CLARIFICATION QUESTIONS:
  Q1: Are "Arun Kumar Singh" and "Arun Kumar" the same person?
  Q2: Are "Priya Sharma" and "Priya" the same person?
  Q3: Confirm consolidation of "Munjappa" and "Munyappa"?

================================================================================
TEST VALIDATION CHECKLIST
================================================================================

ENTITY EXTRACTION:
  ☐ System extracts all persons mentioned
  ☐ System extracts dates correctly
  ☐ System extracts sections (IPC 379, 380, 406, 34)
  ☐ System extracts case numbers
  ☐ System extracts amounts (Rs. 2,50,000)
  ☐ System extracts locations

ANOMALY DETECTION:
  ☐ Name variation detected (Munjappa ↔ Munyappa)
  ☐ Role conflict detected (Arun Kumar dual roles)
  ☐ Name ambiguity detected (Priya - two different people)
  ☐ Successful consolidation (Rajesh Kumar)

CONFLICT FLAGGING:
  ☐ HIGH severity conflicts marked
  ☐ MEDIUM severity conflicts marked
  ☐ LOW severity conflicts marked (if any)
  ☐ Severity levels accurate

CLARIFICATION QUESTIONS:
  ☐ Questions generated for HIGH severity conflicts
  ☐ Questions are clear and specific
  ☐ Questions can be answered by lawyer
  ☐ Lawyer interface allows responses

RESULT: ✅ PASS if all checkboxes are verified

================================================================================
EXPECTED TEST RESULTS
================================================================================

PASSING CRITERIA:
✓ All 6 persons extracted
✓ Munjappa/Munyappa consolidated to 1 entity
✓ 2+ conflicts detected and flagged
✓ HIGH severity conflicts properly identified
✓ 3+ clarification questions generated
✓ No false positives in anomaly detection

TIMELINE ACCURACY:
✓ All dates normalized
✓ Sequence of events preserved
✓ Timestamps accurate

LEGAL ACCURACY:
✓ IPC sections correctly identified
✓ Charges properly extracted
✓ Case numbers preserved

================================================================================
TROUBLESHOOTING
================================================================================

IF FILES DON'T UPLOAD:
- Ensure file names are exactly as shown
- File format must be .txt
- Maximum file size: 10 MB each

IF ANOMALIES NOT DETECTED:
- Verify LLM is configured (Claude/OpenAI)
- Check that Entity Extraction is enabled
- Review compute logs for errors
- Try running compute again

IF CONFLICTS NOT FLAGGED:
- Ensure anomaly detection is enabled
- Check conflict detection parameters
- Review LLM response for anomaly analysis
- Verify that conflicting data is present in problem statement

IF NAMES NOT CONSOLIDATED:
- Verify fuzzy matching is enabled
- Check minimum similarity threshold (should be ~80%+)
- Try running normalization step again

================================================================================
ADDITIONAL NOTES
================================================================================

1. This test case is designed to stress-test the NER system
2. Real-world cases may have MORE anomalies
3. The specific anomalies here are intentional and well-documented
4. Use this test case to validate system behavior before production use
5. Expected test duration: 5-10 minutes with UI + compute time

LEGAL CONTEXT:
- Case is fictional but based on realistic Indian legal scenario
- IPC sections and procedures are accurate
- Medical examination format follows Indian standards
- Witness statements follow legal documentation format

CONTACT FOR ISSUES:
If anomalies are not detected as expected, please:
1. Check system logs for LLM errors
2. Verify NER model is properly initialized
3. Ensure all dependencies are installed
4. Contact development team with detailed logs

================================================================================
