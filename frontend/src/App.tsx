import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import CaseList from './components/CaseList';
import CaseWorkflow from './pages/CaseWorkflow';
import HomePage from './pages/HomePage';
import { ThemeProvider } from './contexts/ThemeContext';
import ThemeToggle from './components/ThemeToggle';
import './App.css';

function App() {
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  return (
    <ThemeProvider>
      <Router>
        <div className="app">
          <ThemeToggle />
          <nav className="navbar">
          <div className="navbar-brand">
            <Link to="/" className="brand-link">
              ⚖️ Lawyer Agent AI
            </Link>
          </div>
          <ul className="nav-links">
            <li>
              <Link to="/">Home</Link>
            </li>
            <li>
              <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
                API Docs
              </a>
            </li>
          </ul>
        </nav>

        <main className="app-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/case/:caseId" element={<CaseWorkflow />} />
          </Routes>
        </main>

        <footer className="app-footer">
          <p>&copy; 2024 Lawyer Agent AI. All rights reserved.</p>
        </footer>
      </div>
    </Router>
    </ThemeProvider>
  );
}

export default App;
