"""Camada central de gamificação: XP, conquistas e progresso rumo à Platina.

Ref.: pedido "NEUROACADEMY — IMPLEMENTAÇÃO DO SISTEMA REAL DE GAMIFICAÇÃO".

Toda regra de recompensa do produto passa por aqui -- nenhuma rota decide
sozinha "quanto XP" ou "qual conquista"; e nenhum valor vindo do cliente é
usado para creditar recompensa (Seção 16 do pedido: "nunca permita que o
navegador diga 'me dê 500 XP'"). As rotas em routes.py só chamam estas
funções depois de já terem validado o evento no servidor (resposta certa,
aula concluída, etc.) -- o "quanto" sempre vem do banco (achievement.xp,
lesson_question.reward_xp), nunca do request.

Duas garantias estruturais, não convenções que dependem de lembrar de
checar algo:

1. IDEMPOTÊNCIA (Seção 3): cada concessão de XP ou conquista tem uma chave
   estável por usuário (`reason_code` em xp_transaction, `achievement_id`
   em user_achievement) protegida por UNIQUE no banco. Chamar a mesma
   função duas vezes para o mesmo evento é, por construção, um no-op na
   segunda vez -- não existe um "if already_granted" espalhado pelo código
   verificando isso; é a própria constraint que garante.

2. XP É UM SISTEMA SÓ (Seção 2): `user.points`, que já existia (usado pelo
   leaderboard de /comunidade), continua sendo o total. Não criamos um
   segundo contador paralelo -- xp_transaction é o *histórico* que
   sustenta esse total (auditoria + idempotência), não um valor
   concorrente. Ações de comunidade (postar/comentar) continuam somando
   pontos diretamente, como antes desta mudança -- ver limitação
   documentada no relatório final.
"""
import repo

PLATINUM_SLUG = "platina_neuroacademy"


def grant_xp(user_id, amount, reason_code, reason_label, source_type=None, source_id=None, lesson_id=None):
    """Concede `amount` de XP a `user_id`, uma única vez por `reason_code`.

    Devolve sempre {"granted", "amount", "new_total"}: `granted` é True só
    quando este chamado especificamente foi quem creditou o XP (primeira
    vez); em qualquer nova tentativa com o mesmo reason_code, `granted` é
    False e `amount` é 0 -- o total (`new_total`) é sempre o valor real
    atual, então o chamador nunca precisa calcular nada por conta própria.
    """
    if amount <= 0:
        return {"granted": False, "amount": 0, "new_total": repo.get_user_by_id(user_id).points}
    inserted = repo.insert_xp_transaction(
        user_id, amount, reason_code, reason_label, source_type, source_id, lesson_id
    )
    if inserted:
        repo.increment_user_points(user_id, amount)
    new_total = repo.get_user_by_id(user_id).points
    return {"granted": inserted, "amount": amount if inserted else 0, "new_total": new_total}


def unlock_achievement(user_id, slug):
    """Tenta desbloquear a conquista `slug` para `user_id` e conceder o XP
    dela. Idempotente: a segunda chamada (mesmo usuário, mesma conquista)
    devolve unlocked=False e não concede XP de novo."""
    achievement = repo.get_achievement_by_slug(slug)
    empty = {"unlocked": False, "achievement": None, "xp": 0,
              "new_total": repo.get_user_by_id(user_id).points}
    if not achievement or not achievement.active:
        return empty

    inserted = repo.insert_user_achievement(user_id, achievement.id)
    if not inserted:
        return {**empty, "achievement": achievement}

    xp_result = grant_xp(
        user_id, achievement.xp,
        reason_code=f"achievement:{slug}",
        reason_label=f"+{achievement.xp} XP — Conquista: {achievement.title}",
        source_type="achievement", source_id=achievement.id,
        lesson_id=achievement.get("lesson_id"),
    )
    return {
        "unlocked": True,
        "achievement": achievement,
        "xp": xp_result["amount"],
        "new_total": xp_result["new_total"],
    }


