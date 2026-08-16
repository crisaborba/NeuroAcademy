import random
import re
from datetime import datetime

from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, url_for

import repo
import gamification
from auth import current_user, login_required, login_user, logout_user
from utils import password_is_strong, password_requirements, slugify
from tutor_ai import ai_reply

bp = Blueprint("main", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ───────────────────────── public / marketing ─────────────────────────

@bp.route("/")
def home():
    courses = repo.list_courses(is_marketplace=False)[:4]
    stats = {
        "course_count": repo.count_learnable_courses(),
        "lesson_count": repo.count_lessons(),
    }
    return render_template("home.html", courses=courses, stats=stats)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = repo.get_user_by_email(email)
        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get("remember")))
            return redirect(url_for("main.home"))
        return render_template("login.html", error="E-mail ou senha inválidos.")
    return render_template("login.html")


@bp.route("/registrar", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template("login.html", error="Preencha todos os campos para criar sua conta.")
    if not EMAIL_RE.match(email):
        return render_template("login.html", error="Digite um e-mail válido.")
    if not password_is_strong(password):
        return render_template(
            "login.html",
            error="A senha precisa ter pelo menos 8 caracteres, com letra maiúscula, "
                  "minúscula, número e caractere especial.",
        )
    if repo.get_user_by_email(email):
        return render_template("login.html", error="Já existe uma conta com esse e-mail.")

    # Username is derived from the email but must stay unique; retry a few
    # times on collision instead of letting the UNIQUE constraint crash the
    # request with an unhandled 500.
    base_username = re.sub(r"[^a-z0-9]", "", email.split("@")[0]) or "user"
    user = None
    for _ in range(5):
        candidate = base_username + str(random.randint(100, 9999))
        try:
            user = repo.create_user(name, candidate, email, password)
            break
        except repo.IntegrityError:
            continue
    if user is None:
        return render_template("login.html", error="Não foi possível criar sua conta. Tente novamente.")

    login_user(user)
    return redirect(url_for("main.home"))


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.home"))


@bp.route("/verificar-email/<token>")
def verificar_email(token):
    """Confirms a user's e-mail given a valid verification token.

    This endpoint is fully functional today, but nothing in this codebase
    currently sends that token to the user's inbox -- there is no email
    provider wired up (see README / audit report). The link only works if
    the token reaches the user through some other channel (e.g. manually,
    during development). Wiring a real provider (SMTP, SendGrid, AWS SES...)
    and sending this link at signup is the remaining piece.
    """
    user = repo.get_user_by_verify_token(token)
    if not user:
        abort(404)
    repo.mark_email_verified(user.id)
    if current_user().is_authenticated and current_user().id == user.id:
        g.user = repo.get_user_by_id(user.id)
    return render_template("email_verificado.html", user=user)


# ───────────────────────── cursos ─────────────────────────

@bp.route("/cursos")
def cursos():
    category = request.args.get("categoria", "Todos")
    level = request.args.get("nivel", "Todos")
    q = request.args.get("busca", "").strip()

    courses = repo.list_courses(is_marketplace=False, category=category, level=level, q=q)
    categories = ["Todos", "Fundamentos", "Ferramentas", "Prompt", "Carreira", "Dados", "Automação"]
    levels = ["Todos", "Iniciante", "Intermediário", "Avançado"]
    return render_template("cursos.html", courses=courses, categories=categories, levels=levels,
                            active_category=category, active_level=level, q=q)


@bp.route("/cursos/<int:course_id>")
def curso_detalhe(course_id):
    course = repo.get_course_with_modules(course_id)
    if not course:
        abort(404)
    enrollment = None
    lesson_progress_ids = set()
    user = current_user()
    if user.is_authenticated:
        enrollment = repo.get_enrollment(user.id, course.id)
        lesson_progress_ids = repo.done_lesson_ids_for_user(user.id)
    return render_template("curso_detalhe.html", course=course, enrollment=enrollment,
                            lesson_progress_ids=lesson_progress_ids)


@bp.route("/cursos/<int:course_id>/matricular", methods=["POST"])
@login_required
def matricular(course_id):
    user = current_user()
    repo.create_enrollment(user.id, course_id)
    lessons = repo.list_lessons_for_course(course_id)
    if lessons:
        return redirect(url_for("main.aula", course_id=course_id, lesson_id=lessons[0].id))
    return redirect(url_for("main.curso_detalhe", course_id=course_id))


@bp.route("/cursos/<int:course_id>/aula/<int:lesson_id>")
@login_required
def aula(course_id, lesson_id):
    user = current_user()
    course = repo.get_course(course_id)
    lesson = repo.get_lesson(lesson_id)
    # A lesson ID that exists but doesn't belong to this course is a bad
    # request, not a valid state -- don't silently render mismatched data.
    if not course or not lesson or lesson.course_id != course.id:
        abort(404)

    enrollment = repo.get_enrollment(user.id, course_id)
    if not enrollment and not lesson.free:
        # Visiting a lesson URL is a safe GET request; it must not have the
        # side effect of enrolling the user. Enrollment only happens through
        # the explicit POST /matricular action (or by opening a free lesson).
        return redirect(url_for("main.curso_detalhe", course_id=course_id))

    lessons = repo.list_lessons_for_course(course_id)
    idx = next((i for i, l in enumerate(lessons) if l.id == lesson.id), 0)
    prev_lesson = lessons[idx - 1] if idx > 0 else None
    next_lesson = lessons[idx + 1] if idx < len(lessons) - 1 else None
    progress = repo.get_lesson_progress(user.id, lesson.id)
    done_ids = repo.done_lesson_ids_for_user(user.id)
    questions = repo.list_lesson_questions(lesson.id)
    can_complete = repo.lesson_meets_completion_criteria(user.id, lesson.id, lesson.get("pass_threshold_pct", 0))

    # Fase 2 -- Experiência de Aprendizagem (UX/UI): breadcrumb curso › módulo
    # › aula, progresso do módulo e posição da aula dentro do módulo. Dado
    # puramente de apresentação -- não altera nenhuma regra de conclusão,
    # que continua vindo de lesson_meets_completion_criteria/module_progress
    # já existentes desde a Fase 1.
    module = repo.get_module(lesson.module_id)
    module_lessons = [l for l in lessons if l.module_id == lesson.module_id]
    module_position = next((i + 1 for i, l in enumerate(module_lessons) if l.id == lesson.id), 1)
    module_pct = repo.module_progress(user.id, lesson.module_id)
    course_pct = repo.recompute_progress(user.id, course_id) if enrollment else 0
    modules = repo.list_modules_with_lessons(course_id)
    modules_pct = {m.id: repo.module_progress(user.id, m.id) for m in modules}

    # Fase 1 -- Sistema de Aulas (fundação de blocos, Seção 20/23 da spec
    # técnica): se a aula já tem lesson_block, o template renderiza a
    # composição de blocos; se não, cai no fallback legado (lesson.content +
    # lista plana de `questions`) -- nenhum comportamento antigo muda para
    # aulas ainda não migradas.
    blocks = repo.list_lesson_blocks(lesson.id)
    answers = repo.user_answers_for_lesson(user.id, lesson.id)
    # Inclui também as perguntas referenciadas por blocos 'microchallenge'
    # que porventura não estejam na lista "solta" retornada acima (hoje elas
    # sempre estão, já que list_lesson_questions já traz todas da aula --
    # mantido explícito para não quebrar se blocos um dia referenciarem
    # perguntas de outro lugar).
    questions_by_id = {q["id"]: q for q in questions}

    # Contexto real de gamificação para o bloco 'completion_dashboard'
    # (Seção 8/10 do pedido de gamificação): nada aqui é um valor fixo --
    # lesson_xp vem do ledger, achievement_unlocked de user_achievement,
    # platinum de gamification.platinum_progress. O bloco só *exibe* estado
    # que o backend já validou; não decide nada sozinho.
    lesson_achievement = repo.get_achievement_for_lesson(lesson.id)
    unlocked_map = repo.user_achievements_map(user.id)
    gam = {
        "lesson_id": lesson.id,
        "course_id": course.id,
        "lesson_done": lesson.id in done_ids,
        "can_complete": can_complete,
        "lesson_xp": gamification.lesson_xp_earned(user.id, lesson.id),
        "achievement_unlocked": bool(lesson_achievement and lesson_achievement.id in unlocked_map),
        "achievement_xp": lesson_achievement.xp if lesson_achievement else 0,
    }

    return render_template("aula.html", course=course, lesson=lesson, lessons=lessons,
                            prev_lesson=prev_lesson, next_lesson=next_lesson, progress=progress,
                            done_ids=done_ids, questions=questions, can_complete=can_complete,
                            blocks=blocks, answers=answers, questions_by_id=questions_by_id,
                            module=module, module_position=module_position,
                            module_total=len(module_lessons), module_pct=module_pct,
                            course_pct=course_pct, modules=modules, modules_pct=modules_pct,
                            gam=gam)


@bp.route("/cursos/<int:course_id>/aula/<int:lesson_id>/concluir", methods=["POST"])
@login_required
def concluir_aula(course_id, lesson_id):
    user = current_user()
    lesson = repo.get_lesson(lesson_id)
    if not lesson or lesson.course_id != course_id:
        abort(404)
    already_done = lesson_id in repo.done_lesson_ids_for_user(user.id)
    # The frontend disables this button until the gate is satisfied, but the
    # server is the actual security/integrity boundary -- re-check here too.
    if not already_done:
        threshold = lesson.get("pass_threshold_pct", 0)
        if not repo.lesson_meets_completion_criteria(user.id, lesson_id, threshold):
            return jsonify({
                "ok": False,
                "error": "Responda corretamente a verificação desta aula antes de concluí-la.",
            }), 400
    done = repo.toggle_lesson_done(user.id, lesson_id)
    pct = repo.recompute_progress(user.id, course_id)

    # Conquistas/Platina reais: só reage quando a aula é marcada como
    # concluída (não quando é desmarcada), e é idempotente por construção
    # -- re-marcar uma aula já concluída antes (toggle off -> on de novo)
    # não gera XP/conquista duplicados (Seção 3 e Seção 6 do pedido de
    # gamificação: "o frontend pode iniciar a ação, mas não deve ser a
    # única autoridade sobre uma recompensa importante" -- aqui é o
    # backend, depois de já ter validado lesson_meets_completion_criteria
    # acima, quem decide o que foi desbloqueado).
    reward = {"achievement": None, "platinum": None}
    if done:
        reward = gamification.on_lesson_completed(user.id, lesson_id)

    def _serialize_unlock(unlock_result):
        if not unlock_result:
            return None
        a = unlock_result["achievement"]
        return {
            "slug": a.slug, "title": a.title, "description": a.description,
            "xp": unlock_result["xp"], "rarity": a.rarity,
            "mascot_emoji": a.mascot_emoji, "mascot_image_url": a.get("mascot_image_url"),
        }

    return jsonify({
        "ok": True, "done": done, "progress": pct,
        "xp_total": repo.get_user_by_id(user.id).points,
        "achievement_unlocked": _serialize_unlock(reward["achievement"]),
        "platinum_unlocked": _serialize_unlock(reward["platinum"]),
        "platinum_progress": gamification.platinum_progress(user.id),
    })


@bp.route("/questoes/<int:question_id>/responder", methods=["POST"])
@login_required
def responder_questao(question_id):
    user = current_user()
    question = repo.get_lesson_question(question_id)
    if not question:
        abort(404)
    data = request.get_json(silent=True) or {}
    try:
        option_id = int(data.get("option_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False}), 400

    result = repo.submit_question_answer(user.id, question_id, option_id)
    if not result:
        return jsonify({"ok": False}), 400

    lesson = repo.get_lesson(question["lesson_id"])
    can_complete = repo.lesson_meets_completion_criteria(
        user.id, question["lesson_id"], lesson.get("pass_threshold_pct", 0) if lesson else 0
    )

    # XP real, concedido pelo servidor -- só quando a resposta está correta
    # e só na primeira vez (gamification.grant_xp é idempotente por
    # reason_code). O valor concedido vem de question["reward_xp"], nunca
    # de nada que o cliente enviou (Seção 16 do pedido de gamificação).
    xp_result = {"granted": False, "amount": 0, "new_total": user.points}
    if result["is_correct"]:
        xp_result = gamification.on_question_answered_correctly(user.id, question)

    return jsonify({
        "ok": True,
        "is_correct": result["is_correct"],
        "feedback": result["feedback"],
        "can_complete": can_complete,
        "xp_granted": xp_result["amount"],
        "xp_total": xp_result["new_total"],
    })


@bp.route("/cursos/<int:course_id>/aula/<int:lesson_id>/nota", methods=["POST"])
@login_required
def salvar_nota(course_id, lesson_id):
    data = request.get_json(silent=True) or {}
    user = current_user()
    lesson = repo.get_lesson(lesson_id)
    if not lesson or lesson.course_id != course_id:
        abort(404)
    note = (data.get("note") or "")[:5000]  # basic size guard against abuse
    repo.set_lesson_note(user.id, lesson_id, note)
    return jsonify({"ok": True})


@bp.route("/cursos/<int:course_id>/certificado")
@login_required
def certificado(course_id):
    user = current_user()
    course = repo.get_course(course_id)
    if not course:
        abort(404)
    cert = repo.get_certificate(user.id, course.id)
    if not cert:
        # A course still being produced (e.g. only some modules published so
        # far) must never issue a certificate just because the currently
        # available lessons were all completed -- that would misrepresent
        # the real scope of the course.
        if not course.get("content_complete", 1):
            return redirect(url_for("main.curso_detalhe", course_id=course.id))
        pct = repo.recompute_progress(user.id, course.id)
        if pct < 100:
            return redirect(url_for("main.curso_detalhe", course_id=course.id))
        cert = repo.create_certificate(user.id, course.id)
    return render_template("certificado.html", course=course, cert=cert)


# ───────────────────────── avaliação de módulo (Fase 1 -- fundação) ─────────────────────────
# Ref.: Seção 15/23 da spec técnica, Etapa 6 da tarefa desta fase. Rotas
# mínimas para validar a arquitetura ponta a ponta (Cenário 8 dos testes) --
# UI completa (tela de introdução com progresso, revisão de gabarito, etc.)
# é de uma fase posterior; aqui só o necessário para responder e corrigir.

@bp.route("/cursos/<int:course_id>/modulo/<int:module_id>/avaliacao")
@login_required
def modulo_avaliacao(course_id, module_id):
    user = current_user()
    course = repo.get_course(course_id)
    module = repo.get_module(module_id)
    if not course or not module or module.course_id != course.id:
        abort(404)
    enrollment = repo.get_enrollment(user.id, course_id)
    if not enrollment:
        return redirect(url_for("main.curso_detalhe", course_id=course_id))
    assessment = repo.get_module_assessment_for_module(module_id)
    if not assessment:
        abort(404)
    questions = repo.list_module_assessment_questions(assessment["id"])
    last_attempt = repo.latest_module_assessment_attempt(user.id, assessment["id"])
    return render_template(
        "modulo_avaliacao.html", course=course, module=module,
        assessment=assessment, questions=questions, last_attempt=last_attempt,
    )


@bp.route("/cursos/<int:course_id>/modulo/<int:module_id>/avaliacao/enviar", methods=["POST"])
@login_required
def modulo_avaliacao_enviar(course_id, module_id):
    user = current_user()
    module = repo.get_module(module_id)
    if not module or module.course_id != course_id:
        abort(404)
    assessment = repo.get_module_assessment_for_module(module_id)
    if not assessment:
        abort(404)
    data = request.get_json(silent=True) or {}
    raw_answers = data.get("answers") or {}
    # O cliente envia só as respostas escolhidas -- a pontuação é sempre
    # recalculada aqui, no servidor, nunca recebida do cliente (mesmo
    # princípio já usado em submit_question_answer/concluir_aula).
    try:
        answers = {int(qid): int(oid) for qid, oid in raw_answers.items()}
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Respostas em formato inválido."}), 400

    result = repo.grade_and_record_module_assessment_attempt(user.id, assessment["id"], answers)
    if not result:
        return jsonify({"ok": False, "error": "Avaliação sem questões cadastradas."}), 400
    return jsonify({"ok": True, **result})


# ───────────────────────── blog / notícias / ferramentas ─────────────────────────

@bp.route("/blog")
def blog():
    tag = request.args.get("tag", "Todos")
    posts = repo.list_blog_posts(tag=tag)
    tags = ["Todos", "IA Generativa", "Machine Learning", "Carreira", "Ferramentas", "Ética", "Tutoriais"]
    featured = repo.get_featured_blog_post()
    return render_template("blog.html", posts=posts, tags=tags, active_tag=tag, featured=featured)


@bp.route("/blog/<int:post_id>")
def blog_post(post_id):
    post = repo.get_blog_post(post_id)
    if not post:
        abort(404)
    others = repo.other_blog_posts(post.id)
    return render_template("blog_post.html", post=post, others=others)


@bp.route("/noticias")
def noticias():
    category = request.args.get("categoria", "Todas")
    news = repo.list_news(category=category)
    categories = ["Todas", "OpenAI", "Google", "Pesquisa", "Mercado", "Brasil", "Regulação"]
    trending = repo.list_trending_news()
    return render_template("noticias.html", news=news, categories=categories, active_category=category,
                            trending=trending)


@bp.route("/newsletter", methods=["POST"])
def newsletter():
    return jsonify({"ok": True, "message": "Inscrição confirmada! Você vai receber nossas próximas notícias."})


@bp.route("/ferramentas")
def ferramentas():
    category = request.args.get("categoria", "Todas")
    q = request.args.get("busca", "").strip()
    tools = repo.list_tools(category=category, q=q)
    categories = ["Todas", "Chatbots", "Imagem", "Vídeo", "Código", "Escrita", "Produtividade", "Pesquisa"]
    return render_template("ferramentas.html", tools=tools, categories=categories,
                            active_category=category, q=q)


# ───────────────────────── comunidade ─────────────────────────

@bp.route("/comunidade")
def comunidade():
    topic = request.args.get("topico", "Todos")
    posts = repo.list_community_posts(topic=topic)
    topics = ["Todos", "Dúvidas", "Projetos", "Carreira", "Ferramentas", "Desafios"]
    members = repo.top_members(5)
    return render_template("comunidade.html", posts=posts, topics=topics, active_topic=topic,
                            top_members=members)


@bp.route("/comunidade/postar", methods=["POST"])
@login_required
def postar_comunidade():
    user = current_user()
    title = request.form.get("title", "").strip()[:220]
    body = request.form.get("body", "").strip()[:5000]
    topic = request.form.get("topic", "Dúvidas")
    if topic not in ("Dúvidas", "Projetos", "Carreira", "Ferramentas", "Desafios"):
        topic = "Dúvidas"
    if title:
        repo.create_community_post(user.id, topic, title, body)
        repo.update_user(user.id, points=(user.points or 0) + 5)
    return redirect(url_for("main.comunidade"))


@bp.route("/comunidade/<int:post_id>/curtir", methods=["POST"])
@login_required
def curtir_post(post_id):
    if not repo.get_community_post(post_id):
        abort(404)
    likes = repo.like_post(post_id)
    return jsonify({"ok": True, "likes": likes})


@bp.route("/comunidade/<int:post_id>/comentar", methods=["POST"])
@login_required
def comentar_post(post_id):
    user = current_user()
    if not repo.get_community_post(post_id):
        abort(404)
    body = (request.get_json(silent=True) or {}).get("body", "").strip()
    if not body:
        return jsonify({"ok": False, "error": "Comentário vazio."}), 400
    body = body[:2000]  # basic size guard
    repo.add_comment(post_id, user.id, body)
    repo.update_user(user.id, points=(user.points or 0) + 2)
    return jsonify({"ok": True, "author": user.name, "body": body, "initial": user.initial})


# ───────────────────────── roadmaps ─────────────────────────

@bp.route("/roadmaps")
def roadmaps():
    all_roadmaps = repo.list_roadmaps()
    progress_map = {}
    user = current_user()
    if user.is_authenticated:
        progress_map = repo.get_roadmap_progress_map(user.id)
    return render_template("roadmaps.html", roadmaps=all_roadmaps, progress_map=progress_map)


@bp.route("/roadmaps/<int:roadmap_id>/avancar", methods=["POST"])
@login_required
def avancar_roadmap(roadmap_id):
    user = current_user()
    roadmap = repo.get_roadmap(roadmap_id)
    if not roadmap:
        return jsonify({"ok": False}), 404
    total_steps = len(roadmap.steps)
    new_idx = repo.advance_roadmap(user.id, roadmap_id, total_steps)
    return jsonify({"ok": True, "current_step_index": new_idx, "total": total_steps})


# ───────────────────────── perfil / configurações ─────────────────────────

@bp.route("/perfil")
@login_required
def perfil():
    user = current_user()
    enrollments = repo.list_enrollments_for_user(user.id)
    certificates = repo.list_certificates_for_user(user.id)
    posts_count = repo.count_posts_by_user(user.id)
    comments_count = repo.count_comments_by_user(user.id)
    return render_template("perfil.html", enrollments=enrollments, certificates=certificates,
                            posts_count=posts_count, comments_count=comments_count)


@bp.route("/perfil/conquistas")
@login_required
def conquistas():
    """Central de Conquistas (Seção 13 do pedido de gamificação). Só usa
    dados que já existem de verdade -- nenhuma estatística inventada."""
    user = current_user()
    catalog = gamification.achievements_catalog_for_user(user.id)
    platinum = gamification.platinum_progress(user.id)
    done_ids = repo.done_lesson_ids_for_user(user.id)
    stats = {
        "xp_total": user.points,
        "streak": user.streak,
        "lessons_done": len(done_ids),
        "certificates": len(repo.list_certificates_for_user(user.id)),
    }
    return render_template("conquistas.html", catalog=catalog, platinum=platinum, stats=stats)


@bp.route("/configuracoes", methods=["GET", "POST"])
@login_required
def configuracoes():
    user = current_user()
    if request.method == "POST":
        form = request.form
        action = form.get("action")
        if action == "conta":
            repo.update_user(user.id, name=form.get("name", user.name), bio=form.get("bio", user.bio))
        elif action == "notificacoes":
            repo.update_user(
                user.id,
                email_notifications=1 if form.get("email_notifications") else 0,
                community_notifications=1 if form.get("community_notifications") else 0,
                news_notifications=1 if form.get("news_notifications") else 0,
                marketing_notifications=1 if form.get("marketing_notifications") else 0,
            )
        elif action == "senha":
            old = form.get("old_password", "")
            new = form.get("new_password", "")
            if user.check_password(old) and new and password_is_strong(new):
                repo.set_password(user.id, new)
        user = repo.get_user_by_id(user.id)
        g.user = user
    return render_template("configuracoes.html")


# ───────────────────────── marketplace / premium ─────────────────────────

@bp.route("/marketplace")
def marketplace():
    q = request.args.get("busca", "").strip()
    items = repo.list_courses(is_marketplace=True, q=q)
    featured = [i for i in items if i.featured]
    others = [i for i in items if not i.featured]
    return render_template("marketplace.html", featured=featured, others=others, q=q)


@bp.route("/premium")
def premium():
    return render_template("premium.html")


@bp.route("/assinar/<plano>", methods=["POST"])
@login_required
def assinar(plano):
    user = current_user()
    if plano in ("Pro", "Anual", "Gratuito"):
        repo.update_user(user.id, plan=plano)
    return redirect(url_for("main.premium"))


# ───────────────────────── admin ─────────────────────────

@bp.route("/admin")
@login_required
def admin():
    user = current_user()
    if user.role != "admin":
        return redirect(url_for("main.home"))
    total_users = repo.count_users()
    total_courses = repo.count_courses()
    total_certificates = repo.count_certificates()
    recent_users_list = repo.recent_users(6)
    recent_courses_list = repo.recent_courses(6)
    avg_rating = round(repo.avg_course_rating(), 1)
    return render_template("admin.html", total_users=total_users, total_courses=total_courses,
                            total_certificates=total_certificates, recent_users=recent_users_list,
                            recent_courses=recent_courses_list, avg_rating=avg_rating)


@bp.route("/admin/curso/novo", methods=["POST"])
@login_required
def admin_novo_curso():
    user = current_user()
    if user.role != "admin":
        return redirect(url_for("main.home"))
    title = request.form.get("title", "").strip()[:200]
    valid_categories = {"Fundamentos", "Ferramentas", "Prompt", "Carreira", "Dados", "Automação"}
    valid_levels = {"Iniciante", "Intermediário", "Avançado"}
    category = request.form.get("category", "Fundamentos")
    level = request.form.get("level", "Iniciante")
    if category not in valid_categories:
        category = "Fundamentos"
    if level not in valid_levels:
        level = "Iniciante"
    if title:
        repo.create_course(
            title=title, slug=slugify(title) + "-" + str(random.randint(100, 999)),
            tag="NOVO", tag_color="#22c55e", category=category,
            description=request.form.get("description", "")[:1000], level=level,
            hours_label=request.form.get("hours_label", "1h")[:20], free=1,
            img="photo-1677442135703-1787eea5ce01", is_marketplace=0,
        )
    return redirect(url_for("main.admin"))


# ───────────────────────── tutor IA ─────────────────────────

@bp.route("/tutor")
def tutor():
    return render_template("tutor.html")


@bp.route("/tutor/mensagem", methods=["POST"])
def tutor_mensagem():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "")[:2000]
    user = current_user()

    context = {}
    if user.is_authenticated:
        context = {
            "first_name": (user.name or "").split(" ")[0] or None,
            "plan": user.plan,
            "enrolled_course_ids": [e.course_id for e in repo.list_enrollments_for_user(user.id)],
        }

    reply = ai_reply(text, context)
    return jsonify({"reply": reply, "time": datetime.utcnow().strftime("%H:%M")})
