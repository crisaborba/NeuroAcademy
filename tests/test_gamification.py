"""Testes automatizados -- Sistema Real de Gamificação (Conquistas + XP).

Ref.: pedido "NEUROACADEMY — IMPLEMENTAÇÃO DO SISTEMA REAL DE GAMIFICAÇÃO",
Seção 19 (lista mínima de cenários a cobrir).

Mesmo padrão de tests/test_phase1.py: unittest puro, banco SQLite
temporário próprio por teste (nunca toca em neuroacademy.db), sem
dependência nova.

Uso:
    cd neuroacademy && python -m unittest tests.test_gamification -v
"""
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
import repo
import gamification


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


class GamificationServiceUnitTestCase(unittest.TestCase):
    """Testa gamification.py diretamente (sem HTTP) -- mais rápido e preciso
    para as garantias de idempotência que são o núcleo do pedido."""

    def setUp(self):
        self.app, self.db_path = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = repo.create_user("Teste", "teste_gam", "teste_gam@x.com", "Senha123!")

    def tearDown(self):
        self.ctx.pop()
        os.remove(self.db_path)

    # ---- XP ----

    def test_grant_xp_credits_the_user(self):
        result = gamification.grant_xp(self.user.id, 25, "evento:1", "+25 XP — teste")
        self.assertTrue(result["granted"])
        self.assertEqual(result["amount"], 25)
        self.assertEqual(repo.get_user_by_id(self.user.id).points, 25)

    def test_grant_xp_does_not_duplicate_same_reason_code(self):
        gamification.grant_xp(self.user.id, 25, "evento:1", "+25 XP — teste")
        second = gamification.grant_xp(self.user.id, 25, "evento:1", "+25 XP — teste")
        self.assertFalse(second["granted"])
        self.assertEqual(second["amount"], 0)
        # O total não dobra: continua 25, não 50.
        self.assertEqual(repo.get_user_by_id(self.user.id).points, 25)

    def test_grant_xp_different_reason_codes_both_count(self):
        gamification.grant_xp(self.user.id, 25, "evento:1", "primeiro")
        gamification.grant_xp(self.user.id, 10, "evento:2", "segundo")
        self.assertEqual(repo.get_user_by_id(self.user.id).points, 35)

    def test_grant_xp_zero_or_negative_is_a_noop(self):
        result = gamification.grant_xp(self.user.id, 0, "evento:1", "sem valor")
        self.assertFalse(result["granted"])
        self.assertEqual(repo.get_user_by_id(self.user.id).points, 0)

    # ---- Conquistas ----

    def test_achievement_unlocks_and_grants_its_xp(self):
        repo.create_achievement(slug="teste_a", title="Teste A", description="desc", xp=40)
        result = gamification.unlock_achievement(self.user.id, "teste_a")
        self.assertTrue(result["unlocked"])
        self.assertEqual(result["xp"], 40)
        self.assertEqual(repo.get_user_by_id(self.user.id).points, 40)

    def test_achievement_does_not_duplicate(self):
        repo.create_achievement(slug="teste_b", title="Teste B", description="desc", xp=40)
        gamification.unlock_achievement(self.user.id, "teste_b")
        second = gamification.unlock_achievement(self.user.id, "teste_b")
        self.assertFalse(second["unlocked"])
        # XP não é concedido de novo -- continua 40, não 80.
        self.assertEqual(repo.get_user_by_id(self.user.id).points, 40)
        # E continua existindo só UMA linha de desbloqueio para este usuário.
        unlocked = repo.user_achievements_map(self.user.id)
        self.assertEqual(len(unlocked), 1)

    def test_inactive_achievement_cannot_be_unlocked(self):
        repo.create_achievement(slug="teste_c", title="Teste C", description="desc", xp=40, active=False)
        result = gamification.unlock_achievement(self.user.id, "teste_c")
        self.assertFalse(result["unlocked"])
        self.assertEqual(repo.get_user_by_id(self.user.id).points, 0)

    def test_unknown_slug_is_a_safe_noop(self):
        result = gamification.unlock_achievement(self.user.id, "nao_existe")
        self.assertFalse(result["unlocked"])

    # ---- Platina ----

    def test_platinum_progress_is_zero_with_no_achievements_unlocked(self):
        baseline = gamification.platinum_progress(self.user.id)
        repo.create_achievement(slug="a1", title="A1", description="d", xp=10)
        repo.create_achievement(slug="a2", title="A2", description="d", xp=10)
        progress = gamification.platinum_progress(self.user.id)
        self.assertEqual(progress["unlocked"], baseline["unlocked"])
        self.assertEqual(progress["total"], baseline["total"] + 2)
        self.assertEqual(progress["pct"], 0)

    def test_platinum_progress_updates_as_achievements_unlock(self):
        baseline = gamification.platinum_progress(self.user.id)
        repo.create_achievement(slug="a1", title="A1", description="d", xp=10)
        repo.create_achievement(slug="a2", title="A2", description="d", xp=10)
        gamification.unlock_achievement(self.user.id, "a1")
        progress = gamification.platinum_progress(self.user.id)
        self.assertEqual(progress["unlocked"], baseline["unlocked"] + 1)
        self.assertEqual(progress["total"], baseline["total"] + 2)

    def test_platinum_does_not_unlock_prematurely(self):
        repo.create_achievement(
            slug=gamification.PLATINUM_SLUG, title="Platina", description="d", xp=500, is_platinum=True
        )
        repo.create_achievement(slug="a1", title="A1", description="d", xp=10)
        repo.create_achievement(slug="a2", title="A2", description="d", xp=10)
        gamification.unlock_achievement(self.user.id, "a1")
        result = gamification.maybe_unlock_platinum(self.user.id)
        self.assertFalse(result["unlocked"])
        self.assertFalse(gamification.PLATINUM_SLUG in repo.user_achievements_map(self.user.id).values())

    def test_platinum_unlocks_when_all_requirements_met(self):
        repo.create_achievement(
            slug=gamification.PLATINUM_SLUG, title="Platina", description="d", xp=500, is_platinum=True
        )
        repo.create_achievement(slug="a1", title="A1", description="d", xp=10)
        repo.create_achievement(slug="a2", title="A2", description="d", xp=10)
        # Desbloqueia TODAS as conquistas não-Platina ativas (inclui as que
        # o seed real já registrou, ex. 'iniciado_digital' -- a fórmula é
        # sobre o catálogo inteiro, não só as criadas neste teste).
        for a in repo.list_achievements(active_only=True):
            if not a.is_platinum:
                gamification.unlock_achievement(self.user.id, a.slug)
        result = gamification.maybe_unlock_platinum(self.user.id)
        self.assertTrue(result["unlocked"])
        progress = gamification.platinum_progress(self.user.id)
        self.assertEqual(progress["pct"], 100)

    def test_platinum_does_not_duplicate(self):
        repo.create_achievement(
            slug=gamification.PLATINUM_SLUG, title="Platina", description="d", xp=500, is_platinum=True
        )
        repo.create_achievement(slug="a1", title="A1", description="d", xp=10)
        gamification.unlock_achievement(self.user.id, "a1")
        gamification.maybe_unlock_platinum(self.user.id)
        total_after_first = repo.get_user_by_id(self.user.id).points
        second = gamification.maybe_unlock_platinum(self.user.id)
        self.assertFalse(second["unlocked"])
        self.assertEqual(repo.get_user_by_id(self.user.id).points, total_after_first)


