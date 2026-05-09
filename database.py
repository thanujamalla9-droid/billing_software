import os
from contextlib import contextmanager
from urllib.parse import unquote, urlparse

import mysql.connector
from mysql.connector import Error


class DatabaseError(RuntimeError):
    pass


def has_hosted_database_config() -> bool:
    return bool(
        os.getenv("DATABASE_URL")
        or os.getenv("MYSQL_URL")
        or os.getenv("MYSQL_HOST")
    )


def validate_render_database_config() -> None:
    if os.getenv("RENDER") and not has_hosted_database_config():
        raise DatabaseError(
            "MySQL is not configured. Add DATABASE_URL or MYSQL_HOST, MYSQL_USER, "
            "MYSQL_PASSWORD, and MYSQL_DATABASE in Render environment variables."
        )


def database_name() -> str:
    name = os.getenv("MYSQL_DATABASE", "billing_software")
    if not name.replace("_", "").isalnum():
        raise RuntimeError("MYSQL_DATABASE can contain only letters, numbers, and underscores")
    return name


def db_server_config() -> dict:
    validate_render_database_config()

    database_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
    if database_url:
        parsed = urlparse(database_url)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 3306,
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
        }

    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", "admin"),
    }


def db_config() -> dict:
    config = db_server_config()
    database_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")

    if database_url:
        parsed = urlparse(database_url)
        config["database"] = parsed.path.lstrip("/") or database_name()
    else:
        config["database"] = database_name()

    return config


def init_database() -> None:
    connection = None
    cursor = None
    try:
        database_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")

        if database_url:
            connection = mysql.connector.connect(**db_config())
        else:
            config = db_config()
            db_name = config.pop("database")
            connection = mysql.connector.connect(**config)

        cursor = connection.cursor()
        if not database_url:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            cursor.execute(f"USE `{db_name}`")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(50) NOT NULL UNIQUE,
                item VARCHAR(120) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
    except Error as exc:
        raise DatabaseError(f"Database error: {exc}") from exc
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@contextmanager
def get_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config())
        yield connection
    except Error as exc:
        raise DatabaseError(f"Database error: {exc}") from exc
    finally:
        if connection and connection.is_connected():
            connection.close()
