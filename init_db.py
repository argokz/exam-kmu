#!/usr/bin/env python3
# Однократная инициализация БД: создаёт таблицу results, если её нет.
# Запуск: задайте переменные окружения DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
# или отредактируйте константы ниже и выполните: python init_db.py

import os
import psycopg2
from psycopg2 import sql

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "145.249.247.138"),
    "port": int(os.environ.get("DB_PORT", "5440")),
    "dbname": os.environ.get("DB_NAME", "exam_kmu"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
}

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS results (
    id          SERIAL PRIMARY KEY,
    fio         VARCHAR(255) NOT NULL,
    group_name  VARCHAR(100) NOT NULL,
    credit      VARCHAR(50)  NOT NULL,
    variant     INTEGER      NOT NULL,
    assignment  TEXT,
    code        TEXT,
    score       INTEGER      NOT NULL CHECK (score >= 0 AND score <= 100),
    feedback    TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
CREATE INDEX IF NOT EXISTS idx_results_group_credit ON results(group_name, credit);
"""

def main():
    if not DB_CONFIG["password"]:
        print("Задайте DB_PASSWORD (или отредактируйте init_db.py).")
        return
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    for stmt in CREATE_TABLE.split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    cur.close()
    conn.close()
    print("Таблица results создана/проверена.")

if __name__ == "__main__":
    main()
