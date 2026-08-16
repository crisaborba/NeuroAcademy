import random
import secrets

from werkzeug.security import generate_password_hash

from db import get_db
from utils import slugify


COURSES = [
    dict(tag="FUNDAMENTOS", tag_color="#4D7EFF", category="Fundamentos",
         title="IA do Zero: Guia Completo para Iniciantes",
         description="Entenda o que é inteligência artificial, como funciona e como aplicar no seu dia a dia e carreira.",
         lessons_count=24, hours_label="6h", level="Iniciante", students_count=1847, rating=4.9,
         img="photo-1677442135703-1787eea5ce01", free=1),
    dict(tag="FERRAMENTAS", tag_color="#9B59FF", category="Ferramentas",
         title="ChatGPT & Copilots: Produtividade com IA",
         description="Domine as principais ferramentas de IA generativa e multiplique sua produtividade.",
         lessons_count=18, hours_label="4h 30min", level="Iniciante", students_count=2103, rating=4.8,
         img="photo-1518770660439-4636190af475", free=1),
    dict(tag="CARREIRA", tag_color="#00D4FF", category="Carreira",
         title="IA para o Mercado de Trabalho",
         description="Construa um portfólio com projetos de IA e se destaque nas seleções de estágio e emprego.",
         lessons_count=32, hours_label="9h", level="Intermediário", students_count=964, rating=4.9,
         img="photo-1461749280684-dccba630e2f6", free=0, price="R$ 67"),
    dict(tag="PROMPT", tag_color="#FFD166", category="Prompt",
         title="Engenharia de Prompts: Do Básico ao Avançado",
         description="Aprenda a extrair resultados profissionais de qualquer ferramenta de IA com a técnica certa.",
         lessons_count=21, hours_label="5h", level="Intermediário", students_count=1250, rating=4.7,
         img="photo-1518770660439-4636190af475", free=0, price="R$ 57"),
    dict(tag="DADOS", tag_color="#FF6B6B", category="Dados",
         title="Análise de Dados com IA",
         description="Use IA para analisar, visualizar e interpretar dados sem precisar programar.",
         lessons_count=28, hours_label="7h", level="Intermediário", students_count=634, rating=4.8,
         img="photo-1551288049-bebda4e38f71", free=0, price="R$ 77"),
    dict(tag="AUTOMAÇÃO", tag_color="#22c55e", category="Automação",
         title="Automatize sua Vida com IA",
         description="Crie fluxos de automação com Make, Zapier e IA para economizar horas por semana.",
         lessons_count=16, hours_label="4h", level="Iniciante", students_count=879, rating=4.6,
         img="photo-1518770660439-4636190af475", free=0, price="R$ 47"),
    dict(tag="FUNDAMENTOS", tag_color="#4D7EFF", category="Fundamentos",
         title="Ética e Segurança em IA",
         description="Entenda os riscos, vieses e responsabilidades no uso de inteligência artificial.",
         lessons_count=12, hours_label="3h", level="Iniciante", students_count=421, rating=4.9,
         img="photo-1677442135703-1787eea5ce01", free=1),
    dict(tag="CARREIRA", tag_color="#00D4FF", category="Carreira",
         title="Criação de Conteúdo com IA",
         description="Produza textos, imagens e vídeos com qualidade profissional usando IA generativa.",
         lessons_count=20, hours_label="5h 30min", level="Iniciante", students_count=1567, rating=4.7,
         img="photo-1461749280684-dccba630e2f6", free=0, price="R$ 57"),
]

