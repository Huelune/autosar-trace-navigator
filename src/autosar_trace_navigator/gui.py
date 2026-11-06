"""Tkinter frontend: explicit user selection, read-only source, no automatic linking."""

from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable
from pathlib import Path
from itertools import chain, islice
import sqlite3
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .storage import TraceStore
from .models import FunctionDefinition, SourceRange
from .workbench import Workbench, analyze_project


def _tree(parent: ttk.Frame, columns: tuple[str, ...], height: int = 8) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height, selectmode="browse")
    for column in columns:
        tree.heading(column, text=column)
        tree.column(column, width=160, minwidth=70)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal.set)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
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
        self.page_offset = 0
        self.last_query = ""
        self.picked_location: SourceRange | None = None
        self.pack(fill="both", expand=True)
        root.title("AUTOSAR Trace Navigator")
        root.geometry("1500x950")
        root.minsize(1100, 760)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.buttons = []
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")
        for label, command in (("루트 폴더 선택", self.choose_project), ("선택 범위 분석", self.analyze_scope), ("세션 저장", self.save),
                               ("세션 불러오기", self.restore), ("뒤로", self.back)):
            self.button(toolbar, label, command).pack(side="left", padx=(0, 6))
        self.status = tk.StringVar(value="소스 폴더를 선택하세요. 원본 소스는 읽기 전용입니다.")
        status_label = ttk.Label(self, textvariable=self.status, wraplength=1400)
        status_label.pack(fill="x", pady=5)
        self.project_root = tk.StringVar(value=str(self.workbench.project.root) if self.workbench.project else "미선택")
        ttk.Label(self, textvariable=self.project_root).pack(fill="x")
        scope = ttk.Frame(self)
        scope.pack(fill="x")
        ttk.Label(scope, text="분석 범위 (루트 기준 파일/폴더, ;로 구분)").pack(side="left")
        self.scopes = tk.StringVar()
        self.scope_entry = ttk.Entry(scope, textvariable=self.scopes)
        self.scope_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.scope_info = tk.StringVar(value="분석 범위를 지정하세요. 전체 루트는 . 을 명시해야 합니다.")
        scope_label = ttk.Label(self, textvariable=self.scope_info, wraplength=1400)
        scope_label.pack(fill="x")
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
        value_controls = ttk.Frame(self)
        value_controls.pack(fill="x", pady=(0, 4))
        ttk.Label(value_controls, text="변수").pack(side="left")
        self.variable = tk.StringVar()
        self.variable_entry = ttk.Entry(value_controls, textvariable=self.variable, width=18)
        self.variable_entry.pack(side="left", padx=4)
        ttk.Label(value_controls, text="목표값").pack(side="left")
        self.target_value = tk.StringVar()
        self.target_entry = ttk.Entry(value_controls, textvariable=self.target_value, width=12)
        self.target_entry.pack(side="left", padx=4)
        for label, command in (("변수 목표 설정", self.set_variable_goal),
                               ("현재 변수 조사", self.inspect_variable),
                               ("선택 라인 기록", self.record_location)):
            self.button(value_controls, label, command).pack(side="left", padx=3)
        def resize_labels(event) -> None:
            if event.widget == self.root:
                for label in (status_label, scope_label, goal_label, context_label):
                    label.configure(wraplength=max(400, event.width - 24))
        root.bind("<Configure>", resize_labels)
        pane = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True)
        left, middle, right = (ttk.Frame(pane, padding=4) for _ in range(3))
        pane.add(left, weight=2)
        pane.add(middle, weight=4)
        pane.add(right, weight=3)
        ttk.Label(left, text="함수 검색 — 이름·파일 경로, 결과 100개/페이지").pack(anchor="w")
        search = ttk.Frame(left)
        search.pack(fill="x")
        self.query = tk.StringVar()
        entry = ttk.Entry(search, textvariable=self.query)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda event: self.run_action(self.search_functions))
        self.button(search, "검색", self.search_functions).pack(side="left")
        navigation = ttk.Frame(left)
        navigation.pack(fill="x")
        self.button(navigation, "이전", lambda: self.change_page(-100)).pack(side="left")
        self.button(navigation, "다음", lambda: self.change_page(100)).pack(side="left")
        self.search_summary = tk.StringVar(value="검색어를 입력하세요.")
        ttk.Label(left, textvariable=self.search_summary, wraplength=300).pack(fill="x")
        self.functions = _tree(left, ("함수", "파일:행"), 6)
        self.functions.bind("<<TreeviewSelect>>", self.browse_function)
        ttk.Label(left, text="목표 분기 선택").pack(anchor="w", pady=(8, 0))
        self.branches = _tree(left, ("분기", "조건 / 행"), 4)
        self.branches.bind("<<TreeviewSelect>>", self.preview_branch)
        self.button(left, "선택 분기로 새 조사 시작", self.start).pack(fill="x", pady=6)
        self.source_label = tk.StringVar(value="소스 미리보기 (분석 시점, 읽기 전용)")
        source_label = ttk.Label(middle, textvariable=self.source_label, wraplength=500)
        source_label.pack(fill="x")
        middle.bind("<Configure>", lambda event: source_label.configure(wraplength=max(160, event.width - 8)))
        notebook = self.source_notebook = ttk.Notebook(middle)
        notebook.pack(fill="both", expand=True)
        source_tab, diagnostics_tab = ttk.Frame(notebook), ttk.Frame(notebook)
        notebook.add(source_tab, text="소스")
        notebook.add(diagnostics_tab, text="진단")
        self.source = _text(source_tab)
        self.source.tag_configure("location", background="#fff0b3", foreground="#111111")
        self.source.bind("<ButtonRelease-1>", self.capture_source_selection)
        self.preview_tab = ttk.Frame(notebook)
        notebook.add(self.preview_tab, text="후보 / 이력 코드")
        self.preview_label = tk.StringVar(value="후보를 선택하면 이동 전에 코드를 확인할 수 있습니다.")
        ttk.Label(self.preview_tab, textvariable=self.preview_label, wraplength=440).pack(fill="x")
        self.candidate_source = _text(self.preview_tab)
        self.candidate_source.tag_configure("location", background="#fff0b3", foreground="#111111")
        self.diagnostics = _text(diagnostics_tab)
        ttk.Label(right, text="확정되지 않은 조사 후보").pack(anchor="w")
        candidates = ttk.Notebook(right)
        candidates.pack(fill="both", expand=True)
        call_tab, rte_tab, value_tab = (ttk.Frame(candidates) for _ in range(3))
        candidates.add(call_tab, text="호출 후보")
        candidates.add(rte_tab, text="RTE 공급자 후보")
        candidates.add(value_tab, text="변수 값 출처")
        self.calls = _tree(call_tab, ("호출", "대상 / 위치"), 5)
        self.rte = _tree(rte_tab, ("데이터", "공급자 / 위치"), 5)
        self.values = _tree(value_tab, ("값 출처", "대상 / 위치"), 5)
        self.candidate_tables = (self.calls, self.rte, self.values)
        self.candidate_map = {}
        for table in self.candidate_tables:
            table.bind("<<TreeviewSelect>>", lambda event, table=table: self.preview_candidate(table))
        self.button(call_tab, "호출 후보 조사", lambda: self.follow(self.calls)).pack(fill="x")
        self.button(rte_tab, "RTE 공급자 후보 조사", lambda: self.follow(self.rte)).pack(fill="x")
        self.button(value_tab, "선택 출처 조사", lambda: self.follow(self.values)).pack(fill="x")
        self.detail = _text(right, 4)
        ttk.Label(right, text="전체 조사 이력 (대안 경로 포함)").pack(anchor="w", pady=(6, 0))
        self.history = _tree(right, ("현재 / 관계", "함수", "선택 위치", "조사 이유"), 4)
        self.history.bind("<<TreeviewSelect>>", self.preview_history)
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
            self.project_root.set(directory)
            self.status.set("루트를 선택했습니다. 분석 범위를 입력하고 선택 범위 분석을 누르세요.")

    def analyze_scope(self) -> None:
        if self.project_root.get() == "미선택":
            raise ValueError("먼저 루트 폴더를 선택하세요.")
        self.begin_analysis(Path(self.project_root.get()))

    def begin_analysis(self, directory: Path) -> None:
        if self.busy:
            raise ValueError("분석이 이미 진행 중입니다.")
        includes = tuple(value.strip() for value in self.scopes.get().split(";") if value.strip())
        if not includes:
            raise ValueError("분석 범위에 파일 또는 하위 폴더를 입력하세요. 전체 루트는 . 을 명시하세요.")
        excludes = tuple(value.strip() for value in self.exclusions.get().split(";") if value.strip())
        self.busy = True
        for button in self.buttons:
            button.state(["disabled"])
        self.exclude_entry.state(["disabled"])
        self.scope_entry.state(["disabled"])
        self.status.set(f"분석 중: {directory} — 기존 조사 상태는 유지됩니다.")
        self.future = self.executor.submit(analyze_project, directory, exclude_paths=excludes, include_paths=includes)
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
            self.scope_entry.state(["!disabled"])

    def render_project(self) -> None:
        self.picked_location = None
        self.functions.delete(*self.functions.get_children())
        self.branches.delete(*self.branches.get_children())
        _set_text(self.source, "함수 또는 분기를 선택하면 분석 시점의 소스를 표시합니다.")
        self.source_label.set("소스 미리보기 (분석 시점, 읽기 전용)")
        project = self.workbench.project
        if project is None:
            return
        self.project_root.set(str(project.root))
        scopes = project.scope or (project.root,)
        self.scope_info.set(f"현재 분석 루트: {project.root} | 범위: " + "; ".join(str(path.relative_to(project.root)) for path in scopes)
                            + " | 미확인은 이 범위 안의 결과입니다.")
        self.render_function_page()
        total = sum(len(result.diagnostics) for result in project.results) + len(project.rte.diagnostics)
        diagnostics = chain(*(result.diagnostics for result in project.results), project.rte.diagnostics)
        _set_text(self.diagnostics, f"현재 범위 진단 {total}개 중 최대 500개 표시\n\n" + "\n".join(
            f"{d.location.path}:{d.location.start_line}\n{d.code}: {d.message}\n" for d in islice(diagnostics, 500)))

    def render_function_page(self, offset: int = 0) -> None:
        selected = self.functions.selection()
        self.functions.delete(*self.functions.get_children())
        self.branches.delete(*self.branches.get_children())
        project = self.workbench.project
        self.page_offset = offset
        if project is None:
            return
        self.last_query = self.query.get()
        page = project.search_functions(self.last_query, offset=offset)
        for function in page.functions:
            self.functions.insert("", "end", iid=function.id, values=(
                function.name, f"{function.location.path.relative_to(project.root)}:{function.location.start_line}"))
        manager = self.workbench.manager
        current = manager.current_step.function if manager else None
        if current and project.functions_by_id.get(current.id) == current and not self.functions.exists(current.id):
            self.functions.insert("", "end", iid=current.id, values=(
                "[현재] " + current.name, f"{current.location.path.relative_to(project.root)}:{current.location.start_line}"))
        self.search_summary.set(
            f"{offset + 1 if page.functions else 0}–{offset + len(page.functions)} / {page.total}개 일치 (현재 함수 별도 유지)"
            if self.last_query.strip() else "검색어를 입력하세요. 전체 함수는 자동 표시하지 않습니다.")
        if selected and self.functions.exists(selected[0]):
            self.functions.selection_set(selected[0])
            self.browse_function()

    def search_functions(self) -> None:
        self.render_function_page()

    def change_page(self, delta: int) -> None:
        if self.workbench.project is None:
            return
        if self.query.get() != self.last_query:
            self.search_functions()
            return
        offset = max(0, self.page_offset + delta)
        page = self.workbench.project.search_functions(self.query.get(), offset=offset)
        if offset == 0 or page.functions:
            self.render_function_page(offset)

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
        manager = self.workbench.manager
        location = (manager.current_step.selected_location
                    if manager and manager.current_step.function == function else None)
        self.show_source(location or function.location)

    def show_source(self, location: SourceRange) -> None:
        self.source_notebook.select(0)
        project = self.workbench.project
        data = next((data for path, data in project.sources if path == location.path), None) if project else None
        self.picked_location = location if data is not None else None
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

    def capture_source_selection(self, event: tk.Event) -> None:
        self.pick_source_position(self.source.index(f"@{event.x},{event.y}"))

    def pick_source_position(self, index: str) -> None:
        """Map a numbered Text position to a byte position in the analyzed snapshot."""
        if self.picked_location is None or self.workbench.project is None:
            return
        path = self.picked_location.path
        data = next(data for source_path, data in self.workbench.project.sources if source_path == path)
        lines = data.splitlines(keepends=True)
        row, column = (int(value) for value in index.split("."))
        if not 1 <= row <= len(lines):
            return
        # The seven-character line-number prefix is display-only. Model columns are bytes.
        line = lines[row - 1].decode("utf-8", errors="replace").rstrip("\r\n")
        byte_column = len(line[:max(0, column - 7)].encode("utf-8"))
        offset = sum(len(value) for value in lines[:row - 1]) + byte_column
        self.picked_location = SourceRange(path, row, byte_column + 1, row, byte_column + 1, offset, offset)
        ranges = self.source.tag_ranges("sel")
        if ranges:
            selected = self.source.get(*ranges[:2]).strip()
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", selected):
                self.variable.set(selected)
        self.source_label.set(f"선택 위치 (아직 미기록): {path}:{row}")
        self.source.tag_remove("location", "1.0", "end")
        self.source.tag_add("location", f"{row}.0", f"{row}.end")

    def selected_location(self) -> SourceRange:
        if self.picked_location is None:
            raise ValueError("현재 조사 함수의 소스에서 사용할 라인을 선택하세요.")
        return self.picked_location

    def set_variable_goal(self) -> None:
        self.workbench.set_variable_goal(self.variable.get().strip(), self.target_value.get().strip(),
                                         self.selected_location())
        self.refresh_trace()

    def inspect_variable(self) -> None:
        self.workbench.inspect_variable(self.variable.get().strip(), self.selected_location())
        self.refresh_trace()

    def record_location(self) -> None:
        self.workbench.record_location(self.selected_location())
        self.refresh_trace()

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
        _set_text(self.candidate_source, "후보 또는 이력을 선택하세요.")
        self.preview_label.set("코드는 현재 분석 시점의 읽기 전용 스냅샷입니다.")
        manager = self.workbench.manager
        if manager is None:
            return
        target = manager.session.target_branch
        self.goal.set(f"최초 목표: {manager.session.target_function.name} | {target.kind} {target.condition or '(else)'}"
                      f" | {target.location.path}:{target.location.start_line}")
        objective = manager.session.variable_goal
        if objective:
            self.goal.set(self.goal.get() + f"\n변수 목표: {objective.variable} → {objective.target_value}"
                          f" | {objective.location.path.name}:{objective.location.start_line}")
        note = " [이전 조사 스냅샷 — 소스 변경 여부 미검증]" if self.workbench.restored or self.reanalyzed else ""
        probe = manager.current_step.probe
        value_context = f" | 현재 값 조사: {probe.expression} ({probe.kind})" if probe else ""
        self.context.set(f"현재: {manager.current_step.function.name} | 조사 이유: {manager.current_step.reason}{note}\n"
                         + "경로: " + " → ".join(step.function.name for step in manager.current_path) + value_context)
        if probe and probe.kind == "variable":
            self.variable.set(probe.expression)
        if objective:
            self.target_value.set(objective.target_value)
        for index, candidate in enumerate((*self.workbench.candidates(), *self.workbench.value_candidates())):
            key = str(index)
            self.candidate_map[key] = candidate
            table = (self.values if candidate.value_kind else
                     self.calls if candidate.relation == "call" else self.rte)
            destination = candidate.function
            label = (f"{destination.name} — {destination.location.path.name}:{destination.location.start_line}"
                     if destination else "현재 분석 범위에서 미확인 — 이동 불가")
            table.insert("", "end", iid=key, values=(candidate.label, label))
        for step in manager.session.steps:
            marker = "▶ " if step.id == manager.session.current_step_id else ""
            site = step.selected_location
            label = f"{site.path}:{site.start_line}" if site else "미기록 (이전 세션)"
            self.history.insert("", "end", iid=step.id,
                                values=(marker + step.relation, step.function.name, label, step.reason))
        current = manager.current_step.function
        self.render_function_page(self.page_offset)
        if self.functions.exists(current.id):
            self.functions.selection_set(current.id)
            self.functions.see(current.id)
            self.browse_function()
        self.show_source(manager.current_step.selected_location or current.location)
        self.source_notebook.select(0)

    def preview_candidate(self, table: ttk.Treeview) -> None:
        selected = table.selection()
        candidate = self.candidate_map.get(selected[0]) if selected else None
        if candidate:
            _set_text(self.detail, f"{candidate.relation}: {candidate.label}\n"
                      f"근거: {candidate.evidence.path}:{candidate.evidence.start_line}\n"
                      "확정되지 않은 후보 / 검토 사항:\n" + "\n".join(candidate.uncertainty))
            location = candidate.selected_location or (candidate.function.location if candidate.function else candidate.evidence)
            self.show_preview(candidate.function, location, "후보 코드 — 이동 전 확인")

    def show_preview(self, function: FunctionDefinition | None, location: SourceRange, heading: str) -> None:
        """Display bounded snapshot code without changing the active selection or session."""
        project = self.workbench.project
        self.preview_label.set(f"{heading}\n{location.path}:{location.start_line} | 현재 분석 시점")
        self.source_notebook.select(self.preview_tab)
        if function is not None and (project is None or project.functions_by_id.get(function.id) != function):
            _set_text(self.candidate_source, "저장된 함수와 현재 분석 정보가 일치하지 않아 코드를 표시할 수 없습니다.")
            return
        data = next((data for path, data in project.sources if path == location.path), None) if project else None
        if data is None:
            _set_text(self.candidate_source, "현재 분석 범위에 해당 소스가 없습니다.")
            return
        first = max(1, location.start_line - 5)
        last = location.start_line + 15
        owner = function or next((fn for fn in project.functions
                                 if fn.location.path == location.path
                                 and fn.location.start_byte <= location.start_byte <= fn.location.end_byte), None)
        if owner is not None:
            first = max(first, owner.location.start_line)
            last = min(last, owner.location.end_line)
        lines = data.decode("utf-8", errors="replace").splitlines()
        prefix = "" if function is not None else "대상 함수 미확인 — 호출 근거 주변 코드만 표시합니다.\n"
        _set_text(self.candidate_source, prefix + "\n".join(
            f"{row:5}  {lines[row - 1]}" for row in range(first, min(last, len(lines)) + 1)))
        row = location.start_line - first + 1 + bool(prefix)
        self.candidate_source.tag_add("location", f"{row}.0", f"{row}.end")
        self.candidate_source.see(f"{row}.0")

    def preview_history(self, event: tk.Event | None = None) -> None:
        selected = self.history.selection()
        manager = self.workbench.manager
        if not selected or manager is None:
            return
        step = next(s for s in manager.session.steps if s.id == selected[0])
        site = step.selected_location
        evidence = step.evidence
        _set_text(self.detail, f"{step.function.name} | {step.reason}\n"
                  + (f"선택 위치: {site.path}:{site.start_line}\n" if site else "선택 위치: 미기록\n")
                  + (f"이동 근거: {evidence.path}:{evidence.start_line}\n" if evidence else "")
                  + "\n".join(step.uncertainty))
        self.show_preview(step.function, site or step.function.location, "이력 코드 — 이동은 별도 버튼")

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
