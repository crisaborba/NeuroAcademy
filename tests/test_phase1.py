"""Testes automatizados -- Fase 1 do Sistema de Aulas.

Roda com unittest puro (sem pytest/tox como dependência nova, mesmo
princípio de "sem dependência nova" já usado no resto do projeto).
Cada teste usa um banco SQLite temporário próprio (setUp/tearDown), nunca
toca em neuroacademy.db.

Uso:
    cd neuroacademy && python -m unittest tests.test_phase1 -v
"""
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from db import get_db
import repo
from validators import BlockValidationError, validate_block, is_block_valid
import migrate_lessons_to_blocks


def _make_app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    os.environ["DATABASE_PATH"] = db_path
    os.environ["FLASK_DEBUG"] = "1"
    app = create_app()
    return app, db_path


def _get_csrf(html):
    m = re.search(r'name="csrf-token" content="([^"]+)"', html)
    return m.group(1) if m else None


class ValidatorsTestCase(unittest.TestCase):
    """Testes de tipagem/validação dos blocos (Etapa 2/12 dos cenários mínimos)."""

    def test_text_block_valid(self):
        self.assertTrue(is_block_valid("text", {"markdown": "Olá mundo"}))

    def test_text_block_missing_field(self):
        self.assertFalse(is_block_valid("text", {}))

    def test_text_block_empty_string(self):
        self.assertFalse(is_block_valid("text", {"markdown": "   "}))

    def test_image_requires_alt(self):
        self.assertFalse(is_block_valid("image", {"url": "http://x/y.png"}))
        self.assertTrue(is_block_valid("image", {"url": "http://x/y.png", "alt": "descrição"}))

    def test_flip_card_requires_both_sides(self):
        self.assertFalse(is_block_valid("flip_card", {"front": "A"}))
        self.assertTrue(is_block_valid("flip_card", {"front": "A", "back": "B"}))

    def test_microchallenge_requires_int_question_id(self):
        self.assertFalse(is_block_valid("microchallenge", {"question_id": "1"}))
        self.assertFalse(is_block_valid("microchallenge", {"question_id": True}))
        self.assertTrue(is_block_valid("microchallenge", {"question_id": 1}))

    def test_summary_requires_non_empty_list(self):
        self.assertFalse(is_block_valid("summary", {"items": []}))
        self.assertTrue(is_block_valid("summary", {"items": ["a"]}))

    def test_unknown_block_type_raises(self):
        with self.assertRaises(BlockValidationError):
            validate_block("does_not_exist", {"x": 1})

    def test_video_is_documented_but_not_supported_yet(self):
        with self.assertRaises(BlockValidationError):
            validate_block("video", {"url": "http://x", "provider": "youtube"})

    def test_payload_must_be_dict(self):
        with self.assertRaises(BlockValidationError):
            validate_block("text", ["not", "a", "dict"])


