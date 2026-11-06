"""Tkinter frontend: explicit user selection, read-only source, no automatic linking."""

from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .storage import TraceStore
from .models import SourceRange
from .workbench import Workbench, analyze_project


def _tree(parent: ttk.Frame, columns: tuple[str, ...], height: int = 8) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height, selectmode="browse")
    for column in columns:
        tree.heading(column, text=column)
        tree.column(column, width=160, minwidth=70)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return tree


def _text(parent: ttk.Frame, height: int = 10) -> tk.Text:
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    text = tk.Text(frame, wrap="none", height=height, state="disabled", font=("Consolas", 10))
    y = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    x = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
    text.configure(yscrollcommand=y.set, xscrollcommand=x.set)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    text.grid(row=0, column=0, sticky="nsew")
    y.grid(row=0, column=1, sticky="ns")
    x.grid(row=1, column=0, sticky="ew")
    return text


def _set_text(widget: tk.Text, value: str) -> None:
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", value)
    widget.configure(state="disabled")


class Navigator(ttk.Frame):
    """All Tk calls stay on the main thread; only project analysis uses a worker."""

    def __init__(self, root: tk.Tk, workbench: Workbench | None = None) -> None:
        super().__init__(root, padding=8)
        self.root = root
        self.workbench = workbench or Workbench()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="source-analysis")
        self.future: Future | None = None
        self.busy = False
        self.closed = False
        self.reanalyzed = False
        self.poll_id: str | None = None
        self.pack(fill="both", expand=True)
        root.title("AUTOSAR Trace Navigator")
        root.geometry("1500x950")
        root.minsize(1100, 760)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.buttons = []
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")
        for label, command in (("소스 폴더 분석", self.choose_project), ("세션 저장", self.save),
                               ("세션 불러오기", self.restore), ("뒤로", self.back)):
            self.button(toolbar, label, command).pack(side="left", padx=(0, 6))
        self.status = tk.StringVar(value="소스 폴더를 선택하세요. 원본 소스는 읽기 전용입니다.")
        status_label = ttk.Label(self, textvariable=self.status, wraplength=1400)
        status_label.pack(fill="x", pady=5)
        exclude = ttk.Frame(self)
        exclude.pack(fill="x")
        ttk.Label(exclude, text="제외 경로 (선택 폴더 기준, ;로 구분)").pack(side="left")
        self.exclusions = tk.StringVar(value=".git;.venv;build;wheelhouse")
        self.exclude_entry = ttk.Entry(exclude, textvariable=self.exclusions)
        self.exclude_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.goal = tk.StringVar(value="최초 목표: 아직 선택하지 않았습니다.")
        goal_label = ttk.Label(self, textvariable=self.goal, font=("맑은 고딕", 11, "bold"), wraplength=1400)
        goal_label.pack(fill="x", pady=8)
        self.context = tk.StringVar(value="조사 이유: 목표 분기를 선택하고 시작하세요.")
        context_label = ttk.Label(self, textvariable=self.context, wraplength=1400)
        context_label.pack(fill="x", pady=(0, 6))
        def resize_labels(event) -> None:
            if event.widget == self.root:
                for label in (status_label, goal_label, context_label):
                    label.configure(wraplength=max(400, event.width - 24))
        root.bind("<Configure>", resize_labels)
        pane = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True)
        left, middle, right = (ttk.Frame(pane, padding=4) for _ in range(3))
        pane.add(left, weight=2)
        pane.add(middle, weight=4)
        pane.add(right, weight=3)
        ttk.Label(left, text="함수 목록 — 선택하면 분기와 소스 표시").pack(anchor="w")
        self.functions = _tree(left, ("함수", "파일:행"), 12)
        self.functions.bind("<<TreeviewSelect>>", self.browse_function)
        ttk.Label(left, text="목표 분기 선택").pack(anchor="w", pady=(8, 0))
        self.branches = _tree(left, ("분기", "조건 / 행"), 7)
        self.branches.bind("<<TreeviewSelect>>", self.preview_branch)
        self.button(left, "선택 분기로 새 조사 시작", self.start).pack(fill="x", pady=6)
        self.source_label = tk.StringVar(value="소스 미리보기 (분석 시점, 읽기 전용)")
        source_label = ttk.Label(middle, textvariable=self.source_label, wraplength=500)
        source_label.pack(fill="x")
        middle.bind("<Configure>", lambda event: source_label.configure(wraplength=max(160, event.width - 8)))
        notebook = ttk.Notebook(middle)
        notebook.pack(fill="both", expand=True)
        source_tab, diagnostics_tab = ttk.Frame(notebook), ttk.Frame(notebook)
        notebook.add(source_tab, text="소스")
        notebook.add(diagnostics_tab, text="진단")
        self.source = _text(source_tab)
        self.source.tag_configure("location", background="#fff0b3", foreground="#111111")
        self.diagnostics = _text(diagnostics_tab)
        ttk.Label(right, text="확정되지 않은 조사 후보").pack(anchor="w")
        candidates = ttk.Notebook(right)
        candidates.pack(fill="both", expand=True)
        call_tab, rte_tab = ttk.Frame(candidates), ttk.Frame(candidates)
        candidates.add(call_tab, text="호출 후보")
        candidates.add(rte_tab, text="RTE 공급자 후보")
        self.calls = _tree(call_tab, ("호출", "대상 / 위치"), 7)
        self.rte = _tree(rte_tab, ("데이터", "공급자 / 위치"), 7)
        self.candidate_tables = (self.calls, self.rte)
        self.candidate_map = {}
        for table in self.candidate_tables:
            table.bind("<<TreeviewSelect>>", lambda event, table=table: self.preview_candidate(table))
        self.button(call_tab, "호출 후보 조사", lambda: self.follow(self.calls)).pack(fill="x")
        self.button(rte_tab, "RTE 공급자 후보 조사", lambda: self.follow(self.rte)).pack(fill="x")
        self.detail = _text(right, 5)
        ttk.Label(right, text="전체 조사 이력 (대안 경로 포함)").pack(anchor="w", pady=(6, 0))
        self.history = _tree(right, ("현재 / 관계", "함수", "조사 이유"), 6)
        self.button(right, "선택한 이력 단계로 이동", self.select_history).pack(fill="x", pady=4)
        self.render_project()
        self.refresh_trace()

    def button(self, parent: ttk.Frame, label: str, command: Callable[[], None]) -> ttk.Button:
        widget = ttk.Button(parent, text=label, command=lambda: self.run_action(command))
        self.buttons.append(widget)
        return widget

    def run_action(self, command: Callable[[], None]) -> None:
        try:
            command()
        except (OSError, ValueError, KeyError, RuntimeError, sqlite3.Error) as error:
            messagebox.showerror("작업을 완료하지 못했습니다", str(error), parent=self.root)

    def choose_project(self) -> None:
        directory = filedialog.askdirectory(parent=self.root, title="C/H 소스 폴더 선택")
        if directory:
            self.begin_analysis(Path(directory))

    def begin_analysis(self, directory: Path) -> None:
        if self.busy:
            raise ValueError("분석이 이미 진행 중입니다.")
        excludes = tuple(value.strip() for value in self.exclusions.get().split(";") if value.strip())
        self.busy = True
        for button in self.buttons:
            button.state(["disabled"])
        self.exclude_entry.state(["disabled"])
        self.status.set(f"분석 중: {directory} — 기존 조사 상태는 유지됩니다.")
        self.future = self.executor.submit(analyze_project, directory, exclude_paths=excludes)
        self.poll_id = self.root.after(80, self.poll_analysis)

    def poll_analysis(self) -> None:
        if self.closed or self.future is None:
            return
        if not self.future.done():
            self.poll_id = self.root.after(80, self.poll_analysis)
            return
        try:
            project = self.future.result()
            if self.workbench.manager is not None:
                self.reanalyzed = True
            self.workbench.project = project
            self.render_project()
            self.refresh_trace()
            self.status.set(f"분석 완료: {project.root} | 파일 {len(project.sources)}개 / 함수 {len(project.functions)}개")
        except Exception as error:
            self.status.set("분석 실패 — 기존 분석과 조사 상태를 유지했습니다.")
            messagebox.showerror("분석 실패", str(error), parent=self.root)
        finally:
            self.future = None
            self.busy = False
            for button in self.buttons:
                button.state(["!disabled"])
            self.exclude_entry.state(["!disabled"])

    def render_project(self) -> None:
        self.functions.delete(*self.functions.get_children())
        self.branches.delete(*self.branches.get_children())
        _set_text(self.source, "함수 또는 분기를 선택하면 분석 시점의 소스를 표시합니다.")
        self.source_label.set("소스 미리보기 (분석 시점, 읽기 전용)")
        project = self.workbench.project
        if project is None:
            return
        for function in project.functions:
            self.functions.insert("", "end", iid=function.id, values=(
                function.name, f"{function.location.path.relative_to(project.root)}:{function.location.start_line}"))
        diagnostics = [d for r in project.results for d in r.diagnostics] + list(project.rte.diagnostics)
        _set_text(self.diagnostics, "\n".join(
            f"{d.location.path}:{d.location.start_line}\n{d.code}: {d.message}\n" for d in diagnostics)
            or "진단 없음")

    def browse_function(self, event: tk.Event | None = None) -> None:
        selected = self.functions.selection()
        if not selected or self.workbench.project is None:
            return
        function = next(f for f in self.workbench.project.functions if f.id == selected[0])
        self.branches.delete(*self.branches.get_children())
        for result in self.workbench.project.results:
            for branch in result.branches:
                if branch.function_id == function.id:
                    self.branches.insert("", "end", iid=branch.id,
                                         values=(branch.kind, f"{branch.condition or '(else)'} / {branch.location.start_line}행"))
        self.show_source(function.location)

    def show_source(self, location: SourceRange) -> None:
        project = self.workbench.project
        data = next((data for path, data in project.sources if path == location.path), None) if project else None
        self.source_label.set(f"현재 분석 소스 (읽기 전용): {location.path}:{location.start_line}")
        if data is None:
            _set_text(self.source, "이 위치의 분석 소스가 없습니다. 해당 소스 폴더를 분석하세요.\n"
                      "복원한 위치는 저장 시점의 메타데이터입니다.")
            return
        _set_text(self.source, "\n".join(f"{index:5}  {line}" for index, line in
                                        enumerate(data.decode("utf-8", errors="replace").splitlines(), 1)))
        self.source.tag_remove("location", "1.0", "end")
        self.source.tag_add("location", f"{location.start_line}.0", f"{location.start_line}.end")
        self.source.see(f"{location.start_line}.0")

    def preview_branch(self, event: tk.Event | None = None) -> None:
        selected = self.branches.selection()
        if selected and self.workbench.project:
            branch = next(b for r in self.workbench.project.results for b in r.branches if b.id == selected[0])
            self.show_source(branch.location)

    def discard_allowed(self) -> bool:
        return not self.workbench.dirty or messagebox.askyesno(
            "저장하지 않은 조사", "저장하지 않은 조사 변경을 버리고 계속할까요?", parent=self.root)

    def start(self) -> None:
        functions, branches = self.functions.selection(), self.branches.selection()
        if not functions or not branches:
            raise ValueError("함수와 목표 분기를 선택하세요.")
        reason = simpledialog.askstring("조사 시작", "이 목표 분기를 조사하는 이유", parent=self.root)
        if reason is not None and self.discard_allowed():
            self.workbench.start(functions[0], branches[0], reason)
            self.reanalyzed = False
            self.refresh_trace()

    def refresh_trace(self) -> None:
        self.root.title("AUTOSAR Trace Navigator" + (" *" if self.workbench.dirty else ""))
        for table in (*self.candidate_tables, self.history):
            table.delete(*table.get_children())
        self.candidate_map.clear()
        _set_text(self.detail, "후보를 선택해 근거 위치와 불확실성을 확인하세요.")
        manager = self.workbench.manager
        if manager is None:
            return
        target = manager.session.target_branch
        self.goal.set(f"최초 목표: {manager.session.target_function.name} | {target.kind} {target.condition or '(else)'}"
                      f" | {target.location.path}:{target.location.start_line}")
        note = " [이전 조사 스냅샷 — 소스 변경 여부 미검증]" if self.workbench.restored or self.reanalyzed else ""
        self.context.set(f"현재: {manager.current_step.function.name} | 조사 이유: {manager.current_step.reason}{note}\n"
                         + "경로: " + " → ".join(step.function.name for step in manager.current_path))
        for index, candidate in enumerate(self.workbench.candidates()):
            key = str(index)
            self.candidate_map[key] = candidate
            table = self.calls if candidate.relation == "call" else self.rte
            destination = candidate.function
            label = (f"{destination.name} — {destination.location.path.name}:{destination.location.start_line}"
                     if destination else "함수 미확인 — 이동 불가")
            table.insert("", "end", iid=key, values=(candidate.label, label))
        for step in manager.session.steps:
            marker = "▶ " if step.id == manager.session.current_step_id else ""
            self.history.insert("", "end", iid=step.id, values=(marker + step.relation, step.function.name, step.reason))
        current = manager.current_step.function
        if self.functions.exists(current.id):
            self.functions.selection_set(current.id)
            self.functions.see(current.id)
            self.browse_function()
        self.show_source(current.location)

    def preview_candidate(self, table: ttk.Treeview) -> None:
        selected = table.selection()
        candidate = self.candidate_map.get(selected[0]) if selected else None
        if candidate:
            _set_text(self.detail, f"{candidate.relation}: {candidate.label}\n"
                      f"근거: {candidate.evidence.path}:{candidate.evidence.start_line}\n"
                      "확정되지 않은 후보 / 검토 사항:\n" + "\n".join(candidate.uncertainty))

    def follow(self, table: ttk.Treeview) -> None:
        selected = table.selection()
        candidate = self.candidate_map.get(selected[0]) if selected else None
        if candidate is None or candidate.function is None:
            raise ValueError("대상 함수가 있는 후보를 선택하세요.")
        reason = simpledialog.askstring("함수 조사", f"{candidate.function.name}을 조사하는 이유", parent=self.root)
        if reason is not None:
            self.workbench.follow(candidate, reason)
            self.refresh_trace()

    def back(self) -> None:
        self.workbench.back()
        self.refresh_trace()

    def select_history(self) -> None:
        selected = self.history.selection()
        if selected:
            self.workbench.select(selected[0])
            self.refresh_trace()

    def save(self) -> None:
        self.workbench.session
        path = self.workbench.database or filedialog.asksaveasfilename(
            parent=self.root, title="세션 DB 저장", defaultextension=".sqlite3",
            filetypes=[("SQLite", "*.sqlite3 *.db")])
        if path:
            self.workbench.save(path)
            self.refresh_trace()
            self.status.set(f"저장 완료: {path} / 리비전 {self.workbench.revision}")

    def restore(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="세션 DB 열기", filetypes=[("SQLite", "*.sqlite3 *.db")])
        if not path:
            return
        with TraceStore(path) as store:
            summaries = []
            for key in store.list_sessions():
                try:
                    summaries.append((key, store.load(key).session))
                except ValueError:
                    summaries.append((key, None))
        if not summaries:
            raise ValueError("저장된 세션이 없습니다.")
        dialog = tk.Toplevel(self.root)
        dialog.title("복원할 세션 선택")
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - 850) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - 350) // 2)
        dialog.geometry(f"850x350+{x}+{y}")
        dialog.transient(self.root)
        table = _tree(dialog, ("목표 함수", "목표 분기", "세션 ID"))
        for key, session in summaries:
            table.insert("", "end", iid=key, values=(session.target_function.name if session else "손상된 세션",
                         (session.target_branch.condition or "else") if session else "복원 불가", key))

        def load_selected() -> None:
            selected = table.selection()
            if selected and self.discard_allowed():
                self.workbench.restore(path, selected[0])
                dialog.destroy()
                self.refresh_trace()
                self.status.set("세션 복원 완료 — 저장 시점 이후 소스 변경 여부는 검증하지 않았습니다.")

        ttk.Button(dialog, text="선택 세션 복원", command=lambda: self.run_action(load_selected)).pack(pady=6)
        dialog.grab_set()

    def close(self) -> None:
        if self.discard_allowed():
            self.closed = True
            if self.poll_id is not None:
                self.root.after_cancel(self.poll_id)
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.root.destroy()


def main() -> None:
    """Launch the offline desktop frontend; imports alone do not create windows."""
    root = tk.Tk()
    Navigator(root)
    root.mainloop()
