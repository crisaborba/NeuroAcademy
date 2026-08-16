import os
import sqlite3

from flask import current_app, g

DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "neuroacademy.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    bio TEXT DEFAULT '',
    plan TEXT DEFAULT 'Gratuito',
    role TEXT DEFAULT 'aluno',
    points INTEGER DEFAULT 0,
    streak INTEGER DEFAULT 0,
    email_notifications INTEGER DEFAULT 1,
    community_notifications INTEGER DEFAULT 1,
    news_notifications INTEGER DEFAULT 1,
    marketing_notifications INTEGER DEFAULT 0,
    email_verified INTEGER DEFAULT 0,
    email_verify_token TEXT,
    email_verify_sent_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS course (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    tag TEXT,
    tag_color TEXT DEFAULT '#4D7EFF',
    category TEXT,
    description TEXT,
    long_description TEXT,
    instructor TEXT DEFAULT 'NeuroAcademy',
    lessons_count INTEGER DEFAULT 0,
    hours_label TEXT DEFAULT '0h',
    level TEXT DEFAULT 'Iniciante',
    students_count INTEGER DEFAULT 0,
    rating REAL DEFAULT 4.8,
    price TEXT DEFAULT 'R$ 0',
    original_price TEXT,
    free INTEGER DEFAULT 1,
    img TEXT,
    is_marketplace INTEGER DEFAULT 0,
    featured INTEGER DEFAULT 0,
    content_complete INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS module (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES course(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    ord INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lesson (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL REFERENCES module(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES course(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    duration TEXT DEFAULT '10:00',
    ord INTEGER DEFAULT 0,
    free INTEGER DEFAULT 0,
    content_type TEXT DEFAULT 'video',
    content TEXT DEFAULT '',
    pass_threshold_pct INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS enrollment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES course(id) ON DELETE CASCADE,
    progress_pct INTEGER DEFAULT 0,
    enrolled_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, course_id)
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    lesson_id INTEGER NOT NULL REFERENCES lesson(id) ON DELETE CASCADE,
    done INTEGER DEFAULT 0,
    note TEXT DEFAULT '',
    UNIQUE(user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS certificate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES course(id) ON DELETE CASCADE,
    code TEXT UNIQUE NOT NULL,
    issued_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS blog_post (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    tag TEXT,
    excerpt TEXT,
    content TEXT,
    author TEXT DEFAULT 'NeuroAcademy',
    img TEXT,
    read_time TEXT DEFAULT '5 min',
    date_label TEXT,
    featured INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS news_article (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT,
    excerpt TEXT,
    content TEXT,
    source TEXT,
    time_label TEXT,
    trending INTEGER DEFAULT 0,
    img TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    desc TEXT,
    rating REAL DEFAULT 4.5,
    users_label TEXT,
    free INTEGER DEFAULT 1,
    color TEXT DEFAULT '#4D7EFF',
    img TEXT,
    tags TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS community_post (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    topic TEXT,
    title TEXT NOT NULL,
    body TEXT,
    likes INTEGER DEFAULT 0,
    tags TEXT DEFAULT '',
    pinned INTEGER DEFAULT 0,
    featured INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS community_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES community_post(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    body TEXT,
    likes INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS roadmap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#4D7EFF',
    duration_label TEXT,
    courses_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS roadmap_step (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roadmap_id INTEGER NOT NULL REFERENCES roadmap(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    duration TEXT,
    ord INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_roadmap_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    roadmap_id INTEGER NOT NULL REFERENCES roadmap(id) ON DELETE CASCADE,
    current_step_index INTEGER DEFAULT 1,
    UNIQUE(user_id, roadmap_id)
);

-- Indexes on every foreign-key-style column that list/lookup queries filter
-- or join on (repo.py). Without these, tables like lesson_progress or
-- enrollment do full scans once seed data is replaced with real volume.
CREATE INDEX IF NOT EXISTS idx_module_course ON module(course_id);
CREATE INDEX IF NOT EXISTS idx_lesson_course ON lesson(course_id);
CREATE INDEX IF NOT EXISTS idx_lesson_module ON lesson(module_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_user ON enrollment(user_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_course ON enrollment(course_id);
CREATE INDEX IF NOT EXISTS idx_lesson_progress_user ON lesson_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_lesson_progress_lesson ON lesson_progress(lesson_id);
CREATE INDEX IF NOT EXISTS idx_certificate_user ON certificate(user_id);
CREATE INDEX IF NOT EXISTS idx_community_post_user ON community_post(user_id);
CREATE INDEX IF NOT EXISTS idx_community_comment_post ON community_comment(post_id);
CREATE INDEX IF NOT EXISTS idx_community_comment_user ON community_comment(user_id);
CREATE INDEX IF NOT EXISTS idx_roadmap_step_roadmap ON roadmap_step(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_user_roadmap_progress_user ON user_roadmap_progress(user_id);

-- Interactive in-lesson questions (covers the spec's "Interação", "Atividade"
-- and "Verificação" blocks -- all of them are, structurally, single-answer
-- multiple choice with feedback). `kind` distinguishes their pedagogical
-- role; only 'verification' questions gate lesson completion.
CREATE TABLE IF NOT EXISTS lesson_question (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL REFERENCES lesson(id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'verification',
    prompt TEXT NOT NULL,
    ord INTEGER DEFAULT 0,
    reward_xp INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lesson_question_option (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES lesson_question(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    is_correct INTEGER DEFAULT 0,
    feedback TEXT DEFAULT '',
    ord INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_question_answer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES lesson_question(id) ON DELETE CASCADE,
    option_id INTEGER REFERENCES lesson_question_option(id) ON DELETE SET NULL,
    is_correct INTEGER DEFAULT 0,
    answered_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_lesson_question_lesson ON lesson_question(lesson_id);
CREATE INDEX IF NOT EXISTS idx_lesson_question_option_question ON lesson_question_option(question_id);
CREATE INDEX IF NOT EXISTS idx_user_question_answer_user ON user_question_answer(user_id);
CREATE INDEX IF NOT EXISTS idx_user_question_answer_question ON user_question_answer(question_id);

-- Course-level final assessment (schema prepared now; not yet seeded with
-- the 20-question exam from the spec -- see the audit report). This is
-- intentionally separate from lesson_question: it has different rules
-- (course-wide, multiple attempts, gates the certificate).
CREATE TABLE IF NOT EXISTS course_assessment_question (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES course(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    ord INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS course_assessment_option (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES course_assessment_question(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    is_correct INTEGER DEFAULT 0,
    ord INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_assessment_attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES course(id) ON DELETE CASCADE,
    score_pct INTEGER DEFAULT 0,
    passed INTEGER DEFAULT 0,
    attempt_number INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_course_assessment_question_course ON course_assessment_question(course_id);
CREATE INDEX IF NOT EXISTS idx_user_assessment_attempt_user ON user_assessment_attempt(user_id);

-- ─────────────────────────────────────────────────────────────────────────
-- SCHEMA CHANGELOG -- Sistema de Aulas, Fase 1 (fundação técnica)
-- Ref.: NEUROACADEMY_ESPECIFICACAO_TECNICA_SISTEMA_AULAS_v1.0.md, Seções 8-15.
-- Todas as adições abaixo são aditivas (CREATE TABLE IF NOT EXISTS / colunas
-- com DEFAULT quando aplicável). Nenhuma tabela/coluna existente acima foi
-- removida ou alterada. Ver relatório da Fase 1 para detalhes e rollback.
-- ─────────────────────────────────────────────────────────────────────────

-- Composição de blocos de uma aula (Opção D -- Seção 8/10 da spec técnica).
-- `payload` é sempre um objeto JSON; validado em Python (validators.py)
-- antes de qualquer INSERT/UPDATE -- nunca tratado como JSON arbitrário
-- pela aplicação, mesmo que o SQLite não force um schema sobre ele.
-- `lesson.content` NÃO é removida: continua existindo como fallback (ver
-- repo.list_lesson_blocks / rota aula() em routes.py e migrate_lessons_to_blocks.py).
CREATE TABLE IF NOT EXISTS lesson_block (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL REFERENCES lesson(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    ord INTEGER DEFAULT 0,
    payload TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_lesson_block_lesson ON lesson_block(lesson_id);

-- Avaliação de módulo -- Seção 15 da spec técnica. Deliberadamente uma
-- tabela nova e distinta de course_assessment_* (Decisão 2, Seção 30.2):
-- course_assessment_* passa a ser exclusivamente avaliação final do curso;
-- module_assessment_* é exclusivamente avaliação por módulo. Mesmo padrão
-- estrutural (question/option/attempt), granularidade diferente.
CREATE TABLE IF NOT EXISTS module_assessment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL REFERENCES module(id) ON DELETE CASCADE,
    pass_threshold_pct INTEGER DEFAULT 70
);
CREATE TABLE IF NOT EXISTS module_assessment_question (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_assessment_id INTEGER NOT NULL REFERENCES module_assessment(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    ord INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS module_assessment_option (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES module_assessment_question(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    is_correct INTEGER DEFAULT 0,
    ord INTEGER DEFAULT 0
);
-- Tentativas ilimitadas (regra de produto: aprovação >=70%, sem limite de
-- tentativas). Cada tentativa gera uma linha nova (attempt_number
-- incremental) -- reaproveita o precedente já existente em
-- user_assessment_attempt.attempt_number (Seção 15 da spec técnica).
CREATE TABLE IF NOT EXISTS user_module_assessment_attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    module_assessment_id INTEGER NOT NULL REFERENCES module_assessment(id) ON DELETE CASCADE,
    score_pct INTEGER DEFAULT 0,
    passed INTEGER DEFAULT 0,
    attempt_number INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_module_assessment_module ON module_assessment(module_id);
CREATE INDEX IF NOT EXISTS idx_module_assessment_question_assessment ON module_assessment_question(module_assessment_id);
CREATE INDEX IF NOT EXISTS idx_module_assessment_option_question ON module_assessment_option(question_id);
CREATE INDEX IF NOT EXISTS idx_user_module_assessment_attempt_user ON user_module_assessment_attempt(user_id);
CREATE INDEX IF NOT EXISTS idx_user_module_assessment_attempt_assessment ON user_module_assessment_attempt(module_assessment_id);

-- ─────────────────────────────────────────────────────────────────────────
-- SCHEMA CHANGELOG -- Sistema Real de Gamificação (Conquistas + XP)
-- Ref.: pedido "NEUROACADEMY — IMPLEMENTAÇÃO DO SISTEMA REAL DE GAMIFICAÇÃO".
-- Reaproveita user.points como o total de XP já existente (usado desde
-- antes por /comunidade para o leaderboard `top_members`) em vez de criar
-- um segundo contador paralelo -- ver gamification.py. As tabelas abaixo
-- existem para persistir *conquistas* e o *histórico* de XP (auditoria +
-- idempotência), não para substituir user.points.
-- ─────────────────────────────────────────────────────────────────────────

-- Catálogo de conquistas da plataforma. Uma linha por conquista possível
-- (não por usuário -- isso é `user_achievement` abaixo). `lesson_id` liga
-- uma conquista de aula à aula que a desbloqueia (nullable: conquistas de
-- módulo/curso/Platina não têm uma aula única). `is_platinum` marca a
-- conquista máxima (há no máximo uma ativa por vez, mas não é enforced por
-- constraint para não impedir uma futura re-configuração administrativa).
-- `mascot_image_url` fica pronta para receber uma ilustração real do
-- mascote por conquista (Seção 12 do pedido); até lá, `mascot_emoji` é o
-- fallback visual usado pelo popup.
CREATE TABLE IF NOT EXISTS achievement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'lesson',   -- lesson | module | course | platinum
    xp INTEGER NOT NULL DEFAULT 0,
    rarity TEXT NOT NULL DEFAULT 'Comum',      -- Comum|Incomum|Rara|Épica|Lendária|Platina
    unlock_criteria TEXT NOT NULL DEFAULT '',  -- descrição legível do critério (documentação/UI)
    course_id INTEGER REFERENCES course(id) ON DELETE CASCADE,
    module_id INTEGER REFERENCES module(id) ON DELETE CASCADE,
    lesson_id INTEGER REFERENCES lesson(id) ON DELETE CASCADE,
    is_platinum INTEGER NOT NULL DEFAULT 0,
    mascot_emoji TEXT NOT NULL DEFAULT '🏆',
    mascot_image_url TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Relação usuário↔conquista. UNIQUE(user_id, achievement_id) é o que
-- IMPEDE fisicamente a duplicação (Seção 1 do pedido: "Se o usuário
-- desbloquear uma conquista duas vezes, ela deve continuar sendo apenas
-- uma conquista") -- não depende de nenhuma checagem em Python.
CREATE TABLE IF NOT EXISTS user_achievement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    achievement_id INTEGER NOT NULL REFERENCES achievement(id) ON DELETE CASCADE,
    unlocked_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, achievement_id)
);

-- Histórico/ledger de XP. `reason_code` é a chave de idempotência: cada
-- ação que concede XP usa um reason_code estável (ex.:
-- "question:42:correct", "achievement:iniciado_digital") e
-- UNIQUE(user_id, reason_code) garante que a MESMA ação nunca concede XP
-- duas vezes para o mesmo usuário (Seção 3 do pedido, "idempotência
-- obrigatória") -- recarregar a página, reenviar o POST, ou clicar várias
-- vezes só resulta em novas tentativas de INSERT que o banco ignora.
-- `lesson_id` (quando aplicável) permite somar "quanto XP esta aula
-- especificamente já rendeu" para exibir na tela de conclusão sem valores
-- fixos (Seção 8 do pedido).
CREATE TABLE IF NOT EXISTS xp_transaction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    reason_code TEXT NOT NULL,
    reason_label TEXT NOT NULL,
    source_type TEXT,                          -- 'question' | 'achievement' | ...
    source_id INTEGER,
    lesson_id INTEGER REFERENCES lesson(id) ON DELETE SET NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, reason_code)
);

CREATE INDEX IF NOT EXISTS idx_achievement_lesson ON achievement(lesson_id);
CREATE INDEX IF NOT EXISTS idx_achievement_course ON achievement(course_id);
CREATE INDEX IF NOT EXISTS idx_user_achievement_user ON user_achievement(user_id);
CREATE INDEX IF NOT EXISTS idx_user_achievement_achievement ON user_achievement(achievement_id);
CREATE INDEX IF NOT EXISTS idx_xp_transaction_user ON xp_transaction(user_id);
CREATE INDEX IF NOT EXISTS idx_xp_transaction_lesson ON xp_transaction(lesson_id);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.executescript(SCHEMA)
        # `CREATE TABLE IF NOT EXISTS` does not add columns to a table that
        # already existed before this column was introduced (only fresh
        # databases get it "for free" from SCHEMA above). This keeps
        # existing neuroacademy.db files (dev/prod) working without a
        # manual migration step -- safe to run every boot.
        try:
            conn.execute("ALTER TABLE lesson_question ADD COLUMN reward_xp INTEGER NOT NULL DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.close()
    app.teardown_appcontext(close_db)