class GamificationHttpTestCase(unittest.TestCase):
    """Testes de ponta a ponta via HTTP real (test_client), mesmo padrão do
    EndToEndRegressionTestCase em test_phase1.py -- cobre a Aula 1 semeada
    de verdade (story_choice + drag_drop_quiz + conclusão + Central de
    Conquistas), não um cenário artificial."""

    def setUp(self):
        self.app, self.db_path = _make_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            course = next(c for c in repo.list_courses(is_marketplace=False) if c.slug == "ia-para-iniciantes")
            self.course_id = course.id
            lesson = repo.list_lessons_for_course(course.id)[0]  # Aula 1
            self.lesson_id = lesson.id
            questions = repo.list_lesson_questions(lesson.id)
            story_q = next(q for q in questions if q["kind"] == "activity")
            quiz_q = next(q for q in questions if q["kind"] == "verification")
            self.story_qid = story_q["id"]
            self.story_correct_opt = next(o["id"] for o in story_q["options"] if o["is_correct"])
            self.story_wrong_opt = next(o["id"] for o in story_q["options"] if not o["is_correct"])
            self.quiz_qid = quiz_q["id"]
            self.quiz_correct_opt = next(o["id"] for o in quiz_q["options"] if o["is_correct"])

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

    def _answer(self, csrf, question_id, option_id):
        return self.client.post(
            f"/questoes/{question_id}/responder",
            json={"option_id": option_id},
            headers={"X-CSRFToken": csrf},
        ).get_json()

    def _concluir(self, csrf):
        return self.client.post(
            f"/cursos/{self.course_id}/aula/{self.lesson_id}/concluir",
            headers={"X-CSRFToken": csrf},
        ).get_json()

    # ---- XP via HTTP ----

    def test_correct_answer_grants_xp(self):
        csrf = self._register(1)
        data = self._answer(csrf, self.story_qid, self.story_correct_opt)
        self.assertTrue(data["is_correct"])
        self.assertEqual(data["xp_granted"], 25)
        self.assertEqual(data["xp_total"], 25)

    def test_wrong_answer_grants_no_xp(self):
        csrf = self._register(1)
        data = self._answer(csrf, self.story_qid, self.story_wrong_opt)
        self.assertFalse(data["is_correct"])
        self.assertEqual(data["xp_granted"], 0)

    def test_answering_correctly_twice_grants_xp_once(self):
        csrf = self._register(1)
        first = self._answer(csrf, self.story_qid, self.story_correct_opt)
        second = self._answer(csrf, self.story_qid, self.story_correct_opt)
        self.assertEqual(first["xp_granted"], 25)
        self.assertEqual(second["xp_granted"], 0)
        self.assertEqual(second["xp_total"], 25)

    def test_xp_persists_after_logout_login(self):
        csrf = self._register(1)
        self._answer(csrf, self.story_qid, self.story_correct_opt)
        self.client.get("/logout")
        r = self.client.get("/login")
        csrf2 = _get_csrf(r.get_data(as_text=True))
        self.client.post("/login", data={"email": "aluno1@x.com", "password": "Senha123!", "csrf_token": csrf2})
        with self.app.app_context():
            user = repo.get_user_by_email("aluno1@x.com")
            self.assertEqual(user.points, 25)

    # ---- Conclusão da aula / conquista ----

    def test_lesson_cannot_be_completed_before_verification_quiz(self):
        csrf = self._register(1)
        data = self._concluir(csrf)
        self.assertFalse(data["ok"])
        self.assertIsNone(data.get("achievement_unlocked"))

    def test_lesson_completion_unlocks_the_real_achievement(self):
        csrf = self._register(1)
        self._answer(csrf, self.quiz_qid, self.quiz_correct_opt)
        data = self._concluir(csrf)
        self.assertTrue(data["ok"])
        self.assertTrue(data["done"])
        self.assertIsNotNone(data["achievement_unlocked"])
        self.assertEqual(data["achievement_unlocked"]["slug"], "iniciado_digital")

    def test_reloading_the_page_does_not_grant_anything_again(self):
        """'Popup não aparece apenas porque o usuário rolou a página' --
        GET nunca tem efeito colateral de recompensa."""
        csrf = self._register(1)
        self._answer(csrf, self.quiz_qid, self.quiz_correct_opt)
        self._concluir(csrf)
        with self.app.app_context():
            points_after_completion = repo.get_user_by_email("aluno1@x.com").points
        # Recarrega a página várias vezes (GET puro).
        for _ in range(3):
            r = self.client.get(f"/cursos/{self.course_id}/aula/{self.lesson_id}")
            self.assertEqual(r.status_code, 200)
        with self.app.app_context():
            self.assertEqual(repo.get_user_by_email("aluno1@x.com").points, points_after_completion)

    def test_toggling_lesson_off_and_on_does_not_regrant_achievement(self):
        csrf = self._register(1)
        self._answer(csrf, self.quiz_qid, self.quiz_correct_opt)
        first = self._concluir(csrf)
        self.assertIsNotNone(first["achievement_unlocked"])
        off = self._concluir(csrf)  # desmarca
        self.assertFalse(off["done"])
        self.assertIsNone(off["achievement_unlocked"])
        on_again = self._concluir(csrf)  # marca de novo
        self.assertTrue(on_again["done"])
        self.assertIsNone(on_again["achievement_unlocked"])
        self.assertEqual(first["xp_total"], on_again["xp_total"])

    def test_achievement_persists_after_logout_login(self):
        csrf = self._register(1)
        self._answer(csrf, self.quiz_qid, self.quiz_correct_opt)
        self._concluir(csrf)
        self.client.get("/logout")
        r = self.client.get("/login")
        csrf2 = _get_csrf(r.get_data(as_text=True))
        self.client.post("/login", data={"email": "aluno1@x.com", "password": "Senha123!", "csrf_token": csrf2})
        with self.app.app_context():
            user = repo.get_user_by_email("aluno1@x.com")
            achievement = repo.get_achievement_by_slug("iniciado_digital")
            self.assertIn(achievement.id, repo.user_achievements_map(user.id))

    # ---- Central de Conquistas ----

    def test_central_shows_zero_progress_for_new_user(self):
        self._register(1)
        r = self.client.get("/perfil/conquistas")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("0/1", html.replace(" ", ""))
        self.assertIn("???", html)  # conquista bloqueada, sem revelar título

    def test_central_shows_unlocked_achievement_and_correct_xp(self):
        csrf = self._register(1)
        self._answer(csrf, self.story_qid, self.story_correct_opt)
        self._answer(csrf, self.quiz_qid, self.quiz_correct_opt)
        self._concluir(csrf)
        r = self.client.get("/perfil/conquistas")
        html = r.get_data(as_text=True)
        self.assertIn("Iniciado Digital", html)
        self.assertIn("Platina NeuroAcademy", html)  # só existe 1 conquista não-Platina hoje
        with self.app.app_context():
            user = repo.get_user_by_email("aluno1@x.com")
            self.assertEqual(user.points, 25 + 50 + 100 + 500)
        self.assertIn(str(25 + 50 + 100 + 500), html)


if __name__ == "__main__":
    unittest.main()
