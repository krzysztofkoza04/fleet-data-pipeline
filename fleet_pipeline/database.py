
import os

import psycopg
from dotenv import load_dotenv


def get_database_connection() -> psycopg.Connection:

    load_dotenv()

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    required_settings = {
        "DB_HOST": host,
        "DB_PORT": port,
        "DB_NAME": database,
        "DB_USER": user,
        "DB_PASSWORD": password
    }

    for name, value in required_settings.items():
        if not value:
            raise ValueError(
                f"Missing database configuration: {name}"
            )

    connection = psycopg.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
        connect_timeout=5
    )

    return connection


def check_database_connection() -> dict:

    with get_database_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    current_setting('server_version')
                """
            )

            result = cursor.fetchone()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM fleet.vehicles
                """
            )

            vehicle_count = cursor.fetchone()[0]

    return {
        "database": result[0],
        "user": result[1],
        "postgres_version": result[2],
        "total_vehicles": vehicle_count
    }
