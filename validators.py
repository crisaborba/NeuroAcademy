"""Validation for lesson_block payloads.

Mesmo estilo de utils.py (funções puras, pequenas, sem dependência nova) --
ver Seção 11 da especificação técnica do Sistema de Aulas.

Cada tipo de bloco tem um validador próprio em BLOCK_VALIDATORS. Um
validador recebe o `payload` já deserializado (dict) e devolve True/False.
Ele NUNCA levanta exceção sozinho -- validate_block() é quem decide o que
fazer com um resultado negativo, para que o chamador (rota, script de
migração, script de seed) escolha como reagir (abortar, logar, pular).

`video` está documentado no catálogo (Seção 10.2 da spec) mas não tem
validador aqui de propósito -- é um tipo futuro, ainda não implementado
nesta fase (Etapa 11 da tarefa: preparar, não implementar).
"""


def _non_empty_str(value):
    return isinstance(value, str) and value.strip() != ""


def _list_of_non_empty_str(value, min_len=1):
    return (
        isinstance(value, list)
        and len(value) >= min_len
        and all(_non_empty_str(v) for v in value)
    )


def _validate_heading(p):
    if not _non_empty_str(p.get("text")):
        return False
    level = p.get("level", 2)
    return level in (2, 3)


def _validate_text(p):
    return _non_empty_str(p.get("markdown"))


def _validate_learning_objective(p):
    return _list_of_non_empty_str(p.get("items"), min_len=1)


def _validate_image(p):
    return _non_empty_str(p.get("url")) and _non_empty_str(p.get("alt"))


def _validate_example(p):
    return _non_empty_str(p.get("content"))


def _validate_real_world_scenario(p):
    return _non_empty_str(p.get("scenario"))


def _validate_flip_card(p):
    return _non_empty_str(p.get("front")) and _non_empty_str(p.get("back"))


def _validate_comparison(p):
    columns = p.get("columns")
    if not isinstance(columns, list) or len(columns) < 2:
        return False
    for col in columns:
        if not isinstance(col, dict):
            return False
        if not _non_empty_str(col.get("title")):
            return False
        if not isinstance(col.get("items"), list):
            return False
    return True


def _validate_timeline(p):
    events = p.get("events")
    if not isinstance(events, list) or len(events) < 2:
        return False
    for ev in events:
        if not isinstance(ev, dict) or not _non_empty_str(ev.get("label")):
            return False
    return True


def _validate_interactive_diagram(p):
    # Estrutura livre por enquanto (Seção 10.2) -- só garante o formato
    # mínimo (duas listas) para não aceitar qualquer coisa como payload.
    return isinstance(p.get("nodes"), list) and isinstance(p.get("connections"), list)


def _validate_microchallenge(p):
    qid = p.get("question_id")
    return isinstance(qid, int) and not isinstance(qid, bool) and qid > 0


def _validate_reflection(p):
    return _non_empty_str(p.get("prompt"))


def _validate_summary(p):
    return _list_of_non_empty_str(p.get("items"), min_len=1)


