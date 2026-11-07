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
from .models import FunctionDefinition, SourceRange, ValueProbe
from .access import parse_access_path
from .workbench import InvestigationCandidate, Workbench, analyze_project


_VALUE_LABELS = {
    "return_value": "함수 반환값", "return": "반환식", "initializer": "초기값",
    "assignment": "대입값", "global_write": "변수 쓰기", "rte_data": "RTE 공급 값",
    "expression_operand": "계산 입력", "call_argument": "호출/매크로 입력",
    "unresolved_call": "미해석 호출", "expression": "계산식 (역산 미수행)",
    "constant": "상수", "ct_global_input": "CT 전역 제어 후보",
    "possible_output_argument": "출력 인수 후보", "update": "증감식",
    "member_write": "멤버/객체 쓰기", "member_initializer": "객체/포인터 초기값",
    "object_origin": "객체 자체 출처 (멤버값 별도)", "output_parameter": "함수 출력 인수 후보",
    "member_boundary": "멤버/포인터 해석 경계", "parameter_input": "함수 입력",
}


def _probe_text(probe: ValueProbe | None, default: str = "추적 종점") -> str:
    if probe is None:
        return default
    return probe.expression.replace("$return", "반환값", 1) if probe.kind == "return" else probe.expression


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
    text = tk.Text(frame, wrap="none", width=1, height=height, state="disabled", font=("Consolas", 10))
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
        self.source_focus_id: str | None = None
        self.history_focus_id: str | None = None
        self.page_offset = 0
        self.last_query = ""
        self.picked_location: SourceRange | None = None
        self.pack(fill="both", expand=True)
        root.title("AUTOSAR Trace Navigator")
        root.geometry("1500x950")
        root.minsize(1100, 760)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.buttons = []
        self.variable_inputs = {}
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")
        for label, command in (("루트 폴더 선택", self.choose_project), ("선택 범위 분석", self.analyze_scope),
                               ("세션 저장", self.save), ("세션 불러오기", self.restore), ("뒤로", self.back),
                               ("분석 설정 접기/펼치기", self.toggle_settings)):
            self.button(toolbar, label, command).pack(side="left", padx=(0, 6))
        self.status = tk.StringVar(value="1. 소스 폴더와 분석 범위를 선택하세요.")
        ttk.Label(self, textvariable=self.status, wraplength=1400).pack(fill="x", pady=4)
        self.settings = ttk.LabelFrame(self, text="분석 설정", padding=4)
        self.settings.pack(fill="x")
        self.project_root = tk.StringVar(value=str(self.workbench.project.root) if self.workbench.project else "미선택")
        ttk.Label(self.settings, textvariable=self.project_root, wraplength=1400).pack(fill="x")
        scope = ttk.Frame(self.settings)
        scope.pack(fill="x")
        ttk.Label(scope, text="분석 범위 (;로 구분)").pack(side="left")
        self.scopes = tk.StringVar()
        self.scope_entry = ttk.Entry(scope, textvariable=self.scopes)
        self.scope_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.scope_info = tk.StringVar(value="파일/폴더를 지정하세요. 전체 루트를 분석할 때만 . 을 입력합니다.")
        ttk.Label(self.settings, textvariable=self.scope_info, wraplength=1400).pack(fill="x")
        exclude = ttk.Frame(self.settings)
        exclude.pack(fill="x")
        ttk.Label(exclude, text="제외 경로").pack(side="left")
        self.exclusions = tk.StringVar(value=".git;.venv;build;wheelhouse")
        self.exclude_entry = ttk.Entry(exclude, textvariable=self.exclusions)
        self.exclude_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.goal = tk.StringVar(value="최초 목표: 왼쪽에서 함수와 분기를 선택하세요.")
        self.goal_label = ttk.Label(self, textvariable=self.goal, font=("맑은 고딕", 11, "bold"), wraplength=1400)
        self.goal_label.pack(fill="x", pady=(6, 2))
        self.context = tk.StringVar(value="조사 이유: 목표 분기를 선택하고 시작하세요.")
        self.current_summary = tk.StringVar(value="다음: 분기 선택 → 새 조사 시작 → 조사할 변수 선택")
        self.current_label = ttk.Label(self, textvariable=self.current_summary, wraplength=1400)
        self.current_label.pack(fill="x", pady=(0, 4))
        pane = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True)
        left, middle, right = (ttk.Frame(pane, padding=4, width=width) for width in (240, 570, 650))
        pane.add(left, weight=1)
        pane.add(middle, weight=4)
        pane.add(right, weight=4)
        ttk.Label(left, text="1. 함수와 목표 분기 찾기", font=("맑은 고딕", 10, "bold")).pack(anchor="w")
        search = ttk.Frame(left)
        search.pack(fill="x", pady=4)
        self.query = tk.StringVar()
        entry = ttk.Entry(search, textvariable=self.query, width=16)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda event: self.run_action(self.search_functions))
        self.button(search, "검색", self.search_functions).pack(side="left")
        navigation = ttk.Frame(left)
        navigation.pack(fill="x")
        self.button(navigation, "이전", lambda: self.change_page(-100)).pack(side="left")
        self.button(navigation, "다음", lambda: self.change_page(100)).pack(side="left")
        self.search_summary = tk.StringVar(value="함수 이름을 검색하세요.")
        search_label = ttk.Label(left, textvariable=self.search_summary, wraplength=240)
        search_label.pack(fill="x")
        left.bind("<Configure>", lambda e: search_label.configure(wraplength=max(160, e.width - 10)))
        self.functions = _tree(left, ("함수", "파일:행"), 4)
        self.functions.column("함수", width=130)
        self.functions.column("파일:행", width=120)
        self.functions.bind("<<TreeviewSelect>>", self.browse_function)
        ttk.Label(left, text="목표 분기").pack(anchor="w", pady=(6, 0))
        self.branches = _tree(left, ("분기", "조건 / 행"), 4)
        self.branches.column("분기", width=65)
        self.branches.column("조건 / 행", width=190)
        self.branches.bind("<<TreeviewSelect>>", self.preview_branch)
        self.button(left, "선택 분기로 새 조사 시작", self.start).pack(fill="x", pady=4)

        value_controls = ttk.LabelFrame(middle, text="2. 이 분기에서 어떤 값을 준비할까요?", padding=4)
        value_controls.pack(fill="x", pady=(0, 4))
        self.input_help = tk.StringVar(value="분기를 통과하려는 변수와 원하는 값을 고르세요. 예: pedal → 60")
        self.input_hint = ttk.Label(value_controls, textvariable=self.input_help, wraplength=500)
        self.input_hint.pack(fill="x")
        variable_row = ttk.Frame(value_controls)
        variable_row.pack(fill="x", pady=3)
        ttk.Label(variable_row, text="추적할 변수").pack(side="left")
        self.variable = tk.StringVar()
        self.variable_entry = ttk.Combobox(variable_row, textvariable=self.variable, width=16)
        self.variable_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.variable_entry.bind("<<ComboboxSelected>>", lambda e: self.run_action(self.choose_branch_input))
        self.variable_entry.bind("<KeyRelease>", lambda e: self.update_input_controls())
        self.variable_entry.bind("<Return>", lambda e: self.run_action(self.inspect_variable))
        self.goal_controls = ttk.Frame(value_controls)
        self.goal_controls.pack(fill="x", pady=3)
        ttk.Label(self.goal_controls, text="원하는 값").pack(side="left")
        self.target_value = tk.StringVar()
        self.target_entry = ttk.Entry(self.goal_controls, textvariable=self.target_value, width=10)
        self.target_entry.pack(side="left", padx=4)
        self.goal_button = self.button(self.goal_controls, "변수 목표 설정", self.set_variable_goal)
        self.goal_button.pack(side="left")
        actions = ttk.Frame(value_controls)
        actions.pack(fill="x")
        self.inspect_button = self.button(actions, "현재 변수 조사", self.inspect_variable)
        self.inspect_button.pack(side="left", padx=(0, 4))
        self.button(actions, "선택 라인 기록", self.record_location).pack(side="left")
        self.source_label = tk.StringVar(value="현재 소스 — 읽기 전용")
        source_label = ttk.Label(middle, textvariable=self.source_label, wraplength=500)
        source_label.pack(fill="x")
        middle.bind("<Configure>", lambda e: (source_label.configure(wraplength=max(160, e.width - 10)),
                                              self.input_hint.configure(wraplength=max(160, e.width - 20))))
        notebook = self.source_notebook = ttk.Notebook(middle)
        notebook.pack(fill="both", expand=True)
        source_tab, diagnostics_tab = ttk.Frame(notebook), ttk.Frame(notebook)
        notebook.add(source_tab, text="현재 소스")
        notebook.add(diagnostics_tab, text="분석 진단")
        self.source = _text(source_tab)
        self.source.tag_configure("location", background="#fff0b3", foreground="#111111")
        self.source.tag_configure("tracked_value", background="#cce8ff", foreground="#003b66")
        self.source.bind("<ButtonRelease-1>", self.capture_source_selection)
        self.source.bind("<Double-Button-1>", self.select_source_identifier)
        self.diagnostics = _text(diagnostics_tab)

        self.candidate_context = tk.StringVar(value="3. 조사할 값을 고르면 출처 후보가 표시됩니다.")
        candidate_header = ttk.Label(right, textvariable=self.candidate_context, wraplength=600,
                                     font=("맑은 고딕", 10, "bold"))
        candidate_header.pack(fill="x")
        right_pane = ttk.Panedwindow(right, orient="vertical")
        right_pane.pack(fill="both", expand=True)
        candidate_area, preview_area, history_area = (ttk.Frame(right_pane) for _ in range(3))
        for frame, weight in ((candidate_area, 2), (preview_area, 3), (history_area, 2)):
            right_pane.add(frame, weight=weight)
        candidates = self.candidates_notebook = ttk.Notebook(candidate_area)
        candidates.pack(fill="both", expand=True)
        call_tab, rte_tab, value_tab, condition_tab = (ttk.Frame(candidates) for _ in range(4))
        candidates.add(call_tab, text="함수 호출")
        candidates.add(rte_tab, text="RTE 공급자")
        candidates.add(value_tab, text="값 출처")
        candidates.add(condition_tab, text="실행 조건")
        self.calls = _tree(call_tab, ("호출", "대상 / 위치", "조사 연결"), 3)
        self.rte = _tree(rte_tab, ("데이터", "공급자 / 위치", "조사 연결"), 3)
        self.values = _tree(value_tab, ("값 출처", "대상 / 위치", "조사 연결"), 3)
        self.requirements = _tree(condition_tab, ("필요 조건 / 조사 변수", "대상 / 위치", "조사 연결"), 3)
        self.candidate_tables = (self.calls, self.rte, self.values, self.requirements)
        self.candidate_map = {}
        for table in self.candidate_tables:
            table.column(table["columns"][0], width=200)
            table.column(table["columns"][1], width=170)
            table.column(table["columns"][2], width=160)
            table.bind("<<TreeviewSelect>>", lambda e, table=table: self.preview_candidate(table))
        self.button(call_tab, "호출 후보 조사", lambda: self.follow(self.calls)).pack(fill="x")
        self.button(rte_tab, "RTE 공급자 후보 조사", lambda: self.follow(self.rte)).pack(fill="x")
        self.button(value_tab, "선택 출처 조사", lambda: self.follow(self.values)).pack(fill="x")
        self.button(condition_tab, "조건 변수 하위 조사", lambda: self.follow(self.requirements)).pack(fill="x")
        self.preview_tab = ttk.LabelFrame(preview_area, text="이동 전 비교 — 후보 / 이력 코드", padding=3)
        self.preview_tab.pack(fill="both", expand=True, pady=3)
        self.preview_label = tk.StringVar(value="행을 선택해 코드를 비교하세요. 현재 소스와 조사 위치는 유지됩니다.")
        preview_label = ttk.Label(self.preview_tab, textvariable=self.preview_label, wraplength=600)
        preview_label.pack(fill="x")
        self.candidate_source = _text(self.preview_tab, 5)
        self.candidate_source.tag_configure("location", background="#fff0b3", foreground="#111111")
        self.inspection_notebook = ttk.Notebook(history_area)
        self.inspection_notebook.pack(fill="both", expand=True)
        history_tab, detail_tab, context_tab = (ttk.Frame(self.inspection_notebook) for _ in range(3))
        self.inspection_notebook.add(history_tab, text="조사 이력")
        self.inspection_notebook.add(detail_tab, text="근거 상세")
        self.inspection_notebook.add(context_tab, text="조사 정보")
        self.detail = _text(detail_tab, 4)
        self.trace_details = _text(context_tab, 4)
        self.history = _tree(history_tab, ("현재 / 관계", "함수", "선택 위치", "조사 이유", "조사 변수"), 3)
        for column, width in zip(self.history["columns"], (100, 140, 115, 190, 100)):
            self.history.column(column, width=width)
        self.history.bind("<<TreeviewSelect>>", self.preview_history)
        self.button(history_tab, "선택한 이력 단계로 이동", self.select_history).pack(fill="x", pady=2)
        right.bind("<Configure>", lambda e: (candidate_header.configure(wraplength=max(180, e.width - 10)),
                                             preview_label.configure(wraplength=max(180, e.width - 20))))
        root.bind("<Configure>", lambda e: self.resize_summary(e))
        if self.workbench.project is not None:
            self.settings.pack_forget()
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

    def resize_summary(self, event: tk.Event) -> None:
        if event.widget == self.root:
            for label in (self.goal_label, self.current_label):
                label.configure(wraplength=max(400, event.width - 24))

    def toggle_settings(self) -> None:
        """Keep paths and budgets out of the normal investigation workspace."""
        if self.settings.winfo_manager():
            self.settings.pack_forget()
        else:
            self.settings.pack(fill="x", before=self.goal_label)

    def offer_branch_inputs(self, branch_id: str, preferred: str | None = None) -> None:
        self.variable_inputs = {item.expression: item for item in self.workbench.branch_inputs(branch_id)}
        self.variable_entry.configure(values=tuple(self.variable_inputs))
        if preferred is not None:
            self.variable.set(preferred)
        elif len(self.variable_inputs) == 1:
            self.variable.set(next(iter(self.variable_inputs)))
        else:
            self.variable.set("")
        self.update_input_controls()

    def update_input_controls(self) -> None:
        objective = self.workbench.session.variable_goal if self.workbench.manager else None
        selected = self.variable_inputs.get(self.variable.get())
        supported = selected.supported if selected else parse_access_path(self.variable.get()) is not None
        if objective:
            self.goal_controls.pack_forget()
            help_text = f"최초 목표는 {objective.variable} → {objective.target_value}로 고정됩니다. 다른 값은 현재 변수 조사로 선택하세요."
        else:
            self.goal_controls.pack(fill="x", pady=3, before=self.inspect_button.master)
            help_text = ("조건에 값이 여러 개 있습니다. 추적할 변수를 선택하고 원하는 값을 입력하세요."
                         if len(self.variable_inputs) > 1 else
                         "선택한 분기를 통과하려는 변수와 원하는 값을 지정하세요. 예: pedal → 60")
        if not supported and self.variable.get():
            help_text = f"{self.variable.get()}: 배열 인덱스·복합 포인터 연산은 아직 추적하지 않습니다. 경로를 단순 이름으로 축약하지 않습니다."
        access = parse_access_path(self.variable.get())
        if access is not None and access.indirect:
            help_text += " 포인터 대상은 별칭·호출 근거로 확인할 후보입니다."
        self.input_help.set(help_text)
        self.goal_button.state(["!disabled"] if supported and not self.busy else ["disabled"])
        self.inspect_button.state(["!disabled"] if supported and not self.busy and self.workbench.manager else ["disabled"])

    def choose_branch_input(self) -> None:
        """Selecting a variable previews its own use site; it never changes a trace."""
        item = self.variable_inputs.get(self.variable.get())
        if item is not None:
            self.show_source(item.location)
        self.update_input_controls()

    def choose_project(self) -> None:
        directory = filedialog.askdirectory(parent=self.root, title="C/H 소스 폴더 선택")
        if directory:
            self.project_root.set(directory)
            if not self.settings.winfo_manager():
                self.toggle_settings()
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
            self.settings.pack_forget()
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
            self.update_input_controls()

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
        if self.source_focus_id is not None:
            self.root.after_cancel(self.source_focus_id)
            self.source_focus_id = None
        self.source_notebook.select(0)
        project = self.workbench.project
        data = next((data for path, data in project.sources if path == location.path), None) if project else None
        self.picked_location = location if data is not None else None
        self.source_label.set(f"현재 소스 · {location.path.name}:{location.start_line} · 읽기 전용")
        if data is None:
            _set_text(self.source, "이 위치의 분석 소스가 없습니다. 해당 소스 폴더를 분석하세요.\n"
                      "복원한 위치는 저장 시점의 메타데이터입니다.")
            return
        _set_text(self.source, "\n".join(f"{index:5}  {line}" for index, line in
                                        enumerate(data.decode("utf-8", errors="replace").splitlines(), 1)))
        self.source.tag_remove("location", "1.0", "end")
        self.source.tag_add("location", f"{location.start_line}.0", f"{location.start_line}.end")
        tracked = project.value_resolver.access_at(location)
        if tracked and tracked.supported and tracked.location.start_line == tracked.location.end_line:
            site = tracked.location
            line = data.splitlines()[site.start_line - 1]
            first = 7 + len(line[:site.start_column - 1].decode("utf-8", errors="replace"))
            last = 7 + len(line[:site.end_column - 1].decode("utf-8", errors="replace"))
            self.source.tag_add("tracked_value", f"{site.start_line}.{first}", f"{site.end_line}.{last}")
        self.source.see(f"{location.start_line}.0")
        # Switching tabs and wrapping labels changes the viewport after this call.
        # Apply focus after layout, without overwriting a newer source selection.
        def focus_after_layout() -> None:
            self.source_focus_id = None
            if not self.closed and self.picked_location == location:
                self.source.yview(f"{max(1, location.start_line - 5)}.0")
                self.source.see(f"{location.start_line}.0")
        self.source_focus_id = self.root.after_idle(focus_after_layout)

    def select_source_identifier(self, event: tk.Event) -> str | None:
        """Select a whole syntax access path, including b.a and (*p).a."""
        index = self.source.index(f"@{event.x},{event.y}")
        self.source.tag_remove("sel", "1.0", "end")
        self.pick_source_position(index)
        if self.picked_location is None or self.workbench.project is None:
            return None
        item = self.workbench.project.value_resolver.access_at(self.picked_location)
        if item is None:
            return None
        self.show_source(item.location)
        data = dict(self.workbench.project.sources)[item.location.path].splitlines()
        start = item.location
        first = 7 + len(data[start.start_line - 1][:start.start_column - 1].decode("utf-8", errors="replace"))
        last = 7 + len(data[start.end_line - 1][:start.end_column - 1].decode("utf-8", errors="replace"))
        self.source.tag_add("sel", f"{start.start_line}.{first}", f"{start.end_line}.{last}")
        self.variable.set(item.expression)
        self.update_input_controls()
        return "break"

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
            access = parse_access_path(selected)
            syntax = self.workbench.project.value_resolver.access_at(self.picked_location)
            if syntax and syntax.supported and (access is not None or data[syntax.location.start_byte:syntax.location.end_byte].decode("utf-8", errors="replace") == selected):
                access = parse_access_path(syntax.expression)
            if access is not None:
                self.variable.set(access.expression)
                if self.source.compare(index, ">=", ranges[0]) and self.source.compare(index, "<", ranges[1]):
                    def position(text_index):
                        r, c = (int(value) for value in str(text_index).split("."))
                        byte_column = len(lines[r - 1].decode("utf-8", errors="replace")[:max(0, c - 7)].encode("utf-8"))
                        return r, byte_column + 1, sum(len(value) for value in lines[:r - 1]) + byte_column
                    start_row, start_col, start_byte = position(ranges[0])
                    end_row, end_col, end_byte = position(ranges[1])
                    self.picked_location = SourceRange(path, start_row, start_col, end_row, end_col, start_byte, end_byte)
                    if syntax and syntax.supported:
                        self.picked_location = syntax.location
                self.update_input_controls()
        self.source_label.set(f"선택 위치 (아직 미기록): {path.name}:{row}")
        self.source.tag_remove("location", "1.0", "end")
        self.source.tag_remove("tracked_value", "1.0", "end")
        self.source.tag_add("location", f"{row}.0", f"{row}.end")

    def selected_location(self) -> SourceRange:
        if self.picked_location is None:
            raise ValueError("현재 조사 함수의 소스에서 사용할 라인을 선택하세요.")
        return self.picked_location

    def set_variable_goal(self) -> None:
        if not self.target_value.get().strip():
            raise ValueError("선택한 변수에 준비하려는 값을 '원하는 값'에 입력하세요.")
        access = parse_access_path(self.variable.get())
        if access is None:
            raise ValueError("변수 또는 구조체 멤버 경로를 선택하세요. 배열·포인터 연산은 아직 해석하지 않습니다.")
        if self.workbench.manager is None:
            self.start()
            if self.workbench.manager is None:
                return
        self.workbench.set_variable_goal(access.expression, self.target_value.get().strip(),
                                         self.selected_location())
        self.refresh_trace()
        self.candidates_notebook.select(2)

    def inspect_variable(self) -> None:
        self.workbench.inspect_variable(self.variable.get().strip(), self.selected_location())
        self.refresh_trace()
        self.candidates_notebook.select(2)

    def record_location(self) -> None:
        self.workbench.record_location(self.selected_location())
        self.refresh_trace()

    def preview_branch(self, event: tk.Event | None = None) -> None:
        selected = self.branches.selection()
        if selected and self.workbench.project:
            branch = next(b for r in self.workbench.project.results for b in r.branches if b.id == selected[0])
            self.show_source(branch.location)
            self.offer_branch_inputs(branch.id)

    def discard_allowed(self) -> bool:
        return not self.workbench.dirty or messagebox.askyesno(
            "저장하지 않은 조사", "저장하지 않은 조사 변경을 버리고 계속할까요?", parent=self.root)

    def start(self) -> None:
        functions, branches = self.functions.selection(), self.branches.selection()
        if not functions or not branches:
            raise ValueError("함수와 목표 분기를 선택하세요.")
        variable, desired = self.variable.get(), self.target_value.get()
        reason = simpledialog.askstring("조사 시작", "이 목표 분기를 조사하는 이유", parent=self.root)
        if reason is not None and self.discard_allowed():
            self.workbench.start(functions[0], branches[0], reason)
            self.reanalyzed = False
            self.refresh_trace()
            if variable in self.variable_inputs:
                self.variable.set(variable)
                self.choose_branch_input()
            self.target_value.set(desired)

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
            self.update_input_controls()
            return
        target = manager.session.target_branch
        condition = target.condition or "(else)"
        compact_condition = condition[:100] + ("…" if len(condition) > 100 else "")
        self.goal.set(f"최초 목표: {manager.session.target_function.name} | {target.kind} {compact_condition}"
                      f" | {target.location.path.name}:{target.location.start_line}")
        objective = manager.session.variable_goal
        if objective:
            self.goal.set(self.goal.get() + f"\n변수 목표: {objective.variable} → {objective.target_value}"
                          f" | {objective.location.path.name}:{objective.location.start_line}")
        note = " [이전 조사 스냅샷 — 소스 변경 여부 미검증]" if self.workbench.restored or self.reanalyzed else ""
        probe = manager.current_step.probe
        value_context = f" | 현재 값 조사: {probe.expression} ({probe.kind})" if probe else ""
        if probe is None and "ct_accessibility_not_verified" in manager.current_step.uncertainty:
            value_context = " | CT 전역 후보에서 값 추적 중지"
            _set_text(self.detail, "CT 전역 제어 후보에 도달해 값 출처 추적을 멈췄습니다.\n"
                      "실제 CT 접근성과 설정할 값은 확인이 필요합니다.\n"
                      "필요한 실행 조건은 실행 조건 탭에서 조사할 수 있습니다.")
        self.context.set(f"현재: {manager.current_step.function.name} | 조사 이유: {manager.current_step.reason}{note}\n"
                         + "경로: " + " → ".join(step.function.name for step in manager.current_path) + value_context)
        requirements = [reason.split(": ", 1)[1] + (" → 참 필요" if reason.startswith("execution_requirement_true:") else " → 거짓 필요")
                        for reason in manager.current_step.uncertainty if reason.startswith(
                            ("execution_requirement_true: ", "execution_requirement_false: "))]
        if requirements:
            self.context.set(self.context.get() + "\n하위 조사 조건: " + " / ".join(requirements))
        if probe and probe.kind == "variable":
            self.variable.set(probe.expression)
        else:
            self.variable.set("")
        if objective:
            self.target_value.set(objective.target_value)
        else:
            self.target_value.set("")
        navigation = manager.current_step.relation in {"root", "call", "manual"}
        tracked = _probe_text(probe, "함수 관계" if navigation else "값 추적 종점")
        if probe is None and "ct_accessibility_not_verified" in manager.current_step.uncertainty:
            tracked = "CT 전역 후보에서 값 추적 중지"
        self.current_summary.set(f"지금 조사: {manager.current_step.function.name} :: {tracked}"
                                 + f" | {manager.current_step.reason[:70]}"
                                 + ("…" if len(manager.current_step.reason) > 70 else "")
                                 + (f" | 하위 조건 {len(requirements)}개 (조사 정보)" if requirements else ""))
        if self.workbench.restored or self.reanalyzed:
            self.current_summary.set(self.current_summary.get() + " | 복원·재분석 소스 미검증")
        self.candidate_context.set(f"출처를 찾는 값: {manager.current_step.function.name} :: {tracked}"
                                   if probe else "변수를 선택하면 그 값의 출처를 볼 수 있습니다." if navigation else
                                   "값 출처 추적 중지 · 필요한 실행 조건은 별도로 조사할 수 있습니다.")
        if "ct_accessibility_not_verified" in manager.current_step.uncertainty and probe is None:
            self.candidate_context.set("CT 전역 후보 도달 · 실제 CT 접근성과 설정할 값은 확인이 필요합니다.")
            if "pointer_value_not_pointee_control" in manager.current_step.uncertainty:
                self.candidate_context.set("포인터 변수 값의 CT 후보 · 가리키는 객체/멤버의 직접 제어를 뜻하지 않습니다.")
            elif "object_origin_not_member_value" in manager.current_step.uncertainty:
                self.candidate_context.set("객체 자체의 CT 후보 · 멤버 배치·접근성과 준비할 값은 별도 확인이 필요합니다.")
        _set_text(self.trace_details, f"최초 분기: {condition}\n{target.location.path}:{target.location.start_line}\n"
                  + self.goal.get() + "\n\n" + self.context.get())
        if (manager.current_step.function.id == target.function_id and self.workbench.project is not None
                and self.workbench.project.functions_by_id.get(manager.current_step.function.id) == manager.current_step.function):
            self.offer_branch_inputs(target.id, probe.expression if probe and probe.kind == "variable" else None)
        else:
            self.variable_inputs = {}
            self.variable_entry.configure(values=(probe.expression,) if probe and probe.kind == "variable" else ())
            self.update_input_controls()
        active = (manager.session.id, manager.current_step.id, probe)
        if active != getattr(self, "candidate_focus", None):
            self.candidates_notebook.select(2 if probe else 0)
        self.candidate_focus = active
        for index, candidate in enumerate((*self.workbench.candidates(), *self.workbench.value_candidates(),
                                           *self.workbench.execution_candidates())):
            key = str(index)
            self.candidate_map[key] = candidate
            table = (self.requirements if candidate.value_kind == "execution_condition" else
                     self.values if candidate.value_kind else
                     self.calls if candidate.relation == "call" else self.rte)
            destination = candidate.function
            site = candidate.selected_location or (destination.location if destination else candidate.evidence)
            label = (f"{site.start_line}행 · {site.path.name} — {destination.name}"
                     if destination else "현재 분석 범위에서 미확인 — 이동 불가")
            candidate_label = candidate.label
            if candidate.value_kind in _VALUE_LABELS:
                candidate_label = _VALUE_LABELS[candidate.value_kind] + ": " + candidate.label.split(": ", 1)[1]
            connection = self.candidate_connection(candidate)
            table.insert("", "end", iid=key, values=(candidate_label, label, connection))
        paths, child_counts = {}, {}
        for step in manager.session.steps:
            marker = "▶ " if step.id == manager.session.current_step_id else ""
            child_counts[step.parent_id] = child_counts.get(step.parent_id, 0) + 1
            paths[step.id] = (paths[step.parent_id] + "." if step.parent_id else "") + str(child_counts[step.parent_id])
            site = step.selected_location
            label = f"{site.start_line}행 · {site.path.name}" if site else "미기록 (이전 세션)"
            subject = _probe_text(step.probe, "함수 조사" if step.relation in {"root", "call", "manual"} else "값 추적 종점")
            if step.probe is None and "ct_accessibility_not_verified" in step.uncertainty and step.parent_id:
                parent = next(s for s in manager.session.steps if s.id == step.parent_id)
                subject = (parent.probe.expression if parent.probe else "전역") + " (CT 후보)"
            self.history.insert("", "end", iid=step.id,
                                values=(marker + paths[step.id] + " · " + step.relation, step.function.name, label, step.reason, subject))
        self.history.configure(displaycolumns=("현재 / 관계", "조사 변수", "함수", "선택 위치", "조사 이유"))
        current = manager.current_step.function
        self.render_function_page(self.page_offset)
        if self.functions.exists(current.id):
            self.functions.selection_set(current.id)
            self.functions.see(current.id)
            self.browse_function()
        self.show_source(manager.current_step.selected_location or current.location)
        self.source_notebook.select(0)
        if self.history_focus_id is not None:
            self.root.after_cancel(self.history_focus_id)
        step_id = manager.session.current_step_id

        def focus_history_after_layout() -> None:
            self.history_focus_id = None
            if (not self.closed and self.workbench.manager is manager
                    and manager.session.current_step_id == step_id):
                self.history.see(step_id)
        self.history_focus_id = self.root.after_idle(focus_history_after_layout)

    def candidate_connection(self, candidate: InvestigationCandidate) -> str:
        """Name the tracked value separately from general call/RTE navigation."""
        if candidate.value_kind is None:
            return "함수 호출 (값 연결 미확정)" if candidate.relation == "call" else "RTE 데이터 후보"
        probe = self.workbench.manager.current_step.probe
        origin = _probe_text(probe, "선택 위치")
        destination = candidate.probe
        target = _probe_text(destination)
        return f"{origin} → {target}"

    def preview_candidate(self, table: ttk.Treeview) -> None:
        selected = table.selection()
        candidate = self.candidate_map.get(selected[0]) if selected else None
        if candidate:
            guards = self.workbench.project.value_resolver.conditions(candidate.evidence) if self.workbench.project else ()
            conditions = "\n".join(f"{'참' if guard.required_truth else '거짓'} 필요: {guard.expression}"
                                   for guard in guards)
            _set_text(self.detail, f"조사 연결: {self.candidate_connection(candidate)}\n{candidate.relation}: {candidate.label}\n"
                      f"근거: {candidate.evidence.path}:{candidate.evidence.start_line}\n"
                      + ("이 지점의 구조상 실행 조건 (도달 미증명):\n" + conditions + "\n" if conditions else "")
                      + "확정되지 않은 후보 / 검토 사항:\n" + "\n".join(candidate.uncertainty))
            location = candidate.selected_location or (candidate.function.location if candidate.function else candidate.evidence)
            self.show_preview(candidate.function, location, "후보 값 연결: " + self.candidate_connection(candidate))

    def show_preview(self, function: FunctionDefinition | None, location: SourceRange, heading: str) -> None:
        """Display bounded snapshot code without changing the active selection or session."""
        project = self.workbench.project
        name = function.name if function else "대상 함수 미확인"
        self.preview_label.set(f"{heading} | {name}\n{location.path.name}:{location.start_line}")
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
        subject = _probe_text(step.probe, "종점 / 함수 조사")
        _set_text(self.detail, f"조사 대상: {step.function.name} :: {subject}\n{step.reason}\n"
                  + (f"선택 위치: {site.path}:{site.start_line}\n" if site else "선택 위치: 미기록\n")
                  + (f"이동 근거: {evidence.path}:{evidence.start_line}\n" if evidence else "")
                  + "\n".join(step.uncertainty))
        self.show_preview(step.function, site or step.function.location, "이력 코드 — 이동은 별도 버튼")

    def follow(self, table: ttk.Treeview) -> None:
        selected = table.selection()
        candidate = self.candidate_map.get(selected[0]) if selected else None
        if candidate is None or candidate.function is None:
            raise ValueError("대상 함수가 있는 후보를 선택하세요.")
        reason = simpledialog.askstring("조사 이동", f"{self.candidate_connection(candidate)}\n"
                                       f"{candidate.function.name}: {candidate.label}\n이 후보를 조사하는 이유", parent=self.root)
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
            if self.source_focus_id is not None:
                self.root.after_cancel(self.source_focus_id)
                self.source_focus_id = None
            if self.history_focus_id is not None:
                self.root.after_cancel(self.history_focus_id)
                self.history_focus_id = None
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.root.destroy()


def main() -> None:
    """Launch the offline desktop frontend; imports alone do not create windows."""
    root = tk.Tk()
    Navigator(root)
    root.mainloop()
