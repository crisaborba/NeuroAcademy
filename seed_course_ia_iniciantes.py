"""Seed for the NeuroAcademy flagship course: "IA para Iniciantes".

Source of truth: Curso_1_neuro.txt (pedagogical specification uploaded by
the product owner). This module is intentionally separate from seed.py
(which only creates demo/placeholder catalog data) so that real, produced
course content has its own clearly-named home and can be re-run safely.

STATUS: Module 1 (4 lessons) is fully produced and wired end-to-end,
including interactive questions that gate lesson completion. Modules 2-6,
the final project and the final assessment from the specification are NOT
yet implemented -- see the audit report for what remains. This function is
idempotent: it checks for the course by slug and does nothing if it
already exists, so re-running app startup never duplicates data.
"""

from db import get_db

COURSE_SLUG = "ia-para-iniciantes"


def seed_course_ia_iniciantes(app):
    with app.app_context():
        db = get_db()
        existing = db.execute("SELECT id FROM course WHERE slug = ?", (COURSE_SLUG,)).fetchone()
        if existing:
            return  # already seeded -- idempotent, never duplicates

        course_id = db.execute(
            "INSERT INTO course (title, slug, tag, tag_color, category, description, "
            "long_description, instructor, lessons_count, hours_label, level, "
            "students_count, rating, price, free, img, is_marketplace, featured, content_complete) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,1,0)",
            (
                "IA para Iniciantes",
                COURSE_SLUG,
                "INICIANTE",
                "#4D7EFF",
                "Fundamentos",
                "Seu primeiro passo no mundo da Inteligência Artificial. Um curso 100% "
                "textual e interativo para quem não tem nenhum conhecimento prévio sobre IA.",
                "O curso IA para Iniciantes e a porta de entrada da NeuroAcademy para pessoas "
                "que desejam compreender o universo da Inteligencia Artificial, mas ainda nao "
                "possuem conhecimento previo sobre o assunto. Ao longo da jornada, o aluno vai "
                "conhecer o que e IA, como ela surgiu e evoluiu, como funciona em nivel "
                "conceitual, quais ferramentas existem, qual o impacto da IA na sociedade e no "
                "mercado de trabalho, e tera seus primeiros contatos praticos com ferramentas "
                "de Inteligencia Artificial.",
                "NeuroAcademy",
                0,
                "4h",
                "Iniciante",
                0,
                0,
                "R$ 0",
                1,
                "photo-1677442135703-1787eea5ce01",
            ),
        ).lastrowid

        lesson_count = 0
        for module_order, module_def in enumerate(MODULE_1["modules"]):
            module_id = db.execute(
                "INSERT INTO module (course_id, title, ord) VALUES (?,?,?)",
                (course_id, module_def["title"], module_order),
            ).lastrowid
            for lesson_order, lesson_def in enumerate(module_def["lessons"]):
                lesson_id = db.execute(
                    "INSERT INTO lesson (module_id, course_id, title, duration, ord, free, "
                    "content_type, content, pass_threshold_pct) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        module_id, course_id, lesson_def["title"], lesson_def["duration"],
                        lesson_order, 1 if lesson_order == 0 and module_order == 0 else 0,
                        "text", lesson_def["content"], lesson_def.get("pass_threshold_pct", 0),
                    ),
                ).lastrowid
                lesson_count += 1

                q_order = 0
                for q in lesson_def.get("questions", []):
                    question_id = db.execute(
                        "INSERT INTO lesson_question (lesson_id, kind, prompt, ord) VALUES (?,?,?,?)",
                        (lesson_id, q["kind"], q["prompt"], q_order),
                    ).lastrowid
                    q_order += 1
                    for opt_order, opt in enumerate(q["options"]):
                        db.execute(
                            "INSERT INTO lesson_question_option "
                            "(question_id, label, is_correct, feedback, ord) VALUES (?,?,?,?,?)",
                            (question_id, opt["label"], 1 if opt.get("correct") else 0,
                             opt.get("feedback", ""), opt_order),
                        )

        db.execute("UPDATE course SET lessons_count = ? WHERE id = ?", (lesson_count, course_id))
        db.commit()