def _int_ge0(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _number_in_range(value, lo=0, hi=100):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and lo <= value <= hi


# ── Blocos gamificados (Aula 1 -- "Bem-vindo à Inteligência Artificial") ──
# Mesmo padrão dos validadores acima: puro, sem efeito colateral, nunca
# levanta exceção sozinho. Cada um corresponde a um bloco do documento
# fonte da verdade (aula1.txt).

def _validate_progress_header(p):
    return (
        _non_empty_str(p.get("mission"))
        and _int_ge0(p.get("reward_xp"))
        and isinstance(p.get("reward_extra", ""), str)
        and _number_in_range(p.get("progress_pct", 0))
    )


def _validate_story_choice(p):
    if not _list_of_non_empty_str(p.get("scenario_lines"), min_len=1):
        return False
    if not _non_empty_str(p.get("quote")) or not _non_empty_str(p.get("question")):
        return False
    qid = p.get("question_id")
    return isinstance(qid, int) and not isinstance(qid, bool) and qid > 0


def _validate_before_after_slider(p):
    if not _non_empty_str(p.get("instruction")):
        return False
    for side in ("before", "after"):
        s = p.get(side)
        if not isinstance(s, dict):
            return False
        if not _non_empty_str(s.get("label")) or not _non_empty_str(s.get("text")):
            return False
        if not _non_empty_str(s.get("meta")):
            return False
    return True


def _validate_concept_reveal(p):
    return _list_of_non_empty_str(p.get("lines"), min_len=1)


def _validate_prompt_builder(p):
    if not _non_empty_str(p.get("instruction")):
        return False
    groups = p.get("groups")
    if not isinstance(groups, list) or len(groups) < 2:
        return False
    for g in groups:
        if not isinstance(g, dict) or not _non_empty_str(g.get("label")):
            return False
        if not _list_of_non_empty_str(g.get("options"), min_len=2):
            return False
    return _non_empty_str(p.get("simulated_response"))


def _validate_hotspot_discovery(p):
    if not _non_empty_str(p.get("instruction")):
        return False
    hotspots = p.get("hotspots")
    if not isinstance(hotspots, list) or len(hotspots) < 2:
        return False
    for h in hotspots:
        if not isinstance(h, dict):
            return False
        if not _non_empty_str(h.get("label")) or not _non_empty_str(h.get("description")):
            return False
        if not _number_in_range(h.get("x", -1)) or not _number_in_range(h.get("y", -1)):
            return False
    return True


def _validate_tip_vs_error(p):
    return all(
        _non_empty_str(p.get(k))
        for k in ("error_title", "error_text", "tip_title", "tip_text")
    )


def _validate_speed_challenge(p):
    return (
        _non_empty_str(p.get("instruction"))
        and _non_empty_str(p.get("button_label"))
        and _non_empty_str(p.get("result_intro"))
        and _list_of_non_empty_str(p.get("result_items"), min_len=1)
    )


def _validate_drag_drop_quiz(p):
    if not _non_empty_str(p.get("sentence_before")) or not _non_empty_str(p.get("sentence_after")):
        return False
    qid = p.get("question_id")
    return isinstance(qid, int) and not isinstance(qid, bool) and qid > 0


def _validate_completion_dashboard(p):
    return (
        _non_empty_str(p.get("title"))
        and _list_of_non_empty_str(p.get("items"), min_len=1)
        and _non_empty_str(p.get("achievement_title"))
    )


def _validate_cta_next(p):
    return _non_empty_str(p.get("text")) and _non_empty_str(p.get("button_label"))


BLOCK_VALIDATORS = {
    "heading": _validate_heading,
    "text": _validate_text,
    "learning_objective": _validate_learning_objective,
    "image": _validate_image,
    "example": _validate_example,
    "real_world_scenario": _validate_real_world_scenario,
    "flip_card": _validate_flip_card,
    "comparison": _validate_comparison,
    "timeline": _validate_timeline,
    "interactive_diagram": _validate_interactive_diagram,
    "microchallenge": _validate_microchallenge,
    "reflection": _validate_reflection,
    "summary": _validate_summary,
    "progress_header": _validate_progress_header,
    "story_choice": _validate_story_choice,
    "before_after_slider": _validate_before_after_slider,
    "concept_reveal": _validate_concept_reveal,
    "prompt_builder": _validate_prompt_builder,
    "hotspot_discovery": _validate_hotspot_discovery,
    "tip_vs_error": _validate_tip_vs_error,
    "speed_challenge": _validate_speed_challenge,
    "drag_drop_quiz": _validate_drag_drop_quiz,
    "completion_dashboard": _validate_completion_dashboard,
    "cta_next": _validate_cta_next,
}

# Tipos documentados no catálogo (Seção 10.2) que ainda não têm renderização
# no frontend nesta fase -- a estrutura de dados já suporta, só não há
# componente visual ainda (Etapa 3 da tarefa: "deixe sua estrutura preparada
# e documentada" quando não for necessário implementar agora).
BLOCK_TYPES_NOT_YET_RENDERED = {"comparison", "timeline", "interactive_diagram"}

# Tipo documentado, mas nem validador nem renderização existem ainda --
# reservado para uma fase futura (vídeo), listado aqui só para referência.
FUTURE_BLOCK_TYPES = {"video"}


class BlockValidationError(ValueError):
    """Erro específico para payload de bloco inválido ou tipo desconhecido."""


def validate_block(block_type, payload):
    """Valida um (type, payload) de lesson_block.

    Levanta BlockValidationError com uma mensagem clara se:
      - o tipo é desconhecido (não está em BLOCK_VALIDATORS nem em
        FUTURE_BLOCK_TYPES);
      - o payload não é um dict;
      - o payload não passa no validador do tipo.

    Não modifica o payload. Não tem efeito colateral (não toca no banco) --
    quem chama decide o que fazer com o resultado.
    """
    if not isinstance(payload, dict):
        raise BlockValidationError(
            f"Payload do bloco '{block_type}' precisa ser um objeto JSON, "
            f"recebido: {type(payload).__name__}"
        )

    if block_type in FUTURE_BLOCK_TYPES:
        raise BlockValidationError(
            f"Tipo de bloco '{block_type}' ainda não é suportado nesta fase "
            f"(reservado para implementação futura)."
        )

    validator = BLOCK_VALIDATORS.get(block_type)
    if not validator:
        raise BlockValidationError(f"Tipo de bloco desconhecido: '{block_type}'")

    if not validator(payload):
        raise BlockValidationError(
            f"Payload inválido para bloco do tipo '{block_type}': {payload!r}"
        )

    return True


def is_block_valid(block_type, payload):
    """Versão booleana de validate_block, para chamadores que preferem
    checar em vez de tratar exceção (ex.: renderização, Seção 11: 'Não
    permita que um bloco inválido cause uma falha completa da página')."""
    try:
        validate_block(block_type, payload)
        return True
    except BlockValidationError:
        return False
