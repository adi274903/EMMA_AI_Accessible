# EMMA AI — Accessible

An audio-first, retrieval-grounded consultation assistant for emergency-medicine residents.
EMMA was built as a capstone for **Carnegie Mellon University with Allegheny Health Network
(August – December 2025)**.

A resident asks a clinical question from their last shift; the app retrieves relevant passages
from a textbook corpus (pgvector), reranks them with a medical cross-encoder, and streams a cited
answer from Gemini. Any answer can then be turned into audio — verbatim or rewritten for
listening — so the resident can review it while walking, driving or away from a screen.

> **Not a medical device.** Research prototype. It can be wrong and must not be used for
> diagnosis, treatment decisions or any clinical purpose.

## Why "accessible"

The capstone goal was access, not novelty: residents do not read long answers between patients.
Audio-first answers plus explicit accessibility controls are the point of this build.

| feature | what it does | status |
|---|---|---|
| **Audio-first answers** | Any response can be spoken through Gemini TTS; long answers can be rewritten into a listenable script first | implemented, needs `GOOGLE_API_KEY` |
| **Text transcript with every player** | Each audio player is captioned with the text that will be spoken, so audio is a convenience rather than the only channel | implemented |
| **Verbatim vs. rewritten** | Choose the exact answer, or a script rewritten for listening — both are labelled in the UI | implemented |
| **Text size** | Default / Large / Extra large, applied to the whole interface | implemented |
| **High contrast** | Forced high-contrast palette, in addition to the OS-level `prefers-contrast` media query | implemented |
| **Reduced motion** | Stops animations and smooth scrolling, in addition to `prefers-reduced-motion` | implemented |
| **Visible focus + target size** | 3 px focus ring on every focusable control, 44 px minimum hit targets | implemented |
| **No surprise sound** | Autoplay is off by default and is an explicit opt-in (WCAG 1.4.2) | implemented |
| **Screen-reader semantics** | Decorative emoji are `aria-hidden`; no control is icon-only | implemented |

**Honest status:** these features are implemented and statically verified (unit tests, compile
checks, HTML/CSS assertions). The interface has **not** been audited against WCAG 2.1/2.2 by a
person or with assistive technology, and no screen-reader session has been run. Treat this as a
first pass, not a conformance claim.

## How it works

```
question ──► contextualise (embedding similarity to the previous turn)
         ──► pgvector retrieval over textbook chunks (top-k, default 20)
         ──► MedCPT cross-encoder rerank (CPU)
         ──► Gemini chat, streamed, with textbook + page citations
         ──► optional: Gemini TTS (verbatim or rewritten script) + transcript caption
```

Modules:

| file | role |
|---|---|
| `app_refactored.py` | Streamlit entry point: layout, accessibility panel, audio controls |
| `backend.py` | `MedicalAIBackend`: retrieval, reranking, generation, TTS, timing metrics |
| `accessibility.py` | preferences, accessibility CSS, button labels, transcript captions (pure, unit-tested) |
| `ui_components.py` | CSS and HTML templates for the screens and messages |
| `config.py` | dataclass configuration; nothing machine-specific is hardcoded |
| `session_state.py` | session-state wrapper (messages, backend handle, processing flag) |
| `run_app_vm.py` | local (non-Colab) launcher: loads `.env`, checks configuration, starts Streamlit |
| `example_usage.py`, `test_pipeline_timing.py` | backend usage example and a retrieval/generation timing harness |
| `tests/` | unit tests for `accessibility.py` and `config.py` |

## Run it

You provide the data and the keys. Nothing in this repository is a credential, a corpus or a
vector store.

```bash
pip install -r requirements.txt

export GOOGLE_API_KEY=...            # Gemini chat + TTS  (GEMINI_API_KEY also accepted by run_app_vm.py)
export PG_CONN_STR="host=127.0.0.1 port=5432 dbname=ragdb user=postgres password=..."   # Postgres + pgvector
export MEDICAL_VECTORSTORE_PATH=./medical_vectorstore   # optional, this is the default

streamlit run app_refactored.py      # or: python run_app_vm.py
```

The vector store is a Chroma directory containing a collection named
`harwood_nuss_medical_knowledge`; `MEDICAL_VECTORSTORE_PATH` points at it. The pgvector table
supplies precise page numbers for citations.

Open the sidebar and expand **Accessibility** for text size, contrast, motion and autoplay.

## Configuration

| environment variable | required | purpose |
|---|---|---|
| `GOOGLE_API_KEY` | yes | Gemini chat, TTS and summarisation |
| `PG_CONN_STR` | yes | Postgres + pgvector connection string (citations) |
| `MEDICAL_VECTORSTORE_PATH` | no | Chroma directory, default `./medical_vectorstore` |
| `STREAMLIT_PORT` | no | port used by `run_app_vm.py`, default `8501` |

Models (see `config.py`): `gemini-2.5-flash-lite` for chat,
`gemini-2.5-flash-preview-tts` for speech, `abhinand/MedEmbed-large-v0.1` for embeddings,
`ncbi/MedCPT-Cross-Encoder` for reranking.

## What is deliberately not here

This repository is **code only**:

* the textbook corpus and the built vector store;
* the physician survey responses and the model-response dumps from the pilot;
* any API key, connection string or infrastructure credential;
* the Colab/ngrok notebook used to demo the prototype during the capstone.

The capstone measured a **25% improvement in physician-rated answer accuracy and completeness**
after retrieval over a 20-context corpus was rebuilt on GCP, in two physician surveys. That number
belongs to the capstone report, not to this repository: nothing here re-measures it.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

The tests cover pure logic only (preferences, generated CSS, labels, transcript captions,
configuration defaults and environment overrides). They do not touch Gemini, Postgres or the
vector store, and they cannot: the backend needs a GPU-class embedding model and live credentials.

## Credits and licence context

Capstone project, Carnegie Mellon University with Allegheny Health Network, Fall 2025.
Third-party models keep their own licences (Google Gemini API terms; MedEmbed and MedCPT as
published on Hugging Face). No corpus text is redistributed here.
