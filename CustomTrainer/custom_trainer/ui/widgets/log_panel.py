from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class LogPanel(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.text = tk.Text(self, height=12, wrap="word")
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def log(self, message: str) -> None:
        self.text.insert("end", message + "\n")
        self.text.see("end")
        self.text.update_idletasks()

    def clear(self) -> None:
        self.text.delete("1.0", "end")
