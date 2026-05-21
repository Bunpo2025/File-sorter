"""
File Sorter - ファイル名キーワードによる自動振り分けアプリ
標準ライブラリのみ使用（追加インストール不要）
"""

import json
import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def _app_base_dir() -> str:
    """設定ファイルの保存先となるベースディレクトリを返す。

    PyInstaller の --onefile で起動した場合、__file__ は一時展開フォルダを
    指してしまい次回起動時には消えるため、exe と同じ場所を使うように
    sys.executable を基準にする。通常の python 実行時はソースと同じ
    フォルダを使う。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


RULES_FILE = os.path.join(_app_base_dir(), "rules.json")

# マッチタイプ定数
TYPE_KEYWORD        = "keyword"
TYPE_PREFIX         = "prefix_folder"
TYPE_SUFFIX_EXCLUDE = "suffix_exclude_folder"

# カラーパレット
C_BG       = "#1e1e2e"
C_SURFACE  = "#2a2a3e"
C_SURFACE2 = "#313148"
C_ACCENT   = "#7c6af7"
C_ACCENT_DARK = "#5b4dd4"
C_SUCCESS  = "#3dba6c"
C_DANGER   = "#e05252"
C_TEXT     = "#e8e8f8"
C_TEXT_MUTED = "#b0b0cc"
C_BORDER   = "#555578"


# ---------------------------------------------------------------------------
# データ管理
# ---------------------------------------------------------------------------

def load_config() -> tuple[str, list]:
    """(振り分け先, ルール一覧) を返す。旧形式の rules.json にも対応。"""
    if os.path.exists(RULES_FILE):
        try:
            with open(RULES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data.get("destination", ""), data.get("rules", [])
            if isinstance(data, list):
                dest = data[0].get("destination", "") if data else ""
                rules = [
                    {k: v for k, v in r.items() if k != "destination"}
                    for r in data
                ]
                return dest, rules
        except (json.JSONDecodeError, OSError):
            pass
    return "", []


def save_config(destination: str, rules: list) -> None:
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump({"destination": destination, "rules": rules},
                  f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# マッチング共通ロジック
# ---------------------------------------------------------------------------

def resolve_destination(rule: dict, fname: str, destination_root: str) -> str | None:
    """
    ルールとファイル名からコピー先フォルダパスを返す。
    マッチしない場合は None を返す。
    """
    if not destination_root:
        return None

    match_type = rule.get("match_type", TYPE_KEYWORD)

    if match_type == TYPE_KEYWORD:
        kw = rule.get("keyword", "")
        target = fname if rule.get("case_sensitive") else fname.lower()
        needle = kw if rule.get("case_sensitive") else kw.lower()
        if needle and needle in target:
            return destination_root

    elif match_type == TYPE_PREFIX:
        n = rule.get("prefix_length", 6)
        # 拡張子を除いたファイル名の先頭 N 文字で照合
        stem = os.path.splitext(fname)[0]
        if len(stem) < n:
            return None
        prefix = stem[:n]
        if not rule.get("case_sensitive"):
            prefix = prefix.lower()
        return os.path.join(destination_root, prefix)

    elif match_type == TYPE_SUFFIX_EXCLUDE:
        n = rule.get("suffix_exclude_length", 6)
        # 拡張子を除いたファイル名の末尾 N 文字を除外して照合
        stem = os.path.splitext(fname)[0]
        if len(stem) <= n:
            return None
        folder_name = stem[:-n]
        if not rule.get("case_sensitive"):
            folder_name = folder_name.lower()
        return os.path.join(destination_root, folder_name)

    return None


# ---------------------------------------------------------------------------
# スタイル設定
# ---------------------------------------------------------------------------

def apply_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=C_BG, foreground=C_TEXT, borderwidth=0)
    style.configure("TFrame", background=C_BG)

    style.configure(
        "Treeview",
        background=C_SURFACE,
        foreground=C_TEXT,
        fieldbackground=C_SURFACE,
        rowheight=30,
        borderwidth=0,
        font=("", 10),
    )
    style.configure(
        "Treeview.Heading",
        background=C_SURFACE2,
        foreground=C_TEXT,
        relief="flat",
        font=("", 10, "bold"),
        padding=(8, 6),
    )
    style.map("Treeview",
              background=[("selected", C_ACCENT)],
              foreground=[("selected", "#ffffff")])
    style.map("Treeview.Heading", background=[("active", C_BORDER)])
    style.configure("TScrollbar", background=C_SURFACE2, troughcolor=C_SURFACE,
                    arrowcolor=C_TEXT_MUTED, borderwidth=0, width=14)
    style.map("TScrollbar", background=[("active", C_BORDER)])


def styled_entry(parent, var, **kw) -> tk.Entry:
    """視認性の高い入力欄を作成する。"""
    return tk.Entry(
        parent, textvariable=var, bg=C_SURFACE2, fg=C_TEXT,
        insertbackground=C_TEXT, relief="flat", font=("", 11),
        highlightbackground=C_BORDER, highlightcolor=C_ACCENT,
        highlightthickness=1, bd=6, **kw,
    )


# ---------------------------------------------------------------------------
# カスタムボタン
# ---------------------------------------------------------------------------

class FlatButton(tk.Button):
    def __init__(self, master, text="", command=None, bg=None, fg=C_TEXT,
                 hover_bg=None, **kwargs):
        self._bg    = bg or C_ACCENT
        self._hover = hover_bg or C_ACCENT_DARK
        super().__init__(master, text=text, command=command,
                         bg=self._bg, fg=fg,
                         activebackground=self._hover, activeforeground=fg,
                         relief="flat", bd=0, cursor="hand2",
                         padx=12, pady=6, **kwargs)
        self.bind("<Enter>", lambda _: self.config(bg=self._hover))
        self.bind("<Leave>", lambda _: self.config(bg=self._bg))


# ---------------------------------------------------------------------------
# ルール編集ダイアログ
# ---------------------------------------------------------------------------

class RuleDialog(tk.Toplevel):
    def __init__(self, parent, rule: dict | None = None):
        super().__init__(parent)
        self.configure(bg=C_BG)
        self.title("ルールを編集" if rule else "ルールを追加")
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        rule = rule or {}
        self._match_type = tk.StringVar(
            value=rule.get("match_type", TYPE_KEYWORD)
        )

        self._build(rule)
        self._on_type_change()
        self._fit_to_content(parent)

    def _fit_to_content(self, parent) -> None:
        """内容に合わせてダイアログサイズを調整し、親ウィンドウ中央付近に表示。"""
        self.update_idletasks()
        width = max(600, self.winfo_reqwidth() + 8)
        height = self.winfo_reqheight() + 12
        px = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
        py = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
        self.geometry(f"{width}x{height}+{px}+{py}")
        self.minsize(width, height)

    # --- UI構築 ---

    def _section(self, parent, title: str, row: int) -> tk.Frame:
        """見出し付きセクションコンテナを返す。"""
        hdr = tk.Label(
            parent, text=title, bg=C_BG, fg=C_TEXT,
            font=("", 11, "bold"), anchor="w",
        )
        hdr.grid(row=row, column=0, columnspan=3, sticky="w",
                 padx=18, pady=(14, 6))

        frame = tk.Frame(parent, bg=C_SURFACE, highlightbackground=C_BORDER,
                         highlightthickness=1, padx=14, pady=12)
        frame.grid(row=row + 1, column=0, columnspan=3, sticky="ew",
                   padx=16, pady=(0, 4))
        frame.columnconfigure(1, weight=1)
        return frame

    def _build(self, rule: dict):
        # ── マッチ方式 ────────────────────────────────────
        type_frame = self._section(self, "マッチ方式", row=0)

        options = (
            (TYPE_KEYWORD,        "キーワード部分一致",
             "ファイル名に指定した文字列が含まれる場合に振り分け"),
            (TYPE_PREFIX,         "先頭N文字",
             "拡張子を除いたファイル名の先頭N文字でサブフォルダを作成"),
            (TYPE_SUFFIX_EXCLUDE, "末尾N文字除外",
             "拡張子を除いたファイル名の末尾N文字を除いた部分でサブフォルダを作成"),
        )
        for i, (val, label, desc) in enumerate(options):
            row = tk.Frame(type_frame, bg=C_SURFACE)
            row.grid(row=i, column=0, columnspan=3, sticky="ew", pady=3)
            tk.Radiobutton(
                row, text=label, variable=self._match_type, value=val,
                bg=C_SURFACE, fg=C_TEXT, selectcolor=C_ACCENT,
                activebackground=C_SURFACE, activeforeground=C_TEXT,
                font=("", 11, "bold"), command=self._on_type_change,
            ).pack(anchor="w")
            tk.Label(
                row, text=desc, bg=C_SURFACE, fg=C_TEXT_MUTED,
                font=("", 10), anchor="w", wraplength=480, justify="left",
            ).pack(anchor="w", padx=(22, 0))

        # ── 条件設定 ──────────────────────────────────────
        self._cond_frame = self._section(self, "条件設定", row=2)

        # キーワード行
        self._kw_row = tk.Frame(self._cond_frame, bg=C_SURFACE)
        self._kw_row.grid(row=0, column=0, columnspan=3, sticky="ew")
        self._kw_row.columnconfigure(1, weight=1)
        tk.Label(self._kw_row, text="キーワード", bg=C_SURFACE, fg=C_TEXT,
                 font=("", 11)).grid(row=0, column=0, sticky="w",
                                      padx=(0, 12), pady=4)
        self._keyword_var = tk.StringVar(value=rule.get("keyword", ""))
        self._kw_entry = self._entry(self._kw_row, self._keyword_var)
        self._kw_entry.grid(row=0, column=1, sticky="ew", pady=4)
        tk.Label(self._kw_row, text="部分一致で判定します",
                 bg=C_SURFACE, fg=C_TEXT_MUTED, font=("", 10)
                 ).grid(row=1, column=1, sticky="w", pady=(0, 2))

        # 先頭文字数行
        self._pfx_row = tk.Frame(self._cond_frame, bg=C_SURFACE)
        self._pfx_row.grid(row=1, column=0, columnspan=3, sticky="ew")
        tk.Label(self._pfx_row, text="先頭の文字数", bg=C_SURFACE, fg=C_TEXT,
                 font=("", 11)).grid(row=0, column=0, sticky="w",
                                      padx=(0, 12), pady=4)
        self._prefix_var = tk.IntVar(value=rule.get("prefix_length", 6))
        self._pfx_spin = self._spinbox(self._pfx_row, self._prefix_var)
        self._pfx_spin.grid(row=0, column=1, sticky="w", pady=4)
        tk.Label(self._pfx_row, text="例: 「ABC123_sample.jpg」→ 先頭6文字「ABC123」",
                 bg=C_SURFACE, fg=C_TEXT_MUTED, font=("", 10)
                 ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 2))

        # 末尾除外文字数行
        self._sfx_row = tk.Frame(self._cond_frame, bg=C_SURFACE)
        self._sfx_row.grid(row=2, column=0, columnspan=3, sticky="ew")
        tk.Label(self._sfx_row, text="除外する末尾文字数", bg=C_SURFACE, fg=C_TEXT,
                 font=("", 11)).grid(row=0, column=0, sticky="w",
                                      padx=(0, 12), pady=4)
        self._suffix_var = tk.IntVar(value=rule.get("suffix_exclude_length", 6))
        self._sfx_spin = self._spinbox(self._sfx_row, self._suffix_var)
        self._sfx_spin.grid(row=0, column=1, sticky="w", pady=4)
        tk.Label(self._sfx_row, text="例: 「document_001.pdf」→ 末尾4文字除外「document」",
                 bg=C_SURFACE, fg=C_TEXT_MUTED, font=("", 10)
                 ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 2))

        # ── オプション ────────────────────────────────────
        opt_frame = tk.Frame(self, bg=C_BG)
        opt_frame.grid(row=4, column=0, columnspan=3, sticky="w",
                       padx=18, pady=(12, 0))
        self._case_var = tk.BooleanVar(value=rule.get("case_sensitive", False))
        self._case_ck = tk.Checkbutton(
            opt_frame, text="大文字・小文字を区別する",
            variable=self._case_var,
            bg=C_BG, fg=C_TEXT, selectcolor=C_ACCENT,
            activebackground=C_BG, activeforeground=C_TEXT, font=("", 11),
        )
        self._case_ck.pack(anchor="w")

        # ── ボタン ────────────────────────────────────────
        btn_row = tk.Frame(self, bg=C_BG)
        btn_row.grid(row=5, column=0, columnspan=3, pady=(16, 24), padx=16)
        FlatButton(btn_row, text="キャンセル", command=self.destroy,
                   bg=C_SURFACE2, hover_bg=C_BORDER, font=("", 11)).pack(
            side="left", padx=8)
        FlatButton(btn_row, text="  保 存  ", command=self._save,
                   font=("", 11, "bold")).pack(side="left", padx=8)

        self.columnconfigure(0, weight=1)

    def _entry(self, parent, var, **kw):
        return styled_entry(parent, var, **kw)

    def _spinbox(self, parent, var):
        return tk.Spinbox(
            parent, from_=1, to=50, textvariable=var, width=8,
            bg=C_SURFACE2, fg=C_TEXT, insertbackground=C_TEXT,
            buttonbackground=C_SURFACE2, relief="flat", font=("", 11),
            highlightbackground=C_BORDER, highlightcolor=C_ACCENT,
            highlightthickness=1, bd=4,
        )

    def _show_row(self, row: tk.Frame) -> None:
        row.grid()

    def _hide_row(self, row: tk.Frame) -> None:
        row.grid_remove()

    # --- イベント ---

    def _on_type_change(self):
        match_type = self._match_type.get()
        is_keyword = (match_type == TYPE_KEYWORD)
        is_prefix = (match_type == TYPE_PREFIX)
        is_suffix = (match_type == TYPE_SUFFIX_EXCLUDE)

        # 選択中の条件行だけ表示
        if is_keyword:
            self._show_row(self._kw_row)
        else:
            self._hide_row(self._kw_row)

        if is_prefix:
            self._show_row(self._pfx_row)
        else:
            self._hide_row(self._pfx_row)

        if is_suffix:
            self._show_row(self._sfx_row)
        else:
            self._hide_row(self._sfx_row)

    def _save(self):
        match_type = self._match_type.get()

        if match_type == TYPE_KEYWORD:
            kw = self._keyword_var.get().strip()
            if not kw:
                messagebox.showwarning("入力エラー", "キーワードを入力してください。", parent=self)
                return
            self.result = {
                "match_type": TYPE_KEYWORD,
                "keyword": kw,
                "case_sensitive": self._case_var.get(),
            }
        elif match_type == TYPE_PREFIX:
            try:
                n = int(self._prefix_var.get())
                if n < 1:
                    raise ValueError
            except (ValueError, tk.TclError):
                messagebox.showwarning("入力エラー", "文字数は 1 以上の整数を入力してください。", parent=self)
                return
            self.result = {
                "match_type": TYPE_PREFIX,
                "prefix_length": n,
                "case_sensitive": self._case_var.get(),
            }
        else:  # TYPE_SUFFIX_EXCLUDE
            try:
                n = int(self._suffix_var.get())
                if n < 1:
                    raise ValueError
            except (ValueError, tk.TclError):
                messagebox.showwarning("入力エラー", "文字数は 1 以上の整数を入力してください。", parent=self)
                return
            self.result = {
                "match_type": TYPE_SUFFIX_EXCLUDE,
                "suffix_exclude_length": n,
                "case_sensitive": self._case_var.get(),
            }
        self.destroy()


# ---------------------------------------------------------------------------
# メインウィンドウ
# ---------------------------------------------------------------------------

class FileSorterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Sorter")
        self.geometry("1020x640")
        self.minsize(720, 500)
        self.configure(bg=C_BG)
        apply_styles(self)

        dest, self.rules = load_config()
        self.source_var = tk.StringVar()
        self.dest_var     = tk.StringVar(value=dest)
        self.mode_var     = tk.StringVar(value="move")

        self._build_ui()
        self._refresh_rules_table()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self._build_source_bar()
        self._build_center()
        self._build_bottom_bar()

    def _build_source_bar(self):
        bar = tk.Frame(self, bg=C_BG)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        bar.columnconfigure(0, weight=1)

        folder_panel = tk.Frame(
            bar, bg=C_SURFACE, highlightbackground=C_BORDER,
            highlightthickness=1, padx=14, pady=12,
        )
        folder_panel.grid(row=0, column=0, sticky="ew")
        folder_panel.columnconfigure(1, weight=1)

        tk.Label(folder_panel, text="フォルダ設定", bg=C_SURFACE, fg=C_TEXT,
                 font=("", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        label_opts = dict(bg=C_SURFACE, fg=C_TEXT, font=("", 10, "bold"), width=12, anchor="e")
        btn_opts = dict(font=("", 10))

        tk.Label(folder_panel, text="対象フォルダ", **label_opts).grid(
            row=1, column=0, padx=(0, 10), pady=5, sticky="e")
        styled_entry(folder_panel, self.source_var).grid(
            row=1, column=1, padx=(0, 8), pady=5, sticky="ew")
        FlatButton(folder_panel, text="参照…", command=self._browse_source,
                   bg=C_SURFACE2, hover_bg=C_BORDER, **btn_opts).grid(
            row=1, column=2, pady=5)

        tk.Label(folder_panel, text="振り分け先", **label_opts).grid(
            row=2, column=0, padx=(0, 10), pady=5, sticky="e")
        dest_entry = styled_entry(folder_panel, self.dest_var)
        dest_entry.grid(row=2, column=1, padx=(0, 8), pady=5, sticky="ew")
        dest_entry.bind("<FocusOut>", lambda _: self._save_state())
        FlatButton(folder_panel, text="参照…", command=self._browse_destination,
                   bg=C_SURFACE2, hover_bg=C_BORDER, **btn_opts).grid(
            row=2, column=2, pady=5)

        # 操作モード（移動／コピー）
        mode_panel = tk.Frame(
            bar, bg=C_SURFACE, highlightbackground=C_BORDER,
            highlightthickness=1, padx=16, pady=12,
        )
        mode_panel.grid(row=0, column=1, padx=(12, 0), sticky="ns")

        tk.Label(mode_panel, text="操作", bg=C_SURFACE, fg=C_TEXT,
                 font=("", 11, "bold")).pack(anchor="w", pady=(0, 8))
        for val, label in (("move", "移動"), ("copy", "コピー")):
            tk.Radiobutton(
                mode_panel, text=label, variable=self.mode_var, value=val,
                bg=C_SURFACE, fg=C_TEXT, selectcolor=C_ACCENT,
                activebackground=C_SURFACE, activeforeground=C_TEXT,
                font=("", 11), indicatoron=True,
            ).pack(anchor="w", pady=3)

    def _build_center(self):
        center = tk.Frame(self, bg=C_BG)
        center.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=2)
        center.columnconfigure(1, weight=3)
        self._build_rules_panel(center)
        self._build_preview_panel(center)

    def _panel(self, parent, title: str, col: int, padx) -> tk.Frame:
        outer = tk.Frame(
            parent, bg=C_SURFACE, highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        outer.grid(row=0, column=col, sticky="nsew", padx=padx)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        hdr = tk.Frame(outer, bg=C_SURFACE2)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(hdr, text=title, bg=C_SURFACE2, fg=C_TEXT,
                 font=("", 12, "bold")).pack(side="left", padx=14, pady=10)
        outer._header = hdr
        return outer

    def _build_rules_panel(self, parent):
        outer = self._panel(parent, "振り分けルール", col=0, padx=(0, 6))

        FlatButton(outer._header, text="＋ ルール追加", command=self._add_rule,
                   font=("", 10)).pack(side="right", padx=10, pady=6)

        cols = ("type", "condition")
        self.rules_tree = ttk.Treeview(outer, columns=cols, show="headings",
                                       selectmode="browse")
        self.rules_tree.heading("type",      text="方式")
        self.rules_tree.heading("condition", text="条件")
        self.rules_tree.column("type",      width=130, minwidth=90, anchor="center")
        self.rules_tree.column("condition", width=220, minwidth=100)
        self.rules_tree.grid(row=1, column=0, padx=(12, 0), pady=(0, 4), sticky="nsew")
        self.rules_tree.bind("<Double-1>", lambda _: self._edit_rule())

        sb = ttk.Scrollbar(outer, orient="vertical", command=self.rules_tree.yview)
        sb.grid(row=1, column=1, pady=(0, 4), padx=(0, 6), sticky="ns")
        self.rules_tree.configure(yscrollcommand=sb.set)

        row_btns = tk.Frame(outer, bg=C_SURFACE)
        row_btns.grid(row=2, column=0, columnspan=2, padx=12, pady=(4, 12), sticky="w")
        FlatButton(row_btns, text="  編集  ", command=self._edit_rule,
                   bg=C_SURFACE2, hover_bg=C_BORDER, font=("", 10)).pack(
            side="left", padx=(0, 8))
        FlatButton(row_btns, text="  削除  ", command=self._delete_rule,
                   bg=C_SURFACE2, hover_bg=C_DANGER, font=("", 10)).pack(side="left")

    def _build_preview_panel(self, parent):
        outer = self._panel(parent, "プレビュー", col=1, padx=(6, 0))

        cols = ("file", "condition", "dest_folder")
        self.preview_tree = ttk.Treeview(outer, columns=cols, show="headings",
                                         selectmode="none")
        self.preview_tree.heading("file",        text="ファイル名")
        self.preview_tree.heading("condition",   text="マッチ条件")
        self.preview_tree.heading("dest_folder", text="振り分け先")
        self.preview_tree.column("file",        width=220, minwidth=120)
        self.preview_tree.column("condition",   width=140, minwidth=80)
        self.preview_tree.column("dest_folder", width=260, minwidth=120)
        self.preview_tree.grid(row=1, column=0, padx=(12, 0), pady=(0, 4), sticky="nsew")

        sb2 = ttk.Scrollbar(outer, orient="vertical", command=self.preview_tree.yview)
        sb2.grid(row=1, column=1, pady=(0, 4), padx=(0, 6), sticky="ns")
        self.preview_tree.configure(yscrollcommand=sb2.set)

        self.summary_var = tk.StringVar(value="")
        tk.Label(outer, textvariable=self.summary_var, bg=C_SURFACE,
                 fg=C_TEXT_MUTED, font=("", 10)).grid(
            row=2, column=0, columnspan=2, padx=14, pady=(6, 12), sticky="w")

    def _build_bottom_bar(self):
        bar = tk.Frame(self, bg=C_SURFACE, highlightbackground=C_BORDER,
                       highlightthickness=1)
        bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        bar.columnconfigure(0, weight=1)

        self.status_var   = tk.StringVar(value="")
        self.status_label = tk.Label(bar, textvariable=self.status_var,
                                     bg=C_SURFACE, fg=C_SUCCESS, font=("", 10))
        self.status_label.grid(row=0, column=0, padx=16, pady=14, sticky="w")

        FlatButton(bar, text=" プレビュー更新 ", command=self._refresh_preview,
                   bg=C_SURFACE2, hover_bg=C_BORDER, font=("", 10)).grid(
            row=0, column=1, padx=6, pady=14)
        FlatButton(bar, text="  実  行  ", command=self._execute,
                   bg=C_SUCCESS, hover_bg="#2e9456", font=("", 12, "bold")).grid(
            row=0, column=2, padx=(6, 16), pady=14)

    # ------------------------------------------------------------------
    # ルール操作
    # ------------------------------------------------------------------

    def _save_state(self) -> None:
        save_config(self.dest_var.get().strip(), self.rules)

    def _rule_display(self, rule: dict) -> tuple:
        """テーブル表示用の (方式, 条件) を返す。"""
        mt = rule.get("match_type", TYPE_KEYWORD)
        if mt == TYPE_KEYWORD:
            type_label = "キーワード"
            cond = rule.get("keyword", "")
        elif mt == TYPE_PREFIX:
            type_label = "先頭N文字"
            n = rule.get("prefix_length", 6)
            cond = f"先頭 {n} 文字"
        else:
            type_label = "末尾N文字除外"
            n = rule.get("suffix_exclude_length", 6)
            cond = f"末尾 {n} 文字除外"
        return type_label, cond

    def _refresh_rules_table(self):
        self.rules_tree.delete(*self.rules_tree.get_children())
        for r in self.rules:
            self.rules_tree.insert("", "end", values=self._rule_display(r))

    def _add_rule(self):
        dlg = RuleDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.rules.append(dlg.result)
            self._save_state()
            self._refresh_rules_table()

    def _edit_rule(self):
        sel = self.rules_tree.selection()
        if not sel:
            messagebox.showinfo("選択なし", "編集するルールを選択してください。", parent=self)
            return
        idx = self.rules_tree.index(sel[0])
        dlg = RuleDialog(self, rule=self.rules[idx])
        self.wait_window(dlg)
        if dlg.result:
            self.rules[idx] = dlg.result
            self._save_state()
            self._refresh_rules_table()

    def _delete_rule(self):
        sel = self.rules_tree.selection()
        if not sel:
            messagebox.showinfo("選択なし", "削除するルールを選択してください。", parent=self)
            return
        idx = self.rules_tree.index(sel[0])
        _, cond = self._rule_display(self.rules[idx])
        if messagebox.askyesno("削除確認", f"ルール「{cond}」を削除しますか？", parent=self):
            self.rules.pop(idx)
            self._save_state()
            self._refresh_rules_table()

    # ------------------------------------------------------------------
    # プレビュー
    # ------------------------------------------------------------------

    def _browse_source(self):
        path = filedialog.askdirectory(title="対象フォルダを選択", parent=self)
        if path:
            self.source_var.set(path)
            self._refresh_preview()

    def _browse_destination(self):
        path = filedialog.askdirectory(title="振り分け先フォルダを選択", parent=self)
        if path:
            self.dest_var.set(path)
            self._save_state()
            self._refresh_preview()

    def _collect_matches(self) -> tuple:
        """
        戻り値:
          matched  : [{"file", "path", "rule", "dest_dir", "condition_label"}, ...]
          unmatched: [fname, ...]
        """
        src = self.source_var.get().strip()
        dest_root = self.dest_var.get().strip()
        if not src or not os.path.isdir(src):
            return [], []

        matched   = []
        unmatched = []

        for fname in os.listdir(src):
            fpath = os.path.join(src, fname)
            if not os.path.isfile(fpath):
                continue

            hit_rule = None
            hit_dest = None
            for rule in self.rules:
                dest = resolve_destination(rule, fname, dest_root)
                if dest is not None:
                    hit_rule = rule
                    hit_dest = dest
                    break

            if hit_rule is not None:
                _, cond_label = self._rule_display(hit_rule)
                matched.append({
                    "file":            fname,
                    "path":            fpath,
                    "rule":            hit_rule,
                    "dest_dir":        hit_dest,
                    "condition_label": cond_label,
                })
            else:
                unmatched.append(fname)

        return matched, unmatched

    def _refresh_preview(self):
        self.status_var.set("")
        matched, unmatched = self._collect_matches()
        self.preview_tree.delete(*self.preview_tree.get_children())
        for m in matched:
            self.preview_tree.insert(
                "", "end",
                values=(m["file"], m["condition_label"], m["dest_dir"]),
            )
        total = len(matched) + len(unmatched)
        self.summary_var.set(
            f"合計 {total} ファイル  ／  マッチ {len(matched)} 件"
            f"  ／  未振り分け {len(unmatched)} 件"
        )

    # ------------------------------------------------------------------
    # 実行
    # ------------------------------------------------------------------

    def _execute(self):
        dest_root = self.dest_var.get().strip()
        if not dest_root:
            messagebox.showwarning(
                "振り分け先未設定",
                "振り分け先フォルダを選択してください。",
                parent=self,
            )
            return

        matched, _ = self._collect_matches()
        if not matched:
            messagebox.showinfo("対象なし",
                                "振り分け対象のファイルが見つかりませんでした。\n"
                                "対象フォルダとルールを確認してください。", parent=self)
            return

        mode = self.mode_var.get()
        mode_label = "移動" if mode == "move" else "コピー"
        if not messagebox.askyesno(
            "実行確認",
            f"{len(matched)} 件のファイルを{mode_label}します。\nよろしいですか？",
            parent=self,
        ):
            return

        errors  = []
        success = 0
        for m in matched:
            dest_dir = m["dest_dir"]
            try:
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, m["file"])
                if mode == "move":
                    shutil.move(m["path"], dest_path)
                else:
                    shutil.copy2(m["path"], dest_path)
                success += 1
            except OSError as e:
                errors.append(f"{m['file']}: {e}")

        self._refresh_preview()

        if errors:
            messagebox.showerror(
                "一部エラー",
                f"{success} 件成功、{len(errors)} 件失敗:\n" + "\n".join(errors[:10]),
                parent=self,
            )
        else:
            self._save_state()
            self.status_var.set(f"✓ {success} 件を{mode_label}しました")
            self.status_label.configure(fg=C_SUCCESS)


# ---------------------------------------------------------------------------
# エントリーポイント
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = FileSorterApp()
    app.mainloop()