MARKETPLACE_COURSES = [
    dict(tag="BESTSELLER", tag_color="#FFD166", category="Marketplace", instructor="Prof. Carlos Mendes",
         title="Python para IA: Do Básico ao Machine Learning",
         description="Aprenda Python aplicado à inteligência artificial, do zero ao seu primeiro modelo de Machine Learning.",
         price="R$ 97", original_price="R$ 197", rating=4.9, students_count=3241,
         img="photo-1461749280684-dccba630e2f6", featured=1),
    dict(tag="NOVO", tag_color="#22c55e", category="Marketplace", instructor="Prof. Ana Rodrigues",
         title="LangChain e Agentes de IA: Construindo Aplicações Inteligentes",
         description="Construa aplicações inteligentes com agentes autônomos usando LangChain.",
         price="R$ 147", original_price="R$ 297", rating=4.8, students_count=892,
         img="photo-1677442135703-1787eea5ce01", featured=1),
    dict(tag="TRENDING", tag_color="#FF6B6B", category="Marketplace", instructor="Prof. Lucas Torres",
         title="Fine-tuning de LLMs: Personalize seus Próprios Modelos",
         description="Aprenda a especializar grandes modelos de linguagem para seus próprios casos de uso.",
         price="R$ 197", original_price="R$ 397", rating=4.9, students_count=548,
         img="photo-1677442135703-1787eea5ce01", featured=1),
    dict(tag="POPULAR", tag_color="#9B59FF", category="Marketplace", instructor="Prof. Marina Silva",
         title="Visão Computacional com IA",
         description="Domine técnicas de visão computacional aplicadas a projetos reais.",
         price="R$ 127", original_price="R$ 247", rating=4.7, students_count=1204,
         img="photo-1518770660439-4636190af475", featured=0),
    dict(tag="NOVO", tag_color="#22c55e", category="Marketplace", instructor="Prof. Roberto Lima",
         title="IA para Negócios: Estratégia e Implementação",
         description="Estratégias práticas para implementar IA em empresas de qualquer tamanho.",
         price="R$ 167", original_price="R$ 327", rating=4.8, students_count=673,
         img="photo-1551288049-bebda4e38f71", featured=0),
    dict(tag="BESTSELLER", tag_color="#FFD166", category="Marketplace", instructor="Prof. Fernanda Costa",
         title="APIs de IA: Integrando os Principais Modelos",
         description="Aprenda a integrar as principais APIs de IA generativa em seus próprios projetos.",
         price="R$ 87", original_price="R$ 167", rating=4.9, students_count=2156,
         img="photo-1461749280684-dccba630e2f6", featured=0),
]

MODULES_TEMPLATE = [
    ("Módulo 1 — Introdução à IA", [
        ("O que é Inteligência Artificial?", "12:30", 1),
        ("Histórico e evolução da IA", "08:45", 1),
        ("IA no cotidiano: exemplos práticos", "15:20", 1),
        ("Quiz: Fundamentos da IA", "5 min", 1),
    ]),
    ("Módulo 2 — Como a IA Aprende", [
        ("Machine Learning: conceitos básicos", "18:40", 0),
        ("Redes neurais explicadas de forma simples", "22:15", 0),
        ("Modelos de linguagem (LLMs)", "16:50", 0),
    ]),
    ("Módulo 3 — Ferramentas Essenciais", [
        ("ChatGPT: configurando e explorando", "14:00", 0),
        ("Google Gemini na prática", "11:30", 0),
        ("Comparativo: qual IA usar em cada situação?", "19:20", 0),
        ("Projeto prático: resolvendo um problema real", "28:00", 0),
    ]),
    ("Módulo 4 — IA para Estudo e Carreira", [
        ("Usando IA para estudar melhor", "16:10", 0),
        ("IA no mercado de trabalho de 2025", "13:45", 0),
        ("Construindo seu perfil com IA", "20:30", 0),
        ("Projeto final e avaliação", "35:00", 0),
    ]),
]

BLOG_POSTS = [
    dict(tag="IA Generativa", title="Como a IA generativa vai mudar o mercado de trabalho nos próximos anos",
         excerpt="Análise completa das principais mudanças que os modelos mais recentes vão trazer para profissionais de todas as áreas.",
         read_time="8 min", date_label="25 Jun 2026", img="photo-1677442135703-1787eea5ce01", featured=1),
    dict(tag="Carreira", title="10 habilidades de IA que todo estudante deve desenvolver",
         excerpt="O mercado de trabalho está transformando-se rapidamente. Veja quais competências em IA vão diferenciar seu currículo.",
         read_time="6 min", date_label="22 Jun 2026", img="photo-1461749280684-dccba630e2f6", featured=0),
    dict(tag="Ferramentas", title="Guia completo: melhores ferramentas de IA para estudantes",
         excerpt="Comparamos mais de 30 ferramentas de IA e selecionamos as melhores para cada tipo de necessidade acadêmica.",
         read_time="12 min", date_label="20 Jun 2026", img="photo-1518770660439-4636190af475", featured=0),
    dict(tag="Tutoriais", title="Como usar IA para escrever trabalhos acadêmicos sem plagiar",
         excerpt="Aprenda a usar IA como ferramenta de apoio à escrita de forma ética, eficiente e que melhora genuinamente seu trabalho.",
         read_time="10 min", date_label="18 Jun 2026", img="photo-1551288049-bebda4e38f71", featured=0),
    dict(tag="Ética", title="IA e direitos autorais: o que todo criador de conteúdo precisa saber",
         excerpt="As questões legais em torno da IA generativa e criação de conteúdo estão evoluindo rapidamente. Entenda seus direitos.",
         read_time="9 min", date_label="15 Jun 2026", img="photo-1551288049-bebda4e38f71", featured=0),
    dict(tag="Machine Learning", title="Redes neurais explicadas para quem nunca programou",
         excerpt="Descomplicamos um dos conceitos mais intimidadores da IA usando analogias simples e exemplos do dia a dia.",
         read_time="7 min", date_label="12 Jun 2026", img="photo-1677442135703-1787eea5ce01", featured=0),
]