class LessonBlockRepoTestCase(unittest.TestCase):
    """Testes de banco / persistência dos blocos (Cenário 1 e 2 dos testes mínimos)."""

    def setUp(self):
        self.app, self.db_path = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        cur = get_db().execute(
            "INSERT INTO course (title, slug) VALUES ('Curso Teste', 'curso-teste')"
        )
        get_db().commit()
        course_id = cur.lastrowid
        mod_id = get_db().execute(
            "INSERT INTO module (course_id, title, ord) VALUES (?, 'Modulo 1', 0)", (course_id,)
        ).lastrowid
        get_db().commit()
        self.lesson_id = get_db().execute(
            "INSERT INTO lesson (module_id, course_id, title, content_type, content) "
            "VALUES (?, ?, 'Aula Teste', 'text', 'conteudo original')",
            (mod_id, course_id),
        ).lastrowid
        get_db().commit()

    def tearDown(self):
        self.ctx.pop()
        os.remove(self.db_path)

    def test_insert_and_list_ordered(self):
        repo.insert_lesson_block(self.lesson_id, "heading", 0, {"text": "Título"})
        repo.insert_lesson_block(self.lesson_id, "text", 1, {"markdown": "corpo"})
        blocks = repo.list_lesson_blocks(self.lesson_id)
        self.assertEqual([b["type"] for b in blocks], ["heading", "text"])
        self.assertEqual(blocks[1]["payload"]["markdown"], "corpo")

    def test_insert_invalid_block_raises_and_does_not_persist(self):
        with self.assertRaises(BlockValidationError):
            repo.insert_lesson_block(self.lesson_id, "text", 0, {})
        self.assertEqual(repo.list_lesson_blocks(self.lesson_id), [])

    def test_corrupted_block_does_not_break_listing(self):
        """Cenário 2 dos testes mínimos: bloco inválido não derruba a página."""
        db = get_db()
        db.execute(
            "INSERT INTO lesson_block (lesson_id, type, ord, payload) VALUES (?,?,?,?)",
            (self.lesson_id, "text", 0, "{not valid json"),
        )
        db.execute(
            "INSERT INTO lesson_block (lesson_id, type, ord, payload) VALUES (?,?,?,?)",
            (self.lesson_id, "text", 1, json.dumps({"markdown": "ok"})),
        )
        db.commit()
        blocks = repo.list_lesson_blocks(self.lesson_id)
        self.assertEqual(len(blocks), 2)
        self.assertFalse(blocks[0]["valid"])
        self.assertTrue(blocks[1]["valid"])
        self.assertEqual(blocks[1]["payload"]["markdown"], "ok")

    def test_lesson_has_blocks(self):
        self.assertFalse(repo.lesson_has_blocks(self.lesson_id))
        repo.insert_lesson_block(self.lesson_id, "text", 0, {"markdown": "x"})
        self.assertTrue(repo.lesson_has_blocks(self.lesson_id))

    def test_learning_objective_and_summary_items_key_renders(self):
        """Regressão: `items` é também um método de dict em Python: `p.items`
        em Jinja resolve para o método (não para a chave) e quebra a
        renderização com TypeError -- encontrado manualmente ao testar a
        composição completa de blocos. O template usa `p['items']`."""
        repo.insert_lesson_block(self.lesson_id, "learning_objective", 0, {"items": ["A", "B"]})
        repo.insert_lesson_block(self.lesson_id, "summary", 1, {"items": ["C"]})
        blocks = repo.list_lesson_blocks(self.lesson_id)
        self.assertTrue(all(b["valid"] for b in blocks))
        self.assertEqual(blocks[0]["payload"]["items"], ["A", "B"])


class MigrationTestCase(unittest.TestCase):
    """Etapa 8/9: migração aditiva e idempotente do conteúdo atual."""

    def setUp(self):
        self.app, self.db_path = _make_app()

    def tearDown(self):
        os.remove(self.db_path)

    def test_migration_is_additive_and_idempotent(self):
        with self.app.app_context():
            cur = get_db().execute(
                "INSERT INTO course (title, slug) VALUES ('Curso M', 'curso-m')"
            )
            get_db().commit()
            course_id = cur.lastrowid
            mod_id = get_db().execute(
                "INSERT INTO module (course_id, title, ord) VALUES (?, 'Mod', 0)", (course_id,)
            ).lastrowid
            get_db().commit()
            lesson_id = get_db().execute(
                "INSERT INTO lesson (module_id, course_id, title, content_type, content) "
                "VALUES (?, ?, 'Aula', 'text', '# Ola\\n\\nConteudo original preservado.')",
                (mod_id, course_id),
            ).lastrowid
            get_db().commit()

            report1 = migrate_lessons_to_blocks.migrate_lessons_to_blocks()
            self.assertIn(lesson_id, report1["migrated"])

            # lesson.content nunca é removida
            lesson = repo.get_lesson(lesson_id)
            self.assertIn("Conteudo original preservado", lesson.content)

            blocks = repo.list_lesson_blocks(lesson_id)
            self.assertEqual(len(blocks), 1)
            self.assertEqual(blocks[0]["type"], "text")
            self.assertEqual(blocks[0]["payload"]["markdown"], lesson.content)

            # idempotência: rodar de novo não duplica
            report2 = migrate_lessons_to_blocks.migrate_lessons_to_blocks()
            self.assertIn(lesson_id, report2["skipped_has_blocks"])
            blocks_again = repo.list_lesson_blocks(lesson_id)
            self.assertEqual(len(blocks_again), 1)

    def test_video_lessons_are_not_migrated(self):
        with self.app.app_context():
            cur = get_db().execute("INSERT INTO course (title, slug) VALUES ('Curso V', 'curso-v')")
            get_db().commit()
            course_id = cur.lastrowid
            mod_id = get_db().execute(
                "INSERT INTO module (course_id, title, ord) VALUES (?, 'Mod', 0)", (course_id,)
            ).lastrowid
            get_db().commit()
            lesson_id = get_db().execute(
                "INSERT INTO lesson (module_id, course_id, title, content_type, content) "
                "VALUES (?, ?, 'Aula Video', 'video', 'irrelevante')",
                (mod_id, course_id),
            ).lastrowid
            get_db().commit()
            report = migrate_lessons_to_blocks.migrate_lessons_to_blocks()
            self.assertIn(lesson_id, report["skipped_not_text"])
            self.assertEqual(repo.list_lesson_blocks(lesson_id), [])


