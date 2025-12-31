INSTRUCTIONS FOR TESTING THE CASE WORKFLOW
============================================

This document provides a quick start guide for testing the Law AI workflow 
with sample problem statement and evidence files.

---

## STEP 1: Start Backend Server

In a PowerShell terminal, from the project root:

```powershell
cd "C:\Users\kiran\Desktop\law ai"
# Activate virtual environment if using one
.\.venv\Scripts\Activate.ps1
# Start the backend
uvicorn workflows.lawyer_agent.api:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
- "Uvicorn running on http://0.0.0.0:8000"
- Watch for changes enabled

---

## STEP 2: Start Frontend Server

In a second PowerShell terminal:

```powershell
cd "C:\Users\kiran\Desktop\law ai\frontend"
npm run dev -- --host
```

Expected output:
- Server running on http://localhost:3001 (or similar)
- Shows "Local:" and "Network:" URLs

---

## STEP 3: Access the Application

Open your browser and navigate to:
- http://localhost:3001 (or the URL shown in terminal)

---

## STEP 4: Create a Case

1. Click the "Create Case" button
2. Enter a case name: `State vs. Rajesh Kumar - Motor Vehicle Accident`
3. Enter case type (optional): `Motor Vehicle Act Violation`
4. Click "Create Case"
5. You will be navigated to the Case Workflow page with a case ID

---

## STEP 5: Enter Problem Statement

1. On the Case Workflow page, locate the "Problem Statement & Evidence" section
2. Copy the content from `SAMPLE_PROBLEM_STATEMENT.txt`:
   - Open: C:\Users\kiran\Desktop\law ai\SAMPLE_PROBLEM_STATEMENT.txt
   - Copy the "Problem Statement" section (starting from "Case Title:" to "Should the defendant's driving license be revoked?")
3. Paste into the "Problem Statement" textarea in the web application
4. Click the "Save Problem" button

Expected: Alert shows "Problem statement saved"

---

## STEP 6: Upload Evidence Files

1. In the "Attach evidence files" section, click the file input
2. Navigate to: C:\Users\kiran\Desktop\law ai\
3. Select these files:
   - SAMPLE_EVIDENCE_FIR.txt
   - SAMPLE_EVIDENCE_MEDICAL_REPORT.txt
   (You can also include evidence_samples/sample_fir.txt if available)
4. Click "Upload Files" button

Expected: Alert shows number of files uploaded, and they appear in "Uploaded:" list

---

## STEP 7: Run the Compute Workflow

1. Click the "Run Compute" button
2. Observe the "Reasoning Trace" section for real-time progress:
   - Evidence Ingest phase
   - Fact Gathering phase (retrieves facts from evidence)
   - Legal Analysis phase (analyzes applicable laws)
   - Prediction phase (generates prediction and outcome)
3. Once complete, the "Prediction" tab will show:
   - Current prediction
   - Confidence level
   - Reasoning details

---

## STEP 8: Review & Approve Facts

1. Click on the "Facts" tab
2. Review the automatically extracted facts from the evidence
3. For each fact, you can:
   - Edit the content if needed
   - Click "Approve" to mark as reliable
   - Click "Reject" if the fact is incorrect
   - Click "Lock" after approval to finalize

---

## STEP 9: Review & Approve Arguments

1. Click on the "Arguments" tab
2. Review the legal arguments generated based on facts
3. Similar actions available:
   - Edit, Approve, Reject, Lock

---

## STEP 10: View Prediction

1. Click on the "Prediction" tab
2. Review the AI-generated prediction for case outcome
3. If you want to re-run with different facts:
   - Edit facts in the "Facts" tab
   - Click "Run Compute" again
   - The system will use the new facts for re-analysis

---

## SAMPLE DATA LOCATION

All sample files are located at: C:\Users\kiran\Desktop\law ai\

Files created for testing:
- SAMPLE_PROBLEM_STATEMENT.txt     (Problem statement)
- SAMPLE_EVIDENCE_FIR.txt          (First Information Report)
- SAMPLE_EVIDENCE_MEDICAL_REPORT.txt (Medical examination report)

Existing evidence samples (optional):
- evidence_samples/sample_fir.txt
- evidence_samples/sample_charge_sheet.txt
- evidence_samples/sample_fir_hindi.txt
- evidence_samples/multilingual_sample.txt

---

## TROUBLESHOOTING

### Backend won't start:
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000
# Try a different port:
uvicorn workflows.lawyer_agent.api:app --reload --host 0.0.0.0 --port 8001
# Then update VITE_API_BASE in frontend .env:
# VITE_API_BASE=http://localhost:8001
```

### Frontend won't start:
```powershell
# Clear node_modules and reinstall
rm -r node_modules package-lock.json
npm install
npm run dev
```

### Port conflicts:
```powershell
# Kill process using port 3001
netstat -ano | findstr :3001
taskkill /PID <PID_NUMBER> /F
# Or use a different port:
npm run dev -- --port 3002
```

### API connection issues:
- Ensure backend is running on port 8000
- Check browser console (F12) for network errors
- Verify VITE_API_BASE environment variable is set correctly

---

## EXPECTED WORKFLOW OUTPUT

After running compute, you should see:

### Facts (5-8 facts):
- Accident occurred at specific location and time
- Defendant was driving at excessive speed
- Defendant ran red traffic signal
- Defendant's BAC was above legal limit
- Victim sustained multiple injuries
- etc.

### Arguments (3-5 arguments):
- Breach of Motor Vehicle Act, 1988
- Violation of traffic safety regulations
- Negligence causing bodily harm
- Aggravated offense due to alcohol consumption
- etc.

### Prediction:
- Liability: HIGH (85-95% confidence)
- Recommended Outcome: Guilty of charges under Section 304A IPC
- Compensation Range: Based on injury severity and damages
- License Action: Suspension for 2-3 years

---

## NOTES

- The system uses placeholder LLM if real API keys are not configured
- For production analysis, configure environment variables:
  - LLM_PROVIDER (groq, openai)
  - LLM_MODEL
  - OPENAI_API_KEY or GROQ_API_KEY
  - EMBEDDING_MODEL
  
- All data is stored in SQLite: case_sessions.db
- Evidence files are saved in: evidence_uploads/ directory

---

Happy testing! For issues, check the backend terminal logs and browser console (F12).
