# NeuroAcademy

Plataforma educacional de Inteligência Artificial — clone funcional do design
original, sem qualquer marca, arquivo ou referência ao Figma, com backend
completo em **Python + Flask**.

## Stack

- **Backend:** Flask (rotas, sessão, autenticação própria)
- **Banco de dados:** SQLite via `sqlite3` (biblioteca padrão do Python — não
  requer instalação de driver externo)
- **Frontend:** HTML + Jinja2 + CSS puro + JavaScript vanilla (sem build step)

Não há dependência de Flask-SQLAlchemy nem Flask-Login: a camada de dados
(`db.py` + `models.py` + `repo.py`) e a autenticação (`auth.py`, baseada na
sessão nativa do Flask) foram implementadas à mão para manter o projeto leve
e com o mínimo de dependências externas.

## Como rodar

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Acesse http://127.0.0.1:5000

O banco (`neuroacademy.db`) é criado e populado automaticamente na primeira
execução (arquivo `seed.py`), com cursos, aulas, posts de blog, notícias,
ferramentas de IA, tópicos de comunidade e trilhas de aprendizado de exemplo.

### Conta de demonstração

- **E-mail:** gabriela@neuroacademy.dev
- **Senha:** neuro123

### Conta de administrador

- **E-mail:** admin@neuroacademy.dev
- **Senha:** admin123

## Funcionalidades implementadas

- Cadastro/login/logout com sessão e senha criptografada (Werkzeug)
- Catálogo de cursos com filtro por categoria, nível e busca
- Página de curso com módulos/aulas, matrícula e trilha de progresso
- Player de aula com marcação de conclusão, anotações e navegação entre aulas
- Emissão de certificado ao concluir 100% de um curso
- Blog e Notícias com filtros por tag/categoria
- Diretório de ferramentas de IA com busca e filtro
- Comunidade: postagens, curtidas, comentários e ranking de membros
- Roadmaps (trilhas) com progresso por etapa
- Perfil do usuário com cursos, certificados e estatísticas
- Configurações de conta, notificações e senha
- Marketplace de cursos pagos e área Premium com assinatura de planos
- Painel administrativo (apenas para contas com role "admin")
- Assistente "NeuroIA" com respostas baseadas em palavras-chave (sem
  dependência de APIs externas de IA)

## Estrutura

```
app.py            → factory da aplicação Flask
db.py             → conexão sqlite3 + schema
models.py         → classes de modelo (wrappers sobre linhas do sqlite3)
repo.py           → todas as queries SQL (camada de acesso a dados)
auth.py           → autenticação baseada em sessão (substitui Flask-Login)
routes.py         → todas as rotas/páginas
seed.py           → dados de demonstração
tutor_ai.py       → motor de respostas do assistente NeuroIA
templates/        → HTML (Jinja2)
static/           → CSS e JS
```
