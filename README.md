# Personal Wiki with Local Gemma

This project is an original Python CLI and harness for a small wiki about local AI. It runs Gemma 4 E2B on this Mac, retrieves original documents locally, and separates casual conversation from evidence-based research. No sample application was cloned. Ollama supplies model inference; the connecting application code is in [wiki.py](wiki.py).

**Verified offline:** the final run completed ingestion, all four research questions, casual chat, a shorter-draft follow-up, raw search, chat-history isolation, and duplicate-ingestion checks with Wi-Fi off throughout the sampled interval. Wi-Fi was restored automatically afterward. See the [review and measured results](evidence/evaluations/20260930T064343Z/review.md).

## Start here

- [Human wiki landing page](vault/index.md)
- Obsidian screenshots: [grouped index](evidence/obsidian/index.png), [note title and metadata](evidence/obsidian/note-title.png), [sources and related notes](evidence/obsidian/note-sources.png), [opened original source](evidence/obsidian/source-open.png), and [filtered graph](evidence/obsidian/graph.png).
- [Original source catalog](sources.json)
- [Harness source](wiki.py) and [separate instructions](instructions/)
- [Fixed research questions and expectations](tests/questions.json)
- [Actual preflight evaluation](evidence/online-preflight.txt)
- Verified offline question cards: [question 1](evidence/evaluations/20260930T064343Z/cards/ask-1.md), [question 2](evidence/evaluations/20260930T064343Z/cards/ask-2.md), [question 3](evidence/evaluations/20260930T064343Z/cards/ask-3.md), and [unsupported question](evidence/evaluations/20260930T064343Z/cards/ask-4.md).
- [Chat and follow-up](evidence/evaluations/20260930T064343Z/chat.txt), [chat-history isolation](evidence/evaluations/20260930T064343Z/chat-isolation.txt), [raw search](evidence/evaluations/20260930T064343Z/search.txt), and [answer-quality and timing review](evidence/evaluations/20260930T064343Z/review.md).
- [Offline run status](evidence/offline/status.json), [network evidence](evidence/offline/network.txt), [terminal transcript](evidence/offline/terminal.txt), and [replayable terminal recording](evidence/offline/terminal.cast)
- [Model identity](evidence/model.json) and [device snapshot](evidence/device.json)
- [Implementation tests](tests/test_harness.py) and [test output](evidence/unit-tests.txt)

This is a local project. Publishing a public repository and submitting its URL are separate submission steps; neither has been done automatically.

The user-supplied Obsidian screenshots show the vault open, the Context Window Memory note, its source and related-note links, and the original source opened in `raw/`. The graph uses `path:wiki/` with Attachments off and displays three readable curated note labels with connections. These screenshots document visual navigation; they do not establish completion of the separate offline CLI test.

## Purpose and sources

The only supplied document was the assignment brief. It remains unchanged outside the vault and is not indexed as research evidence. The working wiki uses three public Ollama documentation sources, downloaded on September 29, 2026: the FAQ, context-length guide, and embeddings guide. This choice avoids importing private files without identifying a source collection. The source catalog records original URLs, publishers, checksums, readable note names, and topic relationships.

The documents are preserved byte-for-byte in `vault/raw/`. The Markdown copies retain upstream MDX components and relative links, which may not render fully in Obsidian; generated notes provide a readable overview and link to the complete originals. Upstream documentation can change and can disagree: the FAQ states a 4,096-token default, while the context guide gives VRAM-dependent defaults. The project explicitly fixes its context at 4,096 tokens.

## Device and model choice

Observed device: MacBook Air with Apple M4, 10 CPU cores, 8 GPU cores, macOS 26.3, and 16 GiB unified memory. CPU and GPU share that memory; there is no separate dedicated VRAM pool. Before setup, disk space was approximately 19 GiB. macOS reported 39% in its memory-pressure free indicator, but also about 6.3 GiB in compressed physical pages. That indicator is not a promise of available model memory. The runtime later estimated 3.6 GiB available at initial load. About 12 GiB disk remained after installation.

Selected model: `gemma4:e2b`, GGUF, Q4_K_M, served by Ollama 0.34.4. The installed manifest digest and exact byte size are in [model.json](evidence/model.json). The download is 7,162,405,886 bytes. Use the recorded digest to check whether a future tag download is the same model.

