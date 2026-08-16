import json
import secrets
import sqlite3

from werkzeug.security import generate_password_hash

from db import get_db
from validators import BlockValidationError, validate_block

IntegrityError = sqlite3.IntegrityError
from models import (
    Achievement, BlogPost, Certificate, CommunityComment, CommunityPost, Course, Enrollment,
    Lesson, LessonProgress, Module, NewsArticle, Roadmap, RoadmapStep, Tool, User,
)


# ───────────────────────── users ─────────────────────────

def get_user_by_id(user_id):
    row = get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    return User(row) if row else None


def get_user_by_email(email):
    row = get_db().execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()
    return User(row) if row else None


def create_user(name, username, email, password, **extra):
    db = get_db()
    verify_token = secrets.token_urlsafe(32)
    cur = db.execute(
        "INSERT INTO user (name, username, email, password_hash, plan, role, bio, points, streak, "
        "email_verified, email_verify_token, email_verify_sent_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,0,?,datetime('now'))",
        (name, username, email, generate_password_hash(password),
         extra.get("plan", "Gratuito"), extra.get("role", "aluno"),
         extra.get("bio", ""), extra.get("points", 0), extra.get("streak", 0),
         verify_token),
    )
    db.commit()
    return get_user_by_id(cur.lastrowid)


def get_user_by_verify_token(token):
    if not token:
        return None
    row = get_db().execute("SELECT * FROM user WHERE email_verify_token = ?", (token,)).fetchone()
    return User(row) if row else None


def mark_email_verified(user_id):
    db = get_db()
    db.execute(
        "UPDATE user SET email_verified = 1, email_verify_token = NULL WHERE id = ?", (user_id,)
    )
    db.commit()


def update_user(user_id, **fields):
    if not fields:
        return
    db = get_db()
    cols = ", ".join(f"{k} = ?" for k in fields)
    db.execute(f"UPDATE user SET {cols} WHERE id = ?", (*fields.values(), user_id))
    db.commit()


def set_password(user_id, password):
    update_user(user_id, password_hash=generate_password_hash(password))


def increment_user_points(user_id, delta):
    """Incremento atômico (`points = points + ?`), diferente do padrão
    read-modify-write já usado em pontos de comunidade (routes.py:
    `points=(user.points or 0) + 5`). Usado pelo sistema de gamificação
    (gamification.py) para não perder incrementos concorrentes -- a soma
    já acontece no SQL, não em Python."""
    if not delta:
        return
    db = get_db()
    db.execute("UPDATE user SET points = points + ? WHERE id = ?", (delta, user_id))
    db.commit()


def top_members(limit=5):
    rows = get_db().execute(
        "SELECT * FROM user WHERE role = 'aluno' ORDER BY points DESC LIMIT ?", (limit,)
    ).fetchall()
    return [User(r) for r in rows]


def count_users():
    return get_db().execute("SELECT COUNT(*) c FROM user").fetchone()["c"]