MODULE_1 = {
    "modules": [
        {
            "title": "Modulo 1 - O que e Inteligencia Artificial?",
            "lessons": [
                {
                    "title": "Bem-vindo a Inteligencia Artificial",
                    "duration": "12 min",
                    "pass_threshold_pct": 0,
                    "content": """## Objetivo desta aula

Ao final desta aula, voce vai entender o que este curso pode te dar, vai perceber que **nao precisa de nenhum conhecimento tecnico** para comecar, e vai descobrir que a Inteligencia Artificial provavelmente ja faz parte do seu dia -- mesmo que voce nunca tenha parado para notar.

## Seja bem-vindo

Voce esta prestes a dar o primeiro passo em uma jornada de aprendizado sobre um dos temas mais importantes do nosso tempo: a Inteligencia Artificial.

Antes de qualquer coisa, uma tranquilidade: **voce nao precisa saber tudo sobre Inteligencia Artificial para comecar. Precisa apenas estar disposto a aprender.**

Este curso nao vai transformar voce em programador, cientista de dados ou especialista em IA. O objetivo e bem mais simples e, ao mesmo tempo, poderoso: dar a voce uma **alfabetizacao inicial em IA** -- uma base solida para compreender o que esta acontecendo no mundo, reconhecer os principais conceitos, identificar aplicacoes de IA no seu cotidiano e usar ferramentas de forma mais consciente.

## A IA ja esta mais perto do que voce imagina

Um erro comum e pensar que Inteligencia Artificial e sinonimo de robos futuristas ou, mais recentemente, apenas de ferramentas como o ChatGPT. Na pratica, muitas pessoas utilizam sistemas baseados em IA diariamente, sem perceber.

Alguns exemplos comuns:

- Recomendacoes de videos e musicas em aplicativos de streaming
- Aplicativos de mapas que sugerem a melhor rota
- Filtros de spam que limpam sua caixa de e-mail
- Reconhecimento facial para desbloquear o celular
- Traducao automatica de textos e paginas
- Assistentes virtuais que respondem perguntas por voz
- Ferramentas que geram textos, imagens ou videos a partir de uma descricao

## Um dia comum, cheio de IA

Imagine uma pessoa comum, em um dia comum:

Ela acorda e o aplicativo de musica ja sugere uma playlist. No caminho para o trabalho, usa um aplicativo de mapas que calcula a rota mais rapida considerando o transito em tempo real. Durante o dia, um e-mail suspeito e automaticamente filtrado como spam. Na hora do almoco, assiste a um video recomendado por uma plataforma de streaming. A tarde, usa uma ferramenta de IA para gerar uma imagem para uma apresentacao. A noite, tira uma duvida rapida conversando com um assistente de IA.

**Quantas dessas situacoes voce imagina que podem envolver Inteligencia Artificial?**

Se voce pensou "quase todas", acertou. Todas essas tecnologias, hoje, costumam utilizar algum tipo de Inteligencia Artificial por tras.

## Reflexao

> Antes deste curso, onde voce imaginava que a Inteligencia Artificial estava presente?

Pense na sua resposta antes de continuar. Nao existe resposta certa ou errada aqui -- o objetivo e simplesmente comecar a observar o quanto a IA ja esta espalhada pelo seu dia a dia.""",
                    "questions": [
                        {
                            "kind": "interaction",
                            "prompt": "Antes deste curso, onde voce imaginava que a Inteligencia Artificial estava presente?",
                            "options": [
                                {"label": "Apenas em robos", "feedback": "E uma ideia comum! Ao longo do curso voce vai ver que a IA esta em muito mais lugares do que imaginamos."},
                                {"label": "Apenas em ferramentas como ChatGPT", "feedback": "Faz sentido pensar assim, ja que essas ferramentas ficaram muito conhecidas. Mas a IA vai muito alem delas."},
                                {"label": "Em diversas tecnologias do cotidiano", "feedback": "Exatamente essa e a percepcao que este curso quer reforcar e aprofundar."},
                                {"label": "Eu nao sabia onde ela estava presente", "feedback": "Sem problema -- e exatamente para isso que este curso existe."},
                            ],
                        },
                        {
                            "kind": "activity",
                            "prompt": "Atividade - Encontre a IA: uma calculadora realiza a operacao 2 + 2. Isso provavelmente envolve Inteligencia Artificial?",
                            "options": [
                                {"label": "Provavelmente utiliza IA", "feedback": "Nao e o mais provavel: uma calculadora comum segue uma regra matematica fixa, sem aprender padroes a partir de dados."},
                                {"label": "Provavelmente nao utiliza IA", "correct": True, "feedback": "Isso mesmo. Operacoes matematicas fixas seguem regras diretas -- nao e esse o tipo de tarefa que caracteriza a IA."},
                                {"label": "Nao e possivel determinar", "feedback": "Neste caso da para determinar: uma soma simples nao exige nenhuma das capacidades tipicas da IA."},
                            ],
                        },
                        {
                            "kind": "verification",
                            "prompt": "Qual e o principal objetivo deste curso?",
                            "options": [
                                {"label": "Transformar o aluno em programador especialista em IA", "feedback": "Esse nao e o objetivo -- o curso nao exige nem ensina programacao."},
                                {"label": "Construir uma compreensao basica sobre Inteligencia Artificial e preparar o aluno para continuar aprendendo", "correct": True, "feedback": "Exatamente esse e o objetivo do curso."},
                                {"label": "Ensinar a criar sistemas de Inteligencia Artificial do zero", "feedback": "Esse nao e o foco deste curso introdutorio."},
                                {"label": "Substituir a necessidade de aprender qualquer outra habilidade", "feedback": "Esse nao e o objetivo -- a IA e mais uma habilidade complementar."},
                            ],
                        },
                    ],
                },
                {
                    "title": "O que e Inteligencia Artificial?",
                    "duration": "16 min",
                    "pass_threshold_pct": 70,
                    "content": """## Objetivo desta aula

Voce vai compreender o conceito geral de Inteligencia Artificial e ser capaz de explica-lo com suas proprias palavras.

## Nao existe uma unica definicao

Nao existe uma definicao universal e fechada de Inteligencia Artificial -- mesmo entre especialistas, o termo e usado de formas um pouco diferentes. Mas, em termos simples, podemos dizer:

> **Inteligencia Artificial e um campo da tecnologia e da computacao dedicado a criacao de sistemas capazes de realizar tarefas que normalmente associamos a capacidades inteligentes.**

Essas capacidades podem incluir:

- Reconhecer padroes
- Classificar informacoes
- Fazer previsoes
- Recomendar conteudos
- Compreender linguagem
- Gerar conteudos
- Auxiliar na tomada de decisoes

## IA nao e uma unica ferramenta

Um ponto importante: **Inteligencia Artificial nao e uma coisa so.** E um campo inteiro, com muitas aplicacoes diferentes.

O ChatGPT e uma aplicacao de IA. Um sistema de recomendacao de filmes e outra aplicacao. Um sistema que reconhece objetos em uma fotografia e outra ainda. Todas essas aplicacoes, tao diferentes entre si, fazem parte do mesmo grande campo: a Inteligencia Artificial.

## Um conceito importante: IA nao e igual a inteligencia humana

> **Inteligencia Artificial nao e igual a inteligencia humana.**

Um sistema pode realizar uma tarefa extremamente bem -- como recomendar um filme perfeito para o seu gosto, ou reconhecer seu rosto em decimos de segundo -- sem possuir consciencia, emocoes ou qualquer compreensao humana do mundo. Ele esta processando padroes, nao "pensando" como uma pessoa pensa.

## Exemplos para fixar

- Um sistema recomenda filmes com base no comportamento de outros usuarios parecidos com voce.
- Outro sistema gera uma imagem a partir de uma descricao em texto.
- Outro identifica objetos especificos dentro de uma fotografia.

Sao tres aplicacoes completamente diferentes -- e todas sao, ao mesmo tempo, Inteligencia Artificial.

## Mito ou realidade?

Antes de seguir, teste sua compreensao com as afirmacoes abaixo -- pense se cada uma e verdadeira ou falsa antes de continuar lendo:

1. "Toda IA e um robo." -- **Falso.** A maior parte da IA que usamos no dia a dia nao tem corpo fisico nenhum; ela roda dentro de aplicativos e sistemas.
2. "IA pode ser utilizada para fazer recomendacoes." -- **Verdadeiro.**
3. "Toda IA possui consciencia." -- **Falso.** Nenhum sistema de IA atual possui consciencia no sentido humano.
4. "IA pode ser utilizada para gerar conteudo." -- **Verdadeiro.**

## Atividade - Explique com suas palavras

Antes de seguir para a verificacao, tente responder mentalmente:

> Explique o que e Inteligencia Artificial em ate tres frases, como se estivesse explicando para alguem que nunca ouviu falar no assunto.

Nao existe uma resposta perfeita -- o exercicio serve para voce notar se realmente conseguiu internalizar o conceito. Uma boa explicacao de referencia seria: *"Inteligencia Artificial e a area da tecnologia que cria sistemas capazes de realizar tarefas como reconhecer padroes, entender linguagem ou gerar conteudo -- sem que isso signifique que esses sistemas pensam como um ser humano."*""",
                    "questions": [
                        {
                            "kind": "interaction",
                            "prompt": "\"Toda IA e um robo.\" Essa afirmacao e verdadeira ou falsa?",
                            "options": [
                                {"label": "Verdadeira", "feedback": "Na verdade e falsa: a maior parte da IA que usamos roda dentro de aplicativos, sem nenhum corpo fisico."},
                                {"label": "Falsa", "correct": True, "feedback": "Isso mesmo -- a maioria dos sistemas de IA nao tem forma fisica nenhuma."},
                            ],
                        },
                        {
                            "kind": "verification",
                            "prompt": "Qual alternativa melhor define Inteligencia Artificial?",
                            "options": [
                                {"label": "Um unico programa que pensa exatamente como um ser humano", "feedback": "IA nao significa pensar como um humano -- sistemas de IA nao tem consciencia."},
                                {"label": "Um campo amplo que envolve sistemas capazes de realizar tarefas associadas a inteligencia", "correct": True, "feedback": "Correto -- essa e a definicao usada ao longo do curso."},
                                {"label": "Um tipo especifico de robo", "feedback": "IA nao se resume a robos -- a maioria das aplicacoes de IA nao tem corpo fisico."},
                                {"label": "Uma ferramenta utilizada exclusivamente para gerar textos", "feedback": "Gerar texto e apenas uma entre muitas aplicacoes possiveis de IA."},
                            ],
                        },
                    ],
                },
                {
                    "title": "A IA esta em todo lugar",
                    "duration": "20 min",
                    "pass_threshold_pct": 70,
                    "content": """## Objetivo desta aula

Reconhecer aplicacoes de Inteligencia Artificial em diferentes areas da vida e da sociedade.

## IA em diferentes contextos

A Inteligencia Artificial nao esta restrita a um unico setor. Ela aparece -- com formatos e finalidades diferentes -- em praticamente todas as areas da sociedade.

**Entretenimento** -- Recomendacao de filmes, musicas e videos com base no seu historico e no comportamento de usuarios parecidos com voce.

**Transporte** -- Calculo de rotas, previsao de transito em tempo real e sistemas de apoio a conducao.

**Comunicacao** -- Traducao automatica entre idiomas, filtros de spam e ferramentas que ajudam a escrever e revisar textos.

**Financas** -- Deteccao de transacoes suspeitas e analise de padroes de consumo para identificar fraudes.

**Saude** -- Apoio na analise de exames e imagens medicas, alem de suporte a pesquisas cientificas.

**Educacao** -- Personalizacao do ritmo de aprendizagem e ferramentas de apoio ao estudo.

**Trabalho** -- Automacao de tarefas repetitivas, analise de documentos e geracao de conteudo.

## Um dia inteiro acompanhado por IA

Se voce juntar os exemplos acima, percebe que uma pessoa comum pode passar o dia inteiro interagindo, direta ou indiretamente, com sistemas de Inteligencia Artificial -- do momento em que acorda e ve recomendacoes no celular, ate a rota do trajeto de volta para casa.

## Atividade - Onde esta a IA?

Observe as situacoes abaixo e pense, para cada uma, se ela representa uma aplicacao de IA, provavelmente nao representa, ou se nao ha informacao suficiente para decidir:

1. Uma plataforma recomenda uma musica com base no que voce ja ouviu.
2. Uma calculadora realiza uma soma simples.
3. Um aplicativo reconhece um rosto para desbloquear o aparelho.
4. Um sistema detecta uma mensagem como spam.
5. Um programa executa sempre a mesma formula fixa, sem se adaptar.

## Pense no seu dia

> Cite mentalmente tres situacoes do seu cotidiano em que voce acredita que a IA pode estar presente.

Depois de pensar na sua resposta, veja alguns exemplos possiveis: sugestoes de compra em lojas online, previsao do tempo personalizada por localizacao, correcao automatica de texto no teclado do celular, entre muitos outros.""",
                    "questions": [
                        {
                            "kind": "activity",
                            "prompt": "Um programa executa sempre a mesma formula fixa, sem se adaptar aos dados. Isso e uma aplicacao tipica de IA?",
                            "options": [
                                {"label": "Ha uma aplicacao de IA", "feedback": "Uma formula fixa, que nunca se adapta, e justamente o oposto do que caracteriza a maioria dos sistemas de IA."},
                                {"label": "Nao necessariamente ha IA", "correct": True, "feedback": "Correto. Regras fixas que nao se adaptam a dados normalmente nao sao consideradas Inteligencia Artificial."},
                                {"label": "Nao ha informacao suficiente", "feedback": "Neste caso ha informacao suficiente: uma formula sempre fixa nao exige as capacidades tipicas de IA."},
                            ],
                        },
                        {
                            "kind": "verification",
                            "prompt": "Qual situacao representa claramente uma aplicacao de IA?",
                            "options": [
                                {"label": "Um relogio digital mostrar 10:30", "feedback": "Mostrar a hora e uma funcao fixa, sem analise de padroes."},
                                {"label": "Uma plataforma analisar seu historico e recomendar conteudo", "correct": True, "feedback": "Correto -- analisar padroes de comportamento para recomendar conteudo e uma aplicacao classica de IA."},
                                {"label": "Uma calculadora realizar uma soma", "feedback": "Uma soma segue uma regra matematica fixa, sem aprendizado de padroes."},
                                {"label": "Um interruptor ligar uma lampada", "feedback": "Essa e uma acao mecanica simples, sem nenhuma analise de dados envolvida."},
                            ],
                        },
                    ],
                },
                {
                    "title": "IA, Machine Learning e Deep Learning",
                    "duration": "22 min",
                    "pass_threshold_pct": 80,
                    "content": """## Objetivo desta aula

Compreender a relacao entre tres termos que aparecem o tempo todo quando o assunto e IA: Inteligencia Artificial, Machine Learning e Deep Learning.

## Tres circulos, um dentro do outro

Uma forma simples de entender a relacao entre esses tres termos e imaginar tres circulos, um dentro do outro:

**Inteligencia Artificial** (o circulo maior, mais externo) contem **Machine Learning**, que por sua vez contem **Deep Learning** (o circulo menor, mais interno).

## O que e cada um

**Inteligencia Artificial** e o campo mais amplo -- o "guarda-chuva" que engloba qualquer sistema capaz de realizar tarefas associadas a inteligencia.

**Machine Learning** (Aprendizado de Maquina) e uma abordagem dentro da IA: sao sistemas que **aprendem padroes a partir de dados e exemplos**, em vez de depender exclusivamente de regras explicitamente programadas para cada situacao possivel.

**Deep Learning** (Aprendizado Profundo) e, por sua vez, uma abordagem especifica de Machine Learning, baseada em **redes neurais profundas** -- estruturas inspiradas, de forma bem simplificada, no funcionamento de neuronios biologicos.

## Uma analogia

Pense em categorias e subcategorias, como em uma classificacao de seres vivos:

A Inteligencia Artificial e o grande guarda-chuva -- a categoria mais ampla. Machine Learning esta dentro desse guarda-chuva: e uma das formas de se fazer IA. Deep Learning, por sua vez, e uma area especifica dentro de Machine Learning -- nem todo Machine Learning usa Deep Learning, mas todo Deep Learning e Machine Learning.

## Organizando o que voce aprendeu

Antes de seguir, tente organizar mentalmente do conceito mais amplo para o mais especifico: Inteligencia Artificial, Machine Learning, Deep Learning.

A ordem correta e: **Inteligencia Artificial -> Machine Learning -> Deep Learning.** Deep Learning esta dentro de Machine Learning, que esta dentro do campo mais amplo da Inteligencia Artificial.

## Verificando o que ficou

As perguntas a seguir vao te ajudar a confirmar se a relacao entre os tres conceitos ficou clara.""",
                    "questions": [
                        {
                            "kind": "interaction",
                            "prompt": "Todo Machine Learning faz parte da Inteligencia Artificial?",
                            "options": [
                                {"label": "Sim", "correct": True, "feedback": "Correto -- Machine Learning e uma das abordagens dentro do campo da IA."},
                                {"label": "Nao", "feedback": "Na verdade sim: Machine Learning e uma abordagem que existe dentro do campo da Inteligencia Artificial."},
                            ],
                        },
                        {
                            "kind": "interaction",
                            "prompt": "Toda Inteligencia Artificial e Deep Learning?",
                            "options": [
                                {"label": "Sim", "feedback": "Nao -- Deep Learning e apenas uma abordagem especifica, bem mais restrita que o campo geral da IA."},
                                {"label": "Nao", "correct": True, "feedback": "Correto -- a IA e um campo muito mais amplo, e o Deep Learning e apenas uma parte dela."},
                            ],
                        },
                        {
                            "kind": "verification",
                            "prompt": "Qual das afirmacoes abaixo esta correta?",
                            "options": [
                                {"label": "Deep Learning faz parte de Machine Learning, que faz parte da Inteligencia Artificial", "correct": True, "feedback": "Exatamente essa e a relacao entre os tres conceitos."},
                                {"label": "Machine Learning faz parte de Deep Learning", "feedback": "E o contrario: Deep Learning e que faz parte de Machine Learning."},
                                {"label": "Inteligencia Artificial faz parte de Machine Learning", "feedback": "E o contrario: a Inteligencia Artificial e o campo mais amplo dos tres."},
                                {"label": "Os tres termos significam exatamente a mesma coisa", "feedback": "Nao -- cada termo tem um escopo diferente, do mais amplo (IA) ao mais especifico (Deep Learning)."},
                            ],
                        },
                    ],
                },
            ],
        },
    ],
}
