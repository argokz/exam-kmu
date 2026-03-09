-- Подключитесь к серверу PostgreSQL и выполните один раз.
-- Пример: psql -h 145.249.247.138 -p 5440 -U postgres -W

-- 1) Создание базы (от имени суперпользователя, один раз):
CREATE DATABASE exam_kmu ENCODING 'UTF8';

-- 2) Подключитесь к exam_kmu и выполните ниже (например: psql -h ... -p 5440 -U postgres -d exam_kmu):

-- Таблица результатов контрольной
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

COMMENT ON TABLE results IS 'Результаты контрольной: ФИО, группа, кредит, вариант, код, оценка 0-100';
