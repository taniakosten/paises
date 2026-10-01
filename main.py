"""CRUD de escritorio para la tabla MySQL/MariaDB `pais`."""

import os
import tkinter as tk
from tkinter import messagebox, ttk

import mysql.connector
from dotenv import load_dotenv


load_dotenv()

TABLE_NAME = "pais"


def quote_identifier(identifier):
    """Escapa un identificador MySQL (tabla/columna) obtenido del esquema."""
    return "`" + identifier.replace("`", "``") + "`"


def connect_database():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "paises_tk"),
        charset="utf8mb4",
    )


class PaisCrudApp:
    def __init__(self, root, connection):
        self.root = root
        self.connection = connection
        self.columns = []
        self.primary_keys = []
        self.entries = {}
        self.row_keys = {}

        self.root.title("CRUD de países")
        self.root.geometry("1100x720")
        self.root.minsize(760, 480)

        self._load_schema()
        self._build_interface()
        self.refresh_records()

    def _load_schema(self):
        table = quote_identifier(TABLE_NAME)
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(f"SHOW COLUMNS FROM {table}")
            schema = cursor.fetchall()
        finally:
            cursor.close()

        if not schema:
            raise RuntimeError(f"No se encontró la tabla '{TABLE_NAME}' o no tiene columnas.")

        self.columns = schema
        self.primary_keys = [column["Field"] for column in schema if column["Key"] == "PRI"]
        if not self.primary_keys:
            raise RuntimeError(
                f"La tabla '{TABLE_NAME}' necesita una clave primaria para actualizar y borrar registros."
            )

    def _build_interface(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        form = ttk.LabelFrame(self.root, text="Datos del país", padding=10)
        form.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        for index, column in enumerate(self.columns):
            row, pair = divmod(index, 2)
            base_col = pair * 2
            name = column["Field"]
            ttk.Label(form, text=name).grid(row=row, column=base_col, sticky="w", padx=(0, 8), pady=3)
            entry = ttk.Entry(form)
            entry.grid(row=row, column=base_col + 1, sticky="ew", padx=(0, 18), pady=3)
            self.entries[name] = entry

        buttons = ttk.Frame(self.root, padding=(10, 4))
        buttons.grid(row=2, column=0, sticky="ew")
        ttk.Button(buttons, text="Agregar", command=self.add_record).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Guardar cambios", command=self.update_record).pack(side="left", padx=6)
        ttk.Button(buttons, text="Eliminar", command=self.delete_record).pack(side="left", padx=6)
        ttk.Button(buttons, text="Limpiar", command=self.clear_form).pack(side="left", padx=6)
        ttk.Button(buttons, text="Actualizar lista", command=self.refresh_records).pack(side="right")

        listing = ttk.Frame(self.root, padding=(10, 6, 10, 10))
        listing.grid(row=1, column=0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(0, weight=1)

        names = [column["Field"] for column in self.columns]
        self.tree = ttk.Treeview(listing, columns=names, show="headings", selectmode="browse")
        for name in names:
            self.tree.heading(name, text=name)
            self.tree.column(name, width=140, minwidth=80, stretch=True)
        vertical = ttk.Scrollbar(listing, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(listing, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self.select_record)

    def _fetch_records(self):
        columns = ", ".join(quote_identifier(column["Field"]) for column in self.columns)
        table = quote_identifier(TABLE_NAME)
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(f"SELECT {columns} FROM {table}")
            return cursor.fetchall()
        finally:
            cursor.close()

    def refresh_records(self):
        try:
            records = self._fetch_records()
        except mysql.connector.Error as error:
            messagebox.showerror("Error de base de datos", str(error), parent=self.root)
            return

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.row_keys.clear()
        for record in records:
            values = [record[column["Field"]] for column in self.columns]
            item = self.tree.insert("", "end", values=values)
            self.row_keys[item] = tuple(record[key] for key in self.primary_keys)

    def _form_values(self, inserting):
        values = {}
        for column in self.columns:
            name = column["Field"]
            value = self.entries[name].get().strip()
            auto_increment = "auto_increment" in (column["Extra"] or "").lower()
            has_default = column["Default"] is not None

            if inserting and value == "" and (auto_increment or has_default):
                continue
            if value == "" and column["Null"] == "YES":
                values[name] = None
            else:
                values[name] = value
        return values

    def add_record(self):
        if self.tree.selection():
            messagebox.showwarning(
                "Formulario en edición",
                "Pulsa Limpiar antes de agregar un país nuevo.",
                parent=self.root,
            )
            return
        values = self._form_values(inserting=True)
        if not values:
            messagebox.showwarning("Datos incompletos", "Introduce los datos del país.", parent=self.root)
            return

        names = list(values)
        placeholders = ", ".join(["%s"] * len(names))
        sql = (
            f"INSERT INTO {quote_identifier(TABLE_NAME)} "
            f"({', '.join(quote_identifier(name) for name in names)}) VALUES ({placeholders})"
        )
        self._execute_write(sql, [values[name] for name in names], "País agregado correctamente.")

    def update_record(self):
        item = self._selected_item()
        if item is None:
            return

        values = self._form_values(inserting=False)
        for key in self.primary_keys:
            values.pop(key, None)
        if not values:
            messagebox.showwarning("Sin cambios", "No hay campos editables para actualizar.", parent=self.root)
            return

        assignments = ", ".join(f"{quote_identifier(name)} = %s" for name in values)
        where, key_values = self._where_primary_key(self.row_keys[item])
        sql = f"UPDATE {quote_identifier(TABLE_NAME)} SET {assignments} WHERE {where}"
        self._execute_write(sql, list(values.values()) + key_values, "País actualizado correctamente.")

    def delete_record(self):
        item = self._selected_item()
        if item is None:
            return
        if not messagebox.askyesno("Confirmar eliminación", "¿Eliminar el país seleccionado?", parent=self.root):
            return

        where, key_values = self._where_primary_key(self.row_keys[item])
        sql = f"DELETE FROM {quote_identifier(TABLE_NAME)} WHERE {where}"
        self._execute_write(sql, key_values, "País eliminado correctamente.")
        self.clear_form()

    def _where_primary_key(self, key_values):
        where = " AND ".join(f"{quote_identifier(key)} = %s" for key in self.primary_keys)
        return where, list(key_values)

    def _execute_write(self, sql, values, success_message):
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, values)
            self.connection.commit()
        except mysql.connector.Error as error:
            self.connection.rollback()
            messagebox.showerror("Error de base de datos", str(error), parent=self.root)
            return
        finally:
            cursor.close()

        self.refresh_records()
        messagebox.showinfo("Correcto", success_message, parent=self.root)

    def _selected_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selecciona un país", "Selecciona un registro de la lista.", parent=self.root)
            return None
        return selected[0]

    def select_record(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        values = self.tree.item(item, "values")
        for column, value in zip(self.columns, values):
            entry = self.entries[column["Field"]]
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            if value is not None:
                entry.insert(0, value)
            if column["Field"] in self.primary_keys:
                entry.configure(state="disabled")

    def clear_form(self):
        self.tree.selection_remove(self.tree.selection())
        for entry in self.entries.values():
            entry.configure(state="normal")
            entry.delete(0, tk.END)

    def close(self):
        try:
            self.connection.close()
        finally:
            self.root.destroy()


def main():
    root = tk.Tk()
    try:
        connection = connect_database()
        app = PaisCrudApp(root, connection)
    except (mysql.connector.Error, RuntimeError, ValueError) as error:
        messagebox.showerror("No se pudo iniciar", str(error), parent=root)
        root.destroy()
        return

    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
