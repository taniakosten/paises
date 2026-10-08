"""Aplicación web local para administrar la tabla MySQL/MariaDB `pais`."""

import os

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

load_dotenv()

TABLE_NAME = "pais"


def quote_identifier(identifier):
    """Escapa un nombre de tabla o columna obtenido del esquema."""
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


def read_schema(cursor):
    cursor.execute(f"SHOW COLUMNS FROM {quote_identifier(TABLE_NAME)}")
    columns = cursor.fetchall()
    if not columns:
        raise RuntimeError(f"No se encontró la tabla '{TABLE_NAME}' o no tiene columnas.")

    primary_keys = [column["Field"] for column in columns if column["Key"] == "PRI"]
    if not primary_keys:
        raise RuntimeError(
            f"La tabla '{TABLE_NAME}' necesita una clave primaria para actualizar y borrar registros."
        )
    return columns, primary_keys


def form_values(columns, inserting):
    values = {}
    for column in columns:
        name = column["Field"]
        value = request.form.get(name, "").strip()
        auto_increment = "auto_increment" in (column["Extra"] or "").lower()
        has_default = column["Default"] is not None

        if inserting and value == "" and (auto_increment or has_default):
            continue
        values[name] = None if value == "" and column["Null"] == "YES" else value
    return values


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)

    @app.get("/")
    def index():
        connection = None
        cursor = None
        try:
            connection = connect_database()
            cursor = connection.cursor(dictionary=True)
            columns, primary_keys = read_schema(cursor)
            selected_columns = ", ".join(quote_identifier(column["Field"]) for column in columns)
            order_by = ", ".join(quote_identifier(key) for key in primary_keys)
            cursor.execute(
                f"SELECT {selected_columns} FROM {quote_identifier(TABLE_NAME)} "
                f"ORDER BY {order_by}"
            )
            records = cursor.fetchall()
            return render_template(
                "index.html", columns=columns, primary_keys=primary_keys, records=records
            )
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            flash(f"No se pudieron cargar los países: {error}", "error")
            return render_template("index.html", columns=[], primary_keys=[], records=[]), 503
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    @app.post("/create")
    def create_record():
        connection = None
        cursor = None
        try:
            connection = connect_database()
            cursor = connection.cursor(dictionary=True)
            columns, _ = read_schema(cursor)
            values = form_values(columns, inserting=True)
            if not values:
                flash("Completa al menos un campo antes de agregar el país.", "error")
                return redirect(url_for("index"))

            names = list(values)
            placeholders = ", ".join(["%s"] * len(names))
            sql = (
                f"INSERT INTO {quote_identifier(TABLE_NAME)} "
                f"({', '.join(quote_identifier(name) for name in names)}) "
                f"VALUES ({placeholders})"
            )
            cursor.execute(sql, [values[name] for name in names])
            connection.commit()
            flash("País agregado correctamente.", "success")
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            if connection is not None and connection.is_connected():
                connection.rollback()
            flash(f"No se pudo agregar el país: {error}", "error")
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()
        return redirect(url_for("index"))

    @app.post("/record/<action>")
    def change_record(action):
        if action not in {"update", "delete"}:
            return "Acción no válida", 404
        connection = None
        cursor = None
        try:
            connection = connect_database()
            cursor = connection.cursor(dictionary=True)
            columns, primary_keys = read_schema(cursor)
            key_values = [request.form.get(f"pk_{index}", "") for index in range(len(primary_keys))]
            if any(value == "" for value in key_values):
                flash("No se recibió la clave del país seleccionado.", "error")
                return redirect(url_for("index"))

            where_clause = " AND ".join(
                f"{quote_identifier(key)} = %s" for key in primary_keys
            )
            if action == "delete":
                cursor.execute(
                    f"DELETE FROM {quote_identifier(TABLE_NAME)} WHERE {where_clause}",
                    key_values,
                )
                connection.commit()
                flash("País eliminado correctamente.", "success")
            else:
                values = form_values(columns, inserting=False)
                for key in primary_keys:
                    values.pop(key, None)
                if not values:
                    flash("No hay campos editables para actualizar.", "error")
                    return redirect(url_for("index"))

                assignments = ", ".join(
                    f"{quote_identifier(name)} = %s" for name in values
                )
                cursor.execute(
                    f"UPDATE {quote_identifier(TABLE_NAME)} SET {assignments} "
                    f"WHERE {where_clause}",
                    list(values.values()) + key_values,
                )
                connection.commit()
                flash("País actualizado correctamente.", "success")
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            if connection is not None and connection.is_connected():
                connection.rollback()
            flash(f"No se pudo modificar el país: {error}", "error")
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    # Solo escucha en este equipo; no publica la base de datos en la red.
    create_app().run(host="127.0.0.1", port=int(os.getenv("WEB_PORT", "5000")), debug=False)
