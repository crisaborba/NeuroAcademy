"""Migração aditiva: lesson.content (Markdown) -> lesson_block (type='text').

Ref.: Seção 20 da especificação técnica do Sistema de Aulas (Etapa 8/9 desta
fase). Mesmo estilo/idempotência dos scripts seed_*.py já existentes no
projeto.

O QUE ESTE SCRIPT FAZ:
  - Para cada aula com content_type='text' e `content` não vazio que ainda
    não tem nenhum lesson_block, cria UM bloco `type='text'` com
    `payload={"markdown": lesson.content}` -- preservando o conteúdo
    original byte a byte, sem reescrita editorial (regra explícita da
    Etapa 8 da tarefa: "NÃO REESCREVA O CONTEÚDO PEDAGÓGICO").

O QUE ESTE SCRIPT NÃO FAZ:
  - Não remove `lesson.content` (nunca) -- é o mecanismo de rollback/
    fallback (Seção 20, item 2).
  - Não migra aulas content_type='video' (não têm Markdown para migrar
    nesta fase; content_type='video' de aulas sem produção real hoje
    é ignorado silenciosamente aqui, e reportado por list de retorno).
  - Não migra lesson_question/lesson_question_option (não precisam migrar
    -- permanecem como estão, Seção 20).

IDEMPOTÊNCIA: uma aula que já tem >=1 lesson_block é pulada
(repo.lesson_has_blocks) -- rodar o script várias vezes nunca duplica
blocos, mesmo padrão de idempotência de seed_course_ia_iniciantes.py.

ROLLBACK: apagar as linhas de lesson_block inseridas por este script
(`DELETE FROM lesson_block WHERE lesson_id IN (...)`) reverte 100% sem
qualquer perda de dado, porque lesson.content nunca foi tocado.

USO:
    python migrate_lessons_to_blocks.py            # roda a migração
    python migrate_lessons_to_blocks.py --dry-run   # só relata, não grava
"""
import sys

from app import create_app
import repo


def migrate_lessons_to_blocks(dry_run=False):
    """Retorna um relatório dict: {migrated: [...], skipped_has_blocks: [...],
    skipped_no_content: [...], skipped_not_text: [...]}."""
    report = {
        "migrated": [],
        "skipped_has_blocks": [],
        "skipped_no_content": [],
        "skipped_not_text": [],
    }
    for lesson in repo.list_all_lessons():
        if lesson.content_type != "text":
            report["skipped_not_text"].append(lesson.id)
            continue
        if repo.lesson_has_blocks(lesson.id):
            report["skipped_has_blocks"].append(lesson.id)
            continue
        if not lesson.content or not lesson.content.strip():
            report["skipped_no_content"].append(lesson.id)
            continue
        if not dry_run:
            repo.insert_lesson_block(
                lesson.id, "text", 0, {"markdown": lesson.content}
            )
        report["migrated"].append(lesson.id)
    return report


def main():
    dry_run = "--dry-run" in sys.argv
    app = create_app()
    with app.app_context():
        report = migrate_lessons_to_blocks(dry_run=dry_run)
    label = "[DRY RUN] " if dry_run else ""
    print(f"{label}Aulas migradas: {report['migrated']}")
    print(f"{label}Aulas já com blocos (puladas): {report['skipped_has_blocks']}")
    print(f"{label}Aulas sem conteúdo (puladas): {report['skipped_no_content']}")
    print(f"{label}Aulas não-texto (puladas): {report['skipped_not_text']}")


if __name__ == "__main__":
    main()