The E in E2B and E4B means effective parameters; extra embedding tables also use memory. The 26B A4B mixture-of-experts model activates approximately 4B parameters per token, but its total stored weights remain much larger. Active parameters are not the memory footprint. Google's approximate Q4_0 loading estimates are 2.9 GB for E2B, 4.5 GB for E4B, and 14.4 GB for 26B A4B. These are not full application requirements or the size of this particular Q4_K_M package. See [Google's model and memory documentation](https://ai.google.dev/gemma/docs/core) and [the Ollama model listing](https://ollama.com/library/gemma4:e2b).

E2B was chosen because this 16 GiB Mac already had substantial memory compression. A short context, one loaded model, and one concurrent request limit additional pressure. Only one model was downloaded and tested. No training, fine-tuning, hardware purchase, or cloud inference is required.

In the verified offline run, ingestion took 43.343 seconds; the three answerable ask commands took 28.329, 21.171, and 21.541 seconds. The unsupported ask took 16.417 seconds. A runtime process sample reported a 3.4 GB physical footprint and a 3.5 GB process-lifetime peak. These are observed measurements, not guaranteed speeds or whole-system memory totals. See the linked review for distinctions between process footprint, CLI RSS, and runtime-reported model allocation.

## Setup

The tested interpreter is Python 3.14. The application itself uses only Python's standard library: argparse, urllib, sqlite3, hashlib, and JSON/file handling. There is no embedding model or hosted search dependency. Obsidian is needed for browsing and screenshots, not for running the CLI.

On this Mac, open a terminal in the project directory:

```sh
cd "/Users/joannetamayo/Documents/ChatGPT/Assignment 4_Wiki Page"
./scripts/serve.sh
```

Leave that terminal open. In a second terminal in the same directory:

**Before offline use:** this project's Documents folder is synced with iCloud. In Finder, right-click **Assignment 4_Wiki Page**, choose **Keep Downloaded**, and wait for all downloads to finish. A filename being visible does not mean its contents are stored locally. This caused real failed offline attempts when instructions, test questions, and the model weights were cloud placeholders. The offline runner now checks for those placeholders before changing Wi-Fi.

```sh
python3 wiki.py help
python3 wiki.py model-info
python3 wiki.py rebuild
python3 wiki.py search "embeddings cosine similarity"
python3 wiki.py ask "How can I disable Ollama cloud features using an environment variable?" --mode local
python3 wiki.py chat
```

The runtime and model already downloaded on this Mac live under `.local/`, which is excluded from version control. For a fresh Apple Silicon Mac installation, download the official pinned runtime while online:

```sh
mkdir -p .local/runtime .local/models
curl -fL https://github.com/ollama/ollama/releases/download/v0.34.4/ollama-darwin.tgz -o .local/ollama-darwin.tgz
tar -xzf .local/ollama-darwin.tgz -C .local/runtime
./scripts/serve.sh
```

In a second terminal:

```sh
OLLAMA_HOST=127.0.0.1:11435 .local/runtime/ollama pull gemma4:e2b
python3 wiki.py model-info
python3 wiki.py ingest vault/raw
```

The script binds only `127.0.0.1:11435` and sets `OLLAMA_NO_CLOUD=1`. On first launch Ollama creates its standard local identity under `~/.ollama`; model files remain in this project. If the port is occupied, stop the existing project server before starting another. The CLI has no online option, automatic model download, remote endpoint setting, or cloud fallback. An unavailable server produces a useful error. Download everything before disconnecting.

## Commands and mode boundaries

| Command | Behavior |
|---|---|
| `python3 wiki.py chat` | Wren helps draft, plan, and brainstorm with recent conversation. Casual chat never retrieves notes. |
| `/notes QUERY` inside chat | Explicitly retrieves original passages for a source-based chat turn. |
| `/reset` or `/exit` inside chat | Clears the session or exits. Chat history is kept in memory, not silently saved as research evidence. |
| `python3 wiki.py ask "QUESTION"` | Independent, neutral RAG answer with citations or insufficient evidence. Loads no chat history or persona. |
| `python3 wiki.py search "QUERY"` | Exact source passages and paths; no generation and no model server required. |
| `python3 wiki.py ingest vault/raw` | Generates notes for catalogued originals, preserves existing reviewed notes, and rebuilds both indexes. |
| `python3 wiki.py ingest "vault/raw/Ollama Embeddings.md" --regenerate` | Explicitly regenerates a note, retaining the prior note in evidence backups. Review the new version. |
| `python3 wiki.py rebuild` | Rebuilds only the original-source retrieval database. |
| `python3 wiki.py audit` | Checks generated filenames/headings and internal link targets. |
| `python3 wiki.py help` | Lists commands. Each command also accepts `--help`. |

To add a source, copy an unchanged UTF-8 `.md` or `.txt` file to `vault/raw/`, then add an entry in `sources.json` with a stable ID, path, descriptive 2–6 word title, topic, description, source URL, checksum, and meaningful related-note explanations. Run ingest on that path. PDF/Word parsing and OCR are not implemented: this project deliberately uses text sources whose extraction can be inspected. Do not put answer keys or assistant instructions in `raw/`.

## How the application connects the parts

The **model** generates text from supplied messages. It does not independently read the vault, remember conversations, or execute commands.

The **retrieval tool** searches a SQLite-backed passage store built exclusively from the originals. It uses a small BM25 implementation with word tokenization, stop-word removal, and inverse document frequency. This avoids an extra embedding download and works offline. The embeddings note explains an alternative approach; this implementation does not use embeddings.

The **RAG workflow** is question → retrieval → labelled evidence prompt → local Gemma → citation checks → displayed answer. RAG adds context at inference time; it does not train Gemma.

The **harness** is the application code that chooses modes, loads the appropriate instructions, carries chat context, invokes retrieval when requested, builds messages, calls the local runtime, validates citation labels, handles errors, and saves outputs. The **CLI** is the command interface into that harness.

Trace an ask command through `main`, `ask`, `search`, `context`, `generate`, `check_citations`, and `save` in [wiki.py](wiki.py). Search returns up to four original passages, usually up to 1,400 characters each, with source paths and original line ranges. The harness creates a system message from `instructions/research.md`, then a user message containing only the question and retrieved evidence. It calls the local Ollama chat API using a 4,096-token window, temperature 0.2, seed 42, thinking disabled, and a 650-token generation cap. The source labels are resolved to displayed paths. Unknown or missing citation labels cause the displayed answer to be withheld, while the original model output remains saved for inspection.

Label checking is not semantic verification: a valid citation can still support the wrong claim. The question evidence cards therefore include a source-by-source assessment. The model can also refuse on a topical but insufficient passage. When retrieval returns no hits, the harness returns insufficient evidence without a model call.

Chat loads `instructions/persona.md` and keeps at most eight recent messages, further capped at 5,500 characters. Individual user messages are limited to 2,500 characters. `/notes` is an explicit retrieval control rather than a model tool-routing heuristic. Long conversations can lose older context; generated drafts and conversation claims never enter the original-source index.

Ingestion loads `instructions/ingest.md` and sends at most the first 8,000 source characters to Gemma. It saves a structured summary with deterministic titles and source references. The long FAQ was explicitly truncated for summary generation; full-source retrieval was not truncated. Very long source lines can exceed the nominal passage target; the supplied sources were inspected and do not cause a context overflow. A stronger future implementation would tokenize and bound every request by the runtime's exact tokenizer.

## Wiki design and source integrity

Open **`vault/` itself** in Obsidian. It contains `raw/`, `wiki/Local AI/`, `wiki/Retrieval/`, and a grouped `index.md`. Actual filenames are Context Window Memory.md, Local Runtime Settings.md, and Embeddings for Retrieval.md. Their headings match. IDs and source checksums are properties; chunks, database files, model weights, logs, tests, and answers stay outside the vault.

Meaningful note-to-note links explain why the topics connect. Each note links directly to an unchanged original and its online publication. The source catalog maps stable machine IDs to readable paths. Standard re-ingestion skips existing notes and preserves manual review corrections. An explicit regeneration backs up the old note before replacing it. A checksum mismatch refuses to treat altered source bytes as the original.

This implementation was created in an empty project, so there were no old machine-named wiki notes to migrate. If renaming later, preserve a backup, change the catalog mapping, update incoming links and the grouped index, remove no originals, rebuild retrieval, and rerun the questions before claiming cleanup is complete.

## Evaluation and limitations

Expectations are outside the searchable vault in [questions.json](tests/questions.json). Three questions target cloud-disable configuration, context-memory relationships, and embeddings in RAG. The fourth asks for an exact speed on this specific Mac, which the original documentation cannot supply. A separate mode-boundary check places a fictional project code only in chat, then asks about it in research mode; the required response is insufficient evidence.

The preflight run used local inference while the computer remained connected. It is not offline proof. The offline demonstration separately records Wi-Fi power off, absence of a default route, a failed external connection, fresh CLI processes, ingestion through Gemma, all four questions, casual chat, a draft and follow-up, raw search, chat isolation, and duplicate-ingestion checks. The local server can remain running because the requirement is a fresh CLI after disconnection; no cloud access is available to it.

Run implementation checks with `python3 -m unittest discover -s tests`. Run the full real-model evaluation with `python3 scripts/evaluate.py`. On this Mac, `python3 scripts/offline_demo.py` temporarily turns off Wi-Fi en0, records the evaluation in a real terminal session, and restores Wi-Fi in a finally block with a ten-minute watchdog. It is Mac-specific. It refuses to assert offline success unless disconnection and completed test output are present.

Every run retains the exact answers and retrieved passages under `evidence/runs/`; evaluation directories hold transcripts and expectations. Older failed attempts remain separate. Per-call JSON does not independently prove disconnection: the network log and offline run manifest establish that for the full run.

Observed limitation: the initial generated runtime note blurred the distinction between local-data handling and the hosted service's privacy statements. It was corrected against the original, and the original generated output and note backup remain available. An initial chat follow-up also provided too many alternatives; the persona was tightened to request one shorter draft and retested. Keyword retrieval can miss synonyms and can return irrelevant lower-ranked passages. A future improvement is local embeddings with a fixed evaluation comparison, plus stronger claim-by-claim grounding checks.

No result should be treated as passing merely because the process exited successfully. Review the saved answers and citation support separately from retrieval and execution checks.