NEWS = [
    dict(category="OpenAI", title="Novo modelo de linguagem chega com capacidades multimodais inéditas",
         excerpt="O novo modelo apresenta raciocínio aprimorado e consegue processar vídeos em tempo real, segundo a empresa.",
         time_label="há 2 horas", source="TechCrunch", trending=1, img="photo-1677442135703-1787eea5ce01"),
    dict(category="Brasil", title="Ministério da Educação anuncia plano de IA para escolas públicas brasileiras",
         excerpt="Iniciativa prevê capacitar 200 mil professores em inteligência artificial até o final de 2027.",
         time_label="há 4 horas", source="G1", trending=1, img="photo-1461749280684-dccba630e2f6"),
    dict(category="Google", title="Novo modelo supera humanos em novos benchmarks de raciocínio",
         excerpt="Os resultados colocam o modelo entre os líderes em tarefas de matemática e programação complexa.",
         time_label="há 6 horas", source="The Verge", trending=0, img="photo-1518770660439-4636190af475"),
    dict(category="Mercado", title="Mercado de IA deve movimentar R$ 85 bilhões no Brasil até 2028",
         excerpt="Estudo aponta aceleração do setor e crescente demanda por profissionais qualificados em inteligência artificial.",
         time_label="há 8 horas", source="Folha de S.Paulo", trending=0, img="photo-1518770660439-4636190af475"),
    dict(category="Pesquisa", title="Pesquisadores criam IA capaz de prever doenças com anos de antecedência",
         excerpt="Modelo treinado com dados de milhões de pacientes apresenta alta acurácia em diagnóstico precoce.",
         time_label="há 12 horas", source="Nature", trending=0, img="photo-1551288049-bebda4e38f71"),
    dict(category="Regulação", title="União Europeia publica guia definitivo para conformidade com o AI Act",
         excerpt="Documento detalha obrigações de empresas que desenvolvem ou usam IA de alto risco.",
         time_label="há 1 dia", source="Reuters", trending=0, img="photo-1677442135703-1787eea5ce01"),
    dict(category="OpenAI", title="Assistente de IA atinge centenas de milhões de usuários ativos",
         excerpt="Números foram divulgados em apresentação para investidores, confirmando crescimento exponencial da plataforma.",
         time_label="há 1 dia", source="Bloomberg", trending=0, img="photo-1461749280684-dccba630e2f6"),
    dict(category="Brasil", title="Startup brasileira de IA educacional recebe grande investimento",
         excerpt="A rodada foi liderada por investidores internacionais e consolida o Brasil como hub de IA educacional.",
         time_label="há 2 dias", source="Startups.com.br", trending=0, img="photo-1461749280684-dccba630e2f6"),
]

