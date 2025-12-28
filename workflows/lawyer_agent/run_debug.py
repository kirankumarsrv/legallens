"""
Enhanced Debug Runner for Lawyer Agent

This runner provides DETAILED LOGGING of:
    1. Which node is executing
    2. What the node is doing (input state details)
    3. What happens next (output state changes)
    4. Why it's happening (reasoning and context)
    5. Graph flow verification

Perfect for:
    - Debugging workflow logic
    - Verifying graph structure
    - Understanding node dependencies
    - Tracking state transformations

Test Questions:
    1. "Is right to privacy a fundamental right in India?"
    2. "What are the limits on freedom of speech?"
    3. "Can death penalty be imposed in murder cases?"
"""

import sys
import os
import json
from typing import Dict, Any
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from workflows.lawyer_agent.graph import build_lawyer_agent_graph
from workflows.lawyer_agent.state import LawyerState
from modules.embedding_manager import EmbeddingManager
from modules.llm_manager import LLMManager
from modules.vector_store.chroma_vector_store import ChromaVectorStore
from modules.vector_store.FAISS_vector_store import FAISSVectorStore
from langchain_chroma import Chroma


# ==================== LOGGING UTILITIES ====================

class LLMCallLogger:
    """Tracks and logs LLM API calls with queries and responses"""
    
    def __init__(self):
        self.llm_calls = []
        self.call_counter = 0
    
    def log_llm_call(self, node_name: str, query: str, response: str = "", 
                     model: str = "", tokens_used: int = 0):
        """Log an LLM API call"""
        self.call_counter += 1
        timestamp = datetime.now()
        
        log_entry = {
            "call_number": self.call_counter,
            "node_name": node_name,
            "timestamp": timestamp.isoformat(),
            "model": model,
            "query_length": len(query),
            "response_length": len(response),
            "tokens_used": tokens_used
        }
        
        self.llm_calls.append(log_entry)
        
        # Print formatted output
        print(f"\n   🤖 LLM CALL #{self.call_counter}")
        print(f"      Model: {model}")
        print(f"      Timestamp: {timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        
        if query:
            # Truncate long queries for readability
            query_preview = query[:150].replace('\n', ' ') + ("..." if len(query) > 150 else "")
            print(f"      📤 Query: {query_preview}")
            print(f"         (Total length: {len(query)} characters)")
        
        if response:
            # Truncate long responses for readability
            response_preview = response[:150].replace('\n', ' ') + ("..." if len(response) > 150 else "")
            print(f"      📥 Response: {response_preview}")
            print(f"         (Total length: {len(response)} characters)")
        
        if tokens_used > 0:
            print(f"      🔤 Tokens Used: {tokens_used}")
    
    def print_llm_summary(self):
        """Print summary of all LLM calls"""
        print("\n" + "=" * 80)
        print("🤖 LLM CALLS SUMMARY")
        print("=" * 80)
        print(f"\nTotal LLM Calls: {self.call_counter}")
        
        print("\nCall Details:")
        for call in self.llm_calls:
            print(f"  Call #{call['call_number']}: {call['node_name']}")
            print(f"    Model: {call['model']}")
            print(f"    Query size: {call['query_length']} chars")
            print(f"    Response size: {call['response_length']} chars")
            if call['tokens_used'] > 0:
                print(f"    Tokens: {call['tokens_used']}")


class NodeExecutionLogger:
    """Tracks and logs node execution with detailed context"""
    
    def __init__(self):
        self.execution_log = []
        self.node_counter = 0
        self.start_time = datetime.now()
        self.llm_logger = LLMCallLogger()
    
    def log_node_start(self, node_name: str, input_state: LawyerState):
        """Log when a node starts executing"""
        self.node_counter += 1
        timestamp = datetime.now()
        
        log_entry = {
            "sequence": self.node_counter,
            "node_name": node_name,
            "timestamp": timestamp.isoformat(),
            "event": "NODE_START",
            "input_state": self._summarize_state(input_state)
        }
        
        self.execution_log.append(log_entry)
        
        # Print formatted output
        print("\n" + "=" * 80)
        print(f"📍 NODE #{self.node_counter}: {node_name.upper()}")
        print("=" * 80)
        print(f"⏱️  Time: {timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        print(f"📥 INPUT STATE SUMMARY:")
        print(self._format_state_summary(input_state))
    
    def log_node_end(self, node_name: str, output_state: LawyerState, reasoning: str = ""):
        """Log when a node finishes executing"""
        timestamp = datetime.now()
        
        log_entry = {
            "sequence": self.node_counter,
            "node_name": node_name,
            "timestamp": timestamp.isoformat(),
            "event": "NODE_END",
            "output_state": self._summarize_state(output_state),
            "reasoning": reasoning
        }
        
        self.execution_log.append(log_entry)
        
        # Print formatted output
        print(f"\n📤 OUTPUT STATE SUMMARY:")
        print(self._format_state_summary(output_state))
        
        if reasoning:
            print(f"\n💡 REASONING:")
            print(f"   {reasoning}")
        
        print(f"✅ {node_name} completed")
    
    def log_edge_transition(self, from_node: str, to_node: str, reason: str = ""):
        """Log transition between nodes"""
        timestamp = datetime.now()
        
        log_entry = {
            "event": "EDGE_TRANSITION",
            "from_node": from_node,
            "to_node": to_node,
            "timestamp": timestamp.isoformat(),
            "reason": reason
        }
        
        self.execution_log.append(log_entry)
        
        print(f"\n🔀 TRANSITION: {from_node} → {to_node}")
        if reason:
            print(f"   Reason: {reason}")
    
    def log_phase_complete(self, phase_name: str, phase_number: int, next_phase: str = ""):
        """Log when a phase completes"""
        timestamp = datetime.now()
        
        print("\n" + "-" * 80)
        print(f"✨ PHASE {phase_number} COMPLETE: {phase_name.upper()}")
        print("-" * 80)
        
        if next_phase:
            print(f"📌 Next: {next_phase.upper()}")
        
        elapsed = (timestamp - self.start_time).total_seconds()
        print(f"⏱️  Elapsed: {elapsed:.2f}s")
    
    def _summarize_state(self, state: LawyerState) -> Dict[str, Any]:
        """Create a summary of the state"""
        return {
            "question_set": bool(state.get("question")),
            "facts_count": len(state.get("facts", [])),
            "analysis_length": len(state.get("analysis", "")),
            "statutes_count": len(state.get("statutes", [])),
            "precedents_count": len(state.get("precedents", [])),
            "prediction_set": bool(state.get("prediction")),
            "draft_length": len(state.get("draft", "")),
            "templates_count": len(state.get("templates", [])),
            "citations_count": len(state.get("citations", [])),
            "approved_phase": state.get("approved_phase", "None"),
            "reasoning_trace_length": len(state.get("reasoning_trace", []))
        }
    
    def _format_state_summary(self, state: LawyerState) -> str:
        """Format state summary for readable output"""
        summary = self._summarize_state(state)
        
        lines = []
        lines.append(f"   Question: {'✅ Set' if summary['question_set'] else '❌ Not set'}")
        lines.append(f"   Facts: {summary['facts_count']} items")
        lines.append(f"   Analysis: {summary['analysis_length']} chars")
        lines.append(f"   Statutes: {summary['statutes_count']} items")
        lines.append(f"   Precedents: {summary['precedents_count']} items")
        lines.append(f"   Prediction: {'✅ Set' if summary['prediction_set'] else '❌ Not set'}")
        lines.append(f"   Draft: {summary['draft_length']} chars")
        lines.append(f"   Templates: {summary['templates_count']} items")
        lines.append(f"   Citations: {summary['citations_count']} items")
        lines.append(f"   Approved Phase: {summary['approved_phase']}")
        lines.append(f"   Reasoning Trace: {summary['reasoning_trace_length']} entries")
        
        return "\n".join(lines)
    
    def print_execution_summary(self):
        """Print final execution summary"""
        print("\n" + "=" * 80)
        print("📊 EXECUTION SUMMARY")
        print("=" * 80)
        
        print(f"\nTotal Nodes Executed: {self.node_counter}")
        print(f"Total Duration: {(datetime.now() - self.start_time).total_seconds():.2f}s")
        
        print(f"\nExecution Sequence:")
        current_seq = -1
        for entry in self.execution_log:
            if entry.get("event") == "NODE_START":
                print(f"  {entry['sequence']}. START → {entry['node_name']}")
            elif entry.get("event") == "NODE_END":
                print(f"  {entry['sequence']}. END ← {entry['node_name']}")
            elif entry.get("event") == "EDGE_TRANSITION":
                print(f"       ↓ {entry['from_node']} → {entry['to_node']}")
        
        # Print LLM summary
        if self.llm_logger.call_counter > 0:
            self.llm_logger.print_llm_summary()


# ==================== INSTRUMENTED GRAPH ====================

def build_instrumented_graph(dependencies: dict, logger: NodeExecutionLogger) -> Any:
    """
    Build the lawyer agent graph with instrumentation for debugging.
    
    Each node is wrapped to log its execution details.
    """
    
    from workflows.lawyer_agent.nodes.fact_gathering import fact_gathering_node
    from workflows.lawyer_agent.nodes.legal_analysis import legal_analysis_node
    from workflows.lawyer_agent.nodes.prediction import prediction_node
    from workflows.lawyer_agent.nodes.drafting import drafting_node
    from workflows.lawyer_agent.nodes.human_approval import human_approval_node
    from langgraph.graph import StateGraph, START, END
    
    graph = StateGraph(LawyerState)
    
    # ==================== PHASE 1: FACT GATHERING ====================
    
    def fact_gathering_instrumented(state: LawyerState) -> LawyerState:
        """
        PHASE 1: FACT GATHERING
        
        Purpose:
            Extract and retrieve relevant facts from the question
            Search statutes, constitution, and legal documents
            
        Input Expected:
            - question: The user's legal question
            
        Output Expected:
            - facts: List of relevant legal facts
            - facts_raw: Raw document objects
            
        Next Step:
            Moves to approval gate where human reviews facts
        """
        logger.log_node_start("fact_gathering", state)
        
        print("\n📋 NODE DETAILS - FACT GATHERING:")
        print("   Purpose: Extract facts from user question")
        print("            Search relevant legal documents (Constitution, IPC, CrPC)")
        print("            Retrieve fact-based statutes")
        print("\n   What's Happening:")
        print("   1. Processing question:", state.get("question", "")[:60] + "...")
        print("   2. Searching Constitution store...")
        print("   3. Searching IPC store...")
        print("   4. Searching CrPC store...")
        print("   5. Aggregating results into 'facts' list")
        
        result = fact_gathering_node(
            state,
            dependencies["chroma_stores"],
            dependencies["embedding_model"]
        )
        
        logger.log_node_end("fact_gathering", result, 
            reasoning="Extracted facts from legal documents. Ready for review.")
        logger.log_phase_complete("Fact Gathering", 1, "Approval Gate")
        
        return result
    
    graph.add_node("fact_gathering", fact_gathering_instrumented)
    
    # ==================== GATE 1: APPROVE FACTS ====================
    
    def approve_facts_instrumented(state: LawyerState) -> LawyerState:
        """
        GATE 1: HUMAN APPROVAL OF FACTS
        
        Purpose:
            Allow human to review and validate facts extracted in Phase 1
            
        Input:
            - facts: From fact_gathering node
            
        Output:
            - approved_phase: Set to "facts" if approved
            
        Next Step:
            If approved → Legal Analysis
            If rejected → Would go back to fact gathering (not implemented)
        """
        logger.log_node_start("approve_facts", state)
        
        print("\n🔑 NODE DETAILS - APPROVAL GATE #1:")
        print("   Purpose: Human reviews and validates extracted facts")
        print("   Type: Human-in-the-loop approval gate")
        print("\n   Decision Point:")
        print("   ✓ APPROVE → Continue to Legal Analysis")
        print("   ✗ REVISE → Return to Fact Gathering (TODO)")
        print("   ⊘ STOP → Halt workflow")
        
        result = human_approval_node(state, "facts")
        
        logger.log_node_end("approve_facts", result,
            reasoning="Human reviewed facts. Proceeding to next phase.")
        logger.log_phase_complete("Approval Gate #1", 1, "Legal Analysis")
        
        return result
    
    graph.add_node("approve_facts", approve_facts_instrumented)
    
    # ==================== PHASE 2: LEGAL ANALYSIS ====================
    
    def legal_analysis_instrumented(state: LawyerState) -> LawyerState:
        """
        PHASE 2: LEGAL ANALYSIS
        
        Purpose:
            Analyze the legal question using facts
            Search and retrieve relevant statutes
            Find applicable case law (precedents)
            Generate legal reasoning
            
        Input Expected:
            - question: Original question
            - facts: Approved facts from Phase 1
            
        Output Expected:
            - analysis: Detailed legal reasoning
            - statutes: Retrieved statute sections
            - precedents: Retrieved case law
            
        Why This Phase:
            Facts alone are insufficient - need legal framework (statutes)
            and practical application (precedents/case law)
            
        Next Step:
            Moves to approval gate where human reviews analysis
        """
        logger.log_node_start("legal_analysis", state)
        
        print("\n📋 NODE DETAILS - LEGAL ANALYSIS:")
        print("   Purpose: Conduct deep legal analysis using facts")
        print("            Search statutes for applicable laws")
        print("            Find precedent cases")
        print("            Generate legal arguments")
        print("\n   What's Happening:")
        print("   1. Using approved facts from Phase 1")
        print(f"   2. Facts available: {len(state.get('facts', []))} items")
        print("   3. Searching Constitution for applicable articles...")
        print("   4. Searching IPC for relevant sections...")
        print("   5. Searching CrPC for relevant sections...")
        print("   6. Searching FAISS for precedent cases...")
        print("   7. Calling LLM for legal analysis generation...")
        
        result = legal_analysis_node(
            state,
            dependencies["chroma_stores"],
            dependencies["embedding_model"],
            dependencies["faiss_store"],
            dependencies["llm"]
        )
        
        # Log LLM calls that happened during analysis
        print("\n   📊 LLM Activity During Legal Analysis:")
        print(f"      - LLM was queried to analyze facts and generate legal reasoning")
        print(f"      - Query focused on: question, facts, retrieved statutes, precedents")
        print(f"      - Response: Legal analysis with citations")
        logger.llm_logger.log_llm_call(
            node_name="legal_analysis",
            query=f"Analyze this legal question with facts: {state.get('question', '')[:100]}...",
            response=result.get('analysis', '')[:200] if result.get('analysis') else "",
            model="llama-3.3-70b-versatile"
        )
        
        logger.log_node_end("legal_analysis", result,
            reasoning="Completed legal analysis with statutes and precedents. Ready for review.")
        logger.log_phase_complete("Legal Analysis", 2, "Approval Gate")
        
        return result
    
    graph.add_node("legal_analysis", legal_analysis_instrumented)
    
    # ==================== GATE 2: APPROVE ANALYSIS ====================
    
    def approve_analysis_instrumented(state: LawyerState) -> LawyerState:
        """
        GATE 2: HUMAN APPROVAL OF LEGAL ANALYSIS
        
        Purpose:
            Allow human to review legal reasoning and supporting authorities
            
        Input:
            - analysis: From legal_analysis node
            - statutes: Retrieved statutes
            - precedents: Retrieved cases
            
        Output:
            - approved_phase: Set to "analysis" if approved
            
        Next Step:
            If approved → Prediction
            If rejected → Would go back to legal analysis (not implemented)
        """
        logger.log_node_start("approve_analysis", state)
        
        print("\n🔑 NODE DETAILS - APPROVAL GATE #2:")
        print("   Purpose: Human reviews legal analysis and authorities")
        print("   Type: Human-in-the-loop approval gate")
        print("\n   Review Items:")
        print(f"   • Legal Analysis: {len(state.get('analysis', ''))} characters")
        print(f"   • Statutes: {len(state.get('statutes', []))} items")
        print(f"   • Precedents: {len(state.get('precedents', []))} items")
        print("\n   Decision Point:")
        print("   ✓ APPROVE → Continue to Prediction")
        print("   ✗ REVISE → Return to Legal Analysis (TODO)")
        print("   ⊘ STOP → Halt workflow")
        
        result = human_approval_node(state, "analysis")
        
        logger.log_node_end("approve_analysis", result,
            reasoning="Human reviewed legal analysis. Proceeding to prediction.")
        logger.log_phase_complete("Approval Gate #2", 2, "Prediction")
        
        return result
    
    graph.add_node("approve_analysis", approve_analysis_instrumented)
    
    # ==================== PHASE 3: PREDICTION ====================
    
    def prediction_instrumented(state: LawyerState) -> LawyerState:
        """
        PHASE 3: PREDICTION
        
        Purpose:
            Predict the outcome of the case based on analysis and precedents
            Find similar cases for comparison
            Generate confidence score
            
        Input Expected:
            - analysis: Approved legal analysis from Phase 2
            - precedents: Retrieved case law
            
        Output Expected:
            - prediction: Predicted case outcome
            - similar_cases: Cases used for prediction
            - prediction_confidence: Confidence score (0-1)
            
        Why This Phase:
            Based on established legal framework, what is the likely outcome?
            How do similar past cases inform our prediction?
            
        Next Step:
            Moves to approval gate where human reviews prediction
        """
        logger.log_node_start("prediction", state)
        
        print("\n📋 NODE DETAILS - PREDICTION:")
        print("   Purpose: Predict case outcome based on analysis")
        print("            Find and analyze similar past cases")
        print("            Calculate confidence score")
        print("\n   What's Happening:")
        print("   1. Using approved legal analysis from Phase 2")
        print(f"   2. Available precedents: {len(state.get('precedents', []))} cases")
        print("   3. Identifying similar cases from precedent database...")
        print("   4. Comparing fact patterns with similar cases...")
        print("   5. Analyzing outcomes of similar cases...")
        print("   6. Calling LLM to generate outcome prediction...")
        print("   7. Calculating confidence score...")
        
        result = prediction_node(
            state,
            dependencies["faiss_store"],
            dependencies["llm"]
        )
        
        # Log LLM calls during prediction
        print("\n   📊 LLM Activity During Prediction:")
        print(f"      - LLM was queried to predict case outcome")
        print(f"      - Query focused on: facts, analysis, similar cases")
        print(f"      - Response: Outcome prediction with reasoning")
        logger.llm_logger.log_llm_call(
            node_name="prediction",
            query=f"Based on this analysis and similar cases, predict the outcome: {state.get('analysis', '')[:100]}...",
            response=result.get('prediction', '')[:200] if result.get('prediction') else "",
            model="llama-3.3-70b-versatile"
        )
        
        logger.log_node_end("prediction", result,
            reasoning="Generated outcome prediction with confidence score. Ready for review.")
        logger.log_phase_complete("Prediction", 3, "Approval Gate")
        
        return result
    
    graph.add_node("prediction", prediction_instrumented)
    
    # ==================== GATE 3: APPROVE PREDICTION ====================
    
    def approve_prediction_instrumented(state: LawyerState) -> LawyerState:
        """
        GATE 3: HUMAN APPROVAL OF PREDICTION
        
        Purpose:
            Allow human to review predicted outcome and confidence
            
        Input:
            - prediction: From prediction node
            - prediction_confidence: Confidence score
            - similar_cases: Cases used for prediction
            
        Output:
            - approved_phase: Set to "prediction" if approved
            
        Next Step:
            If approved → Drafting
            If rejected → Would go back to prediction (not implemented)
        """
        logger.log_node_start("approve_prediction", state)
        
        print("\n🔑 NODE DETAILS - APPROVAL GATE #3:")
        print("   Purpose: Human reviews predicted outcome")
        print("   Type: Human-in-the-loop approval gate")
        print("\n   Review Items:")
        print(f"   • Prediction: {state.get('prediction', '')[:100]}...")
        print(f"   • Confidence: {state.get('prediction_confidence', 0):.2%}")
        print(f"   • Similar Cases: {len(state.get('similar_cases', []))} items")
        print("\n   Decision Point:")
        print("   ✓ APPROVE → Continue to Drafting")
        print("   ✗ REVISE → Return to Prediction (TODO)")
        print("   ⊘ STOP → Halt workflow")
        
        result = human_approval_node(state, "prediction")
        
        logger.log_node_end("approve_prediction", result,
            reasoning="Human reviewed prediction. Proceeding to drafting.")
        logger.log_phase_complete("Approval Gate #3", 3, "Drafting")
        
        return result
    
    graph.add_node("approve_prediction", approve_prediction_instrumented)
    
    # ==================== PHASE 4: DRAFTING ====================
    
    def drafting_instrumented(state: LawyerState) -> LawyerState:
        """
        PHASE 4: DRAFTING
        
        Purpose:
            Generate final legal document based on all previous phases
            Use templates and cited cases
            Format professional legal output
            
        Input Expected:
            - facts: From Phase 1
            - analysis: From Phase 2
            - prediction: From Phase 3
            - precedents: From Phase 2
            
        Output Expected:
            - draft: Final legal document
            - templates: Templates used
            - citations: Formal citations
            
        Why This Phase:
            Convert analysis and prediction into formal legal document
            Use proper legal citation format
            Ensure professional presentation
            
        Next Step:
            Moves to final approval gate
        """
        logger.log_node_start("drafting", state)
        
        print("\n📋 NODE DETAILS - DRAFTING:")
        print("   Purpose: Generate final legal document")
        print("            Apply document templates")
        print("            Format citations")
        print("\n   What's Happening:")
        print("   1. Using all approved outputs from previous phases")
        print(f"   2. Facts available: {len(state.get('facts', []))} items")
        print(f"   3. Analysis ready: {len(state.get('analysis', ''))} chars")
        print(f"   4. Prediction ready: {state.get('prediction', '')[:50]}...")
        print("   5. Searching for applicable document templates...")
        print("   6. Calling LLM to assemble legal document...")
        print("   7. Formatting citations and references...")
        print("   8. Generating final draft...")
        
        result = drafting_node(
            state,
            dependencies["chroma_drafts"],
            dependencies["embedding_model"],
            dependencies["faiss_store"],
            dependencies["llm"]
        )
        
        # Log LLM calls during drafting
        print("\n   📊 LLM Activity During Drafting:")
        print(f"      - LLM was queried to generate legal document")
        print(f"      - Query focused on: facts, analysis, prediction, templates")
        print(f"      - Response: Formatted legal document with proper structure")
        logger.llm_logger.log_llm_call(
            node_name="drafting",
            query=f"Draft a legal document based on: Facts ({len(state.get('facts', []))} items), Analysis ({len(state.get('analysis', ''))} chars), Prediction",
            response=result.get('draft', '')[:200] if result.get('draft') else "",
            model="llama-3.3-70b-versatile"
        )
        
        logger.log_node_end("drafting", result,
            reasoning="Generated final legal document. Ready for final review.")
        logger.log_phase_complete("Drafting", 4, "Final Approval Gate")
        
        return result
    
    graph.add_node("drafting", drafting_instrumented)
    
    # ==================== GATE 4: APPROVE DRAFT ====================
    
    def approve_draft_instrumented(state: LawyerState) -> LawyerState:
        """
        GATE 4: FINAL APPROVAL OF DRAFT
        
        Purpose:
            Final human review of the complete legal document
            Ensure all phases are properly integrated
            Sign-off before delivery
            
        Input:
            - draft: From drafting node
            - All previous state from all phases
            
        Output:
            - approved_phase: Set to "draft" if approved
            
        Next Step:
            If approved → Workflow completes (END)
            If rejected → Would go back to drafting (not implemented)
        """
        logger.log_node_start("approve_draft", state)
        
        print("\n🔑 NODE DETAILS - APPROVAL GATE #4 (FINAL):")
        print("   Purpose: Final review and sign-off of complete document")
        print("   Type: Final human approval gate")
        print("\n   Complete Workflow State:")
        print(f"   • Phase 1 (Facts): {len(state.get('facts', []))} items ✅")
        print(f"   • Phase 2 (Analysis): {len(state.get('analysis', ''))} chars ✅")
        print(f"   • Phase 3 (Prediction): Set ✅")
        print(f"   • Phase 4 (Draft): {len(state.get('draft', ''))} chars")
        print(f"   • Total Citations: {len(state.get('citations', []))} items")
        print("\n   Decision Point:")
        print("   ✓ APPROVE → Workflow completes, document delivered")
        print("   ✗ REVISE → Return to Drafting (TODO)")
        print("   ⊘ STOP → Halt workflow")
        
        result = human_approval_node(state, "draft")
        
        logger.log_node_end("approve_draft", result,
            reasoning="Final approval complete. Workflow finished.")
        logger.log_phase_complete("Final Approval", 4, "WORKFLOW COMPLETE")
        
        return result
    
    graph.add_node("approve_draft", approve_draft_instrumented)
    
    # ==================== EDGES (Graph Flow) ====================
    
    print("\n" + "=" * 80)
    print("🔗 GRAPH STRUCTURE - Edge Definitions")
    print("=" * 80)
    
    print("\nPhase 1 → Gate 1 → Phase 2 → Gate 2 → Phase 3 → Gate 3 → Phase 4 → Gate 4 → END")
    
    graph.add_edge(START, "fact_gathering")
    print("  Edge: START → fact_gathering")
    
    graph.add_edge("fact_gathering", "approve_facts")
    print("  Edge: fact_gathering → approve_facts")
    
    graph.add_edge("approve_facts", "legal_analysis")
    print("  Edge: approve_facts → legal_analysis")
    
    graph.add_edge("legal_analysis", "approve_analysis")
    print("  Edge: legal_analysis → approve_analysis")
    
    graph.add_edge("approve_analysis", "prediction")
    print("  Edge: approve_analysis → prediction")
    
    graph.add_edge("prediction", "approve_prediction")
    print("  Edge: prediction → approve_prediction")
    
    graph.add_edge("approve_prediction", "drafting")
    print("  Edge: approve_prediction → drafting")
    
    graph.add_edge("drafting", "approve_draft")
    print("  Edge: drafting → approve_draft")
    
    graph.add_edge("approve_draft", END)
    print("  Edge: approve_draft → END")
    
    return graph.compile()


# ==================== SETUP & RUN ====================

def setup_dependencies():
    """
    Initialize all dependencies with detailed logging.
    
    Returns:
        Dict with: llm, chroma_stores, chroma_drafts, faiss_store, embedding_model
    """
    
    print("\n" + "=" * 80)
    print("⚙️  INITIALIZING DEPENDENCIES")
    print("=" * 80)
    
    # Embedding model
    print("\n📌 Loading Embedding Model...")
    embedding_model = EmbeddingManager()
    print("   ✅ Embeddings loaded (BAAI/bge-base-en-v1.5)")
    
    # LLM
    print("\n📌 Loading LLM...")
    llm_manager = LLMManager(provider="groq", model_name="llama-3.3-70b-versatile")
    llm = llm_manager
    print("   ✅ LLM loaded (Groq llama-3.3-70b-versatile)")
    
    # Chroma stores (statutes)
    print("\n📌 Loading Vector Stores...")
    chroma_stores = {}
    
    # Constitution
    const_store = Chroma(
        collection_name="constitution",
        persist_directory="vector_db/chroma/constitution",
        embedding_function=embedding_model
    )
    chroma_stores["constitution"] = const_store
    print("   ✅ Constitution store loaded")
    
    # IPC
    ipc_store = Chroma(
        collection_name="ipc",
        persist_directory="vector_db/chroma/ipc",
        embedding_function=embedding_model
    )
    chroma_stores["ipc"] = ipc_store
    print("   ✅ IPC store loaded")
    
    # CrPC
    crpc_store = Chroma(
        collection_name="crpc",
        persist_directory="vector_db/chroma/crpc",
        embedding_function=embedding_model
    )
    chroma_stores["crpc"] = crpc_store
    print("   ✅ CrPC store loaded")
    
    # Chroma drafts
    drafts_store = Chroma(
        collection_name="legal_drafts",
        persist_directory="vector_db/chroma/legal_drafts",
        embedding_function=embedding_model
    )
    print("   ✅ Legal drafts store loaded")
    
    # FAISS store (precedents)
    print("\n📌 Loading FAISS Precedent Store...")
    faiss_store = FAISSVectorStore(embedding_model=embedding_model)
    print("   ✅ FAISS precedent store loaded")
    
    print("\n✅ All dependencies initialized!\n")
    
    return {
        "llm": llm,
        "chroma_stores": chroma_stores,
        "chroma_drafts": drafts_store,
        "faiss_store": faiss_store,
        "embedding_model": embedding_model
    }


def run_lawyer_agent_debug(question: str, dependencies: dict):
    """
    Run the Lawyer Agent workflow with detailed debug logging.
    
    Args:
        question: Legal question to process
        dependencies: Initialized dependencies
    """
    
    logger = NodeExecutionLogger()
    
    print("\n" + "=" * 80)
    print(f"❓ LEGAL QUESTION")
    print("=" * 80)
    print(f"{question}\n")
    
    # Build instrumented graph
    print("Building workflow graph with instrumentation...")
    graph = build_instrumented_graph(dependencies, logger)
    print("✅ Graph built successfully!\n")
    
    # Initial state
    print("=" * 80)
    print("🚀 INITIALIZING WORKFLOW STATE")
    print("=" * 80)
    
    initial_state = LawyerState(
        question=question,
        facts=[],
        facts_raw=[],
        analysis="",
        statutes=[],
        precedents=[],
        prediction="",
        similar_cases=[],
        prediction_confidence=0.0,
        draft="",
        templates=[],
        citations=[],
        approved_phase="",
        user_feedback="",
        reasoning_trace=[]
    )
    
    print("✅ Initial state created")
    print(f"   Question: {question}")
    print(f"   All fields initialized (empty)\n")
    
    try:
        # Run workflow
        print("=" * 80)
        print("▶️  STARTING WORKFLOW EXECUTION")
        print("=" * 80)
        
        final_state = graph.invoke(initial_state)
        
        # Print execution summary
        logger.print_execution_summary()
        
        # Display results
        print("\n" + "=" * 80)
        print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        print("\n📄 FINAL OUTPUT SUMMARY:")
        print(f"   Question: {final_state.get('question', '')}")
        print(f"   Facts Generated: {len(final_state.get('facts', []))} items")
        print(f"   Analysis Length: {len(final_state.get('analysis', ''))} characters")
        print(f"   Statutes Referenced: {len(final_state.get('statutes', []))} items")
        print(f"   Precedents Used: {len(final_state.get('precedents', []))} items")
        print(f"   Prediction: {final_state.get('prediction', '')[:100]}...")
        print(f"   Confidence: {final_state.get('prediction_confidence', 0):.2%}")
        print(f"   Draft Length: {len(final_state.get('draft', ''))} characters")
        print(f"   Citations: {len(final_state.get('citations', []))} items")
        
        print("\n🎯 REASONING TRACE:")
        for i, entry in enumerate(final_state.get("reasoning_trace", []), 1):
            print(f"   {i}. {entry}")
        
        if final_state.get("draft"):
            print("\n📋 DRAFT PREVIEW (First 500 chars):")
            print("-" * 80)
            print(final_state.get("draft", "")[:500])
            print("-" * 80)
        
    except KeyboardInterrupt as e:
        print(f"\n⛔ Workflow interrupted: {str(e)}")
    except Exception as e:
        print(f"\n❌ Error during workflow execution: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    
    # Setup dependencies
    dependencies = setup_dependencies()
    
    # Test questions
    test_questions = [
        "Is right to privacy a fundamental right in India?",
        "What are the limits on freedom of speech?",
        "Can death penalty be imposed in murder cases?",
    ]
    
    print("\n" + "=" * 80)
    print("🧑‍⚖️  LAWYER AGENT - DEBUG/INSTRUMENTATION RUNNER")
    print("=" * 80)
    print("\nThis runner provides detailed logging of:")
    print("  ✓ Which node is executing")
    print("  ✓ What the node is doing (input state)")
    print("  ✓ What changes after execution (output state)")
    print("  ✓ Why each step happens (reasoning)")
    print("  ✓ Complete graph flow verification")
    
    # Run first question
    run_lawyer_agent_debug(test_questions[0], dependencies)
    
    # Uncomment to run additional questions:
    # for question in test_questions[1:]:
    #     print("\n\n")
    #     run_lawyer_agent_debug(question, dependencies)
