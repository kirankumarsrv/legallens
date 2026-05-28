#!/usr/bin/env python3
"""
Generate workflow graph images for the four RAG/workflow modules.

Creates DOT files and renders PNG and SVG using the `dot` command from Graphviz.

Run: python3 scripts/generate_workflow_graphs.py
"""
import os
import subprocess

OUT_DIR = "docs/workflow_graphs"
os.makedirs(OUT_DIR, exist_ok=True)

WORKFLOWS = {
    "adaptive_rag": {
        "nodes": ["adaptive", "metadata", "faiss", "grade", "answer"],
        "edges": [
            ("adaptive", "answer"),
            ("adaptive", "metadata"),
            ("metadata", "answer"),
            ("metadata", "faiss"),
            ("faiss", "grade"),
            ("grade", "answer"),
        ],
    },
    "basic_rag": {
        "nodes": ["retrieve", "generate"],
        "edges": [("retrieve", "generate")],
    },
    "tool_rag": {
        "nodes": ["yearwise_faiss", "answer"],
        "edges": [("yearwise_faiss", "answer")],
    },
    "corrective_rag": {
        "nodes": ["retrieve", "grade", "answer"],
        "edges": [("retrieve", "grade"), ("grade", "answer")],
    },
    "lawyer_agent_workflow_1_fact_retrieval": {
        "nodes": [
            "evidence_ingest",
            "entity_extraction",
            "entity_normalization",
            "fact_gathering",
        ],
        "edges": [
            ("evidence_ingest", "entity_extraction"),
            ("entity_extraction", "entity_normalization"),
            ("entity_normalization", "fact_gathering"),
        ],
    },
    "lawyer_agent_workflow_2_argument_generation": {
        "nodes": ["legal_analysis"],
        "edges": [],
    },
    "lawyer_agent_workflow_3_prediction": {
        "nodes": ["prediction"],
        "edges": [],
    },
    "lawyer_agent_workflow_4_draft_generation": {
        "nodes": ["draft_generation"],
        "edges": [],
    },
}


def write_dot(name, data):
    dot_path = os.path.join(OUT_DIR, f"{name}.dot")
    with open(dot_path, "w") as f:
        f.write("digraph G {\n")
        f.write("  rankdir=LR;\n")
        f.write("  node [shape=box, style=rounded, fontsize=12];\n")

        # optional entry/exit markers
        f.write('  entry [label="ENTRY", shape=circle, style=filled, fillcolor=lightgrey];\n')
        f.write('  exit [label="FINISH", shape=doublecircle, style=filled, fillcolor=lightgrey];\n')

        for n in data["nodes"]:
            f.write(f'  "{n}";\n')

        # heuristics for entry: certain names
        first = data["nodes"][0]
        f.write(f'  entry -> "{first}";\n')

        for a, b in data["edges"]:
            f.write(f'  "{a}" -> "{b}";\n')

        # connect last node to exit
        last = data["nodes"][-1]
        f.write(f'  "{last}" -> exit;\n')

        f.write("}\n")
    return dot_path


def render(dot_path, name):
    png = os.path.join(OUT_DIR, f"{name}.png")
    svg = os.path.join(OUT_DIR, f"{name}.svg")
    try:
        subprocess.run(["dot", "-Tpng", dot_path, "-o", png], check=True)
        subprocess.run(["dot", "-Tsvg", dot_path, "-o", svg], check=True)
        print(f"Rendered: {png}, {svg}")
    except FileNotFoundError:
        print("Graphviz 'dot' command not found. Please install graphviz (apt install graphviz) and retry.")
    except subprocess.CalledProcessError as e:
        print("Graphviz rendering failed:", e)


def main():
    created = []
    for name, data in WORKFLOWS.items():
        dot = write_dot(name, data)
        render(dot, name)
        created.append(os.path.join(OUT_DIR, f"{name}.png"))

    print("All done. Images are in:", OUT_DIR)


if __name__ == "__main__":
    main()
