# Sistema de Aulas — Fase 1 (Fundação Técnica)

Documentação técnica de referência rápida para quem for mexer no código
depois desta fase. Não repete a especificação completa (ver
`NEUROACADEMY_ESPECIFICACAO_TECNICA_SISTEMA_AULAS_v1.0.md` no pacote de
contexto) — só o que foi efetivamente implementado.

## 1. Arquivos novos

| Arquivo | Papel |
|---|---|
| `validators.py` | `BLOCK_VALIDATORS`, `validate_block()`, `is_block_valid()` -- um validador puro por tipo de bloco. |
| `migrate_lessons_to_blocks.py` | Script one-off, idempotente: `lesson.content` (Markdown) → `lesson_block(type='text')`. |
| `templates/partials/blocks.html` | Macro Jinja `render_block`/`render_blocks` -- o renderizador de blocos. |
| `templates/modulo_avaliacao.html` | Tela mínima (fundação) de avaliação de módulo. |
| `docs/SISTEMA_DE_AULAS_FASE1.md` | Este arquivo. |
| `tests/test_phase1.py` | Suíte de testes automatizados desta fase. |

## 2. Como adicionar um novo tipo de bloco

1. Adicionar um validador em `validators.py` → `BLOCK_VALIDATORS["novo_tipo"] = fn`.
2. Adicionar um `{% elif type == 'novo_tipo' %}` em `templates/partials/blocks.html`
   (ou deixar de fora do renderizador de propósito, documentando em
   `BLOCK_TYPES_NOT_YET_RENDERED`, se o componente visual for de fase futura).
3. Nenhuma migration é necessária — `payload` é `TEXT` (JSON) livre; só a
   validação em Python muda.

## 3. Como funciona a leitura de uma aula

```
repo.list_lesson_blocks(lesson_id)
    → lê lesson_block ORDER BY ord, id
    → json.loads(payload) + validate_block(type, payload)
    → se falhar (JSON corrompido OU payload não passa mais na validação):
          bloco volta com valid=False, payload={}
          (nunca lança exceção -- Seção 11 da spec técnica)
```

O template (`aula.html`) escolhe entre dois caminhos:

```
{% if blocks %}      -> renderiza via templates/partials/blocks.html (novo)
{% else %}            -> renderiza lesson.content + questions soltas (legado)
{% endif %}
```

Uma aula só entra no caminho novo depois que
`migrate_lessons_to_blocks.py` (ou uma inserção manual via
`repo.insert_lesson_block`) tiver criado ao menos um `lesson_block` para
ela. **Rodar a migração não é automático no boot** — é um passo explícito,
assim como os scripts `seed_*.py` já existentes.

## 4. Bloco `microchallenge` não duplica perguntas

`{"question_id": 3}` só referencia uma linha já existente em
`lesson_question`. Toda a lógica de correção, feedback e persistência de
resposta continua vivendo em `lesson_question`/`lesson_question_option`/
`user_question_answer`+`submit_question_answer` (inalterados nesta fase).
O bloco é só "onde, na composição da aula, essa pergunta aparece".

## 5. Tentativas ilimitadas — o que mudou de fato

- **Backend:** nada mudou (já sobrescrevia a resposta via
  `ON CONFLICT DO UPDATE`, ver `repo.submit_question_answer`).
- **Frontend (`aula.html`, script inline):** resposta incorreta agora
  reabre os botões (com um pequeno delay para o aluno ler o feedback) em
  vez de desabilitá-los para sempre. Resposta correta marca
  `data-answered="1"` e não reabre.
- **F5 / login-logout:** `repo.user_answers_for_lesson()` devolve as
  respostas já dadas; o template pré-renderiza o estado (opção marcada,
  feedback visível) para que o F5 não pareça "esquecer" a resposta.

## 6. Avaliação de módulo — fundação (não é a UI final)

Tabelas: `module_assessment`, `module_assessment_question`,
`module_assessment_option`, `user_module_assessment_attempt` (mesmo
padrão de `course_assessment_*`, mas para módulo, nunca para curso --
Decisão 2 da Seção 30 da spec técnica).

Rotas (mínimas, sem revisão de gabarito nem tela de introdução elaborada):

```
GET  /cursos/<course_id>/modulo/<module_id>/avaliacao
POST /cursos/<course_id>/modulo/<module_id>/avaliacao/enviar   {"answers": {"<question_id>": <option_id>, ...}}
```

Correção sempre no servidor (`repo.grade_and_record_module_assessment_attempt`)
-- o cliente nunca envia pontuação. Cada envio cria uma nova linha
(`attempt_number` incremental) -- nunca sobrescreve, ao contrário de
`user_question_answer`.

## 7. O que foi deliberadamente deixado fora desta fase

- Componente visual para `comparison`, `timeline`, `interactive_diagram`
  (estrutura validada, aviso "chega em fase futura" no lugar do
  componente).
- Bloco `video` (documentado no catálogo, sem validador ativo -- levanta
  `BlockValidationError` se alguém tentar inserir um hoje).
- `final_project` / `user_final_project_submission` (fora do escopo exato
  desta fase -- ver relatório da Fase 1).
- Breadcrumb curso › módulo › aula e barra de progresso do módulo dentro
  da aula (Fase 5 do plano de implementação da spec técnica).
- Painel administrativo / edição de conteúdo fora de scripts Python.
