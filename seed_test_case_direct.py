#!/usr/bin/env python3
"""Seed a test case directly into SQLite database with persistent data."""

import sqlite3
import uuid
from datetime import datetime

DB_PATH = r"c:\Users\kiran\Desktop\law ai\case_sessions.db"
case_id = str(uuid.uuid4())

# Create/connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    case_name TEXT,
    case_type TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT,
    updated_at TEXT,
    fact_count INTEGER DEFAULT 0,
    argument_count INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS state_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    flag_key TEXT NOT NULL,
    flag_value TEXT,
    created_at TEXT,
    UNIQUE(case_id, flag_key),
    FOREIGN KEY(case_id) REFERENCES cases(case_id)
)
''')

# Insert case
now = datetime.now().isoformat()
cursor.execute('''
INSERT INTO cases (case_id, case_name, case_type, status, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?)
''', (case_id, "Demo: State vs. Munjappa - Persistent Data Test", "Criminal Theft", "active", now, now))

# Problem Statement
problem_statement = """On January 15, 2025, at approximately 10:30 PM, a theft incident occurred at the Central Shopping Mall, Bangalore. The accused, Munjappa (also known as Munyappa, Age: 42, Resident of 123 Domlur Lane, Bangalore 560071), allegedly stole electronics worth Rs. 2,50,000.

Key Persons Involved:
- Accused: Munjappa (also referred as Munyappa in police records, DOB: 1982-03-10)
- Complainant: Arun Kumar Singh (Age: 38, Shop owner at Kiosk 15, Central Mall)
- Police Officer: Arun Kumar (ID: DL-2025-CSI-4521, Senior Constable, Bangalore Police)
- Witness 1: Priya Sharma (Age: 45, Mall Security Officer)
- Witness 2: Priya (Age: 28, CCTV Operator at Central Shopping Complex)
- Witness 3: Rajesh Kumar (Age: 55, Store Manager, Central Shopping Mall)

The accused allegedly stole electronics worth Rs. 2,50,000 from the electronics section."""

cursor.execute('''
INSERT OR REPLACE INTO state_flags (case_id, flag_key, flag_value, created_at)
VALUES (?, ?, ?, ?)
''', (case_id, 'problem_statement', problem_statement, now))

# Evidence files
evidence_files = '["evidence_uploads/TEST_FIR_BNG_2025_78945.txt","evidence_uploads/TEST_MEDICAL_REPORT.txt","evidence_uploads/TEST_WITNESS_STATEMENTS.txt","evidence_uploads/TEST_CCTV_REPORT.txt"]'
cursor.execute('''
INSERT OR REPLACE INTO state_flags (case_id, flag_key, flag_value, created_at)
VALUES (?, ?, ?, ?)
''', (case_id, 'evidence_files', evidence_files, now))

# Legal Analysis
analysis = """**Legal Position Analysis**

The law applicable to this case is primarily the Indian Penal Code (IPC), specifically Sections 379, 380, and 406, which pertain to theft, theft in a dwelling house, and criminal breach of trust, respectively. Additionally, Section 34 of the IPC, which deals with acts done by several persons in furtherance of a common intention, may also be relevant given the potential involvement of Police Officer Arun Kumar.

**Key Legal Arguments:**

**1. Theft Under IPC Section 379:** The facts clearly indicate that Munjappa allegedly stole electronics worth Rs. 2,50,000, which directly falls under the definition of theft as per IPC Section 379. This argument is persuasive because it is based on direct evidence of the act of theft.

**2. Criminal Breach of Trust Under IPC Section 406:** If it can be proven that Munjappa was entrusted with the electronics or had access to them in a position of trust (e.g., as a customer allowed to handle goods), and he then misappropriated them, this could constitute a criminal breach of trust. This argument is strong because it highlights a potential betrayal of trust.

**3. Common Intention Under IPC Section 34:** The presence of Police Officer Arun Kumar during the theft time raises questions about potential complicity. If evidence suggests that both Munjappa and Arun Kumar acted in furtherance of a common intention, they could both be charged under Section 34."""

cursor.execute('''
INSERT OR REPLACE INTO state_flags (case_id, flag_key, flag_value, created_at)
VALUES (?, ?, ?, ?)
''', (case_id, 'current_analysis', analysis, now))

# Draft
draft = """**LEGAL MEMORANDUM**

**Title:** Prosecution Brief - State vs. Munjappa & Arun Kumar (Alleged)

**Case Reference:** BNG/2025/78945

**1. FACTS OF THE CASE**

- On January 15, 2025, at 10:30 PM, a theft incident occurred at Central Shopping Mall, Bangalore
- Electronics worth Rs. 2,50,000 were allegedly stolen from the electronics counter
- The accused, Munjappa (also referred to as Munyappa), allegedly committed the theft
- Police Officer Arun Kumar was on patrol duty at the mall during the incident

**2. LEGAL ISSUES TO BE DETERMINED**

1. Whether Munjappa is guilty of theft under IPC Section 379?
2. Whether Police Officer Arun Kumar was complicit in the theft?
3. Whether the elements of criminal breach of trust (IPC Section 406) are satisfied?
4. Whether the doctrine of common intention (IPC Section 34) applies?

**3. APPLICABLE LAW**

- **Indian Penal Code Section 379:** Defines theft as dishonestly removing, secreting, or causing to be removed or secreted any movable property
- **Indian Penal Code Section 380:** Prescribes enhanced punishment for theft in a dwelling house
- **Indian Penal Code Section 406:** Deals with criminal breach of trust
- **Indian Penal Code Section 34:** Concerns acts done by several persons in furtherance of common intention

**4. RECOMMENDATION**

Proceed with prosecution under Sections 379 and 34 IPC. Conduct further investigation into Police Officer Arun Kumar's role."""

cursor.execute('''
INSERT OR REPLACE INTO state_flags (case_id, flag_key, flag_value, created_at)
VALUES (?, ?, ?, ?)
''', (case_id, 'current_draft', draft, now))

# Prediction
prediction = """Based on the evidence available and the legal framework, the prosecution has a **moderately strong case** against Munjappa for theft under IPC Section 379.

**Strengths:**
- Direct CCTV evidence showing Munjappa at the scene
- Clear eyewitness account from Shop Owner Arun Kumar Singh
- Medical examination evidence from Apollo Hospital
- Stolen items recovery report dated January 16, 2025

**Weaknesses:**
- Potential role of Police Officer Arun Kumar raises questions about complicity
- Name variations (Munjappa/Munyappa) need clarification
- Need to establish whether theft was from a dwelling house (for Section 380)

**Likely Outcome:**
- Conviction probability: **65-75%** for theft under Section 379
- Likelihood of co-accused charges: **Moderate** (pending investigation into Arun Kumar)
- Recommended further investigation: Police conduct and timing"""

cursor.execute('''
INSERT OR REPLACE INTO state_flags (case_id, flag_key, flag_value, created_at)
VALUES (?, ?, ?, ?)
''', (case_id, 'current_prediction', prediction, now))

# Confidence
cursor.execute('''
INSERT OR REPLACE INTO state_flags (case_id, flag_key, flag_value, created_at)
VALUES (?, ?, ?, ?)
''', (case_id, 'current_confidence', '0.70', now))

# Timestamps
cursor.execute('''
INSERT OR REPLACE INTO state_flags (case_id, flag_key, flag_value, created_at)
VALUES (?, ?, ?, ?)
''', (case_id, 'workflow_output_timestamp', now, now))

cursor.execute('''
INSERT OR REPLACE INTO state_flags (case_id, flag_key, flag_value, created_at)
VALUES (?, ?, ?, ?)
''', (case_id, 'problem_statement_saved_at', now, now))

cursor.execute('''
INSERT OR REPLACE INTO state_flags (case_id, flag_key, flag_value, created_at)
VALUES (?, ?, ?, ?)
''', (case_id, 'evidence_uploaded_at', now, now))

conn.commit()
conn.close()

print(f"\n{'='*70}")
print(f"✅ SEEDING COMPLETE!")
print(f"{'='*70}")
print(f"\n📋 Test Case Created: {case_id}")
print(f"\n🔗 Open this URL to see persisted data:")
print(f"   http://localhost:5173/cases/{case_id}/workflow")
print(f"\n📊 Persisted Data (in SQLite):")
print(f"   ✅ Problem Statement")
print(f"   ✅ Evidence Files (4 files persisted as paths)")
print(f"   ✅ Legal Analysis (markdown formatted)")
print(f"   ✅ Draft Memorandum (formatted with sections)")
print(f"   ✅ Prediction (with 70% confidence)")
print(f"   ✅ All timestamps")
print(f"\n🔄 Test Persistence:")
print(f"   1. Make sure frontend is running at http://localhost:5173/")
print(f"   2. Open the case in frontend (click link above)")
print(f"   3. See all data displays")
print(f"   4. Close the browser or refresh page (Ctrl+R)")
print(f"   5. All data persists! ✨")
print(f"\n{'='*70}\n")