def recent_users(limit=6):
    rows = get_db().execute("SELECT * FROM user ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [User(r) for r in rows]


# ───────────────────────── courses ─────────────────────────

def list_courses(is_marketplace=False, category=None, level=None, q=None):
    sql = "SELECT * FROM course WHERE is_marketplace = ?"
    params = [1 if is_marketplace else 0]
    if category and category not in ("Todos", "Todas"):
        sql += " AND category = ?"
        params.append(category)
    if level and level != "Todos":
        sql += " AND level = ?"
        params.append(level)
    if q:
        sql += " AND title LIKE ?"
        params.append(f"%{q}%")
    sql += " ORDER BY id"
    rows = get_db().execute(sql, params).fetchall()
    return [Course(r) for r in rows]


def get_course(course_id):
    row = get_db().execute("SELECT * FROM course WHERE id = ?", (course_id,)).fetchone()
    return Course(row) if row else None


def get_course_with_modules(course_id):
    course = get_course(course_id)
    if not course:
        return None
    course.modules = list_modules_with_lessons(course_id)
    return course


def list_modules_with_lessons(course_id):
    mrows = get_db().execute(
        "SELECT * FROM module WHERE course_id = ? ORDER BY ord", (course_id,)
    ).fetchall()
    modules = []
    for mr in mrows:
        module = Module(mr)
        lrows = get_db().execute(
            "SELECT * FROM lesson WHERE module_id = ? ORDER BY ord", (module.id,)
        ).fetchall()
        module.lessons = [Lesson(lr) for lr in lrows]
        modules.append(module)
    return modules


def list_lessons_for_course(course_id):
    rows = get_db().execute(
        "SELECT * FROM lesson WHERE course_id = ? ORDER BY id", (course_id,)
    ).fetchall()
    return [Lesson(r) for r in rows]


def get_lesson(lesson_id):
    row = get_db().execute("SELECT * FROM lesson WHERE id = ?", (lesson_id,)).fetchone()
    return Lesson(row) if row else None


def create_course(**fields):
    db = get_db()
    cols = ", ".join(fields.keys())
    marks = ", ".join(["?"] * len(fields))
    cur = db.execute(f"INSERT INTO course ({cols}) VALUES ({marks})", list(fields.values()))
    db.commit()
    return get_course(cur.lastrowid)


def count_courses():
    return get_db().execute("SELECT COUNT(*) c FROM course").fetchone()["c"]


def count_learnable_courses():
    """Courses actually enrollable/learnable on the platform today (excludes
    marketplace listings, which have no real purchase flow yet)."""
    return get_db().execute(
        "SELECT COUNT(*) c FROM course WHERE is_marketplace = 0"
    ).fetchone()["c"]


def count_lessons():
    return get_db().execute("SELECT COUNT(*) c FROM lesson").fetchone()["c"]


def avg_course_rating():
    row = get_db().execute("SELECT AVG(rating) a FROM course").fetchone()
    return row["a"] or 0


def recent_courses(limit=6):
    rows = get_db().execute("SELECT * FROM course ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [Course(r) for r in rows]


# ───────────────────────── enrollments / progress ─────────────────────────

def get_enrollment(user_id, course_id):
    row = get_db().execute(
        "SELECT * FROM enrollment WHERE user_id = ? AND course_id = ?", (user_id, course_id)
    ).fetchone()
    return Enrollment(row) if row else None


def create_enrollment(user_id, course_id):
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO enrollment (user_id, course_id, progress_pct) VALUES (?,?,0)",
        (user_id, course_id),
    )
    db.commit()
    return get_enrollment(user_id, course_id)


def update_enrollment_progress(user_id, course_id, pct):
    db = get_db()
    db.execute(
        "UPDATE enrollment SET progress_pct = ? WHERE user_id = ? AND course_id = ?",
        (pct, user_id, course_id),
    )
    db.commit()


def list_enrollments_for_user(user_id):
    rows = get_db().execute(
        "SELECT * FROM enrollment WHERE user_id = ? ORDER BY enrolled_at DESC", (user_id,)
    ).fetchall()
    result = []
    for r in rows:
        e = Enrollment(r)
        e.course = get_course(e.course_id)
        result.append(e)
    return result


def get_lesson_progress(user_id, lesson_id):
    row = get_db().execute(
        "SELECT * FROM lesson_progress WHERE user_id = ? AND lesson_id = ?", (user_id, lesson_id)
    ).fetchone()
    return LessonProgress(row) if row else None


def done_lesson_ids_for_user(user_id):
    rows = get_db().execute(
        "SELECT lesson_id FROM lesson_progress WHERE user_id = ? AND done = 1", (user_id,)
    ).fetchall()
    return {r["lesson_id"] for r in rows}


def toggle_lesson_done(user_id, lesson_id):
    db = get_db()
    existing = get_lesson_progress(user_id, lesson_id)
    if existing:
        new_done = 0 if existing.done else 1
        db.execute(
            "UPDATE lesson_progress SET done = ? WHERE user_id = ? AND lesson_id = ?",
            (new_done, user_id, lesson_id),
        )
    else:
        new_done = 1
        db.execute(
            "INSERT INTO lesson_progress (user_id, lesson_id, done, note) VALUES (?,?,1,'')",
            (user_id, lesson_id),
        )
    db.commit()
    return bool(new_done)


def set_lesson_note(user_id, lesson_id, note):
    db = get_db()
    existing = get_lesson_progress(user_id, lesson_id)
    if existing:
        db.execute(
            "UPDATE lesson_progress SET note = ? WHERE user_id = ? AND lesson_id = ?",
            (note, user_id, lesson_id),
        )
    else:
        db.execute(
            "INSERT INTO lesson_progress (user_id, lesson_id, done, note) VALUES (?,?,0,?)",
            (user_id, lesson_id, note),
        )
    db.commit()


def recompute_progress(user_id, course_id):
    lessons = list_lessons_for_course(course_id)
    if not lessons:
        return 0
    done_ids = done_lesson_ids_for_user(user_id)
    lesson_ids = {l.id for l in lessons}
    done_count = len(done_ids & lesson_ids)
    pct = int(done_count / len(lessons) * 100)
    if get_enrollment(user_id, course_id):
        update_enrollment_progress(user_id, course_id, pct)
    return pct


# ───────────────────────── certificates ─────────────────────────

def get_certificate(user_id, course_id):
    row = get_db().execute(
        "SELECT * FROM certificate WHERE user_id = ? AND course_id = ?", (user_id, course_id)
    ).fetchone()
    return Certificate(row) if row else None


def create_certificate(user_id, course_id):
    db = get_db()
    code = secrets.token_hex(8).upper()
    db.execute(
        "INSERT INTO certificate (user_id, course_id, code) VALUES (?,?,?)",
        (user_id, course_id, code),
    )
    db.commit()
    return get_certificate(user_id, course_id)


def list_certificates_for_user(user_id):
    rows = get_db().execute(
        "SELECT * FROM certificate WHERE user_id = ? ORDER BY issued_at DESC", (user_id,)
    ).fetchall()
    result = []
    for r in rows:
        c = Certificate(r)
        c.course = get_course(c.course_id)
        result.append(c)
    return result


def count_certificates():
    return get_db().execute("SELECT COUNT(*) c FROM certificate").fetchone()["c"]


# ───────────────────────── blog ─────────────────────────

def list_blog_posts(tag=None):
    sql = "SELECT * FROM blog_post"
    params = []
    if tag and tag != "Todos":
        sql += " WHERE tag = ?"
        params.append(tag)
    sql += " ORDER BY created_at DESC"
    rows = get_db().execute(sql, params).fetchall()
    return [BlogPost(r) for r in rows]


def get_blog_post(post_id):
    row = get_db().execute("SELECT * FROM blog_post WHERE id = ?", (post_id,)).fetchone()
    return BlogPost(row) if row else None


def get_featured_blog_post():
    row = get_db().execute("SELECT * FROM blog_post WHERE featured = 1 LIMIT 1").fetchone()
    return BlogPost(row) if row else None


def other_blog_posts(exclude_id, limit=3):
    rows = get_db().execute(
        "SELECT * FROM blog_post WHERE id != ? ORDER BY created_at DESC LIMIT ?", (exclude_id, limit)
    ).fetchall()
    return [BlogPost(r) for r in rows]


# ───────────────────────── news ─────────────────────────

def list_news(category=None):
    sql = "SELECT * FROM news_article"
    params = []
    if category and category not in ("Todas", "Todos"):
        sql += " WHERE category = ?"
        params.append(category)
    sql += " ORDER BY created_at DESC"
    rows = get_db().execute(sql, params).fetchall()
    return [NewsArticle(r) for r in rows]


def list_trending_news():
    rows = get_db().execute("SELECT * FROM news_article WHERE trending = 1").fetchall()
    return [NewsArticle(r) for r in rows]


# ───────────────────────── tools ─────────────────────────

def list_tools(category=None, q=None):
    sql = "SELECT * FROM tool WHERE 1=1"
    params = []
    if category and category not in ("Todas", "Todos"):
        sql += " AND category = ?"
        params.append(category)
    if q:
        sql += " AND name LIKE ?"
        params.append(f"%{q}%")
    sql += " ORDER BY id"
    rows = get_db().execute(sql, params).fetchall()
    return [Tool(r) for r in rows]


# ───────────────────────── community ─────────────────────────

def list_community_posts(topic=None):
    sql = "SELECT * FROM community_post"
    params = []
    if topic and topic != "Todos":
        sql += " WHERE topic = ?"
        params.append(topic)
    sql += " ORDER BY pinned DESC, created_at DESC"
    rows = get_db().execute(sql, params).fetchall()
    posts = []
    for r in rows:
        p = CommunityPost(r)
        p.author_user = get_user_by_id(p.user_id)
        p.comment_count = get_db().execute(
            "SELECT COUNT(*) c FROM community_comment WHERE post_id = ?", (p.id,)
        ).fetchone()["c"]
        posts.append(p)
    return posts


def get_community_post(post_id):
    row = get_db().execute("SELECT * FROM community_post WHERE id = ?", (post_id,)).fetchone()
    return CommunityPost(row) if row else None


def create_community_post(user_id, topic, title, body):
    db = get_db()
    db.execute(
        "INSERT INTO community_post (user_id, topic, title, body, likes, tags) VALUES (?,?,?,?,0,'')",
        (user_id, topic, title, body),
    )
    db.commit()


def like_post(post_id):
    db = get_db()
    db.execute("UPDATE community_post SET likes = likes + 1 WHERE id = ?", (post_id,))
    db.commit()
    row = db.execute("SELECT likes FROM community_post WHERE id = ?", (post_id,)).fetchone()
    return row["likes"] if row else 0


def add_comment(post_id, user_id, body):
    db = get_db()
    db.execute(
        "INSERT INTO community_comment (post_id, user_id, body, likes) VALUES (?,?,?,0)",
        (post_id, user_id, body),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM community_comment WHERE post_id = ? ORDER BY id DESC LIMIT 1", (post_id,)
    ).fetchone()
    c = CommunityComment(row)
    c.author = get_user_by_id(user_id)
    return c


def count_posts_by_user(user_id):
    return get_db().execute(
        "SELECT COUNT(*) c FROM community_post WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]


def count_comments_by_user(user_id):
    return get_db().execute(
        "SELECT COUNT(*) c FROM community_comment WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]


# ───────────────────────── roadmaps ─────────────────────────

def list_roadmaps():
    rows = get_db().execute("SELECT * FROM roadmap ORDER BY id").fetchall()
    roadmaps = []
    for r in rows:
        rm = Roadmap(r)
        srows = get_db().execute(
            "SELECT * FROM roadmap_step WHERE roadmap_id = ? ORDER BY ord", (rm.id,)
        ).fetchall()
        rm.steps = [RoadmapStep(sr) for sr in srows]
        roadmaps.append(rm)
    return roadmaps


def get_roadmap(roadmap_id):
    row = get_db().execute("SELECT * FROM roadmap WHERE id = ?", (roadmap_id,)).fetchone()
    if not row:
        return None
    rm = Roadmap(row)
    srows = get_db().execute(
        "SELECT * FROM roadmap_step WHERE roadmap_id = ? ORDER BY ord", (rm.id,)
    ).fetchall()
    rm.steps = [RoadmapStep(sr) for sr in srows]
    return rm


def get_roadmap_progress_map(user_id):
    rows = get_db().execute(
        "SELECT roadmap_id, current_step_index FROM user_roadmap_progress WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return {r["roadmap_id"]: r["current_step_index"] for r in rows}


def advance_roadmap(user_id, roadmap_id, total_steps):
    db = get_db()
    row = db.execute(
        "SELECT * FROM user_roadmap_progress WHERE user_id = ? AND roadmap_id = ?",
        (user_id, roadmap_id),
    ).fetchone()
    if row:
        new_idx = min(row["current_step_index"] + 1, total_steps)
        db.execute(
            "UPDATE user_roadmap_progress SET current_step_index = ? WHERE user_id = ? AND roadmap_id = ?",
            (new_idx, user_id, roadmap_id),
        )
    else:
        new_idx = min(2, total_steps)
        db.execute(
            "INSERT INTO user_roadmap_progress (user_id, roadmap_id, current_step_index) VALUES (?,?,?)",
            (user_id, roadmap_id, new_idx),
        )
    db.commit()
    return new_idx


# ───────────────────────── lesson questions (interactions/activities/verification) ─────────────────────────

def list_lesson_questions(lesson_id, kind=None):
    sql = "SELECT * FROM lesson_question WHERE lesson_id = ?"
    params = [lesson_id]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " ORDER BY ord"
    rows = get_db().execute(sql, params).fetchall()
    questions = []
    for r in rows:
        q = dict(r)
        opts = get_db().execute(
            "SELECT * FROM lesson_question_option WHERE question_id = ? ORDER BY ord", (q["id"],)
        ).fetchall()
        q["options"] = [dict(o) for o in opts]
        questions.append(q)
    return questions


def get_lesson_question(question_id):
    row = get_db().execute("SELECT * FROM lesson_question WHERE id = ?", (question_id,)).fetchone()
    return dict(row) if row else None


def get_question_option(option_id):
    row = get_db().execute(
        "SELECT * FROM lesson_question_option WHERE id = ?", (option_id,)
    ).fetchone()
    return dict(row) if row else None


def user_answer_for_question(user_id, question_id):
    row = get_db().execute(
        "SELECT * FROM user_question_answer WHERE user_id = ? AND question_id = ?",
        (user_id, question_id),
    ).fetchone()
    return dict(row) if row else None


def submit_question_answer(user_id, question_id, option_id):
    """Grades an answer server-side (the client never receives which option
    is correct until after submitting) and stores/overwrites the result."""
    option = get_question_option(option_id)
    if not option or option["question_id"] != question_id:
        return None
    is_correct = 1 if option["is_correct"] else 0
    db = get_db()
    db.execute(
        "INSERT INTO user_question_answer (user_id, question_id, option_id, is_correct) "
        "VALUES (?,?,?,?) "
        "ON CONFLICT(user_id, question_id) DO UPDATE SET option_id=excluded.option_id, "
        "is_correct=excluded.is_correct, answered_at=datetime('now')",
        (user_id, question_id, option_id, is_correct),
    )
    db.commit()
    return {"is_correct": bool(is_correct), "feedback": option["feedback"]}


def user_verification_progress(user_id, lesson_id):
    """Returns (answered_count, total_count, correct_pct) for the
    'verification' questions of a lesson -- used to gate completion."""
    questions = list_lesson_questions(lesson_id, kind="verification")
    total = len(questions)
    if total == 0:
        return 0, 0, 100  # no verification defined -> nothing to gate on
    answered = 0
    correct = 0
    for q in questions:
        ans = user_answer_for_question(user_id, q["id"])
        if ans:
            answered += 1
            if ans["is_correct"]:
                correct += 1
    pct = int(correct / total * 100) if total else 100
    return answered, total, pct


def lesson_meets_completion_criteria(user_id, lesson_id, pass_threshold_pct):
    answered, total, pct = user_verification_progress(user_id, lesson_id)
    if total == 0:
        return True  # lesson has no verification questions -- unchanged legacy behavior
    if answered < total:
        return False
    return pct >= (pass_threshold_pct or 0)


def user_answers_for_lesson(user_id, lesson_id):
    """Todas as respostas do usuário para perguntas desta aula, indexadas por
    question_id -- usado para reidratar o estado das perguntas ao renderizar
    aula() (persistência ao F5, Seção 5/23 da spec técnica)."""
    rows = get_db().execute(
        "SELECT a.* FROM user_question_answer a "
        "JOIN lesson_question q ON q.id = a.question_id "
        "WHERE a.user_id = ? AND q.lesson_id = ?",
        (user_id, lesson_id),
    ).fetchall()
    return {r["question_id"]: dict(r) for r in rows}


# ───────────────────────── lesson blocks (Fase 1 -- Sistema de Aulas) ─────────────────────────
# Ref.: NEUROACADEMY_ESPECIFICACAO_TECNICA_SISTEMA_AULAS_v1.0.md, Seções 8-11.
# `payload` é sempre validado (validators.validate_block) antes de qualquer
# INSERT/UPDATE. Leitura (list_lesson_blocks) nunca falha por causa de um
# bloco malformado -- ele é reportado, não deixa a página inteira quebrar
# (Seção 11: "Não permita que um bloco inválido cause uma falha completa").

def lesson_has_blocks(lesson_id):
    row = get_db().execute(
        "SELECT 1 FROM lesson_block WHERE lesson_id = ? LIMIT 1", (lesson_id,)
    ).fetchone()
    return row is not None


def insert_lesson_block(lesson_id, block_type, ord, payload):
    """Valida e persiste um bloco. Levanta validators.BlockValidationError
    se o payload for inválido -- nunca insere um bloco não validado."""
    validate_block(block_type, payload)
    db = get_db()
    cur = db.execute(
        "INSERT INTO lesson_block (lesson_id, type, ord, payload) VALUES (?,?,?,?)",
        (lesson_id, block_type, ord, json.dumps(payload, ensure_ascii=False)),
    )
    db.commit()
    return cur.lastrowid


def list_lesson_blocks(lesson_id):
    """Devolve os blocos da aula, ordenados, com `payload` já deserializado
    e uma flag `valid` por bloco. Um bloco com JSON corrompido ou payload
    que não passa mais na validação atual é marcado `valid=False` e
    devolvido com `payload={}`, em vez de derrubar a função inteira --
    o renderizador (Etapa 3) decide como lidar com blocos inválidos
    (pular, mostrar aviso), a leitura nunca lança exceção."""
    rows = get_db().execute(
        "SELECT * FROM lesson_block WHERE lesson_id = ? ORDER BY ord, id", (lesson_id,)
    ).fetchall()
    blocks = []
    for r in rows:
        block = dict(r)
        try:
            payload = json.loads(block["payload"])
            validate_block(block["type"], payload)
            block["payload"] = payload
            block["valid"] = True
        except (ValueError, BlockValidationError):
            block["payload"] = {}
            block["valid"] = False
        blocks.append(block)
    return blocks


def list_all_lessons():
    rows = get_db().execute("SELECT * FROM lesson ORDER BY id").fetchall()
    return [Lesson(r) for r in rows]


# ───────────────────────── modules ─────────────────────────

def get_module(module_id):
    row = get_db().execute("SELECT * FROM module WHERE id = ?", (module_id,)).fetchone()
    return Module(row) if row else None


def module_progress(user_id, module_id):
    """% de aulas concluídas do módulo (0-100), usado para uma futura barra
    de progresso de módulo (Fase 5 do plano -- não renderizado nesta fase,
    função de dados disponível desde já). Definição de "módulo concluído"
    (Seção 19 da spec técnica) exige também avaliação de módulo aprovada
    quando ela existir; ver module_meets_completion_criteria."""
    lrows = get_db().execute(
        "SELECT id FROM lesson WHERE module_id = ?", (module_id,)
    ).fetchall()
    lesson_ids = {r["id"] for r in lrows}
    if not lesson_ids:
        return 0
    done_ids = done_lesson_ids_for_user(user_id)
    done_count = len(lesson_ids & done_ids)
    return int(done_count / len(lesson_ids) * 100)


def module_meets_completion_criteria(user_id, module_id):
    """Módulo concluído = todas as aulas concluídas E (sem module_assessment
    cadastrada OU última tentativa com passed=1) -- Seção 19 da spec técnica.
    Sempre recalculado a partir da fonte primária, nunca lido de um campo
    cacheado (mesmo padrão de lesson_meets_completion_criteria)."""
    if module_progress(user_id, module_id) < 100:
        return False
    assessment = get_module_assessment_for_module(module_id)
    if not assessment:
        return True
    attempt = latest_module_assessment_attempt(user_id, assessment["id"])
    return bool(attempt and attempt["passed"])


# ───────────────────────── module assessments (Fase 1 -- fundação) ─────────────────────────
# Ref.: Seção 15 da spec técnica. Fundação de dados + correção server-side;
# UI completa é de uma fase posterior (Etapa 6 da tarefa desta fase).

def get_module_assessment_for_module(module_id):
    row = get_db().execute(
        "SELECT * FROM module_assessment WHERE module_id = ?", (module_id,)
    ).fetchone()
    return dict(row) if row else None


def create_module_assessment(module_id, pass_threshold_pct=70):
    db = get_db()
    cur = db.execute(
        "INSERT INTO module_assessment (module_id, pass_threshold_pct) VALUES (?,?)",
        (module_id, pass_threshold_pct),
    )
    db.commit()
    return get_module_assessment_for_module(module_id)


def add_module_assessment_question(module_assessment_id, prompt, ord, options):
    """`options` é uma lista de dicts {label, is_correct}. Levanta ValueError
    se não houver nenhuma alternativa correta (mesma checagem recomendada
    pela Seção 11 para lesson_question, reaproveitada aqui)."""
    if not options or not any(o.get("is_correct") for o in options):
        raise ValueError("A questão precisa de ao menos uma alternativa correta.")
    db = get_db()
    qid = db.execute(
        "INSERT INTO module_assessment_question (module_assessment_id, prompt, ord) "
        "VALUES (?,?,?)",
        (module_assessment_id, prompt, ord),
    ).lastrowid
    for opt_ord, opt in enumerate(options):
        db.execute(
            "INSERT INTO module_assessment_option (question_id, label, is_correct, ord) "
            "VALUES (?,?,?,?)",
            (qid, opt["label"], 1 if opt.get("is_correct") else 0, opt_ord),
        )
    db.commit()
    return qid


def list_module_assessment_questions(module_assessment_id):
    rows = get_db().execute(
        "SELECT * FROM module_assessment_question WHERE module_assessment_id = ? ORDER BY ord",
        (module_assessment_id,),
    ).fetchall()
    questions = []
    for r in rows:
        q = dict(r)
        opts = get_db().execute(
            "SELECT * FROM module_assessment_option WHERE question_id = ? ORDER BY ord",
            (q["id"],),
        ).fetchall()
        q["options"] = [dict(o) for o in opts]
        questions.append(q)
    return questions


def latest_module_assessment_attempt(user_id, module_assessment_id):
    row = get_db().execute(
        "SELECT * FROM user_module_assessment_attempt "
        "WHERE user_id = ? AND module_assessment_id = ? "
        "ORDER BY attempt_number DESC LIMIT 1",
        (user_id, module_assessment_id),
    ).fetchone()
    return dict(row) if row else None


def grade_and_record_module_assessment_attempt(user_id, module_assessment_id, answers):
    """`answers` é {question_id(int): option_id(int)}. Pontuação é sempre
    calculada aqui, no servidor, nunca a partir de um valor vindo do cliente
    (mesmo princípio de submit_question_answer/concluir_aula -- Seção 23/24
    da spec técnica). Cada chamada grava uma NOVA linha (tentativas
    ilimitadas, sem sobrescrever histórico) -- diferente de
    user_question_answer, que sobrescreve; aqui o precedente é
    user_assessment_attempt.attempt_number, que já registra cada tentativa."""
    assessment = get_db().execute(
        "SELECT * FROM module_assessment WHERE id = ?", (module_assessment_id,)
    ).fetchone()
    if not assessment:
        return None
    questions = list_module_assessment_questions(module_assessment_id)
    total = len(questions)
    if total == 0:
        return None
    correct = 0
    for q in questions:
        chosen_option_id = answers.get(q["id"])
        if chosen_option_id is None:
            continue
        for opt in q["options"]:
            if opt["id"] == chosen_option_id and opt["is_correct"]:
                correct += 1
                break
    score_pct = int(correct / total * 100)
    passed = 1 if score_pct >= (assessment["pass_threshold_pct"] or 70) else 0

    prev = latest_module_assessment_attempt(user_id, module_assessment_id)
    attempt_number = (prev["attempt_number"] + 1) if prev else 1

    db = get_db()
    db.execute(
        "INSERT INTO user_module_assessment_attempt "
        "(user_id, module_assessment_id, score_pct, passed, attempt_number) "
        "VALUES (?,?,?,?,?)",
        (user_id, module_assessment_id, score_pct, passed, attempt_number),
    )
    db.commit()
    return {"score_pct": score_pct, "passed": bool(passed), "attempt_number": attempt_number}


# ───────────────────────── gamificação: conquistas + XP ─────────────────────────
# Ref.: pedido "Sistema Real de Gamificação". Toda regra de negócio (quando
# conceder, quanto conceder) fica em gamification.py -- este módulo só faz
# leitura/escrita persistente, sempre com a idempotência garantida por
# constraints UNIQUE (ver db.py), nunca por checagem em Python.

def create_achievement(slug, title, description, xp, **extra):
    """Usado por scripts de seed (idempotente via slug: se já existir,
    atualiza os campos em vez de duplicar -- permite rodar o seed de novo
    com segurança ao ajustar texto/XP de uma conquista)."""
    db = get_db()
    existing = db.execute("SELECT id FROM achievement WHERE slug = ?", (slug,)).fetchone()
    fields = {
        "title": title,
        "description": description,
        "xp": xp,
        "category": extra.get("category", "lesson"),
        "rarity": extra.get("rarity", "Comum"),
        "unlock_criteria": extra.get("unlock_criteria", ""),
        "course_id": extra.get("course_id"),
        "module_id": extra.get("module_id"),
        "lesson_id": extra.get("lesson_id"),
        "is_platinum": 1 if extra.get("is_platinum") else 0,
        "mascot_emoji": extra.get("mascot_emoji", "🏆"),
        "mascot_image_url": extra.get("mascot_image_url"),
        "active": 1 if extra.get("active", True) else 0,
    }
    if existing:
        cols = ", ".join(f"{k} = ?" for k in fields)
        db.execute(f"UPDATE achievement SET {cols} WHERE id = ?", (*fields.values(), existing["id"]))
        db.commit()
        return existing["id"]
    cur = db.execute(
        "INSERT INTO achievement (slug, title, description, xp, category, rarity, unlock_criteria, "
        "course_id, module_id, lesson_id, is_platinum, mascot_emoji, mascot_image_url, active) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (slug, *fields.values()),
    )
    db.commit()
    return cur.lastrowid


def get_achievement_by_slug(slug):
    row = get_db().execute("SELECT * FROM achievement WHERE slug = ?", (slug,)).fetchone()
    return Achievement(row) if row else None


def get_achievement_for_lesson(lesson_id):
    """Conquista de conclusão associada a uma aula específica, se existir
    (categoria 'lesson', não-Platina -- uma aula pode, no máximo, ter uma
    conquista de conclusão própria)."""
    row = get_db().execute(
        "SELECT * FROM achievement WHERE lesson_id = ? AND is_platinum = 0 AND active = 1 LIMIT 1",
        (lesson_id,),
    ).fetchone()
    return Achievement(row) if row else None


def list_achievements(active_only=True):
    sql = "SELECT * FROM achievement"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY is_platinum, id"
    rows = get_db().execute(sql).fetchall()
    return [Achievement(r) for r in rows]


def count_achievements(active_only=True, exclude_platinum=True):
    sql = "SELECT COUNT(*) c FROM achievement WHERE 1=1"
    if active_only:
        sql += " AND active = 1"
    if exclude_platinum:
        sql += " AND is_platinum = 0"
    return get_db().execute(sql).fetchone()["c"]


def user_achievements_map(user_id):
    """dict achievement_id -> unlocked_at (string), só para os desbloqueados
    deste usuário -- usado para saber o que já foi conquistado sem um join
    por chamada de página."""
    rows = get_db().execute(
        "SELECT achievement_id, unlocked_at FROM user_achievement WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return {r["achievement_id"]: r["unlocked_at"] for r in rows}


def count_user_achievements(user_id, exclude_platinum=True):
    sql = (
        "SELECT COUNT(*) c FROM user_achievement ua "
        "JOIN achievement a ON a.id = ua.achievement_id "
        "WHERE ua.user_id = ? AND a.active = 1"
    )
    if exclude_platinum:
        sql += " AND a.is_platinum = 0"
    return get_db().execute(sql, (user_id,)).fetchone()["c"]


def insert_user_achievement(user_id, achievement_id):
    """Tenta desbloquear; devolve True só se esta chamada REALMENTE inseriu
    a linha (primeira vez). UNIQUE(user_id, achievement_id) faz a segunda
    tentativa (ou a centésima) ser um no-op seguro -- é isso que impede a
    duplicação exigida na Seção 1 do pedido."""
    db = get_db()
    cur = db.execute(
        "INSERT OR IGNORE INTO user_achievement (user_id, achievement_id) VALUES (?,?)",
        (user_id, achievement_id),
    )
    db.commit()
    return cur.rowcount > 0


def insert_xp_transaction(user_id, amount, reason_code, reason_label, source_type=None, source_id=None, lesson_id=None):
    """Mesma lógica de idempotência do achievement acima, mas para XP:
    UNIQUE(user_id, reason_code) garante que a mesma reason_code nunca
    concede XP duas vezes para o mesmo usuário. Devolve True só se este
    INSERT específico foi o que realmente aconteceu."""
    db = get_db()
    cur = db.execute(
        "INSERT OR IGNORE INTO xp_transaction "
        "(user_id, amount, reason_code, reason_label, source_type, source_id, lesson_id) "
        "VALUES (?,?,?,?,?,?,?)",
        (user_id, amount, reason_code, reason_label, source_type, source_id, lesson_id),
    )
    db.commit()
    return cur.rowcount > 0


def xp_earned_for_lesson(user_id, lesson_id):
    row = get_db().execute(
        "SELECT COALESCE(SUM(amount), 0) s FROM xp_transaction WHERE user_id = ? AND lesson_id = ?",
        (user_id, lesson_id),
    ).fetchone()
    return row["s"]


def xp_history_for_user(user_id, limit=50):
    rows = get_db().execute(
        "SELECT * FROM xp_transaction WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]
