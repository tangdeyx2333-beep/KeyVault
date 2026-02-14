from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
import threading
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

from save_api_key.storage import ApiKeyStore


class LoginDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, is_first_run: bool = False) -> None:
        print("[DEBUG] 初始化LoginDialog...")
        super().__init__(master)
        
        title_text = "初始化主密码" if is_first_run else "登录"
        self.title(f"{title_text} - API Key Manager")
        self.resizable(False, False)
        self.result: str | None = None
        
        # 设置窗口大小和位置
        self.geometry("300x150")
        self.transient(master)
        self.grab_set()
        
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_reqwidth()) // 2
        y = (self.winfo_screenheight() - self.winfo_reqheight()) // 2
        self.geometry(f"+{x}+{y}")
        
        # 确保对话框在最前面并可见
        self.lift()
        self.focus_force()
        self.deiconify()

        if is_first_run:
            tip_label = ttk.Label(self, text="首次运行，请设置您的主密码：", foreground="blue")
            tip_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        row_idx = 1 if is_first_run else 0
        ttk.Label(self, text="主密码:").grid(row=row_idx, column=0, padx=10, pady=10, sticky="w")
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(self, textvariable=self.password_var, show="*", width=30)
        self.password_entry.grid(row=row_idx, column=1, padx=10, pady=10, sticky="ew")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row_idx + 1, column=0, columnspan=2, pady=10, sticky="e")
        
        btn_text = "设置密码并启动" if is_first_run else "登录"
        ok_btn = ttk.Button(btn_frame, text=btn_text, command=self._on_ok)
        ok_btn.grid(row=0, column=0, padx=(0, 8))

        self.bind("<Return>", lambda _e: self._on_ok())
        self.password_entry.focus_set()
        print("[DEBUG] LoginDialog初始化完成")

    def _on_ok(self) -> None:
        pwd = self.password_var.get()
        if not pwd:
            messagebox.showerror("错误", "主密码不能为空", parent=self)
            return
        self.result = pwd
        self.destroy()  # 只销毁自己，wait_window就会停止等待


class ApiKeyEditDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        title: str,
        initial_key: str,
        initial_value: str,
        initial_remark: str,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: tuple[str, str, str] | None = None

        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Key").grid(row=0, column=0, padx=10, pady=(10, 6), sticky="w")
        ttk.Label(self, text="Value").grid(row=1, column=0, padx=10, pady=6, sticky="w")
        ttk.Label(self, text="备注").grid(row=2, column=0, padx=10, pady=6, sticky="w")

        self.key_var = tk.StringVar(value=initial_key)
        self.value_var = tk.StringVar(value=initial_value)
        self.remark_var = tk.StringVar(value=initial_remark)

        self.key_entry = ttk.Entry(self, textvariable=self.key_var, width=40)
        self.value_entry = ttk.Entry(self, textvariable=self.value_var, width=40)
        self.remark_entry = ttk.Entry(self, textvariable=self.remark_var, width=40)

        self.key_entry.grid(row=0, column=1, padx=10, pady=(10, 6), sticky="ew")
        self.value_entry.grid(row=1, column=1, padx=10, pady=6, sticky="ew")
        self.remark_entry.grid(row=2, column=1, padx=10, pady=6, sticky="ew")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=(10, 10), sticky="e")

        ok_btn = ttk.Button(btn_frame, text="确定", command=self._on_ok)
        cancel_btn = ttk.Button(btn_frame, text="取消", command=self._on_cancel)
        ok_btn.grid(row=0, column=0, padx=(0, 8))
        cancel_btn.grid(row=0, column=1)

        self.bind("<Escape>", lambda _e: self._on_cancel())
        self.bind("<Return>", lambda _e: self._on_ok())

        self.transient(master)
        self.grab_set()
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_reqwidth() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_reqheight() // 2)
        self.geometry(f"+{x}+{y}")
        self.key_entry.focus_set()

    def _on_ok(self) -> None:
        key = self.key_var.get()
        value = self.value_var.get()
        remark = self.remark_var.get()
        self.result = (key, value, remark)
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


