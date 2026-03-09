import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime
from openai import OpenAI

BACKEND_KEY_URL = os.environ.get("EXAM_BACKEND_KEY_URL", "https://lan.avto-glass.kz/kmu.php")
BACKEND_TOKEN = os.environ.get("EXAM_BACKEND_TOKEN", "1ebecc126f74122ebfae6427b3f6e565753b87edfdb7be2a4ba4ba34e303edb8")
API_KEY = ""
try:
    import urllib.request
    req = urllib.request.Request(BACKEND_KEY_URL)
    token = BACKEND_TOKEN
    if token:
        req.add_header("X-Token", token)
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status == 200:
            data = json.loads(resp.read().decode())
            API_KEY = (data.get("api_key") or "").strip()
except Exception:
    pass
if not API_KEY:
    API_KEY = input("Введите OpenAI API ключ: ").strip()

client = OpenAI(api_key=API_KEY)
MODEL = "gpt-5-mini"


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value, min_v, max_v):
    return max(min_v, min(max_v, value))


def generate_assignment(variant: int) -> str:
    prompt = f"""Сгенерируй ОДНО понятное практическое задание по Python для варианта {variant}.

Уровень: базовый (для начинающих).
Тема: строго медицинская.

Ограничения по сложности:
- 1 сценарий и 1 основная цель;
- 2-3 входные строки максимум;
- ожидаемый объем решения 8-16 строк;
- без перегруженной математики и длинных веток условий.

Что обязательно должно быть в решении студента:
1) ввод через input() и вывод через print() c f-строками;
2) использование списка (list), накопление через append();
3) цикл for (можно с range());
4) проверка условий через if/elif/else;
5) обработка простого edge-case: пустой ввод / неизвестное значение / отсутствие совпадений.

Про match-case:
- можно использовать match-case, только если это делает решение проще и понятнее;
- если match-case усложняет задачу, достаточно if/elif/else.

Ограничения:
- не использовать dict, set, def и внешние библиотеки.

Формат ответа (строго):
1) Условие
2) Что вводится (по строкам и формат)
3) Что нужно сделать
4) Что вывести
5) Подсказка (1 короткая фраза, без готового решения)
6) Примеры (2-3 примера ввода/вывода, минимум один с edge-case)

Пиши только текст задания на русском языке.
Формулировки должны быть короткими, однозначными и понятными студенту с первого чтения.
Не пиши код решения и пояснения для преподавателя."""
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
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


