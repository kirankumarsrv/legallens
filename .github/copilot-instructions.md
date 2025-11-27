## Purpose

This repository is a small tokenization / NLP playground. Primary artifact: `tokrnization_processing.ipynb` (an exploratory notebook demonstrating NLTK tokenization, stopword removal and lemmatization). `app.py` is currently a placeholder for any extracted, reusable code.

## Big picture & workflow

- Primary development happens in the notebook `tokrnization_processing.ipynb`. Treat the notebook as the canonical experiment log: install commands, downloads, and example pipelines live there.
- When converting experiments into production-ready code, extract functions/classes from the notebook into `app.py` or new modules. Keep the notebook as the integration/experiment harness.

## How to run / reproduce locally

1. Open `tokrnization_processing.ipynb` in VS Code (Notebook view) or Jupyter.
2. Run the first cells to install packages and download NLTK data. The notebook uses these commands (run in a Python kernel):

```
pip install nltk spacy pandas
# then in Python cells:
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
```

Notes:
- There is no `requirements.txt` in the repo. Use the notebook install line or create a `requirements.txt` if you stabilize dependencies.

## Project-specific patterns & conventions

- Notebook-first: experiments, data-cleaning and example calls live in `tokrnization_processing.ipynb`.
- Tokenization stack visible in the notebook:
  - NLTK for tokenization and stopwords (see `stopwords` import and `stop_words = set(stopwords.words('english'))`).
  - NLTK `WordNetLemmatizer` for lemmatization (see `lemmatizer = WordNetLemmatizer()`).
- Expect pandas-based data ingestion (the notebook references reading from CSVs/lists). If adding scripts, keep IO via pandas for compatibility.

## Editing and introducing code

- If you add reusable functions, follow this small migration path:
  1. Implement function in a new module (e.g. `nlp_utils.py`) or `app.py`.
  2. Add a short example cell in the notebook that imports and exercises the function.
  3. Keep any heavy data-download or install steps out of library code; put them in a setup script or the notebook.

## Debugging and tests

- There are no existing test suites. Quick checks:
  - Run the notebook cells interactively and verify outputs.
  - For script-level code (in `app.py`), run `python -c "import app; print(dir(app))"` to ensure import and basic symbol exposure.

## Integration points & external dependencies

- External libraries used (discoverable in the notebook): `nltk`, `spacy`, `pandas`.
- NLTK requires runtime downloads (`punkt`, `stopwords`, `wordnet`) — the notebook already triggers these. Keep this in mind when automating runs/CI.

## Guidance for AI agents (concise actionable rules)

1. Primary source of truth for behavior and examples: read `tokrnization_processing.ipynb` before making changes.
2. Preserve notebook install/download cells; when extracting code to modules, do not move downloads into library-level imports.
3. When adding files, include a short example usage cell in the notebook that demonstrates the public API.
4. Prefer pandas-based IO and NLTK primitives (tokenize, stopwords, lemmatize) to remain consistent with existing code.
5. If you modify dependency usage (e.g., switch to spaCy), add a notebook cell showing the alternative and note any large model downloads.

---

If anything here is unclear or you want more detail (examples of functions to extract from the notebook, suggested `requirements.txt`, or a tiny test harness), tell me which part to expand and I will update this file.
