# Complete Setup & Deployment Guide - Lawyer Agent AI

## System Overview

The Lawyer Agent AI is a full-stack application consisting of:
- **Backend**: Python FastAPI (Port 8000)
- **Database**: SQLite (case_sessions.db)
- **Frontend**: React + TypeScript with Vite (Port 3000)

## Prerequisites

### System Requirements
- Windows 10/11 or macOS/Linux
- Python 3.9+ (for backend)
- Node.js 16+ (for frontend)
- Git (for version control)

### Required Tools
```bash
# Python
python --version          # Should be 3.9+

# Node.js & npm
node --version           # Should be 16+
npm --version            # Should be 8+

# Git
git --version            # Should be 2.x+
```

## Complete Installation Steps

### Step 1: Backend Setup

#### 1.1 Navigate to project
```bash
cd c:\Users\kiran\Desktop\law ai
```

#### 1.2 Create and activate virtual environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 1.3 Install Python dependencies
```bash
pip install -r requirements.txt
```

Key packages:
- FastAPI (REST API framework)
- Uvicorn (ASGI server)
- Pydantic (data validation)
- SQLite3 (database)
- LangGraph (workflow orchestration)
- Groq (LLM provider)
- ChromaDB (vector database)

#### 1.4 Configure environment variables
```bash
# Set Groq API key (required for LLM)
$env:GROQ_API_KEY = "your-groq-api-key-here"

# Optional: Configure API settings
$env:API_HOST = "0.0.0.0"
$env:API_PORT = "8000"
```

Get Groq API key from: https://console.groq.com/keys

### Step 2: Frontend Setup

#### 2.1 Navigate to frontend directory
```bash
cd c:\Users\kiran\Desktop\law ai\frontend
```

#### 2.2 Install Node.js dependencies
```bash
npm install
```

This installs:
- React 18
- TypeScript
- Vite
- React Router
- Axios

#### 2.3 Configure environment (optional)
```bash
# Frontend connects to backend on localhost:8000 by default
# To use different backend URL, create .env.local:
echo "REACT_APP_API_URL=http://localhost:8000" > .env.local
```

### Step 3: Database Setup

The SQLite database is created automatically on first run. To reset:

```bash
# Windows
Remove-Item case_sessions.db -ErrorAction SilentlyContinue

# macOS/Linux
rm -f case_sessions.db
```

Database schema includes tables for:
- case_sessions
- case_facts
- case_arguments
- case_prediction_history
- case_state_flags

## Running the Application

### Option 1: Run Both Backend and Frontend (Recommended)

#### Terminal 1 - Start Backend API
```bash
# From project root
cd c:\Users\kiran\Desktop\law ai

# Activate virtual environment if not already active
.\.venv\Scripts\Activate.ps1

# Start FastAPI server
uvicorn workflows.lawyer_agent.api:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Access API docs at: http://localhost:8000/docs

#### Terminal 2 - Start Frontend Dev Server
```bash
# From project root
cd c:\Users\kiran\Desktop\law ai\frontend

# Start Vite dev server
npm run dev
```

Expected output:
```
  VITE v5.0.0  ready in 123 ms

  ➜  Local:   http://localhost:3000/
  ➜  press h to show help
```

Open browser: http://localhost:3000

### Option 2: Production Build

#### Build Frontend
```bash
cd c:\Users\kiran\Desktop\law ai\frontend
npm run build
```

This creates optimized build in `dist/` directory.

#### Serve Production Build
```bash
npm run preview
```

Or use a web server like:
```bash
# Install http-server globally
npm install -g http-server

# Serve the dist folder
http-server dist
```

## Testing

### Run Backend Tests
```bash
# From project root
cd c:\Users\kiran\Desktop\law ai

# Ensure virtual environment is active
.\.venv\Scripts\Activate.ps1

# Run pytest
pytest -v

# Run specific test file
pytest tests/test_groq_connection.py -v

# Run with coverage
pytest --cov=modules --cov=workflows
```

### Test API Manually
```bash
# List all cases
curl http://localhost:8000/cases

# Create new case
curl -X POST http://localhost:8000/cases \
  -H "Content-Type: application/json" \
  -d '{"case_name": "Test Case", "case_type": "Criminal"}'

# View API documentation
# Open browser to: http://localhost:8000/docs
```

## Workflow Usage

### 1. Create a Case
- Navigate to http://localhost:3000
- Click "+ New Case" button
- Enter case name and optionally case type
- Click "Create Case"

### 2. Add Facts
- In case workflow, navigate to "Facts" tab
- Click "+ Add Fact" button
- Enter fact description and source document
- Click "Save Fact"

### 3. Approve/Lock Facts
- Review fact in the list
- Click "✓ Approve" to move to approved status
- Once approved, click "🔒 Lock" to finalize fact

### 4. Create Arguments
- Navigate to "Arguments" tab
- Click "+ Add Argument"
- Enter legal argument text
- Select supporting facts by checking checkboxes
- Click "Save Argument"

### 5. Approve/Lock Arguments
- Similar to facts workflow
- Facts must be locked before arguments can significantly impact predictions

### 6. View Predictions
- Navigate to "Predictions" tab
- Current prediction shows confidence score
- Prediction History shows prior predictions
- Click "Restore" to revert to previous prediction

### 7. Generate Report
- Once prediction is locked, case is complete
- Export or download case summary (feature)

## File Locations

### Backend Files
```
c:\Users\kiran\Desktop\law ai\
├── workflows/
│   └── lawyer_agent/
│       ├── api.py                 # FastAPI REST API
│       ├── nodes/
│       │   ├── interactive_fact_refiner.py
│       │   ├── fact_analysis.py
│       │   ├── argument_generation.py
│       │   └── prediction.py
│       ├── ui_streamlit.py        # Streamlit UI for facts
│       └── ui_argument_refiner.py # Streamlit UI for arguments
├── modules/
│   ├── case_session_storage.py   # SQLite persistence layer
│   ├── fact_storage.py
│   ├── argument_storage.py
│   ├── llm_manager.py
│   └── ...
└── case_sessions.db             # SQLite database
```

### Frontend Files
```
c:\Users\kiran\Desktop\law ai\frontend\
├── package.json               # Dependencies
├── tsconfig.json             # TypeScript config
├── vite.config.ts            # Vite config
├── README.md                 # Frontend docs
├── public/
│   └── index.html
└── src/
    ├── main.tsx             # Entry point
    ├── App.tsx              # Main app
    ├── index.css            # Global styles
    ├── components/
    │   ├── CaseList.tsx
    │   ├── FactEditor.tsx
    │   ├── ArgumentEditor.tsx
    │   └── PredictionViewer.tsx
    ├── pages/
    │   ├── HomePage.tsx
    │   └── CaseWorkflow.tsx
    └── services/
        └── api.ts           # REST API wrapper
