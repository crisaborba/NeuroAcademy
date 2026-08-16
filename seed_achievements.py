"""Seed da conquista máxima da plataforma: 🏆 Platina NeuroAcademy.

Ref.: Seção 9 do pedido de gamificação ("Crie uma conquista especial...
Ela NÃO deve ser desbloqueável manualmente pelo frontend. Ela deve ser
concedida automaticamente pelo backend quando todos os requisitos
definidos forem cumpridos.").

Conquistas ligadas a UMA aula específica (ex.: "Iniciado Digital" da Aula
1) são seedadas junto com o conteúdo daquela aula (seed_aula1_blocks.py,
seed_aula2_blocks.py, etc.) -- só a conquista global/cross-cutting mora
aqui. Isso é o que torna a infraestrutura reutilizável (Seção 17): cada
nova aula só precisa registrar sua própria conquista de conclusão; esta
função não precisa ser tocada, porque `gamification.platinum_progress`
calcula o total dinamicamente a partir de `achievement` (ver docstring lá).

Idempotente: repo.create_achievement faz UPDATE (não duplica) se o slug já
existir -- seguro rodar em todo boot, como os outros seed_*.py.
"""
from repo import create_achievement
from gamification import PLATINUM_SLUG


def seed_achievements(app):
    with app.app_context():
        create_achievement(
            slug=PLATINUM_SLUG,
            title="🏆 Platina NeuroAcademy",
            description=(
                "Você completou 100% da jornada NeuroAcademy: todas as conquistas "
                "disponíveis na plataforma foram desbloqueadas."
            ),
            xp=500,
            category="platinum",
            rarity="Platina",
            unlock_criteria=(
                "Desbloquear todas as demais conquistas ativas da plataforma "
                "(ver gamification.platinum_progress para a fórmula exata)."
            ),
            is_platinum=True,
            mascot_emoji="🏆",
            active=True,
        )
