"""
Run the lawyer-agent workflow on the sample evidence and export state['contradictions']
to a simple text report at `reports/contradictions_report.txt`.

This script is non-interactive and mirrors the test scenario from `run.py`.
"""
import os
from pathlib import Path

from workflows.lawyer_agent.graph import build_lawyer_agent_graph
from workflows.lawyer_agent.state import LawyerState
from workflows.lawyer_agent.run import setup_dependencies


def main():
    base = Path(__file__).resolve().parents[2]
    reports_dir = base / "reports"
    reports_dir.mkdir(exist_ok=True)

    deps = setup_dependencies()

    graph = build_lawyer_agent_graph(deps)

    evidence_files = [
        "evidence_samples/sample_fir.txt",
        "evidence_samples/sample_charge_sheet.txt",
        "evidence_samples/scanned_sample.pdf",
    ]

    initial_state = LawyerState(
        question="Export contradictions report",
        evidence_files=evidence_files,
        evidence_text="",
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
        reasoning_trace=[],
        timeline=None,
        contradictions=None,
    )

    final_state = graph.invoke(initial_state)

    contradictions = final_state.get("contradictions") or []

    out_path = reports_dir / "contradictions_report.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("Cross-Evidence Contradictions Report\n")
        f.write("=================================\n\n")
        f.write(f"Evidence files: {evidence_files}\n\n")
        if not contradictions:
            f.write("No contradictions detected.\n")
        else:
            for i, c in enumerate(contradictions, 1):
                f.write(f"{i}. {c.get('summary', str(c))}\n")
                details = c.get("details")
                if details:
                    f.write("   Details:\n")
                    for d in details:
                        f.write(f"     - {d}\n")
                f.write("\n")

    print(f"Saved contradictions report to: {out_path}")


if __name__ == "__main__":
    main()
