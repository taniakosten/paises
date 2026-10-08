# CRUD de países (Python + MySQL/MariaDB)

Aplicaciones de escritorio (Tkinter) y web (Flask) en Python para consultar, insertar, actualizar y eliminar registros de la tabla `pais` de MySQL/MariaDB. Ambas detectan las columnas y la clave primaria directamente desde la base de datos.

## Requisitos

- Python 3.10 o posterior.
- MySQL o MariaDB activo, con la base `paises_tk` y la tabla `pais` ya creadas.
- La tabla debe tener una clave primaria.
- En Linux, Tkinter puede requerir el paquete del sistema `python3-tk`.

## Configuración

1. Crea y activa un entorno virtual si todavía no tienes uno.
2. Instala las dependencias: `pip install -r requirements.txt`.
3. Copia `.env.example` a `.env` y ajusta `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. La contraseña se mantiene en `.env`, que está excluido de Git.
4. Comprueba que el usuario de MySQL tenga permisos `SELECT`, `INSERT`, `UPDATE` y `DELETE` sobre `paises_tk.pais`.
5. Ejecuta `python main.py` para abrir la aplicación de escritorio, o `python web.py` para la versión web.

## Aplicación web

Con el entorno virtual activo, inicia el servidor con `./.venv/bin/python web.py` y abre `http://127.0.0.1:5000` en el navegador. El servidor escucha solo en el equipo local; no está publicado en la red. La página permite agregar, editar y eliminar filas de `pais`. Cierra el servidor con `Ctrl+C` en la terminal.

Ejemplo de tabla compatible:

```sql
CREATE DATABASE paises_tk CHARACTER SET utf8mb4;

CREATE TABLE pais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    capital VARCHAR(100),
    poblacion BIGINT
);
```

El ejemplo solo ilustra el formato esperado; no se ejecuta automáticamente ni cambia la base de datos. La interfaz usa los nombres reales de las columnas detectadas.