class ModuleAssessmentTestCase(unittest.TestCase):
    """Etapa 6: fundação de avaliações de módulo -- aprovação >=70%, tentativas ilimitadas."""

    def setUp(self):
        self.app, self.db_path = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        cur = get_db().execute("INSERT INTO course (title, slug) VALUES ('Curso A', 'curso-a')")
        get_db().commit()
        self.course_id = cur.lastrowid
        self.module_id = get_db().execute(
            "INSERT INTO module (course_id, title, ord) VALUES (?, 'Mod', 0)", (self.course_id,)
        ).lastrowid
        get_db().commit()
        self.user_id = get_db().execute(
            "INSERT INTO user (name, username, email, password_hash) "
            "VALUES ('U', 'u1', 'u1@x.com', 'hash')"
        ).lastrowid
        get_db().commit()

    def tearDown(self):
        self.ctx.pop()
        os.remove(self.db_path)

    def _make_assessment_with_questions(self, n_correct, n_total, threshold=70):
        assessment = repo.create_module_assessment(self.module_id, pass_threshold_pct=threshold)
        qids = []
        for i in range(n_total):
            qid = repo.add_module_assessment_question(
                assessment["id"], f"Questão {i}", i,
                [{"label": "certo", "is_correct": True}, {"label": "errado", "is_correct": False}],
            )
            qids.append(qid)
        return assessment, qids

    def test_question_without_correct_option_is_rejected(self):
        assessment = repo.create_module_assessment(self.module_id)
        with self.assertRaises(ValueError):
            repo.add_module_assessment_question(
                assessment["id"], "Q", 0,
                [{"label": "a", "is_correct": False}, {"label": "b", "is_correct": False}],
            )

    def test_grading_below_threshold_fails(self):
        assessment, qids = self._make_assessment_with_questions(0, 3)
        questions = repo.list_module_assessment_questions(assessment["id"])
        # responde tudo errado
        answers = {}
        for q in questions:
            wrong = next(o for o in q["options"] if not o["is_correct"])
            answers[q["id"]] = wrong["id"]
        result = repo.grade_and_record_module_assessment_attempt(self.user_id, assessment["id"], answers)
        self.assertEqual(result["score_pct"], 0)
        self.assertFalse(result["passed"])
        self.assertEqual(result["attempt_number"], 1)

    def test_grading_at_or_above_threshold_passes(self):
        assessment, qids = self._make_assessment_with_questions(0, 3, threshold=70)
        questions = repo.list_module_assessment_questions(assessment["id"])
        answers = {}
        for i, q in enumerate(questions):
            opt_key = "is_correct" if i < 3 else None
            correct = next(o for o in q["options"] if o["is_correct"])
            answers[q["id"]] = correct["id"]
        result = repo.grade_and_record_module_assessment_attempt(self.user_id, assessment["id"], answers)
        self.assertEqual(result["score_pct"], 100)
        self.assertTrue(result["passed"])

    def test_unlimited_attempts_creates_new_rows_every_time(self):
        assessment, qids = self._make_assessment_with_questions(0, 2)
        questions = repo.list_module_assessment_questions(assessment["id"])
        wrong_answers = {q["id"]: next(o["id"] for o in q["options"] if not o["is_correct"]) for q in questions}
        correct_answers = {q["id"]: next(o["id"] for o in q["options"] if o["is_correct"]) for q in questions}

        r1 = repo.grade_and_record_module_assessment_attempt(self.user_id, assessment["id"], wrong_answers)
        r2 = repo.grade_and_record_module_assessment_attempt(self.user_id, assessment["id"], wrong_answers)
        r3 = repo.grade_and_record_module_assessment_attempt(self.user_id, assessment["id"], correct_answers)
        self.assertEqual([r1["attempt_number"], r2["attempt_number"], r3["attempt_number"]], [1, 2, 3])
        self.assertFalse(r1["passed"])
        self.assertFalse(r2["passed"])
        self.assertTrue(r3["passed"])
        # sistema não bloqueia novas tentativas
        latest = repo.latest_module_assessment_attempt(self.user_id, assessment["id"])
        self.assertEqual(latest["attempt_number"], 3)
        self.assertTrue(latest["passed"])


