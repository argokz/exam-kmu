# Служебный модуль контрольной: ключ, генерация и проверка заданий через GPT.
# Подключается из ноутбука по raw-URL с GitHub. Студентам код не показывать.

import os
import json
import sqlite3
from datetime import datetime
from openai import OpenAI

# Ключ из Colab Secrets
try:
    from google.colab import userdata
    API_KEY = userdata.get("OPENAI_API_KEY")
except Exception:
    API_KEY = os.environ.get("OPENAI_API_KEY") or ""
if not API_KEY:
    API_KEY = input("Введите OpenAI API ключ: ").strip()

client = OpenAI(api_key=API_KEY)
MODEL = "gpt-4o-mini"


def generate_assignment(variant: int) -> str:
    prompt = f"""
Сгенерируй ОДНО задание по программированию на Python для варианта {variant}.

Требования к заданию:
- Один связный сценарий (ввод данных, обработка, вывод результата).
- Обязательно: ввод и вывод (input/print), условные операторы (if/elif/else),
  сравнение строк, цикл(ы) (for или while), строки, списки, кортежи.
- Задание однозначно понятное, 15–25 строк кода. Язык: русский.
Выдай только текст задания, без кода.
"""
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return r.choices[0].message.content.strip()


def get_or_generate_assignments() -> dict:
    cache_file = "control_work_assignments.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    assignments = {}
    for v in range(1, 18):
        print(f"Генерация варианта {v}...")
        assignments[str(v)] = generate_assignment(v)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(assignments, f, ensure_ascii=False, indent=2)
    return assignments


def evaluate_solution(assignment_text: str, code: str, variant: int) -> dict:
    prompt = f"""
Ты проверяешь решение студента по программированию на Python.

ЗАДАНИЕ (вариант {variant}):
{assignment_text}

КОД СТУДЕНТА:
```python
{code}
```

Требования: ввод/вывод, условные операторы, сравнение строк, циклы, строки, списки или кортежи.
Ответь СТРОГО JSON: {{"score": <0-100>, "feedback": "<комментарий на русском>"}}
"""
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    text = r.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
        score = max(0, min(100, int(data.get("score", 0))))
        return {"score": score, "feedback": data.get("feedback", "")}
    except (json.JSONDecodeError, ValueError):
        return {"score": 0, "feedback": "Ошибка разбора ответа модели."}


def save_to_sqlite(fio: str, group_name: str, credit: str, variant: int,
                   assignment: str, code: str, score: int, feedback: str) -> bool:
    """Сохраняет результат в SQLite на Google Drive (задание, решение, ФИО, группа, оценка, комментарий)."""
    try:
        from google.colab import drive
        if not os.path.exists("/content/drive/MyDrive"):
            drive.mount("/content/drive", force_remount=False)
        db_path = "/content/drive/MyDrive/exam_results.db"
    except Exception:
        return False
    if not os.path.exists("/content/drive/MyDrive"):
        return False
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fio TEXT,
                group_name TEXT,
                credit TEXT,
                variant INTEGER,
                assignment TEXT,
                code TEXT,
                score INTEGER,
                feedback TEXT,
                created_at TEXT
            )
        """)
        conn.execute(
            """INSERT INTO results (fio, group_name, credit, variant, assignment, code, score, feedback, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                (fio or "")[:500],
                (group_name or "")[:200],
                (credit or "")[:200],
                variant,
                (assignment or "")[:15000],
                (code or "")[:30000],
                score,
                (feedback or "")[:2000],
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