TOOLS = [
    dict(name="ChatGPT", category="Chatbots", desc="Assistente de IA da OpenAI para conversação, escrita, análise e resolução de problemas do dia a dia.",
         rating=4.9, users_label="300M+", free=1, color="#10a37f", img="photo-1677442135703-1787eea5ce01", tags="Escrita,Código,Análise"),
    dict(name="Claude", category="Chatbots", desc="Assistente de IA da Anthropic com raciocínio avançado e foco em segurança. Forte em análise de textos longos.",
         rating=4.8, users_label="10M+", free=1, color="#d97706", img="photo-1518770660439-4636190af475", tags="Análise,Escrita,Código"),
    dict(name="Gemini", category="Chatbots", desc="Assistente de IA do Google integrado ao ecossistema Workspace, com acesso a busca em tempo real.",
         rating=4.6, users_label="100M+", free=1, color="#4285f4", img="photo-1461749280684-dccba630e2f6", tags="Pesquisa,Imagem,Código"),
    dict(name="Midjourney", category="Imagem", desc="Geração de imagens artísticas com qualidade profissional a partir de descrições em texto. Popular entre designers.",
         rating=4.9, users_label="20M+", free=0, color="#7c3aed", img="photo-1518770660439-4636190af475", tags="Arte,Design,Criação"),
    dict(name="Adobe Firefly", category="Imagem", desc="Geração e edição de imagens da Adobe, integrada ao Photoshop e Illustrator. Treinada para uso comercial seguro.",
         rating=4.6, users_label="50M+", free=0, color="#ff4d4f", img="photo-1551288049-bebda4e38f71", tags="Ilustração,Design"),
    dict(name="GitHub Copilot", category="Código", desc="Assistente de programação da GitHub/Microsoft integrado a VS Code e outras IDEs. Sugere e completa código em tempo real.",
         rating=4.8, users_label="5M+", free=0, color="#6366f1", img="photo-1461749280684-dccba630e2f6", tags="Programação,Produtividade"),
    dict(name="Perplexity AI", category="Pesquisa", desc="Motor de busca com IA que responde perguntas citando as fontes originais. Ótimo para pesquisa acadêmica.",
         rating=4.7, users_label="15M+", free=1, color="#06b6d4", img="photo-1551288049-bebda4e38f71", tags="Pesquisa,Citações"),
    dict(name="Notion AI", category="Produtividade", desc="IA integrada ao Notion para resumir, reescrever e gerar conteúdo diretamente dentro dos seus documentos.",
         rating=4.5, users_label="30M+", free=0, color="#374151", img="photo-1518770660439-4636190af475", tags="Documentos,Resumo"),
    dict(name="Runway", category="Vídeo", desc="Plataforma de IA para geração e edição de vídeo, incluindo remoção de fundo e efeitos sem habilidade técnica.",
         rating=4.6, users_label="2M+", free=0, color="#ec4899", img="photo-1677442135703-1787eea5ce01", tags="Vídeo,Edição"),
    dict(name="Grammarly", category="Escrita", desc="Assistente de escrita com IA que corrige gramática, ortografia e tom. Disponível como extensão de navegador.",
         rating=4.5, users_label="50M+", free=1, color="#16a34a", img="photo-1461749280684-dccba630e2f6", tags="Correção,Estilo"),
    dict(name="Suno AI", category="Produtividade", desc="Geração de músicas completas, com letra e instrumental, a partir de uma descrição em texto.",
         rating=4.4, users_label="5M+", free=1, color="#f59e0b", img="photo-1551288049-bebda4e38f71", tags="Música,Criação"),
    dict(name="Canva AI (Magic Studio)", category="Imagem", desc="Ferramentas de IA dentro do Canva para gerar e editar imagens, remover fundos e redimensionar designs.",
         rating=4.6, users_label="1M+", free=1, color="#8b5cf6", img="photo-1518770660439-4636190af475", tags="Design,Real-time"),
]

COMMUNITY_TOPICS_SEED = [
    dict(topic="Dúvidas", title="Como faço para que a IA responda sempre em um formato específico?",
         body="Estou tentando usar um assistente de IA para gerar relatórios, mas ele nunca mantém o formato que eu peço. Alguém tem uma dica de como estruturar o prompt?",
         likes=24, tags="prompt,ia,formatação", author_name="Lucas Ferreira"),
    dict(topic="Projetos", title="Criei um assistente de estudos com IA — deixa eu mostrar como ficou",
         body="Passei o fim de semana construindo um sistema que usa IA para criar flashcards automaticamente a partir dos meus resumos. O resultado ficou incrível e quero compartilhar o passo a passo.",
         likes=87, tags="projeto,estudos,ia", featured=1, author_name="Mariana Silva"),
    dict(topic="Carreira", title="Consegui meu primeiro estágio! A NeuroAcademy foi fundamental",
         body="Quero compartilhar com a comunidade que acabei de receber a proposta de estágio que tanto queria. O curso de IA para Carreira me ajudou a montar um portfólio que realmente impressionou o entrevistador.",
         likes=142, tags="carreira,estágio,portfólio", author_name="Rafael Oliveira"),
    dict(topic="Ferramentas", title="Comparação de ferramentas de imagem para estudantes com orçamento limitado",
         body="Testei duas plataformas durante um mês focando em casos de uso para estudantes (apresentações, trabalhos, projetos). Aqui está minha análise honesta.",
         likes=58, tags="ferramentas,imagem,comparação", author_name="Ana Pereira"),
    dict(topic="Desafios", title="Desafio da Semana: crie um prompt que gere um plano de estudos personalizado",
         body="Esta semana o desafio é criar o melhor prompt possível para gerar planos de estudo personalizados. Os 3 melhores receberão badges exclusivos e destaque na plataforma!",
         likes=95, tags="desafio,prompt,badge", pinned=1, author_name="NeuroAcademy"),
]

