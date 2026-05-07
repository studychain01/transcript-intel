# Transcript Intelligence

> **Rule-first pipeline** over per-meeting JSON → **`outputs/meetings.parquet`** · **notebook** for charts, **top‑5 sentiment tails**, and optional **Ask the transcript**.

---

## At a glance

| | |
|:---|:---|
| **Ingest** | Walk `dataset/<meeting_id>/`, load JSON, one row per call |
| **Enrich** | Call type · utterance sentiment → proportions · title rules → primary category · topics → tags |
| **Deliver** | Parquet + CSV · analysis notebook · optional LLM Q&A over raw dialogue |

---

## Ingestion pipeline

**Goal:** Turn each meeting folder into a single flat record you can analyze in pandas.

1. **Discover meetings** — `iter_meeting_dirs()` lists folders under `dataset/`.
2. **Load JSON** — `meeting-info`, `summary`, `transcript` (and related files) per folder.
3. **Skeleton row** — Title, schedule, canned summary/topics from `summary.json`, transcript text (built from utterances).
4. **Compute fields** — `call_type` from title patterns · **sentiment** from transcript utterances · **classification** from rules + summary topics (see below).
5. **Write outputs** — `outputs/meetings.parquet` + `meetings.csv` (lists/dicts JSON-stringified for CSV).

```text
dataset/01KQ…/
  ├── meeting-info.json  ──┐
  ├── summary.json        ├──► one meetings.parquet row
  └── transcript.json    ──┘
```

📂 **Modules:** `load.py` → `normalize.py` → `call_type.py` · `sentiment_agg.py` · `classify_rules.py` · `pipeline.py`

---

## Sentiment analysis

**Source of truth:** each line in **`transcript.json`** already carries a **`sentimentType`** per utterance (`positive` / `neutral` / `negative`).

| Step | What happens |
|:---:|:---|
| 1 | Count utterances by `sentimentType`. |
| 2 | **`pct_positive`**, **`pct_neutral`**, **`pct_negative`** = fractions of all utterances on that call. |
| 3 | **`aggregated_label`** = rollup from those fractions (e.g. very negative if ≥60% negative; mostly neutral if ≥70% neutral; mixed / leaning / polarized otherwise). Sparse calls (`n < 5`) get **`low_signal`**. |

Per-speaker breakdowns land in **`speaker_sentiment`** (turn share + per-speaker fractions) for notebook drill‑down.

📊 **Module:** `sentiment_agg.py` (`sentiment_proportions`, `label_from_proportions`, `speaker_sentiment_breakdown`)

---

## Classification (primary + tags)

**Primary category** — short, **deterministic** buckets from **`meeting-info.json` title** (easy to defend in a review):

Support case · Detect outage · Comply · Aegis · Others  

**Topics** — **`summary.json`** `topics` populate **`secondary_categories`**; rules path mirrors the first tags into **`subthemes`** as a short snippet.

📌 **Canonical labels:** `src/transcript_intel/taxonomy.py` · **Rules:** `classify_rules.py`

---

## Notebook: top 5 + chart

Open **`notebooks/02_analysis.ipynb`** and run top-to-bottom. The first code section calls `run_pipeline()` and creates parquet automatically.

| Piece | Idea |
|:---:|:---|
| **Top 5 negative** | Highest **`pct_negative`** — where to drill for friction, incidents, or churn cues. |
| **Top 5 positive** | Highest **`pct_positive`** — balances the story; shows you’re not cherry-picking only bad calls. |
| **Bar chart** | Mean **negative** utterance share by **`primary_category`** — *where* tone clusters across the portfolio. |

Figures export to **`outputs/figures/`** (e.g. sentiment-by-category PNG) when you run the viz cell.

📈 These rankings use **only** pipeline columns — **no** extra composite scores.

---

## Ask the transcript (chatbot)

**Optional** widget in the same notebook:

- Pick a **`meeting_id`**, ask a natural-language question.
- Answers are grounded in **`dataset/<meeting_id>/transcript.json`** (dialogue turns), **not** the canned `summary.json`.
- Requires **`OPENAI_API_KEY`** in the environment; model defaults to **`gpt-4o-mini`** (`OPENAI_MODEL` overrides).

💬 Useful for **ad‑hoc diligence** (“What did they say about the outage?”) with traceability back to the raw chat log.

---

## How to run

**Prerequisite:** Python **3.10+** (`requires-python` in `pyproject.toml`).

### 1️⃣ Install (once)

From the **`interview-assignment/`** directory (this repo folder):

```bash
cd interview-assignment

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .
pip install -r requirements.txt       # includes jupyter, matplotlib, ipywidgets, …
```

**No editable install?** Same folder, then:

```bash
pip install -r requirements.txt
export PYTHONPATH=src
```

### 2️⃣ (Optional) Build `meetings.parquet` from terminal

Still in **`interview-assignment/`** (parent of `src/` and `dataset/`):

```bash
python -m transcript_intel.pipeline
```

**You should see** log lines ending with parquet + CSV paths. **Artifacts:**

| Output | Purpose |
|:---|:---|
| `outputs/meetings.parquet` | Notebook + pandas |
| `outputs/meetings.csv` | Quick Excel / grep |
| `outputs/figures/` | Created empty; notebook writes PNGs here |
| `outputs/llm_logs/` | Only if you use LLM classification |

**Custom paths:**

```bash
export TRANSCRIPT_INTEL_DATASET=/path/to/dataset
export TRANSCRIPT_INTEL_OUTPUT=/path/to/outputs
python -m transcript_intel.pipeline
```

### 3️⃣ Analysis notebook

Paths in the notebook use **`../outputs/`** and **`../dataset/`**, so the Jupyter **process working directory** should be **`interview-assignment/notebooks/`**.

```bash
cd interview-assignment/notebooks
jupyter lab
```

Open **`02_analysis.ipynb`**, then:

1. **Run → Run All Cells** (or top to bottom once).
2. The first code section runs **`run_pipeline()`** and writes parquet/CSV from `../dataset/`.
3. After **`df = pd.read_parquet(...)`** loads, continue through **sentiment**, **Part 3 (top 5 + chart)**, and optional **Ask the transcript**.

If you already built parquet from terminal (step 2), you can skip re-running the notebook pipeline cell.

**Ask the transcript:** set the key **before** starting Jupyter (same terminal session), or your shell profile:

```bash
export OPENAI_API_KEY=sk-...
# optional:
export OPENAI_MODEL=gpt-4o-mini
```

Then run the widget cell; pick a call, type a question, click **Ask transcript**.

**If parquet is “missing”:** you started Jupyter from the wrong folder — use **`cd …/interview-assignment/notebooks`** as above, or run the pipeline again from **`interview-assignment/`**.

---

## Package layout

| Module | Role |
|:---|:---|
| `load.py` | Folder walk + JSON load |
| `normalize.py` | Flatten fields, transcript text |
| `call_type.py` | Title → `call_type` |
| `taxonomy.py` | Allowed primary labels + normalization |
| `classify_rules.py` | Primary + secondary tags (default path) |
| `sentiment_agg.py` | `pct_*`, labels, speaker breakdown |
| `pipeline.py` | Orchestration |

---
