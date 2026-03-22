"""Графический интерфейс для простого файлового менеджера."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from filemanager import copy_file, count_files, delete_path, find_files, rename_with_date


class Tooltip:
    """Простой tooltip для виджета tkinter."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self._show)
        self.widget.bind("<Leave>", self._hide)

    def _show(self, _event: tk.Event) -> None:
        if self.tip_window or not self.text:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(
            self.tip_window,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padding=5,
        )
        label.pack()

    def _hide(self, _event: tk.Event) -> None:
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class FileManagerGUI(tk.Tk):
    """Окно GUI для запуска операций файлового менеджера."""

    def __init__(self) -> None:
        super().__init__()
        self.title("File Manager GUI")
        self.geometry("900x650")

        self._build_ui()

    def _build_ui(self) -> None:
        top_hint = ttk.Label(
            self,
            text="Выберите вкладку с операцией, укажите пути через кнопки выбора или вручную, затем нажмите Выполнить.",
        )
        top_hint.pack(fill="x", padx=10, pady=(10, 5))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)

        copy_tab = ttk.Frame(notebook)
        delete_tab = ttk.Frame(notebook)
        count_tab = ttk.Frame(notebook)
        find_tab = ttk.Frame(notebook)
        rename_tab = ttk.Frame(notebook)

        notebook.add(copy_tab, text="Копирование")
        notebook.add(delete_tab, text="Удаление")
        notebook.add(count_tab, text="Подсчет")
        notebook.add(find_tab, text="Поиск")
        notebook.add(rename_tab, text="Переименование даты")

        self._build_copy_tab(copy_tab)
        self._build_delete_tab(delete_tab)
        self._build_count_tab(count_tab)
        self._build_find_tab(find_tab)
        self._build_rename_tab(rename_tab)

        log_frame = ttk.LabelFrame(self, text="Лог")
        log_frame.pack(fill="both", expand=False, padx=10, pady=(5, 10))
        self.log_box = ScrolledText(log_frame, height=10, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=8, pady=8)

    def _add_row(
        self,
        parent: ttk.Frame,
        row: int,
        label_text: str,
        variable: tk.StringVar,
        browse_command,
        tooltip_text: str,
        button_text: str = "Выбрать",
    ) -> None:
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky="w", padx=8, pady=6)
        entry = ttk.Entry(parent, textvariable=variable, width=70)
        entry.grid(row=row, column=1, sticky="we", padx=8, pady=6)
        button = ttk.Button(parent, text=button_text, command=browse_command)
        button.grid(row=row, column=2, sticky="w", padx=8, pady=6)
        Tooltip(entry, tooltip_text)
        Tooltip(button, tooltip_text)

    def _build_copy_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)

        self.copy_src_var = tk.StringVar()
        self.copy_dest_var = tk.StringVar(value=".")

        self._add_row(
            tab,
            row=0,
            label_text="Исходный файл:",
            variable=self.copy_src_var,
            browse_command=self._pick_copy_source,
            tooltip_text="Выберите файл, который нужно скопировать.",
            button_text="Файл",
        )
        self._add_row(
            tab,
            row=1,
            label_text="Папка или файл назначения:",
            variable=self.copy_dest_var,
            browse_command=self._pick_copy_destination,
            tooltip_text="Можно выбрать папку или ввести путь вручную.",
            button_text="Папка",
        )

        hint = ttk.Label(tab, text="Если указать папку, имя файла сохранится автоматически.")
        hint.grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 8))

        run_btn = ttk.Button(tab, text="Выполнить Copy", command=self._run_copy)
        run_btn.grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=8)
        Tooltip(run_btn, "Запускает копирование файла.")

    def _build_delete_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)

        self.delete_path_var = tk.StringVar()
        self._add_row(
            tab,
            row=0,
            label_text="Путь к файлу/папке:",
            variable=self.delete_path_var,
            browse_command=self._pick_delete_path,
            tooltip_text="Выберите файл или папку для удаления.",
            button_text="Выбрать",
        )

        warning = ttk.Label(tab, text="Удаление безвозвратное. Перед удалением будет запрос подтверждения.")
        warning.grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 8))

        run_btn = ttk.Button(tab, text="Выполнить Delete", command=self._run_delete)
        run_btn.grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=8)
        Tooltip(run_btn, "Удаляет выбранный путь.")

    def _build_count_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)

        self.count_folder_var = tk.StringVar()
        self._add_row(
            tab,
            row=0,
            label_text="Папка:",
            variable=self.count_folder_var,
            browse_command=self._pick_count_folder,
            tooltip_text="Выберите папку, в которой нужно посчитать файлы.",
            button_text="Папка",
        )

        run_btn = ttk.Button(tab, text="Выполнить Count", command=self._run_count)
        run_btn.grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=8)
        Tooltip(run_btn, "Считает файлы во всех вложенных папках.")

    def _build_find_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)

        self.find_folder_var = tk.StringVar()
        self.find_pattern_var = tk.StringVar()

        self._add_row(
            tab,
            row=0,
            label_text="Папка:",
            variable=self.find_folder_var,
            browse_command=self._pick_find_folder,
            tooltip_text="Выберите папку, где будет поиск.",
            button_text="Папка",
        )

        pattern_label = ttk.Label(tab, text="Regex-шаблон:")
        pattern_label.grid(row=1, column=0, sticky="w", padx=8, pady=6)
        pattern_entry = ttk.Entry(tab, textvariable=self.find_pattern_var, width=70)
        pattern_entry.grid(row=1, column=1, sticky="we", padx=8, pady=6)
        Tooltip(pattern_entry, "Пример: \\.py$ или report.*\\.txt$")

        hint = ttk.Label(tab, text="Шаблон использует регулярные выражения Python.")
        hint.grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 8))

        run_btn = ttk.Button(tab, text="Выполнить Find", command=self._run_find)
        run_btn.grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=8)
        Tooltip(run_btn, "Ищет файлы по шаблону.")

    def _build_rename_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)

        self.rename_path_var = tk.StringVar()
        self.rename_recursive_var = tk.BooleanVar(value=False)

        self._add_row(
            tab,
            row=0,
            label_text="Файл или папка:",
            variable=self.rename_path_var,
            browse_command=self._pick_rename_path,
            tooltip_text="Выберите файл или папку для переименования.",
            button_text="Выбрать",
        )

        recursive_box = ttk.Checkbutton(
            tab,
            text="Рекурсивно (для папки)",
            variable=self.rename_recursive_var,
        )
        recursive_box.grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=6)
        Tooltip(recursive_box, "Если включено, обработаются файлы во всех подпапках.")

        hint = ttk.Label(tab, text="К имени файла будет добавлена дата создания: YYYY-MM-DD_имя")
        hint.grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 8))

        run_btn = ttk.Button(tab, text="Выполнить Rename Date", command=self._run_rename)
        run_btn.grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=8)
        Tooltip(run_btn, "Добавляет дату в начало имени файла.")

    def _pick_copy_source(self) -> None:
        selected = filedialog.askopenfilename(title="Выберите исходный файл")
        if selected:
            self.copy_src_var.set(selected)

    def _pick_copy_destination(self) -> None:
        selected = filedialog.askdirectory(title="Выберите папку назначения")
        if selected:
            self.copy_dest_var.set(selected)

    def _pick_delete_path(self) -> None:
        selected = filedialog.askopenfilename(title="Выберите файл для удаления")
        if selected:
            self.delete_path_var.set(selected)
            return

        selected = filedialog.askdirectory(title="Или выберите папку для удаления")
        if selected:
            self.delete_path_var.set(selected)

    def _pick_count_folder(self) -> None:
        selected = filedialog.askdirectory(title="Выберите папку")
        if selected:
            self.count_folder_var.set(selected)

    def _pick_find_folder(self) -> None:
        selected = filedialog.askdirectory(title="Выберите папку")
        if selected:
            self.find_folder_var.set(selected)

    def _pick_rename_path(self) -> None:
        selected = filedialog.askopenfilename(title="Выберите файл")
        if selected:
            self.rename_path_var.set(selected)
            return

        selected = filedialog.askdirectory(title="Или выберите папку")
        if selected:
            self.rename_path_var.set(selected)

    def _append_log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _run_safe(self, action_name: str, action) -> None:
        try:
            action()
        except Exception as exc:  # noqa: BLE001
            message = f"Ошибка в операции {action_name}: {exc}"
            messagebox.showerror("Ошибка", message)
            self._append_log(message)

    def _run_copy(self) -> None:
        def action() -> None:
            src = self.copy_src_var.get().strip()
            dest = self.copy_dest_var.get().strip() or "."
            if not src:
                raise ValueError("Укажите исходный файл.")

            result = copy_file(src, dest)
            message = f"Файл скопирован: {result}"
            messagebox.showinfo("Успешно", message)
            self._append_log(message)

        self._run_safe("copy", action)

    def _run_delete(self) -> None:
        def action() -> None:
            path = self.delete_path_var.get().strip()
            if not path:
                raise ValueError("Укажите путь к файлу или папке.")

            confirm = messagebox.askyesno("Подтверждение", f"Удалить безвозвратно?\n{path}")
            if not confirm:
                self._append_log("Удаление отменено пользователем.")
                return

            delete_path(path)
            message = f"Удалено: {path}"
            messagebox.showinfo("Успешно", message)
            self._append_log(message)

        self._run_safe("delete", action)

    def _run_count(self) -> None:
        def action() -> None:
            folder = self.count_folder_var.get().strip()
            if not folder:
                raise ValueError("Укажите папку.")

            count = count_files(folder)
            message = f"Количество файлов: {count}"
            messagebox.showinfo("Результат", message)
            self._append_log(f"{folder} -> {message}")

        self._run_safe("count", action)

    def _run_find(self) -> None:
        def action() -> None:
            folder = self.find_folder_var.get().strip()
            pattern = self.find_pattern_var.get().strip()

            if not folder:
                raise ValueError("Укажите папку для поиска.")
            if not pattern:
                raise ValueError("Укажите regex-шаблон.")

            results = find_files(folder, pattern)
            if not results:
                messagebox.showinfo("Результат", "Совпадения не найдены.")
                self._append_log(f"{folder} | {pattern} -> 0 файлов")
                return

            lines = [f"Найдено файлов: {len(results)}"] + results
            messagebox.showinfo("Результат", "\n".join(lines[:20]))
            self._append_log("\n".join(lines))

        self._run_safe("find", action)

    def _run_rename(self) -> None:
        def action() -> None:
            path = self.rename_path_var.get().strip()
            recursive = self.rename_recursive_var.get()

            if not path:
                raise ValueError("Укажите файл или папку.")

            renamed = rename_with_date(path, recursive=recursive)
            message = f"Переименовано файлов: {len(renamed)}"
            messagebox.showinfo("Результат", message)
            if renamed:
                self._append_log(message)
                self._append_log("\n".join(renamed))
            else:
                self._append_log(message)

        self._run_safe("rename_date", action)


def main() -> None:
    app = FileManagerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
