import os
import mysql.connector
from dotenv import load_dotenv
from data_ingestion.logger import logger

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

_conn = None


def get_db_conn():
    global _conn

    if _conn is None or not _conn.is_connected():
        _conn = mysql.connector.connect(**DB_CONFIG)
        logger.info("MySQL ligado (data_ingestion)")

    return _conn
