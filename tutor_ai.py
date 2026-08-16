"""Motor simples de respostas da NeuroIA (tutora virtual).

Nao depende de servicos externos: usa correspondencia de palavras-chave para
devolver respostas uteis e contextuais, como no prototipo original.
"""

RESPONSES = {
    "plano": (
        "Otimo! Vou criar um plano de 30 dias para voce:\n\n"
        "**Semana 1 - Fundamentos**\n"
        "- Dias 1-3: O que e IA e como funciona\n"
        "- Dias 4-5: Principais ferramentas disponiveis\n"
        "- Dias 6-7: Pratica com assistentes de IA\n\n"
        "**Semana 2 - Prompt Engineering**\n"
        "- Dias 8-10: Tecnicas basicas de prompts\n"
        "- Dias 11-14: Casos praticos de uso\n\n"
        "**Semana 3 - Aplicacoes**\n"
        "- Dias 15-20: IA para estudo e trabalho\n"
        "- Dia 21: Projeto pratico\n\n"
        "**Semana 4 - Carreira**\n"
        "- Dias 22-28: Portfolio com IA\n"
        "- Dias 29-30: Revisao e certificacao\n\n"
        "Quer que eu detalhe alguma dessas etapas?"
    ),
    "curso": (
        "Para comecar, recomendo o curso **IA do Zero: Guia Completo para Iniciantes** - "
        "ele cobre os fundamentos sem exigir conhecimento previo de programacao.\n\n"
        "Depois, da pra seguir para **ChatGPT & Copilots** e, quando estiver confortavel, "
        "Engenharia de Prompts. Quer que eu monte a ordem completa da sua trilha?"
    ),
    "ferramenta": (
        "Depende do seu objetivo:\n\n"
        "- Para conversar e escrever: ChatGPT ou Claude\n"
        "- Para gerar imagens: Midjourney ou geradores de imagem integrados\n"
        "- Para pesquisar com fontes: motores de busca com IA\n"
        "- Para programar: copilots de codigo\n\n"
        "Da uma olhada na pagina de Ferramentas para comparar todas com avaliacoes."
    ),
    "prova": (
        "Otima ideia usar IA para estudar! Algumas tecnicas:\n\n"
        "- Peca para gerar resumos dos seus materiais\n"
        "- Crie flashcards automaticamente a partir das suas anotacoes\n"
        "- Peca simulados com perguntas no estilo da prova\n"
        "- Use a IA para explicar conceitos dificeis de formas diferentes ate fazer sentido\n\n"
        "Quer que eu monte um roteiro de estudos para sua proxima prova?"
    ),
    "certificado": (
        "Os certificados da NeuroAcademy sao emitidos automaticamente quando voce completa "
        "100% das aulas de um curso. Voce pode conferir e baixar seus certificados na sua "
        "pagina de Perfil, na secao de certificados."
    ),
    "default": (
        "Otima pergunta! Deixa eu te ajudar com isso.\n\n"
        "Baseado no que voce perguntou, posso recomendar comecar pelo **curso de fundamentos de IA** "
        "- ele vai dar a base que voce precisa para avancar.\n\n"
        "Quer que eu monte um plano de estudo personalizado para voce?"
    ),
}

KEYWORD_MAP = [
    (("plano", "30 dias", "cronograma"), "plano"),
    (("curso", "por onde", "comecar"), "curso"),
    (("ferramenta", "qual ia usar", "chatgpt", "midjourney", "imagem"), "ferramenta"),
    (("prova", "estudar", "estudo", "aprender melhor"), "prova"),
    (("certificado", "certificacao"), "certificado"),
]


def ai_reply(text: str, context: dict | None = None) -> str:
    """Return a reply for the tutor chat.

    `context`, when provided, carries a snapshot of the logged-in student
    (name, enrolled courses, plan, etc. -- see routes.tutor_mensagem). The
    matching is still keyword-based today; this signature exists so that a
    future, genuinely contextualized NeuroIA (per the product vision: a
    tutor aware of the student's courses/progress/roadmap, not a generic
    chatbot) can be dropped in here without touching the route or the
    frontend contract. `context` is currently only used for a light
    personalization touch (using the student's first name).
    """
    context = context or {}
    lower = (text or "").lower()

    reply = RESPONSES["default"]
    for keywords, key in KEYWORD_MAP:
        if any(k in lower for k in keywords):
            reply = RESPONSES[key]
            break

    first_name = context.get("first_name")
    if first_name and key_is_greeting_worthy(lower):
        reply = f"{first_name}, {reply[0].lower()}{reply[1:]}"
    return reply


def key_is_greeting_worthy(lower_text: str) -> bool:
    """Only prefix the student's name for short/simple greetings, so we
    don't awkwardly interrupt a longer, structured answer (e.g. the 30-day
    plan) with a mid-sentence name insertion."""
    return len(lower_text) < 40