def run_student_code(code: str, stdin_text: str = "\n\n\n\n\n", timeout: int = 5) -> dict:
    """Запускает код студента в отдельном процессе, возвращает stdout, stderr, returncode."""
    if not code or not code.strip():
        return {"stdout": "", "stderr": "", "returncode": -1, "error": "Код пустой"}
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
        )
        return {
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "returncode": proc.returncode,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timeout", "returncode": -1, "error": "Превышено время выполнения"}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "error": str(e)}


def evaluate_solution(assignment_text: str, code: str, variant: int) -> dict:
    """Проверяет решение: запускает код, затем ИИ даёт разбор ошибок и пример правильного решения."""
    run_result = run_student_code(code)
    prompt = f"""Ты проверяешь решение студента по Python. Код студента был реально выполнен (не только прочитан).

ЗАДАНИЕ (вариант {variant}):
{assignment_text}

КОД СТУДЕНТА:
```python
{code}
```

РЕЗУЛЬТАТ ВЫПОЛНЕНИЯ КОДА:
- returncode: {run_result["returncode"]}
- stdout: {repr(run_result["stdout"][:2000])}
- stderr: {repr(run_result["stderr"][:1000])}
- error: {run_result["error"]}

Оцени по фиксированной рубрике (100 баллов):
- Логика и корректность результата: 40
- Соответствие обязательным требованиям темы: 30
- Ввод/вывод и формат результата: 15
- Качество кода и устойчивость к типичным случаям: 15

Требования к ответу:
1) Обязательно дай конкретные причины снятия баллов (если есть).
2) В feedback сделай 2 части:
   - "Что сделано правильно: ..."
   - "Почему не максимум: ..."
3) errors_analysis — по пунктам, коротко и по делу.
4) correct_example — только если решение неполное/ошибочное, 10-25 строк.
5) deductions: список объектов вида {{"reason":"...","points":N}}.
6) criteria_scores: объект с ключами logic, requirements, io_format, quality.
7) Сначала выстави criteria_scores, затем score вычисли как:
   score = (logic + requirements + io_format + quality) - сумма штрафов deductions.
   Потом ограничь score диапазоном 0..100.
8) Не штрафуй за стиль и оформление, если логика верна и требования выполнены.
9) Если решение корректно по сути, score должен быть не ниже 90.
10) В errors_analysis пиши в формате: "Проблема -> эффект -> как исправить".

Ответ СТРОГО в формате JSON (один объект, без markdown):
{{
  "score": <0-100>,
  "feedback": "<общий комментарий на русском>",
  "errors_analysis": "<разбор ошибок по пунктам или «Ошибок нет»>",
  "deductions": [{{"reason":"...","points": <число>}}],
  "criteria_scores": {{"logic": <0-40>, "requirements": <0-30>, "io_format": <0-15>, "quality": <0-15>}},
  "correct_example": "<краткий пример правильного кода на Python или пустая строка, если решение засчитано>"
}}
"""
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    text = r.choices[0].message.content.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) > 1:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    text = text.strip()
    if "{" in text and "}" in text:
        text = text[text.find("{"): text.rfind("}") + 1]
    try:
        data = json.loads(text)
        raw_score = _to_int(data.get("score", 0), 0)
        criteria_scores = data.get("criteria_scores", {})
        if not isinstance(criteria_scores, dict):
            criteria_scores = {}
        deductions = data.get("deductions", [])
        if not isinstance(deductions, list):
            deductions = []
        norm_criteria = {
            "logic": _clamp(_to_int(criteria_scores.get("logic", 0), 0), 0, 40),
            "requirements": _clamp(_to_int(criteria_scores.get("requirements", 0), 0), 0, 30),
            "io_format": _clamp(_to_int(criteria_scores.get("io_format", 0), 0), 0, 15),
            "quality": _clamp(_to_int(criteria_scores.get("quality", 0), 0), 0, 15),
        }
        criteria_total = sum(norm_criteria.values())
        norm_deductions = []
        deduction_total = 0
        for item in deductions:
            if isinstance(item, dict):
                reason = str(item.get("reason", "Причина не указана")).strip() or "Причина не указана"
                points = _clamp(_to_int(item.get("points", 0), 0), 0, 100)
            else:
                reason = str(item)
                points = 0
            norm_deductions.append({"reason": reason, "points": points})
            deduction_total += points
        computed_score = _clamp(criteria_total - deduction_total, 0, 100)
        # Если модель прислала несогласованный score, берем вычисленный.
        if abs(raw_score - computed_score) > 5:
            score = computed_score
        else:
            score = _clamp(raw_score, 0, 100)
        return {
            "score": score,
            "feedback": data.get("feedback", ""),
            "errors_analysis": data.get("errors_analysis", ""),
            "criteria_scores": norm_criteria,
            "deductions": norm_deductions,
            "score_formula": f"{criteria_total} - {deduction_total} = {score}",
            "correct_example": data.get("correct_example", ""),
        }
    except (json.JSONDecodeError, ValueError):
        return {
            "score": 0,
            "feedback": "Не удалось разобрать ответ модели. Проверьте формат JSON-ответа.",
            "errors_analysis": f"Сырой ответ модели: {text[:1000]}",
            "criteria_scores": {"logic": 0, "requirements": 0, "io_format": 0, "quality": 0},
            "deductions": [],
            "score_formula": "0 - 0 = 0",
            "correct_example": "",
        }


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