def platinum_progress(user_id):
    """Progresso (0-100) rumo à Platina.

    FÓRMULA (v1, documentada -- Seção 8 do pedido):

        progresso = (conquistas ativas e não-Platina DESBLOQUEADAS pelo
                      usuário) / (conquistas ativas e não-Platina que
                      EXISTEM na plataforma) × 100

    Determinística e sempre igual para o mesmo usuário no mesmo estado do
    banco -- nunca hardcoded no frontend. Como o denominador é "quantas
    conquistas existem hoje", o progresso automaticamente passa a refletir
    o curso inteiro à medida que novas aulas seedarem novas conquistas;
    esta função não muda quando isso acontecer.

    Limitação conhecida (reportada no final): com só a Aula 1 implementada,
    há apenas 1 conquista não-Platina cadastrada, então o progresso pula de
    0% a 100% num único evento. Isso é uma consequência do estado atual do
    catálogo, não da fórmula -- ela já está pronta para escalar.
    """
    total = repo.count_achievements(active_only=True, exclude_platinum=True)
    unlocked = repo.count_user_achievements(user_id, exclude_platinum=True)
    pct = round((unlocked / total) * 100) if total else 0
    return {"unlocked": unlocked, "total": total, "pct": min(pct, 100)}


def maybe_unlock_platinum(user_id):
    """Verifica os requisitos globais e concede a Platina automaticamente
    quando cumpridos (Seção 9: "NÃO deve ser desbloqueável manualmente
    pelo frontend"). Idempotente pela mesma UNIQUE de sempre."""
    progress = platinum_progress(user_id)
    if progress["total"] > 0 and progress["unlocked"] >= progress["total"]:
        return unlock_achievement(user_id, PLATINUM_SLUG)
    return {"unlocked": False, "achievement": None, "xp": 0,
            "new_total": repo.get_user_by_id(user_id).points}


def on_question_answered_correctly(user_id, question):
    """Chamado por routes.responder_questao quando a resposta está certa.
    Concede o reward_xp da PRÓPRIA pergunta (fonte única de verdade sobre
    quanto vale acertá-la) -- sem precisar de um endpoint separado de
    "recompensa de bloco". reason_code é por pergunta, então responder
    certo, sair, voltar e ver a resposta já marcada não gera XP de novo."""
    xp = question.get("reward_xp") or 0
    if xp <= 0:
        return {"granted": False, "amount": 0, "new_total": repo.get_user_by_id(user_id).points}
    return grant_xp(
        user_id, xp,
        reason_code=f"question:{question['id']}:correct",
        reason_label=f"+{xp} XP — Resposta correta",
        source_type="question", source_id=question["id"], lesson_id=question["lesson_id"],
    )


def on_lesson_completed(user_id, lesson_id):
    """Chamado por routes.concluir_aula sempre que a aula é marcada como
    concluída -- inclusive em re-toggles (marcar/desmarcar/marcar de novo):
    idempotente por construção, então só a primeira vez real desbloqueia
    algo; as demais chamadas são no-ops seguros e baratos (Seção 3 e
    Seção 7 do pedido: "a conclusão deve ocorrer quando os requisitos reais
    da aula forem cumpridos" -- quem decide isso é lesson_meets_completion_
    criteria, chamado ANTES desta função, em routes.py; esta função só
    reage a uma conclusão que o servidor já validou).

    Desbloqueia a conquista de conclusão da aula (se existir uma cadastrada
    para este lesson_id) e, em seguida, sempre reavalia a Platina."""
    result = {"achievement": None, "platinum": None}
    achievement = repo.get_achievement_for_lesson(lesson_id)
    if achievement:
        unlock_result = unlock_achievement(user_id, achievement.slug)
        if unlock_result["unlocked"]:
            result["achievement"] = unlock_result
    platinum_result = maybe_unlock_platinum(user_id)
    if platinum_result["unlocked"]:
        result["platinum"] = platinum_result
    return result


def lesson_xp_earned(user_id, lesson_id):
    """XP real já creditado a este usuário, nesta aula especificamente
    (soma do ledger, não um número fixo) -- usado pelo dashboard de
    conclusão em vez do antigo `progressPct: 8` hardcoded no frontend."""
    return repo.xp_earned_for_lesson(user_id, lesson_id)


def achievements_catalog_for_user(user_id):
    """Para a Central de Conquistas: cada conquista ativa da plataforma com
    o status (desbloqueada ou não) e a data, quando aplicável."""
    unlocked_map = repo.user_achievements_map(user_id)
    catalog = []
    for a in repo.list_achievements(active_only=True):
        catalog.append({
            "achievement": a,
            "unlocked": a.id in unlocked_map,
            "unlocked_at": unlocked_map.get(a.id),
        })
    return catalog
