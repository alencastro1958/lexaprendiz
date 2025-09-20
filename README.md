# LexAprendiz — Deploy no Render, PostgreSQL e Domínio

Guia rápido para operar o backend Flask no Render, trocar SQLite por PostgreSQL e conectar o domínio leidaaprendizagembr.com.br.

## Visão geral
- Plataforma: Render (Web Service — Python)
- Servidor: Gunicorn (`web: gunicorn app:app` via `Procfile`)
- Python: 3.12.11 (definido em `render.yaml` e `runtime.txt`)
- Health check: `/healthz` (valida app + DB)
- Banco: SQLite local; em produção use `DATABASE_URL` (PostgreSQL)

## Variáveis de ambiente (produção)
Defina no Render → Web Service → Settings → Environment:
- SECRET_KEY: um valor aleatório longo
- OPENAI_API_KEY: sua chave da OpenAI
- OPENAI_MODEL: opcional (padrão: `gpt-3.5-turbo`)
- OPENAI_MAX_TOKENS: opcional (padrão: `500`)
- DATABASE_URL: string do PostgreSQL (Render fornece)

Obs.: Se a URL vier como `postgres://...`, o app converte para `postgresql+psycopg2://` automaticamente e força `sslmode=require` se não houver.

## 1) Criar PostgreSQL (Free) no Render
1. Acesse o dashboard do Render
2. New → PostgreSQL → plano Free → escolha a mesma região do Web Service
3. Aguarde a criação e abra o recurso do banco
4. Em “Connections”, copie a “External Connection String”

## 2) Configurar `DATABASE_URL` no Web Service
1. Render → seu Web Service (Flask)
2. Settings → Environment → Add Environment Variable
3. Key: `DATABASE_URL` | Value: cole a connection string do passo anterior
4. Garanta também as variáveis: `SECRET_KEY`, `OPENAI_API_KEY` (e opcionais `OPENAI_MODEL`, `OPENAI_MAX_TOKENS`)

## 3) Redeploy com limpar cache
1. Render → seu Web Service → Deploys → Manual Deploy
2. Selecione “Clear build cache & deploy”
3. Aguarde o deploy completar

## 4) Verificar saúde
- Abra: `https://<seu-servico>.onrender.com/healthz`
- Esperado: `{ "status": "ok", "db": "ok" }`
- Se retornar erro 503, verifique `DATABASE_URL` e os logs do Render

## 5) Conectar domínio leidaaprendizagembr.com.br
1. Render → seu Web Service → Settings → Custom Domains → Add Custom Domain
2. Adicione:
   - Apex: `leidaaprendizagembr.com.br`
   - `www.leidaaprendizagembr.com.br` (recomendado)
3. Siga as instruções de DNS exibidas pelo Render (variam por provedor):
   - `www` → CNAME apontando para `<seu-servico>.onrender.com`
   - Apex → ALIAS/ANAME para `<seu-servico>.onrender.com` (se o seu DNS suportar). Se não suportar, siga a instrução do Render (geralmente A/AAAA específicos).
4. Aguarde a propagação DNS (pode levar algumas horas) e a emissão automática de SSL.

Dicas:
- Se já tiver uma Static Site no Render com o mesmo domínio, remova ou altere o domínio dela para evitar conflito.
- Ative redirecionamento `www` → apex ou vice-versa conforme sua preferência no Render.

## 6) Migração de dados (opcional)
O app cria as tabelas automaticamente no primeiro boot com Postgres. Para migrar dados do SQLite:
- Manual: exportar do SQLite (`instance/database.db`) e importar no Postgres com scripts SQL.
- Ferramentas: DBeaver/DBConvert/etc.

Para migrações futuras, considere Flask-Migrate/Alembic.

## Desenvolvimento local
1. Copie `.env.example` para `.env` e preencha o que for necessário
2. Sem `DATABASE_URL`, o app usa SQLite local (`instance/database.db`)
3. Para Postgres local, defina `DATABASE_URL` (ex.: `postgresql+psycopg2://user:pass@localhost:5432/dbname`)

## Solução de problemas
- Health check 503: confirme `DATABASE_URL`, verifique se a instância está “Available” e veja os logs
- psycopg2: usamos `psycopg2-binary` no `requirements.txt`
- Python errado: confira `runtime.txt` (python-3.12.11) e `render.yaml`
- Branch errado no Render: Settings → Branch deve apontar para `master`

## Detalhes do serviço
- buildCommand: `pip install -r requirements.txt`
- startCommand: `gunicorn app:app`
- runtime: python
- healthCheckPath: `/healthz`
- PYTHON_VERSION: `3.12.11`

—
Se quiser, me diga o provedor do domínio e o subdomínio do serviço no Render que eu te passo os registros DNS exatos.
