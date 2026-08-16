# NeuroAcademy — Fase 2: Experiência de Aprendizagem (UX/UI)

## Nota inicial importante

O pacote recebido junto com o prompt continha o código (zip) e o
`docs/SISTEMA_DE_AULAS_FASE1.md`. Os demais documentos citados no prompt
(especificação pedagógica, especificação oficial do Sistema de Aulas,
especificação visual/UX, especificação técnica completa e o "contexto de
transferência da Fase 1" como arquivo à parte) **não estavam no zip enviado**
— só o README e o `SISTEMA_DE_AULAS_FASE1.md`. O trabalho abaixo foi guiado
pelo texto do próprio prompt (que é bem específico) e pelo código/testes
existentes, que serviram como a "fonte da verdade" sobre o que já estava
implementado e o que a Fase 1 deixou explicitamente fora do escopo. Se algum
desses documentos existir e não tiver sido anexado, vale conferir se algo
aqui diverge do que eles descrevem — nenhuma decisão de design contradiz o
que está no `SISTEMA_DE_AULAS_FASE1.md` ou nos testes.

---

## Resumo

A página de aula (`aula.html`) e o renderizador de blocos (`blocks.html`)
foram redesenhados para parecer uma sala de aula moderna em vez de um wall
of text. Mudança é só de **experiência/visual** — nenhuma regra de negócio,
rota, endpoint ou schema de banco mudou. A suíte de testes da Fase 1
(`tests/test_phase1.py`, 25 testes) passa sem alteração nenhuma nos testes.

Entregue:

- Largura de leitura redesenhada (coluna de leitura com largura ótima,
  centralizada, em vez de esticar o texto pela tela toda em monitores
  grandes).
- Modo Foco (esconde sidebar/topbar/sumário, amplia a área de leitura,
  `Esc` ou botão flutuante para sair).
- Hierarquia visual por bloco: cada tipo (texto, objetivo, imagem, exemplo,
  mundo real, flip card, microdesafio, reflexão, resumo) tem cor de
  destaque e ícone próprios, mas a mesma linguagem visual (cartão,
  espaçamento, tipografia).
- Flip cards com virada 3D suave (CSS), acessíveis via teclado (é um
  `<button>` real, não uma `div` com `onclick`).
- Feedback de microdesafio mais educativo visualmente (cartão de feedback
  com cor e ícone, não só texto solto).
- Breadcrumb curso › módulo › aula, barra de progresso do módulo, posição
  da aula ("Aula 3 de 8") e barra fina de progresso de leitura (rolagem).
- Sumário do curso (TOC) lateral agrupado por módulo, com progresso por
  módulo, aula atual destacada, e colapsável — vira gaveta em mobile.
- Navegação da aula: Anterior / Próxima / Voltar ao módulo (deep-link para
  o módulo certo em `curso_detalhe.html`).
- Responsividade desktop → mobile revisada conscientemente (não só
  "encolher"), com padding, tipografia e componentes ajustados por
  breakpoint.
- Acessibilidade: `aria-label`, `aria-pressed`, `aria-expanded` nos
  controles interativos novos (Modo Foco, flip card, TOC), navegação por
  teclado no flip card e no colapsar de módulos do TOC, foco visível.

---

## Arquivos alterados

| Arquivo | O que mudou |
|---|---|
| `templates/aula.html` | Reescrito: breadcrumb, barra de progresso do módulo/posição, Modo Foco, coluna de leitura, TOC lateral agrupado por módulo, navegação (anterior/próxima/voltar ao módulo), barra de progresso de leitura. IDs e textos exigidos pelos testes (`blocksArea`, `questionsArea`, `AULA EM TEXTO`, `completeBtn`, `gateHint`, feedback contendo "Correto") foram preservados. |
| `templates/partials/blocks.html` | Reescrito visualmente: cada tipo de bloco ganhou classe/cor/ícone próprios (`.block-card`, `.block-eyebrow`, variantes `accent-*`). Nenhuma regra de validação ou lógica de dados mudou; o fallback "componente visual chega em fase futura" para `comparison`/`timeline`/`interactive_diagram` continua igual (texto preservado). |
| `templates/curso_detalhe.html` | Adicionado `id="modulo-{{ m.id }}"` em cada cartão de módulo, só para o link "Voltar ao módulo" da aula funcionar como deep-link. |
| `templates/partials/icons.html` | 4 ícones novos: `maximize`, `minimize` (Modo Foco), `list` (sumário do curso), `flag` (posição da aula). |
| `static/css/style.css` | Adicionada uma seção nova ("FASE 2 — EXPERIÊNCIA DE APRENDIZAGEM DA AULA") com todo o CSS da página de aula: coluna de leitura, blocos, flip card, microdesafio, Modo Foco, TOC, breadcrumb, barra de progresso, responsividade. Nada do CSS existente (usado pelo resto do site) foi removido ou alterado. |
| `routes.py` | Rota `aula()`: passou a calcular e enviar ao template `module`, `module_position`, `module_total`, `module_pct`, `course_pct`, `modules`, `modules_pct` — todos via funções de repositório já existentes desde a Fase 1 (`repo.get_module`, `repo.module_progress`, `repo.list_modules_with_lessons`, `repo.recompute_progress`). Nenhuma query nova foi escrita; nenhuma rota nova foi criada. |

## Componentes criados

- **Modo Foco** (`.focus-toggle` / `body.focus-mode`) — alterna via botão,
  `Esc`, ou botão flutuante de saída; lembrado durante a aba (sessionStorage,
  não persiste entre sessões de propósito).
- **Barra de progresso de leitura** (`.reading-progress`) — sticky no topo
  da coluna, preenche conforme a rolagem da página.
- **Barra de progresso do módulo + posição da aula** (`.lesson-progress-bar`).
- **Breadcrumb da aula** (`.lesson-breadcrumb`).
- **Sumário do curso agrupado por módulo** (`.lesson-toc`), com progresso por
  módulo, aula atual destacada, colapsável por módulo, e como gaveta em
  mobile (`.lesson-toc.is-open`).
- **Sistema de cartões de bloco** (`.block-card` + variantes `accent-blue`,
  `accent-purple`, `accent-cyan`, `accent-green`, `accent-dashed`,
  `accent-red`) usado por todos os tipos de bloco.
- **Flip card 3D acessível** (`.flip-card-wrap`, `.flip-card-btn`,
  `.flip-card-inner`).
- **Feedback de microdesafio estilizado** (`.question-feedback.fb-correct` /
  `.fb-wrong`), com destaque temporário no cartão (`.just-answered-ok` /
  `.just-answered-wrong`) quando o aluno responde.

## Melhorias implementadas

Ver "Resumo" acima — cobre aparência simples, texto contínuo, hierarquia
visual, sensação de progresso, uso do espaço da tela, separação entre
blocos e responsividade, que eram os problemas listados no prompt.

## Melhorias adiadas

Fora do escopo desta fase, por instrução explícita do prompt ("NÃO
IMPLEMENTAR") ou por já estarem documentadas como fase futura em
`SISTEMA_DE_AULAS_FASE1.md`:

- Componente visual para `comparison`, `timeline`, `interactive_diagram`
  (estrutura validada, aviso "chega em fase futura" mantido).
- Bloco `video` (sem validador ativo, como já era).
- Projeto final / avaliação final de curso, CMS, vídeos, gamificação
  pesada, rankings, fórum, chat, marketplace novo.
- Reescrita editorial do conteúdo do Módulo 1 — só o texto **auxiliar**
  (rótulos, ícones, badges) foi adicionado; o conteúdo pedagógico em si não
  foi tocado.
- Tela de introdução elaborada e revisão de gabarito da avaliação de
  módulo — a fundação de dados já existe desde a Fase 1, a UI completa
  segue como próxima fase.
- Animações de entrada por bloco ao rolar a página (fade/slide) foram
  deliberadamente **não** adicionadas: o prompt pede performance e
  animações discretas, e a Fase 1 já tem uma sensação de "salas" via
  espaçamento e cartões — um `IntersectionObserver` por bloco a mais
  pareceu risco/benefício desnecessário nesta fase.

## Testes realizados

- **Suíte automatizada:** `python -m unittest tests.test_phase1 -v` → 25/25
  testes passando, sem nenhuma alteração no arquivo de teste.
- **Fluxo ponta a ponta manual** (via `test_client`, simulando navegador):
  registro → matrícula → migração de blocos → GET da aula migrada → resposta
  errada/errada/certa a uma verificação → refresh (estado persistido) →
  concluir aula → logout/login → estado ainda consistente.
- **Renderização de todos os tipos de bloco** juntos numa aula real (heading,
  text, learning_objective, image, example, real_world_scenario, flip_card,
  microchallenge, reflection, summary, timeline) sem erro de template.
- **Caminho legado** (aula sem `lesson_block`) continua renderizando com
  `questionsArea` / "AULA EM TEXTO" e sem `blocksArea`.
- **Deep-link do módulo:** confirmado que `curso_detalhe.html` responde 200
  e contém `id="modulo-<id>"` para o link "Voltar ao módulo" funcionar.
- **Compilação Python** de `routes.py`, `repo.py`, `models.py`, `app.py`
  (`py_compile`) sem erros de sintaxe.
- **Manual/visual:** não foi possível abrir um navegador real neste ambiente
  (sem servidor gráfico) — a responsividade, Modo Foco, flip card e TOC
  foram verificados por leitura cuidadosa do CSS/JS e por inspeção do HTML
  gerado, não por screenshot. Recomendo abrir a aula localmente
  (`python3 app.py` → `/cursos/<id>/aula/<id>`) e testar visualmente em
  desktop/tablet/mobile antes de considerar esta fase 100% fechada.

## Problemas encontrados

- Os arquivos de especificação citados no prompt (pedagógica, visual/UX,
  técnica completa, contexto de transferência da Fase 1 como documento à
  parte) não vieram no zip — só código + `SISTEMA_DE_AULAS_FASE1.md` +
  README. Trabalhei com o que existe; se houver divergência com algum
  desses documentos quando forem anexados, vale um segundo olhar.
- Nenhum bloco do tipo `image`, `flip_card`, `example`, etc. está de fato
  populado no Módulo 1 hoje — a migração da Fase 1 só converteu
  `lesson.content` (Markdown) em blocos `text`. Os componentes visuais para
  os outros tipos estão prontos e testados, mas só vão aparecer de verdade
  quando o conteúdo for enriquecido com esses blocos (isso é, de propósito,
  a "grande reescrita" mencionada no prompt como tarefa futura).
- Sem navegador real disponível neste ambiente para captura de tela /
  teste visual interativo (ver "Testes realizados" acima).

## Recomendação para a próxima fase

1. Popular o Módulo 1 com pelo menos um bloco de cada tipo novo (`image`,
   `flip_card`, `example`, `real_world_scenario`) para validar visualmente
   o sistema com conteúdo real, antes da reescrita editorial completa.
2. Implementar a tela de introdução da avaliação de módulo e a revisão de
   gabarito (fundação de dados já pronta desde a Fase 1).
3. Considerar registrar imagens ilustrativas reais (não decorativas) para
   os primeiros blocos migrados, já que "poucas imagens" era um dos
   problemas citados.
4. Teste real em navegador (desktop, tablet, mobile) e com leitor de tela,
   já que a verificação nesta fase foi por código/HTML, não visual.

---

# CONTEXTO DE TRANSFERÊNCIA — PRÓXIMO CHAT

## O que mudou nesta fase (delta)

- `templates/aula.html`: reescrito (layout, Modo Foco, TOC, breadcrumb,
  progresso, navegação). IDs/textos usados pelos testes preservados.
- `templates/partials/blocks.html`: reescrito (visual apenas — mesma
  validação/lógica).
- `templates/curso_detalhe.html`: `id="modulo-{{ m.id }}"` adicionado por
  cartão de módulo.
- `templates/partials/icons.html`: ícones `maximize`, `minimize`, `list`,
  `flag` adicionados.
- `static/css/style.css`: seção nova ao final do arquivo, só com estilos da
  página de aula (nada removido/alterado do CSS pré-existente).
- `routes.py`: rota `aula()` passa agora `module`, `module_position`,
  `module_total`, `module_pct`, `course_pct`, `modules`, `modules_pct` ao
  template (via funções de repo já existentes — nenhuma query nova).

## O que **não** mudou

- Nenhuma tabela, coluna ou migração de banco.
- Nenhuma rota nova, nenhum endpoint novo.
- Nenhuma regra de conclusão de aula/módulo, correção de questão, ou
  tentativas ilimitadas — tudo isso continua exatamente como a Fase 1
  implementou (`repo.py` não foi tocado além da leitura de funções já
  existentes a partir de `routes.py`).
- Conteúdo pedagógico do Módulo 1 (nenhum texto de aula foi reescrito).

## Estado atual

- 25/25 testes de `tests/test_phase1.py` passam.
- A aula migrada (Módulo 1) hoje só tem blocos `text` (herdados da
  migração) — os componentes visuais dos demais tipos existem e foram
  testados isoladamente, mas ainda não aparecem "ao vivo" em nenhuma aula
  real até que blocos desses tipos sejam inseridos.

## Pendências conhecidas para quem continuar

- Ver "Recomendação para a próxima fase" no relatório acima.
- Documentos de especificação completa (pedagógica/visual/técnica) citados
  no prompt original não estavam no pacote desta fase — se aparecerem numa
  próxima conversa, vale conferir contra o que foi implementado aqui.