class LessonCompletionUnchangedTestCase(unittest.TestCase):
    """Regressão: lesson_meets_completion_criteria não muda de comportamento
    nesta fase (Etapa 10 -- compatibilidade)."""

    def setUp(self):
        self.app, self.db_path = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
        os.remove(self.db_path)

    def test_lesson_without_verification_questions_always_completable(self):
        self.assertTrue(repo.lesson_meets_completion_criteria(999, 999, 70))


class EndToEndRegressionTestCase(unittest.TestCase):
    """Cenário 9 dos testes mínimos: funcionalidades existentes continuam
    funcionando (login, catálogo, matrícula, aula, conclusão, certificado)."""

    def setUp(self):
        self.app, self.db_path = _make_app()
        self.client = self.app.test_client()

    def tearDown(self):
        os.remove(self.db_path)

    def _register(self, n):
        r = self.client.get("/login")
        csrf = _get_csrf(r.get_data(as_text=True))
        r = self.client.post(
            "/registrar",
            data={
                "name": f"Aluno {n}", "username": f"aluno{n}", "email": f"aluno{n}@x.com",
                "password": "Senha123!", "csrf_token": csrf,
            },
            follow_redirects=True,
        )
        return _get_csrf(r.get_data(as_text=True))

    def test_home_and_catalog_still_render(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/cursos")
        self.assertEqual(r.status_code, 200)

    def test_full_block_composition_renders_without_error(self):
        """Testa o renderizador de blocos (Etapa 3) com uma composição real
        de quase todos os tipos do catálogo (Seção 10.2), via HTTP real --
        não só validação de payload. Pega regressões de template que os
        testes de repo (que não renderizam Jinja) não pegariam -- foi assim
        que o bug `p.items` (método de dict vs. chave) foi encontrado."""
        csrf = self._register(3)
        with self.app.app_context():
            course = next(c for c in repo.list_courses(is_marketplace=False) if c.slug == "ia-para-iniciantes")
            lessons = repo.list_lessons_for_course(course.id)
            lesson_id = lessons[1].id
            qid = repo.list_lesson_questions(lesson_id)[0]["id"]
            repo.insert_lesson_block(lesson_id, "heading", 0, {"text": "Introdução"})
            repo.insert_lesson_block(lesson_id, "text", 1, {"markdown": "Texto **forte**."})
            repo.insert_lesson_block(lesson_id, "learning_objective", 2, {"items": ["Entender X"]})
            repo.insert_lesson_block(lesson_id, "image", 3, {"url": "http://x/y.png", "alt": "alt txt"})
            repo.insert_lesson_block(lesson_id, "example", 4, {"content": "Exemplo aqui"})
            repo.insert_lesson_block(lesson_id, "real_world_scenario", 5, {"scenario": "Cenário"})
            repo.insert_lesson_block(lesson_id, "flip_card", 6, {"front": "F", "back": "V"})
            repo.insert_lesson_block(lesson_id, "microchallenge", 7, {"question_id": qid})
            repo.insert_lesson_block(lesson_id, "reflection", 8, {"prompt": "Pense nisso"})
            repo.insert_lesson_block(lesson_id, "summary", 9, {"items": ["Ponto final"]})
            repo.insert_lesson_block(lesson_id, "timeline", 10, {"events": [{"label": "A"}, {"label": "B"}]})
        course_id = course.id
        self.client.post(f"/cursos/{course_id}/matricular", headers={"X-CSRFToken": csrf})
        r = self.client.get(f"/cursos/{course_id}/aula/{lesson_id}")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        for marker in ("Introdução", "Entender X", "alt txt", "MICRODESAFIO", "Ponto final",
                       "componente visual chega em fase futura"):
            self.assertIn(marker, html)


        """Seção 20, item 4: antes da migração, a aula continua sendo
        renderizada pelo caminho antigo (lesson.content + questions soltas)
        -- nada quebra para quem ainda não rodou o script de migração.
        Usa lessons[2]: lessons[0] (Aula 1) agora é pré-semeada com os
        blocos gamificados de aula1.txt por seed_aula1_blocks.py, então já
        não serve como fixture de "aula legada ainda não migrada"."""
        csrf = self._register(2)
        with self.app.app_context():
            course = next(c for c in repo.list_courses(is_marketplace=False) if c.slug == "ia-para-iniciantes")
            lessons = repo.list_lessons_for_course(course.id)
            lesson_id = lessons[2].id
            self.assertFalse(repo.lesson_has_blocks(lesson_id))
        course_id = course.id
        self.client.post(f"/cursos/{course_id}/matricular", headers={"X-CSRFToken": csrf})
        r = self.client.get(f"/cursos/{course_id}/aula/{lesson_id}")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("questionsArea", html)
        self.assertIn("AULA EM TEXTO", html)
        self.assertNotIn("blocksArea", html)

    def test_full_module1_flow_migrated_lesson(self):
        """Usa lessons[2]: lessons[0] (Aula 1) já vem com os blocos
        gamificados de aula1.txt pré-semeados (seed_aula1_blocks.py), então
        não representa mais uma aula legada pendente de migração."""
        csrf = self._register(1)
        with self.app.app_context():
            course = next(c for c in repo.list_courses(is_marketplace=False) if c.slug == "ia-para-iniciantes")
            lessons = repo.list_lessons_for_course(course.id)
            lesson_id = lessons[2].id
            # Migração é um script one-off (Seção 20), não roda automaticamente
            # no boot -- precisa ser executada explicitamente, como em produção.
            migrate_lessons_to_blocks.migrate_lessons_to_blocks()
            questions = repo.list_lesson_questions(lesson_id)
            verification_q = next(q for q in questions if q["kind"] == "verification")
            correct_opt = next(o for o in verification_q["options"] if o["is_correct"])
            wrong_opt = next(o for o in verification_q["options"] if not o["is_correct"])

        course_id = course.id

        r = self.client.post(f"/cursos/{course_id}/matricular", headers={"X-CSRFToken": csrf})
        self.assertEqual(r.status_code, 302)

        # Cenário 1: aula migrada carrega sem erro, com blocos
        r = self.client.get(f"/cursos/{course_id}/aula/{lesson_id}")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("blocksArea", html)

        # Cenário 3/4/5: erra, erra de novo, depois acerta
        r = self.client.post(f"/questoes/{verification_q['id']}/responder",
                              json={"option_id": wrong_opt["id"]}, headers={"X-CSRFToken": csrf})
        self.assertFalse(r.get_json()["is_correct"])
        r = self.client.post(f"/questoes/{verification_q['id']}/responder",
                              json={"option_id": wrong_opt["id"]}, headers={"X-CSRFToken": csrf})
        self.assertFalse(r.get_json()["is_correct"])
        r = self.client.post(f"/questoes/{verification_q['id']}/responder",
                              json={"option_id": correct_opt["id"]}, headers={"X-CSRFToken": csrf})
        self.assertTrue(r.get_json()["is_correct"])

        # Cenário 6: refresh -- estado persistido
        r = self.client.get(f"/cursos/{course_id}/aula/{lesson_id}")
        self.assertIn("Correto", r.get_data(as_text=True))

        # conclusão da aula
        r = self.client.post(f"/cursos/{course_id}/aula/{lesson_id}/concluir", headers={"X-CSRFToken": csrf})
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["done"])

        # Cenário 7: logout / login -- progresso e tentativas continuam consistentes
        self.client.get("/logout")
        r = self.client.get("/login")
        csrf2 = _get_csrf(r.get_data(as_text=True))
        self.client.post("/login", data={"email": "aluno1@x.com", "password": "Senha123!", "csrf_token": csrf2})
        r = self.client.get(f"/cursos/{course_id}/aula/{lesson_id}")
        html = r.get_data(as_text=True)
        self.assertIn("Aula concluída", html)
        self.assertIn("Correto", html)


if __name__ == "__main__":
    unittest.main()