ROADMAPS = [
    dict(title="Trilha do Iniciante", color="#4D7EFF", duration_label="9h", courses_count=3,
         description="A jornada perfeita para quem está começando do zero em inteligência artificial.",
         steps=[("O que é IA?", "1h"), ("Principais ferramentas de IA", "2h"), ("Usando IA no dia a dia", "3h"),
                ("IA para estudar melhor", "2h"), ("Projeto prático final", "1h")]),
    dict(title="Trilha de Produtividade com IA", color="#9B59FF", duration_label="11h", courses_count=4,
         description="Aprenda a automatizar tarefas e multiplicar sua produtividade usando ferramentas de IA.",
         steps=[("Fundamentos de prompts eficientes", "2h"), ("Automatização com Make, Zapier e IA", "4h"),
                ("IA para escrita e comunicação", "3h"), ("Criação de fluxos inteligentes", "2h")]),
    dict(title="Trilha de Carreira em IA", color="#00D4FF", duration_label="19h", courses_count=6,
         description="Prepare-se para o mercado de trabalho transformado pela IA, do zero ao portfólio completo.",
         steps=[("IA no mercado de trabalho atual", "2h"), ("Habilidades mais valorizadas", "3h"),
                ("Construindo projetos para portfólio", "5h"), ("LinkedIn e marca pessoal com IA", "2h"),
                ("Preparação para entrevistas", "3h"), ("Projeto final: portfólio completo", "4h")]),
    dict(title="Trilha de Criação de Conteúdo com IA", color="#FFD166", duration_label="16h", courses_count=5,
         description="Domine a criação de textos, imagens e vídeos profissionais usando ferramentas de IA generativa.",
         steps=[("Prompt engineering para imagens", "3h"), ("Geradores de imagem na prática", "4h"),
                ("Criação de vídeos com IA", "3h"), ("Escrita e copywriting com IA", "4h"),
                ("Projeto: conteúdo para redes sociais", "2h")]),
]