```

## Troubleshooting

### Issue: "ModuleNotFoundError" for Python packages
**Solution:**
```bash
# Verify virtual environment is activated
# Should show (.venv) at start of terminal prompt

# Reinstall requirements
pip install -r requirements.txt

# If still failing, try upgrade pip
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Issue: "Address already in use" (Port 8000 or 3000)
**Solution:**
```bash
# Find process using port 8000
Get-NetTCPConnection -LocalPort 8000

# Kill the process (replace PID with actual ID)
Stop-Process -Id PID -Force

# Or use different port
uvicorn workflows.lawyer_agent.api:app --host 0.0.0.0 --port 8001
```

### Issue: CORS errors in browser console
**Solution:**
- Verify backend is running on http://localhost:8000
- Check CORS is enabled in api.py (it is by default)
- Set `REACT_APP_API_URL` in frontend .env.local

### Issue: npm install fails
**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
Remove-Item node_modules -Recurse -Force
Remove-Item package-lock.json

# Reinstall
npm install
```

### Issue: Groq API key error
**Solution:**
```bash
# Verify API key is set
$env:GROQ_API_KEY

# If not set, set it again
$env:GROQ_API_KEY = "your-groq-api-key"

# Verify it's working
python -c "import os; print(os.getenv('GROQ_API_KEY'))"
```

## Performance Optimization

### Backend
- Database queries are indexed by case_id
- Connection pooling for database
- Async API endpoints with FastAPI
- LLM calls cached where possible

### Frontend
- Code splitting via React Router
- Lazy component loading
- CSS Grid for layout efficiency
- Optimized image and asset loading

## Security Notes

- API uses CORS (Cross-Origin Resource Sharing) - verify in production
- Groq API key should be in environment variables, not hardcoded
- Frontend validates all inputs before sending to API
- Database uses parameterized queries to prevent SQL injection
- Consider adding authentication for production deployment

## Deployment

### Docker Deployment

#### Build Docker Image
```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "workflows.lawyer_agent.api:app", "--host", "0.0.0.0"]

# Frontend Dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Run with Docker Compose
```yaml
version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      GROQ_API_KEY: ${GROQ_API_KEY}
    volumes:
      - ./case_sessions.db:/app/case_sessions.db

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:80"
    environment:
      REACT_APP_API_URL: http://localhost:8000
    depends_on:
      - backend
```

### Cloud Deployment (Azure/AWS)
- Backend: Deploy to App Service / EC2
- Frontend: Deploy to Static Web App / S3 + CloudFront
- Database: Azure SQL / RDS for managed database
- API Gateway: For production API routing

## Monitoring & Logs

### Backend Logs
```bash
# Verbose logging
uvicorn workflows.lawyer_agent.api:app --log-level debug

# Save to file
uvicorn ... > logs.txt 2>&1
```

### Frontend Logs
- Open browser DevTools (F12)
- Check Console tab for errors
- Network tab for API calls

### Database
```bash
# Query database directly
sqlite3 case_sessions.db

# List tables
.tables

# View case data
SELECT * FROM case_sessions;

# View facts for specific case
SELECT * FROM case_facts WHERE case_id = 'case_id_here';
```

## Version Control

### Check Git Status
```bash
git status
git log --oneline

# View recent commits
git log -5
```

### Update from Repository
```bash
git pull origin main
```

### Create New Branch
```bash
git checkout -b feature/new-feature
git add .
git commit -m "Description"
git push origin feature/new-feature
```

## Getting Help

- **API Documentation**: http://localhost:8000/docs (when backend running)
- **Frontend README**: See `frontend/README.md`
- **Backend Documentation**: See project docs/ directory
- **GitHub Issues**: Check repository for similar issues

## Next Steps

1. ✅ Backend running on port 8000
2. ✅ Frontend running on port 3000
3. Create first case and complete workflow
4. Export case summary as PDF (future feature)
5. Set up production deployment
6. Configure monitoring and logging
7. Add user authentication
8. Implement advanced search and filtering

## Summary

The Lawyer Agent AI is now fully configured! 

- Backend: FastAPI REST API with SQLite persistence
- Frontend: React + TypeScript interactive UI
- Integration: Full REST API communication
- Database: Automatic schema creation and management

**To start working:**
```bash
# Terminal 1: Start backend
.\.venv\Scripts\Activate.ps1
uvicorn workflows.lawyer_agent.api:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev

# Open browser
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

Enjoy using Lawyer Agent AI! 🚀⚖️
