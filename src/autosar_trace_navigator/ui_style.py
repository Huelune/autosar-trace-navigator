"""Local Tk appearance; configured only when a window is explicitly created."""

import tkinter as tk
from tkinter import font, ttk


def configure_workspace(root: tk.Tk) -> None:
    """Apply a readable light workspace using fonts and themes shipped with Tk."""
    style = ttk.Style(root)
    style.theme_use("clam")
    font.nametofont("TkDefaultFont", root=root).configure(family="맑은 고딕", size=10)
    style.configure(".", background="#f3f6fa", foreground="#23334d")
    style.configure("TButton", padding=(9, 5), background="#ffffff", bordercolor="#d3dce8")
    style.map("TButton", foreground=[("disabled", "#7b8798")],
              background=[("active", "#e8eef7"), ("disabled", "#edf1f6")])
    style.configure("Accent.TButton", background="#245dcc", foreground="white", bordercolor="#245dcc")
    style.map("Accent.TButton", background=[("disabled", "#e0e7f0"), ("active", "#194ba9")],
              foreground=[("disabled", "#7b8798"), ("!disabled", "white")])
    style.configure("TEntry", padding=4, fieldbackground="white")
    style.configure("TCombobox", padding=4, fieldbackground="white")
    style.configure("Treeview", background="white", fieldbackground="white", rowheight=29,
                    font=("맑은 고딕", 10), bordercolor="#d3dce8")
    style.configure("Treeview.Heading", background="#eaf0f8", padding=(6, 5), font=("맑은 고딕", 9, "bold"))
    style.map("Treeview", background=[("selected", "#dceaff")], foreground=[("selected", "#123c7e")])
    style.configure("TNotebook", borderwidth=0)
    style.configure("TNotebook.Tab", padding=(8, 5))
    style.map("TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", "#194ba9")])
    style.configure("TLabelframe", bordercolor="#d3dce8")
    style.configure("TLabelframe.Label", font=("맑은 고딕", 10, "bold"))
    style.configure("Title.TLabel", font=("맑은 고딕", 14, "bold"))
    style.configure("Muted.TLabel", foreground="#52647d")
    style.configure("Goal.TFrame", background="#e8f0ff")
    style.configure("Goal.TLabel", background="#e8f0ff", foreground="#153d78", font=("맑은 고딕", 11, "bold"))
    style.configure("Current.TLabel", background="#e8f0ff", foreground="#324b70")
    style.configure("Hint.TLabel", foreground="#194ba9", font=("맑은 고딕", 10, "bold"))