def seed_all(app):
    with app.app_context():
        db = get_db()
        existing = db.execute("SELECT COUNT(*) c FROM user").fetchone()["c"]
        if existing:
            return

        demo_id = db.execute(
            "INSERT INTO user (name, username, email, password_hash, bio, plan, role, points, streak) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ("Gabriela Mendes", "gabrielam", "gabriela@neuroacademy.dev",
             generate_password_hash("neuro123"),
             "Estudante de Administração apaixonada por IA aplicada aos negócios.",
             "Pro", "aluno", 634, 7),
        ).lastrowid

        db.execute(
            "INSERT INTO user (name, username, email, password_hash, bio, plan, role, points) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("Equipe NeuroAcademy", "admin", "admin@neuroacademy.dev",
             generate_password_hash("admin123"), "Conta de administração da plataforma.",
             "Anual", "admin", 2000),
        )

        community_author_ids = {}
        for nm in ["Lucas Ferreira", "Mariana Silva", "Rafael Oliveira", "Ana Pereira", "Pedro Martins"]:
            uid = db.execute(
                "INSERT INTO user (name, username, email, password_hash, plan, role) VALUES (?,?,?,?,?,?)",
                (nm, slugify(nm).replace("-", ""), slugify(nm) + "@neuroacademy.dev",
                 generate_password_hash("neuro123"), "Gratuito", "aluno"),
            ).lastrowid
            community_author_ids[nm] = uid

        course_ids = []
        for c in COURSES:
            cid = db.execute(
                "INSERT INTO course (title, slug, tag, tag_color, category, description, instructor, "
                "lessons_count, hours_label, level, students_count, rating, price, free, img, is_marketplace) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                (c["title"], slugify(c["title"]), c["tag"], c["tag_color"], c["category"], c["description"],
                 "NeuroAcademy", c["lessons_count"], c["hours_label"], c["level"], c["students_count"],
                 c["rating"], c.get("price", "R$ 0"), c["free"], c["img"]),
            ).lastrowid
            course_ids.append(cid)

        for c in MARKETPLACE_COURSES:
            db.execute(
                "INSERT INTO course (title, slug, tag, tag_color, category, description, instructor, "
                "rating, students_count, price, original_price, free, img, is_marketplace, featured) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?,1,?)",
                (c["title"], slugify(c["title"]), c["tag"], c["tag_color"], c["category"], c["description"],
                 c["instructor"], c["rating"], c["students_count"], c["price"], c["original_price"],
                 c["img"], c["featured"]),
            )

        for cid in course_ids[:3]:
            order = 0
            for m_title, lessons in MODULES_TEMPLATE:
                mid = db.execute(
                    "INSERT INTO module (course_id, title, ord) VALUES (?,?,?)", (cid, m_title, order)
                ).lastrowid
                for i, (l_title, dur, free) in enumerate(lessons):
                    db.execute(
                        "INSERT INTO lesson (module_id, course_id, title, duration, ord, free, content) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (mid, cid, l_title, dur, i, free,
                         "Conteúdo da aula em vídeo. Assista com atenção e faça anotações."),
                    )
                order += 1

        # demo enrollments
        course1, course2, course4 = course_ids[0], course_ids[1], course_ids[3]
        db.execute("INSERT INTO enrollment (user_id, course_id, progress_pct) VALUES (?,?,28)", (demo_id, course1))
        first_lessons = db.execute(
            "SELECT id FROM lesson WHERE course_id = ? ORDER BY id LIMIT 2", (course1,)
        ).fetchall()
        for row in first_lessons:
            db.execute(
                "INSERT INTO lesson_progress (user_id, lesson_id, done) VALUES (?,?,1)",
                (demo_id, row["id"]),
            )

        db.execute("INSERT INTO enrollment (user_id, course_id, progress_pct) VALUES (?,?,100)", (demo_id, course2))
        db.execute(
            "INSERT INTO certificate (user_id, course_id, code) VALUES (?,?,?)",
            (demo_id, course2, secrets.token_hex(8).upper()),
        )
        db.execute("INSERT INTO enrollment (user_id, course_id, progress_pct) VALUES (?,?,14)", (demo_id, course4))

        for p in BLOG_POSTS:
            db.execute(
                "INSERT INTO blog_post (title, slug, tag, excerpt, author, img, read_time, date_label, featured) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (p["title"], slugify(p["title"]), p["tag"], p["excerpt"], "NeuroAcademy", p["img"],
                 p["read_time"], p["date_label"], p["featured"]),
            )

        for n in NEWS:
            db.execute(
                "INSERT INTO news_article (title, category, excerpt, source, time_label, trending, img) "
                "VALUES (?,?,?,?,?,?,?)",
                (n["title"], n["category"], n["excerpt"], n["source"], n["time_label"], n["trending"], n["img"]),
            )

        for t in TOOLS:
            db.execute(
                "INSERT INTO tool (name, category, desc, rating, users_label, free, color, img, tags) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (t["name"], t["category"], t["desc"], t["rating"], t["users_label"], t["free"],
                 t["color"], t["img"], t["tags"]),
            )

        for r in ROADMAPS:
            steps = r["steps"]
            rid = db.execute(
                "INSERT INTO roadmap (title, description, color, duration_label, courses_count) VALUES (?,?,?,?,?)",
                (r["title"], r["description"], r["color"], r["duration_label"], r["courses_count"]),
            ).lastrowid
            for i, (label, dur) in enumerate(steps):
                db.execute(
                    "INSERT INTO roadmap_step (roadmap_id, label, duration, ord) VALUES (?,?,?,?)",
                    (rid, label, dur, i),
                )

        admin_row = db.execute("SELECT id FROM user WHERE username = 'admin'").fetchone()
        admin_id = admin_row["id"] if admin_row else demo_id

        first_post_id = None
        for cp in COMMUNITY_TOPICS_SEED:
            author_id = community_author_ids.get(cp["author_name"], admin_id)
            pid = db.execute(
                "INSERT INTO community_post (user_id, topic, title, body, likes, tags, pinned, featured) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (author_id, cp["topic"], cp["title"], cp["body"], cp["likes"], cp["tags"],
                 cp.get("pinned", 0), cp.get("featured", 0)),
            ).lastrowid
            if first_post_id is None:
                first_post_id = pid

        if first_post_id:
            db.execute(
                "INSERT INTO community_comment (post_id, user_id, body, likes) VALUES (?,?,?,3)",
                (first_post_id, demo_id,
                 "Boa pergunta! Eu costumo dar um exemplo do formato exato que quero dentro do prompt, ajuda muito."),
            )

        db.commit()