class ToastNotification(tk.Toplevel):
    def __init__(self, master: tk.Misc, message: str, duration: int = 2000):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-alpha", 0.9)
        self.attributes("-topmost", True)

        label = ttk.Label(
            self,
            text=message,
            padding=(10, 5),
            background="#333",
            foreground="#fff",
            font=("Segoe UI", 9),
        )
        label.pack()

        master_root = self.master.winfo_toplevel()
        x = master_root.winfo_x() + (master_root.winfo_width() // 2) - (self.winfo_reqwidth() // 2)
        y = master_root.winfo_y() + (master_root.winfo_height() // 2) - (self.winfo_reqheight() // 2)
        self.geometry(f"+{x}+{y}")

        self.after(duration, self.destroy)


class ApiKeyApp(tk.Tk):
    def __init__(self, store: ApiKeyStore) -> None:
        super().__init__()
        self.title("API Key 管理")
        self.minsize(820, 420)
        self.withdraw()
        self.update_idletasks()
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        size = tuple(int(_) for _ in self.geometry().split("+")[0].split("x"))
        x = w / 2 - size[0] / 2
        y = h / 2 - size[1] / 2
        self.geometry("%dx%d+%d+%d" % (size[0], size[1], x, y))
        self.deiconify()

        self._store = store
        self._clipboard_content: str | None = None

        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)
        root.rowconfigure(1, weight=1)
        root.columnconfigure(0, weight=1)

        title = ttk.Label(root, text="API Keys", font=("Segoe UI", 12, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        table_frame = ttk.Frame(root)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("key", "value", "remark"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("key", text="Key")
        self.tree.heading("value", text="Value")
        self.tree.heading("remark", text="备注")

        self.tree.column("key", width=220, anchor="w")
        self.tree.column("value", width=360, anchor="w")
        self.tree.column("remark", width=200, anchor="w")

        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")

        btn_bar = ttk.Frame(root)
        btn_bar.grid(row=2, column=0, sticky="e", pady=(10, 0))

        self.new_btn = ttk.Button(btn_bar, text="新建(N)...", command=self._on_new)
        self.edit_btn = ttk.Button(btn_bar, text="编辑(E)...", command=self._on_edit, state=tk.DISABLED)
        self.del_btn = ttk.Button(btn_bar, text="删除(D)", command=self._on_delete, state=tk.DISABLED)

        self.new_btn.grid(row=0, column=0, padx=(0, 8))
        self.edit_btn.grid(row=0, column=1, padx=(0, 8))
        self.del_btn.grid(row=0, column=2)

        self.bind("<Alt-n>", lambda _e: self._on_new())
        self.bind("<Alt-N>", lambda _e: self._on_new())
        self.bind("<Alt-e>", lambda _e: self._on_edit())
        self.bind("<Alt-E>", lambda _e: self._on_edit())
        self.bind("<Alt-d>", lambda _e: self._on_delete())
        self.bind("<Alt-D>", lambda _e: self._on_delete())

        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._sync_buttons())
        self.tree.bind("<Double-1>", lambda _e: self._on_edit())
        self.tree.bind("<Button-1>", self._on_cell_click)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._setup_tray()

        self._reload()

    def _setup_tray(self) -> None:
        width, height = 64, 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        shaft_color = (30, 30, 30, 255)
        draw.line([16, 52, 48, 12], fill=shaft_color, width=2)
        feather_blue = (70, 130, 180, 255)
        points = [
            (18, 50), (14, 40), (18, 25), (30, 12), (45, 8),
            (52, 12), (50, 25), (42, 40), (30, 50), (18, 50)
        ]
        draw.polygon(points, fill=feather_blue, outline=shaft_color)
        for i in range(5):
            offset = i * 6
            draw.line([25 + offset, 45 - offset, 35 + offset, 35 - offset], fill=(255, 255, 255, 100), width=1)

        menu = (
            item("显示", self._show_window, default=True),
            item("退出", self._quit_app),
        )
        self.icon = pystray.Icon("ApiKeyManager", image, "API Key 管理", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _show_window(self) -> None:
        self.after(0, self.deiconify)
        self.after(0, self.focus_force)

    def _on_closing(self) -> None:
        self.withdraw()

    def _quit_app(self) -> None:
        # 退出前强制清空剪贴板，防止敏感数据泄露
        try:
            self.clipboard_clear()
        except Exception:
            pass
        self.icon.stop()
        self.after(0, self.quit)
        self.after(0, self.destroy)

    def _sync_buttons(self) -> None:
        has_sel = bool(self.tree.selection())
        self.edit_btn.configure(state=(tk.NORMAL if has_sel else tk.DISABLED))
        self.del_btn.configure(state=(tk.NORMAL if has_sel else tk.DISABLED))

    def _clear_rows(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

    def _reload(self) -> None:
        self._clear_rows()
        for row in self._store.list_all():
            self.tree.insert("", tk.END, values=(row["key"], row["value"], row["remark"]))
        self._sync_buttons()

    def _on_cell_click(self, event: tk.Event) -> None:
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        if not item_id or not column_id:
            return

        try:
            col_idx = int(column_id.replace("#", "")) - 1
            if col_idx < 0:
                return
            value = self.tree.item(item_id, "values")[col_idx]
        except (ValueError, IndexError):
            return

        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()
        ToastNotification(self, "复制成功")
        self._schedule_clipboard_clear(value)

    def _schedule_clipboard_clear(self, content: str) -> None:
        self._clipboard_content = content
        self.after(30000, self._clear_clipboard_if_match, content)

    def _clear_clipboard_if_match(self, content: str) -> None:
        try:
            if self.clipboard_get() == content:
                self.clipboard_clear()
        except Exception:
            pass

    def _get_selected(self) -> tuple[str, str, str] | None:
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = sel[0]
        values = self.tree.item(item_id, "values")
        if len(values) != 3:
            return None
        return (str(values[0]), str(values[1]), str(values[2]))

    def _on_new(self) -> None:
        dialog = ApiKeyEditDialog(self, "新建 API Key", "", "", "")
        self.wait_window(dialog)
        if dialog.result is None:
            return
        key, value, remark = dialog.result
        try:
            self._store.create(key, value, remark)
        except Exception as exc:
            messagebox.showerror("错误", str(exc), parent=self)
            return
        self._reload()

    def _on_edit(self) -> None:
        selected = self._get_selected()
        if selected is None:
            return
        old_key, old_value, old_remark = selected
        dialog = ApiKeyEditDialog(self, "编辑 API Key", old_key, old_value, old_remark)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        new_key, new_value, new_remark = dialog.result
        try:
            self._store.update(old_key, new_key, new_value, new_remark)
        except Exception as exc:
            messagebox.showerror("错误", str(exc), parent=self)
            return
        self._reload()

    def _on_delete(self) -> None:
        selected = self._get_selected()
        if selected is None:
            return
        key, _value, _remark = selected
        if not messagebox.askyesno("确认删除", f"确定要删除 Key: {key} 吗？", parent=self):
            return
        try:
            self._store.delete(key)
        except Exception as exc:
            messagebox.showerror("错误", str(exc), parent=self)
            return
        self._reload()
