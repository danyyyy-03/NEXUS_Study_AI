"""English-only Tkinter interface for NEXUS Study AI."""
from __future__ import annotations
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Any

from .documents import StudyDocument, DocumentError, load_document
from .retrieval import Chunk, build_index
from .ollama_client import OllamaClient, OllamaError, CancelledError
from . import study

BG = "#0e101a"
SIDE = "#171928"
CARD = "#202236"
INPUT = "#292b43"
FG = "#f0f1f9"
MUTED = "#a6a7bc"
PURPLE = "#9068fb"
PURPLE_ACTIVE = "#ab8aff"
BORDER = "#35374e"
GREEN = "#6ed9ad"
WARN = "#ffbc70"


class StudyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NEXUS Study AI  |  v0.1.0")
        self.geometry("1160x750")
        self.minsize(960, 630)
        self.configure(bg=BG)
        self.client = OllamaClient()
        self.docs: list[StudyDocument] = []
        self.chunks: list[Chunk] = []
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.done_callback: Callable[[Any], None] | None = None
        self.summary_text = ""
        self.chat_log: list[tuple[str, str]] = []
        self.quiz: list[dict] = []
        self.quiz_index = 0
        self.quiz_score = 0
        self.quiz_answered = False
        self.cards: list[dict] = []
        self.card_index = 0
        self.card_revealed = False
        self._styles()
        self._layout()
        self.after(100, self._poll_events)
        self.after(200, self.refresh_models)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=SIDE, foreground=MUTED,
                        padding=(24, 12), font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", CARD)],
                  foreground=[("selected", FG)])
        style.configure("TCombobox", fieldbackground=INPUT, background=INPUT, foreground=FG,
                        arrowcolor=FG, padding=7)
        style.map("TCombobox", fieldbackground=[("readonly", INPUT)],
                  foreground=[("readonly", FG)])
        style.configure("Vertical.TScrollbar", background=CARD, troughcolor=BG)
        self.option_add("*TCombobox*Listbox.background", INPUT)
        self.option_add("*TCombobox*Listbox.foreground", FG)

    def _label(self, parent, text, size=10, color=FG, bold=False, **kw):
        return tk.Label(parent, text=text, font=("Segoe UI", size, "bold" if bold else "normal"),
                        bg=parent.cget("bg"), fg=color, **kw)

    def _button(self, parent, text, command, *, primary=False, width=None):
        btn = tk.Button(parent, text=text, command=command,
                        font=("Segoe UI", 10, "bold"),
                        bg=PURPLE if primary else CARD, fg=FG, activebackground=PURPLE_ACTIVE if primary else INPUT,
                        activeforeground=FG, relief="flat", borderwidth=0, padx=14, pady=10,
                        cursor="hand2", width=width)
        return btn

    def _text(self, parent, height=10, readonly=True):
        frame = tk.Frame(parent, bg=BORDER, highlightbackground=BORDER, highlightthickness=1)
        text = tk.Text(frame, wrap="word", height=height, bg=INPUT, fg=FG,
                       insertbackground=FG, selectbackground="#6854b8", relief="flat",
                       font=("Segoe UI", 10), padx=13, pady=11, borderwidth=0,
                       spacing1=3, spacing3=4)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        if readonly:
            text.config(state="disabled")
        return frame, text

    def _set_text(self, widget: tk.Text, value: str, append=False):
        widget.config(state="normal")
        if not append:
            widget.delete("1.0", "end")
        widget.insert("end", value)
        widget.see("end")
        widget.config(state="disabled")

    def _layout(self):
        header = tk.Frame(self, bg=BG, padx=22, pady=15)
        header.pack(side="top", fill="x")
        self._label(header, "◈  NEXUS", 18, FG, True).pack(side="left")
        self._label(header, "STUDY AI", 18, PURPLE, True).pack(side="left", padx=(5, 0))
        self._label(header, "100% LOCAL  •  PDF / DOCX / TXT / MD", 9, MUTED).pack(side="right")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        workspace = tk.Frame(self, bg=BG)
        workspace.pack(fill="both", expand=True)
        sidebar = tk.Frame(workspace, bg=SIDE, width=300, padx=17, pady=18)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        right = tk.Frame(workspace, bg=BG, padx=20, pady=15)
        right.pack(side="left", fill="both", expand=True)

        self._label(sidebar, "STUDY LIBRARY", 10, FG, True).pack(anchor="w", pady=(0, 10))
        self._label(sidebar, "Select one or more files to import.", 9, MUTED).pack(anchor="w")
        self._button(sidebar, "+  Add Documents", self.add_documents, primary=True).pack(fill="x", pady=(13, 10))
        self.listbox = tk.Listbox(sidebar, bg=INPUT, fg=FG, selectbackground="#684faf",
                                  selectforeground=FG, font=("Segoe UI", 10), highlightthickness=1,
                                  highlightbackground=BORDER, relief="flat", borderwidth=0,
                                  activestyle="none", exportselection=False)
        self.listbox.pack(fill="both", expand=True, pady=(0, 7))
        controls = tk.Frame(sidebar, bg=SIDE)
        controls.pack(fill="x")
        self._button(controls, "Remove Selected", self.remove_selected).pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._button(controls, "Clear", self.clear_docs).pack(side="left")
        self.count_var = tk.StringVar(value="No documents loaded")
        self._label(sidebar, "", 9, MUTED, textvariable=self.count_var).pack(anchor="w", pady=(11, 15))
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", pady=8)
        self._label(sidebar, "LOCAL AI MODEL", 10, FG, True).pack(anchor="w", pady=(8, 9))
        self.model_var = tk.StringVar(value="qwen2.5:3b")
        self.model_combo = ttk.Combobox(sidebar, textvariable=self.model_var, state="normal",
                                         values=["qwen2.5:3b", "qwen3:8b"])
        self.model_combo.pack(fill="x")
        self._button(sidebar, "↻  Refresh Installed Models", self.refresh_models).pack(fill="x", pady=(9, 6))
        self.model_status = tk.StringVar(value="Checking Ollama...")
        tk.Label(sidebar, textvariable=self.model_status, bg=SIDE, fg=MUTED,
                 font=("Segoe UI", 9), justify="left", wraplength=250).pack(anchor="w", pady=(4, 18))
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x")
        self._label(sidebar, "PRIVACY", 9, PURPLE, True).pack(anchor="w", pady=(18, 6))
        tk.Label(sidebar, text="Files are read locally. Their contents are sent only to your local Ollama server (127.0.0.1). No cloud account or API key.",
                 font=("Segoe UI", 9), bg=SIDE, fg=MUTED, justify="left", wraplength=255).pack(anchor="w")

        intro = tk.Frame(right, bg=BG)
        intro.pack(fill="x", pady=(0, 10))
        self._label(intro, "Your personal AI study workspace", 17, FG, True).pack(side="left")
        self._button(intro, "Export Current Tab", self.export_current).pack(side="right")
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)
        self.ask_page = tk.Frame(self.tabs, bg=BG)
        self.summary_page = tk.Frame(self.tabs, bg=BG)
        self.quiz_page = tk.Frame(self.tabs, bg=BG)
        self.flash_page = tk.Frame(self.tabs, bg=BG)
        for frame, name in ((self.ask_page, "Ask AI"), (self.summary_page, "Summary"),
                            (self.quiz_page, "Quiz"), (self.flash_page, "Flashcards")):
            self.tabs.add(frame, text=name)
        self._ask_layout()
        self._summary_layout()
        self._quiz_layout()
        self._flash_layout()

        footer = tk.Frame(self, bg=SIDE, padx=15, pady=8)
        footer.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar(value="Ready. Import a document to begin.")
        tk.Label(footer, textvariable=self.status_var, font=("Segoe UI", 9), fg=FG,
                 bg=SIDE, anchor="w").pack(side="left", fill="x", expand=True)
        self.cancel_btn = self._button(footer, "Cancel Task", self.cancel_task)
        self.cancel_btn.pack(side="right")
        self.cancel_btn.config(state="disabled")

    def _ask_layout(self):
        self._label(self.ask_page, "Ask questions about your documents", 12, FG, True).pack(anchor="w", pady=(12, 5))
        self._label(self.ask_page, "Answers use relevant excerpts and show source labels. Verify important details.", 9, MUTED).pack(anchor="w", pady=(0, 10))
        frame, self.ask_result = self._text(self.ask_page, height=18)
        frame.pack(fill="both", expand=True, pady=(0, 12))
        self._set_text(self.ask_result, "Import PDF, DOCX, TXT or MD study material, then ask a question.\n\nTip: use specific keywords from the document for the most relevant results.")
        bottom = tk.Frame(self.ask_page, bg=BG)
        bottom.pack(fill="x", pady=(0, 12))
        input_frame, self.question = self._text(bottom, height=3, readonly=False)
        input_frame.pack(side="left", fill="both", expand=True, padx=(0, 9))
        self.question.bind("<Control-Return>", self._ask_hotkey)
        self._button(bottom, "Ask AI  →", self.ask_question, primary=True).pack(side="right", fill="y")

    def _summary_layout(self):
        top = tk.Frame(self.summary_page, bg=BG)
        top.pack(fill="x", pady=(14, 12))
        self._label(top, "Source-grounded study notes", 12, FG, True).pack(side="left")
        self._button(top, "Generate Summary", self.generate_summary, primary=True).pack(side="right")
        self._label(self.summary_page, "Long documents are processed section by section. This may require multiple model calls.", 9, MUTED).pack(anchor="w", pady=(0, 12))
        frame, self.summary_result = self._text(self.summary_page)
        frame.pack(fill="both", expand=True, pady=(0, 12))
        self._set_text(self.summary_result, "Your summary will appear here.")

    def _quiz_layout(self):
        top = tk.Frame(self.quiz_page, bg=BG)
        top.pack(fill="x", pady=(14, 16))
        self._label(top, "Practice with AI-generated questions", 12, FG, True).pack(side="left")
        self._button(top, "Generate 5 Questions", self.generate_quiz, primary=True).pack(side="right")
        self.quiz_progress = tk.StringVar(value="No quiz generated yet.")
        self._label(self.quiz_page, "", 10, PURPLE, True, textvariable=self.quiz_progress).pack(anchor="w", pady=(0, 12))
        self.quiz_question = tk.StringVar(value="Import a document and generate a quiz to begin.")
        tk.Label(self.quiz_page, textvariable=self.quiz_question, bg=BG, fg=FG,
                 font=("Segoe UI", 13, "bold"), wraplength=650, justify="left", anchor="w").pack(fill="x", pady=(0, 16))
        self.quiz_choice = tk.IntVar(value=-1)
        self.quiz_radios = []
        for i in range(4):
            radio = tk.Radiobutton(self.quiz_page, text="", variable=self.quiz_choice, value=i,
                                   bg=BG, fg=FG, selectcolor=INPUT, activebackground=BG, activeforeground=FG,
                                   font=("Segoe UI", 11), wraplength=640, justify="left", anchor="w",
                                   pady=9, indicatoron=True)
            radio.pack(fill="x", anchor="w")
            radio.pack_forget()
            self.quiz_radios.append(radio)
        self.quiz_feedback = tk.StringVar(value="")
        tk.Label(self.quiz_page, textvariable=self.quiz_feedback, bg=BG, fg=GREEN,
                 font=("Segoe UI", 10), justify="left", wraplength=640, anchor="w").pack(fill="x", pady=(18, 12))
        actions = tk.Frame(self.quiz_page, bg=BG)
        actions.pack(anchor="w", pady=(0, 15))
        self.submit_btn = self._button(actions, "Check Answer", self.check_answer, primary=True)
        self.submit_btn.pack(side="left", padx=(0, 10))
        self.next_btn = self._button(actions, "Next Question  →", self.next_question)
        self.next_btn.pack(side="left")
        self.submit_btn.config(state="disabled")
        self.next_btn.config(state="disabled")

    def _flash_layout(self):
        top = tk.Frame(self.flash_page, bg=BG)
        top.pack(fill="x", pady=(14, 10))
        self._label(top, "Study flashcards", 12, FG, True).pack(side="left")
        self._button(top, "Generate Flashcards", self.generate_cards, primary=True).pack(side="right")
        self.card_count = tk.StringVar(value="No flashcards generated yet.")
        self._label(self.flash_page, "", 10, PURPLE, True, textvariable=self.card_count).pack(anchor="w", pady=(8, 12))
        card = tk.Frame(self.flash_page, bg=CARD, padx=25, pady=26, highlightbackground=BORDER,
                        highlightthickness=1, height=290)
        card.pack(fill="both", expand=True, pady=(0, 16))
        card.pack_propagate(False)
        self.card_front = tk.StringVar(value="Generate flashcards to start practicing.")
        self.card_back = tk.StringVar(value="")
        self.card_source = tk.StringVar(value="")
        tk.Label(card, textvariable=self.card_front, bg=CARD, fg=FG, font=("Segoe UI", 16, "bold"),
                 wraplength=600, justify="center").pack(fill="x", expand=True)
        tk.Label(card, textvariable=self.card_back, bg=CARD, fg=GREEN, font=("Segoe UI", 12),
                 wraplength=600, justify="center").pack(fill="x", expand=True)
        tk.Label(card, textvariable=self.card_source, bg=CARD, fg=MUTED, font=("Segoe UI", 9),
                 wraplength=600, justify="center").pack(fill="x")
        actions = tk.Frame(self.flash_page, bg=BG)
        actions.pack(pady=(0, 20))
        self._button(actions, "← Previous", self.prev_card).pack(side="left", padx=8)
        self._button(actions, "Reveal / Hide", self.reveal_card, primary=True).pack(side="left", padx=8)
        self._button(actions, "Next →", self.next_card).pack(side="left", padx=8)

    def _need_docs(self) -> bool:
        if not self.chunks:
            messagebox.showinfo("Import documents", "Please add at least one readable document first.")
            return False
        return True

    def _begin(self, job: Callable[[], Any], done: Callable[[Any], None], label: str):
        if self.busy:
            messagebox.showinfo("Task in progress", "Finish or cancel the current task first.")
            return
        self.busy = True
        self.cancel = threading.Event()
        self.done_callback = done
        self.cancel_btn.config(state="normal")
        self.status_var.set(label)
        def execute():
            try:
                result = job()
                self.events.put(("done", result))
            except Exception as exc:
                self.events.put(("error", exc))
        threading.Thread(target=execute, daemon=True).start()

    def _poll_events(self):
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "models":
                    models = value
                    self.model_combo["values"] = models
                    if self.model_var.get() not in models and models:
                        preferred = "qwen2.5:3b" if "qwen2.5:3b" in models else models[0]
                        self.model_var.set(preferred)
                    self.model_status.set(f"Ollama online • {len(models)} installed model(s)" if models else "Ollama online • no models installed")
                elif event == "model_error":
                    self.model_status.set(str(value))
                elif event == "progress":
                    self.status_var.set(str(value))
                elif event in ("done", "error"):
                    cb = self.done_callback
                    was_cancelled = self.cancel.is_set()
                    self.busy = False
                    self.done_callback = None
                    self.cancel_btn.config(state="disabled")
                    if was_cancelled or isinstance(value, CancelledError):
                        self.status_var.set("Task cancelled. No output applied.")
                    elif event == "error":
                        self.status_var.set("Task failed. See error details.")
                        messagebox.showerror("NEXUS Study AI", str(value))
                    else:
                        self.status_var.set("Done.")
                        if cb:
                            cb(value)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self._poll_events)

    def cancel_task(self):
        if self.busy:
            self.cancel.set()
            self.status_var.set("Cancelling after the current Ollama response chunk...")

    def refresh_models(self):
        self.model_status.set("Checking local Ollama...")
        def task():
            try:
                self.events.put(("models", self.client.models()))
            except OllamaError as exc:
                self.events.put(("model_error", str(exc)))
        threading.Thread(target=task, daemon=True).start()

    def add_documents(self):
        paths = filedialog.askopenfilenames(title="Import study documents",
                      filetypes=[("Study documents", "*.pdf *.docx *.txt *.md"), ("All files", "*.*")])
        if not paths:
            return
        existing_paths = {str(d.path) for d in self.docs}
        used_names = {d.name for d in self.docs}
        selected = [p for p in paths if str(Path(p).resolve()) not in existing_paths]
        if not selected:
            self.status_var.set("These documents are already in your library.")
            return
        def job():
            results, errors = [], []
            for path in selected:
                if self.cancel.is_set():
                    raise CancelledError("Cancelled.")
                p = Path(path)
                name = p.name
                counter = 2
                while name in used_names:
                    name = f"{p.stem} ({counter}){p.suffix}"
                    counter += 1
                try:
                    doc = load_document(path, display_name=name)
                    results.append(doc)
                    used_names.add(name)
                    self.events.put(("progress", f"Read: {p.name}"))
                except (OSError, DocumentError) as exc:
                    errors.append(f"{p.name}: {exc}")
            return results, errors
        def done(result):
            loaded, errors = result
            self.docs.extend(loaded)
            self._update_library()
            if errors:
                messagebox.showwarning("Some files were skipped", "\n\n".join(errors[:8]))
            self.status_var.set(f"Imported {len(loaded)} document(s). Ready to study.")
        self._begin(job, done, "Reading local files...")

    def _update_library(self):
        self.listbox.delete(0, "end")
        for doc in self.docs:
            self.listbox.insert("end", f"  {doc.name}")
        self.chunks = build_index(self.docs)
        self.count_var.set(f"{len(self.docs)} file(s)  •  {len(self.chunks)} indexed sections")

    def remove_selected(self):
        if self.busy:
            messagebox.showinfo("Busy", "Cancel or finish the current task first.")
            return
        selection = self.listbox.curselection()
        if selection:
            del self.docs[selection[0]]
            self._update_library()

    def clear_docs(self):
        if self.busy:
            return
        self.docs.clear()
        self._update_library()
        self.status_var.set("Library cleared from app memory. Your files were not changed.")

    def _model(self) -> str:
        return self.model_var.get().strip()

    def _ask_hotkey(self, event):
        self.ask_question()
        return "break"

    def ask_question(self):
        if not self._need_docs():
            return
        question = self.question.get("1.0", "end").strip()
        if not question:
            messagebox.showinfo("Enter a question", "Type a question, then click Ask AI.")
            return
        chunks = self.chunks.copy()
        model = self._model()
        self.question.delete("1.0", "end")
        self._set_text(self.ask_result, f"\nYOU: {question}\n\nThinking...\n", append=True)
        def job():
            return study.ask(self.client, model, chunks, question, cancel=self.cancel)
        def done(result):
            answer, evidence = result
            cited = "\n\nEVIDENCE RETRIEVED:\n" + "\n".join(f"• {c.label}" for c in evidence) if evidence else ""
            self._set_text(self.ask_result, f"\nNEXUS: {answer}{cited}\n\n" + "─" * 35 + "\n", append=True)
            self.chat_log.append((question, answer + cited))
        self._begin(job, done, "Asking local Ollama model...")

    def generate_summary(self):
        if not self._need_docs():
            return
        chunks, model = self.chunks.copy(), self._model()
        def job():
            return study.summarize(self.client, model, chunks, cancel=self.cancel,
                 update=lambda s: self.events.put(("progress", s)))
        def done(result):
            self.summary_text = result
            self._set_text(self.summary_result, result)
        self._begin(job, done, "Generating document summary (all indexed sections)...")

    def generate_quiz(self):
        if not self._need_docs():
            return
        chunks, model = self.chunks.copy(), self._model()
        def done(result):
            self.quiz = result
            self.quiz_index = 0
            self.quiz_score = 0
            self._render_quiz()
        self._begin(lambda: study.generate_quiz(self.client, model, chunks, self.cancel),
                    done, "Generating a source-grounded quiz...")

    def _render_quiz(self):
        if not self.quiz:
            return
        if self.quiz_index >= len(self.quiz):
            self.quiz_progress.set(f"Quiz complete! Score: {self.quiz_score}/{len(self.quiz)}")
            self.quiz_question.set("Great work. Generate another quiz whenever you're ready.")
            for radio in self.quiz_radios:
                radio.pack_forget()
            self.quiz_feedback.set("Review the questions and their source explanations in Export Current Tab.")
            self.submit_btn.config(state="disabled")
            self.next_btn.config(state="disabled")
            return
        q = self.quiz[self.quiz_index]
        self.quiz_answered = False
        self.quiz_choice.set(-1)
        self.quiz_progress.set(f"Question {self.quiz_index + 1}/{len(self.quiz)}  •  Score {self.quiz_score}")
        self.quiz_question.set(q["question"])
        self.quiz_feedback.set("")
        for i, radio in enumerate(self.quiz_radios):
            radio.configure(text=f"{chr(65 + i)}.  {q['options'][i]}", state="normal")
            radio.pack(fill="x", anchor="w")
        self.submit_btn.config(state="normal")
        self.next_btn.config(state="disabled")

    def check_answer(self):
        if not self.quiz or self.quiz_index >= len(self.quiz) or self.quiz_answered:
            return
        if self.quiz_choice.get() < 0:
            messagebox.showinfo("Choose an answer", "Select one answer before checking.")
            return
        q = self.quiz[self.quiz_index]
        correct = self.quiz_choice.get() == q["answer_index"]
        if correct:
            self.quiz_score += 1
        self.quiz_answered = True
        answer = f"{chr(65 + q['answer_index'])}. {q['options'][q['answer_index']]}"
        self.quiz_feedback.set(("Correct!" if correct else "Not quite.") +
                    f"  Correct answer: {answer}\n{q['explanation']}\nSource: {q['source']}")
        for radio in self.quiz_radios:
            radio.config(state="disabled")
        self.submit_btn.config(state="disabled")
        self.next_btn.config(state="normal", text="Finish Quiz" if self.quiz_index == len(self.quiz) - 1 else "Next Question  →")

    def next_question(self):
        if self.quiz_answered:
            self.quiz_index += 1
            self._render_quiz()

    def generate_cards(self):
        if not self._need_docs():
            return
        chunks, model = self.chunks.copy(), self._model()
        def done(result):
            self.cards = result
            self.card_index = 0
            self.card_revealed = False
            self._render_card()
        self._begin(lambda: study.generate_flashcards(self.client, model, chunks, self.cancel),
                    done, "Generating flashcards locally...")

    def _render_card(self):
        if not self.cards:
            return
        c = self.cards[self.card_index]
        self.card_count.set(f"Card {self.card_index + 1} of {len(self.cards)}")
        self.card_front.set(c["front"])
        self.card_back.set(c["back"] if self.card_revealed else "Click Reveal / Hide to check your answer")
        self.card_source.set(f"Source: {c['source']}" if self.card_revealed else "")

    def reveal_card(self):
        if self.cards:
            self.card_revealed = not self.card_revealed
            self._render_card()

    def next_card(self):
        if self.cards:
            self.card_index = (self.card_index + 1) % len(self.cards)
            self.card_revealed = False
            self._render_card()

    def prev_card(self):
        if self.cards:
            self.card_index = (self.card_index - 1) % len(self.cards)
            self.card_revealed = False
            self._render_card()

    def export_current(self):
        tab = self.tabs.index(self.tabs.select())
        if tab == 0:
            content = "NEXUS STUDY AI — CHAT\n\n" + "\n\n".join(f"YOU: {q}\nNEXUS: {a}" for q, a in self.chat_log)
            name = "nexus_study_chat.txt"
        elif tab == 1:
            content, name = self.summary_text, "nexus_study_summary.txt"
        elif tab == 2:
            content, name = "NEXUS STUDY AI — QUIZ\n\n", "nexus_study_quiz.txt"
            for i, q in enumerate(self.quiz, 1):
                content += f"{i}. {q['question']}\n" + "\n".join(f"{chr(65 + j)}. {a}" for j, a in enumerate(q["options"]))
                content += f"\nANSWER: {chr(65 + q['answer_index'])}\n{q['explanation']}\nSOURCE: {q['source']}\n\n"
        else:
            content, name = "NEXUS STUDY AI — FLASHCARDS\n\n", "nexus_study_flashcards.txt"
            for i, c in enumerate(self.cards, 1):
                content += f"{i}. FRONT: {c['front']}\nBACK: {c['back']}\nSOURCE: {c['source']}\n\n"
        if not content.strip() or content.strip() in ("NEXUS STUDY AI — QUIZ", "NEXUS STUDY AI — FLASHCARDS", "NEXUS STUDY AI — CHAT"):
            messagebox.showinfo("Nothing to export", "Generate some study content first.")
            return
        path = filedialog.asksaveasfilename(title="Export study notes", defaultextension=".txt",
                           initialfile=name, filetypes=[("Text file", "*.txt")])
        if path:
            try:
                Path(path).write_text(content, encoding="utf-8")
            except OSError as exc:
                messagebox.showerror("Export failed", str(exc))
            else:
                self.status_var.set(f"Saved notes to {Path(path).name}")

    def _close(self):
        self.cancel.set()
        self.destroy()
