# NEXUS Study AI

**Local-first document study companion for Windows.** Ask questions about your notes, generate source-grounded summaries, practice multiple-choice quizzes, and review flashcards. Powered by your own Ollama installation — **no paid AI API needed**.

**Version:** `0.1.0` (MVP)  
**Interface:** English  
**Status:** beta; test on non-sensitive study notes before public distribution.

## Features

| Feature | Details |
| --- | --- |
| 📄 File import | PDF (selectable text), DOCX, TXT, Markdown |
| 💬 Ask AI | Local keyword retrieval with labeled source excerpts |
| 📝 Summary | Processes the *entire indexed document* in sections; hierarchical synthesis |
| ✅ Quiz | Five AI-generated multiple-choice questions, scoring and explanations |
| 🗂 Flashcards | Reveal answer, previous/next navigation, optional text export |
| 🧠 Model selection | Detect installed Ollama models and select one |
| 💾 Exports | Save the current study tab as a UTF-8 `.txt` file |
| 🔒 Local-first | Ollama requests go only to `127.0.0.1:11434`; no cloud API |
| ↩ Cancel | Cancel a pending generation (streaming cancellation may wait for a chunk) |

**Source-label note:** source excerpts are tagged with file name, PDF page number when available, and part number. These labels help you check the original material; they do **not** guarantee that generated claims are correct. Only the passages retrieved for a question are sent to the model. No embeddings, database, registration, tracking or paid account.

## Requirements

- Windows 10/11, 64-bit recommended
- Python **3.12** installed (for development/from-source use)
- Ollama installed and running locally at `http://127.0.0.1:11434`
- An installed text model such as `qwen2.5:3b` (quickest to start) or `qwen3:8b` (heavier)
- Internet connection **only** for initial Python dependencies and/or Ollama model downloads. After that, the app can run offline.

### Installation

1. Extract the ZIP to a folder such as `Downloads\NEXUS_Study_AI_v0.1.0`.
2. Open **Command Prompt**, type `ollama list`, and verify that `qwen2.5:3b` is installed. If it is missing, run `ollama pull qwen2.5:3b` while online.
3. Start Ollama if it is not running (most Windows Ollama installs run it automatically).
4. Double-click **`run.bat`**. This creates a project-local `.venv` (if missing), installs `pypdf` and `python-docx`, and opens the UI.
5. Click **Refresh Installed Models** and choose `qwen2.5:3b`.
6. Click **Add Documents**, select one or more notes, and try each tab.

You can also launch from Command Prompt in the project directory:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

### Make practice files

In Command Prompt opened in the project folder:

```bat
py -3.12 make_demo.py
```

This creates `_DEMO_NOTES` with three harmless, original sample files. Import `physics_notes.txt` and ask **What is acceleration?**

### Run automated tests

Double-click **`test.bat`** or run:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Build standalone Windows executable

Once the app works from `run.bat`, double-click **`build.bat`**. It runs tests, installs PyInstaller into `.venv` if needed, then packages the app. Your output will be:

`dist\NEXUS_Study_AI.exe`

The executable bundles Python libraries, **not** Ollama or a model. Each end user still needs Ollama and an installed model. Because the binary is unsigned, Windows SmartScreen/antivirus may warn; do not bypass protections blindly. Build and test on Windows, and eventually code-sign the application for distribution.

## Project layout

```text
NEXUS_Study_AI_v0.1.0/
├── app.py                     # GUI entry point
├── nexus_study/
│   ├── __init__.py
│   ├── ui.py                  # English GUI and quiz/flashcard controls
│   ├── documents.py           # PDF, DOCX, TXT, Markdown loaders
│   ├── retrieval.py           # Deterministic local keyword retrieval
│   ├── ollama_client.py       # Local Ollama API client, streamed /api/chat
│   └── study.py               # Grounded generation + validation
├── tests/
│   ├── test_documents.py
│   ├── test_retrieval.py
│   ├── test_client.py
│   └── test_study.py
├── make_demo.py
├── run.bat
├── test.bat
├── build.bat
├── requirements.txt
├── START_HERE_RO.md
├── LICENSE
└── .gitignore
```

## Design and safety

- Files are only **read** on import. Removing or clearing from the app does not delete the original files.
- Documents are kept in memory; the app does not automatically save user content or conversations. Text is written only when you explicitly use **Export Current Tab**.
- Ollama server address is deliberately pinned to `127.0.0.1:11434`.
- Imported text is treated as **data**, not executable instructions. However, models can make mistakes; verify important claims in the original documents.
- PDF page labels reflect actual PDF page positions, not necessarily printed page numbers. DOCX does not provide stable page numbers through python-docx.
- PDF files made of scanned images cannot be read until OCR is performed externally. Handwriting and images in Word documents are not analyzed in v0.1.
- Non-PDF text may be read in Windows-1252 if it is not UTF-8 or UTF-16.
- Max file size: 25 MB. Max PDF pages: 400. Max extracted characters: 450,000. Large documents can take many local model calls and minutes or longer depending on the hardware.
- For quiz/flashcards, the app selects representative document sections; they do not necessarily cover *every* fact in a long document. Summary covers all extracted sections.
- No hidden system control, file writes, shell execution or code execution is exposed to the model.

## Limitations

1. Requires Ollama, an installed model and enough RAM / GPU performance.
2. Small models can produce inaccurate answers, poor summaries or invalid quiz JSON. Try another model, simplify the source or retry.
3. No OCR, image understanding, cloud synchronization, shared accounts or mobile support yet.
4. No complete study-session persistence; exported notes are simple text files.
5. No `.exe` is included in the source ZIP. Build the Windows binary yourself with `build.bat`.

## About licenses and commercial usage

The application's own code is under the **MIT License** (`LICENSE`). `pypdf`, `python-docx` and any Ollama models have their **own** licenses; verify their terms before redistributing packages or commercial products. The ZIP does not distribute the models.

## API references

- [Ollama API](https://docs.ollama.com/api)
- [pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
- [python-docx documentation](https://python-docx.readthedocs.io/en/latest/)

