"""Seed dos blocos gamificados da AULA 1: "Bem-vindo à Inteligência Artificial".

Fonte da verdade: aula1.txt (especificação pedagógica anexada pelo dono do
produto). Este script NÃO reescreve texto pedagógico -- cada payload abaixo
reproduz o conteúdo dos 12 blocos do documento na ordem exata em que
aparecem.

Only a handful of small technical choices were left to "bom senso técnico"
where aula1.txt describes a *behavior* rather than giving literal text (ex.:
o texto simulado que a IA "digita" no Prompt Builder, os 3 tópicos do
resumo do Momento WOW 3) -- em nenhum lugar a intenção pedagógica ou a
ordem dos blocos foi alterada.

Idempotente: se a aula já tiver blocos (repo.lesson_has_blocks), não faz
nada -- pode rodar no boot com segurança, como os outros seed_*.py.

--- Sistema Real de Gamificação (segunda passada deste script) ---

Os Blocos 2 (escolha da história) e 10 (quiz de fixação) eram, na primeira
versão deste seed, decorativos: a "correção" e o "+XP" existiam só no
JavaScript do navegador, o que violava a Seção 6 do pedido de gamificação
("uma conquista nunca deve ser desbloqueada simplesmente porque um
elemento apareceu na tela" -- o mesmo vale para XP). Agora os dois viram
`lesson_question` reais (a MESMA infraestrutura de pergunta/opção/resposta
já usada por 'microchallenge' desde a Fase 1), com `reward_xp` -- a
gramática visual (cartão de história com letras A/B/C, frase com lacuna
arrastável) continua sendo só a "roupa" que blocks.html põe em cima da
mesma pergunta/opção validada no servidor. Isso significa reaproveitar
literalmente o endpoint /questoes/<id>/responder e toda a lógica de
tentativas ilimitadas / persistência entre reloads que já existiam --
nenhum endpoint novo foi criado para isso (Seção 18: "não duplique a
arquitetura").

A conquista "Iniciado Digital" (Bloco 11) é registrada aqui, ligada a esta
lesson_id, e só é concedida de verdade quando o backend confirma a
conclusão da aula (routes.concluir_aula -> gamification.on_lesson_completed)
-- nunca porque o bloco 11 apareceu na tela.
"""

from db import get_db
from repo import create_achievement, insert_lesson_block, lesson_has_blocks
from validators import BlockValidationError

COURSE_SLUG = "ia-para-iniciantes"


def seed_aula1_blocks(app):
    with app.app_context():
        db = get_db()
        row = db.execute(
            "SELECT l.id FROM lesson l "
            "JOIN module m ON l.module_id = m.id "
            "JOIN course c ON l.course_id = c.id "
            "WHERE c.slug = ? AND m.ord = 0 AND l.ord = 0",
            (COURSE_SLUG,),
        ).fetchone()
        if not row:
            return  # curso/aula ainda não seedados -- nada a fazer

        lesson_id = row["id"]

        # A conquista de conclusão é registrada (create_achievement é
        # idempotente via slug -- UPDATE, não duplica) independentemente do
        # estado dos blocos, para que ajustes futuros de texto/XP não
        # dependam de apagar a aula inteira.
        create_achievement(
            slug="iniciado_digital",
            title="Iniciado Digital",
            description=(
                "Você concluiu sua primeira missão e iniciou sua jornada na "
                "Inteligência Artificial."
            ),
            xp=100,
            category="lesson",
            rarity="Comum",
            lesson_id=lesson_id,
            unlock_criteria=(
                "Concluir a Aula 1: responder corretamente o quiz de fixação "
                "(Bloco 10) e marcar a aula como concluída."
            ),
            mascot_emoji="🚀",
            active=True,
        )

        if lesson_has_blocks(lesson_id):
            return  # idempotente -- blocos já semeados

        # Perguntas legadas desta aula (do antigo seed_course_ia_iniciantes.py
        # em texto corrido) são removidas -- pertenciam ao conteúdo que esta
        # aula substitui; mantê-las penduradas bloquearia
        # lesson_meets_completion_criteria para sempre, já que a aula não
        # renderiza mais `questions` legadas quando `blocks` existe.
        db.execute("DELETE FROM lesson_question WHERE lesson_id = ?", (lesson_id,))
        db.commit()

        story_qid = _insert_question(
            db, lesson_id,
            kind="activity", reward_xp=25,
            prompt="O que você faz?",
            options=[
                ("Começar a digitar um por um no WhatsApp, na esperança de dar tempo.", False,
                 "Funcionaria, mas você não bateria o prazo de meio-dia com 120 mensagens."),
                ("Copiar a mesma mensagem genérica e colar para os 120 contatos.", False,
                 "Rápido, mas frio e impessoal -- não é isso que o gerente pediu."),
                ("Ativar um assistente de IA para criar os 120 textos em 90 segundos.", True,
                 "Isso mesmo! Em instantes, a IA resolveu o que levaria horas."),
            ],
        )

        quiz_qid = _insert_question(
            db, lesson_id,
            kind="verification", reward_xp=50,
            prompt="Para obter uma excelente resposta da IA, você precisa enviar um _________ detalhado.",
            options=[
                ("PROMPT", True, "Isso mesmo! Um bom PROMPT é a chave para uma resposta excelente."),
                ("ALUCINAÇÃO", False, "Quase lá — pense na palavra que representa \"a ordem que você dá à IA\"."),
                ("CÓDIGO", False, "Quase lá — pense na palavra que representa \"a ordem que você dá à IA\"."),
            ],
        )

        for ord_, (block_type, payload) in enumerate(_build_blocks(story_qid, quiz_qid)):
            try:
                insert_lesson_block(lesson_id, block_type, ord_, payload)
            except BlockValidationError:
                # Nunca deixa o boot inteiro cair por causa de um bloco --
                # mesma filosofia defensiva do resto do Sistema de Aulas.
                app.logger.exception(
                    "Bloco inválido ao seedar Aula 1 (ord=%s, type=%s)", ord_, block_type
                )


def _insert_question(db, lesson_id, kind, reward_xp, prompt, options):
    """Insere uma lesson_question real com suas opções -- mesma tabela e
    forma que 'microchallenge' já usa desde a Fase 1 (repo.list_lesson_questions
    / repo.submit_question_answer), só com reward_xp preenchido."""
    cur = db.execute(
        "INSERT INTO lesson_question (lesson_id, kind, prompt, ord, reward_xp) VALUES (?,?,?,0,?)",
        (lesson_id, kind, prompt, reward_xp),
    )
    qid = cur.lastrowid
    for ord_, (label, is_correct, feedback) in enumerate(options):
        db.execute(
            "INSERT INTO lesson_question_option (question_id, label, is_correct, feedback, ord) "
            "VALUES (?,?,?,?,?)",
            (qid, label, 1 if is_correct else 0, feedback, ord_),
        )
    db.commit()
    return qid


def _build_blocks(story_qid, quiz_qid):
    return [
        # BLOCO 1 — Barra de Progresso & Recompensa
        ("progress_header", {
            "mission": "Missão 1: Seu Primeiro Dia na Era da IA",
            "reward_xp": 100,
            "reward_extra": "Início de Sequência 🔥",
            "progress_pct": 0,
        }),

        # BLOCO 2 — Storytelling Interativo (Desafio Prático)
        # Grading real via lesson_question (story_qid) -- ver docstring do
        # módulo. scenario_lines/quote/question são só a moldura narrativa.
        ("story_choice", {
            "scenario_lines": [
                "Segunda-feira, 08:45. Seu primeiro dia em um escritório.",
                "Seu gerente entrega uma lista de 120 clientes e avisa:",
            ],
            "quote": "Preciso de uma mensagem personalizada confirmando o horário de cada um até meio-dia.",
            "question": "O que você faz?",
            "question_id": story_qid,
        }),

        # BLOCO 3 — Momento WOW 1: Transformação Interativa Antes/Depois
        ("before_after_slider", {
            "instruction": "Arraste a barra central para ver o resultado do seu trabalho:",
            "before": {
                "label": "Sem IA - Manual",
                "text": "Olá cliente. Sua reunião é hoje. Não atrase.",
                "meta": "3 horas gastas • Texto frio • Risco de erro alto",
            },
            "after": {
                "label": "Com IA - NeuroAcademy",
                "text": "Olá, Lucas! Passando para confirmar nossa conversa de hoje às 14h. Qualquer imprevisto, só avisar por aqui!",
                "meta": "2 minutos gastor • Personalizado • Erro zero",
            },
        }),

        # BLOCO 4 — Explicação Curta em Vídeo/Animação
        ("concept_reveal", {
            "lines": [
                "A IA não tem cérebro e não pensa como você.",
                "Ela funciona como um assistente ultraeficiente que leu bilhões de textos e aprendeu a prever a resposta perfeita em segundos.",
                "Sua função não é fazer o trabalho por você, mas eliminar a parte chata da sua rotina.",
            ],
        }),

        # BLOCO 5 — Simulador de IA: Prompt Builder
        ("prompt_builder", {
            "instruction": "Tente obter o melhor resultado da IA agora. Monte a sua instrução selecionando os blocos abaixo:",
            "groups": [
                {"label": "Bloco 1 (Ação)", "options": ["Escreva um e-mail curto", "Faça um texto"]},
                {"label": "Bloco 2 (Público)", "options": ["para um cliente VIP", "para um amigo"]},
                {"label": "Bloco 3 (Objetivo)", "options": ["oferecendo 10% de desconto.", "falando sobre vendas."]},
            ],
            "simulated_response": (
                "Assunto: Uma oferta especial para você 🎁\n\n"
                "Olá! Tudo bem? Como um dos nossos clientes VIP, você tem 10% de "
                "desconto exclusivo na sua próxima compra. Aproveite antes que a "
                "oferta acabe!"
            ),
        }),

        # BLOCO 6 — Hotspot de Descoberta (Explore no Clique)
        ("hotspot_discovery", {
            "instruction": "Clique nos pontos brilhantes do escritório para ver onde a IA atua:",
            "hotspots": [
                {"label": "Mesa de RH", "description": "Analisa 50 currículos em segundos e destaca os 5 melhores.", "x": 18, "y": 28},
                {"label": "Atendimento", "description": "Resume conversas longas antes do atendente responder.", "x": 45, "y": 62},
                {"label": "Marketing", "description": "Gera 10 ideias de títulos para anúncios em instantes.", "x": 72, "y": 22},
                {"label": "Gerência", "description": "Transforma planilhas confusas em resumos claros para reuniões.", "x": 85, "y": 68},
            ],
        }),

        # BLOCO 7 — Cartões de Termos Técnicos (Flip Cards), reaproveitando o
        # bloco 'flip_card' já existente no sistema -- dois cartões, na ordem
        # do documento.
        ("flip_card", {
            "front": "O que é um PROMPT?",
            "back": "É a ordem direta e clara que você digita para a IA. Se o comando for bom, a resposta será incrível.",
        }),
        ("flip_card", {
            "front": "O que é IA GENERATIVA?",
            "back": "É a IA capaz de criar coisas novas (textos, imagens, planilhas) a partir da sua ordem, em vez de só buscar links na internet.",
        }),

        # BLOCO 8 — Dica Profissional vs. Erro Comum (Comparativo Clicável)
        ("tip_vs_error", {
            "error_title": "O Maior Erro: Aceitar a resposta da IA sem ler.",
            "error_text": "A IA pode inventar fatos com total convicção (chamamos isso de Alucinação). Sempre verifique datas e dados!",
            "tip_title": "Regra de Ouro (80/20)",
            "tip_text": "A IA faz 80% do trabalho bruto (gerar o rascunho em segundos). Você faz os 20% mais importantes (revisar, ajustar o tom e aprovar).",
        }),

        # BLOCO 9 — Momento WOW 3: Teste de Velocidade Humano vs. IA
        ("speed_challenge", {
            "instruction": "Tente ler e resumir este texto de 300 palavras em menos de 5 segundos.",
            "button_label": "Iniciar Cronômetro",
            "result_intro": "Em 0.8 segundos, a IA leu o texto e gerou este resumo de 3 tópicos. A velocidade não é humana; o direcionamento é seu!",
            "result_items": [
                "A IA já está presente em várias tarefas do seu dia a dia.",
                "Ela funciona prevendo padrões, não pensando como um ser humano.",
                "Sua função é eliminar tarefas repetitivas, não substituir você.",
            ],
        }),

        # BLOCO 10 — Quiz Rápido de Fixação (Drag and Drop / Complete a Frase)
        # Grading real via lesson_question (quiz_qid, kind='verification' --
        # é ela que gera lesson_meets_completion_criteria=True).
        ("drag_drop_quiz", {
            "sentence_before": "Para obter uma excelente resposta da IA, você precisa enviar um",
            "sentence_after": "detalhado.",
            "question_id": quiz_qid,
        }),

        # BLOCO 11 — Resumo Visual & Conquista
        ("completion_dashboard", {
            "title": "Missão Cumprida! 🎉",
            "items": [
                "Você aprendeu que a IA é um assistente de produtividade.",
                "Descobriu o que é um Prompt e como dar ordens eficientes.",
                "Entendeu a regra dos 80/20 para nunca cometer erros no trabalho.",
            ],
            "achievement_title": "Iniciado Digital",
        }),

        # BLOCO 12 — Próximo Passo (Call to Action)
        ("cta_next", {
            "text": "Pronto para aprender a dar ordens que fazem a IA trabalhar como uma especialista para você?",
            "button_label": "ABRIR AULA 2: A ARTE DOS PROMPTS PERFEITOS 🚀",
        }),
    ]
