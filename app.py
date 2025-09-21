import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, flash
from flask_login import LoginManager, login_required, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from dotenv import load_dotenv
from openai import OpenAI
from models import db, User, Question
from auth import auth, bcrypt
from sqlalchemy import text
from sqlalchemy import inspect
import urllib.parse
import requests
import xml.etree.ElementTree as ET

load_dotenv()

# Verificar se a API key do OpenAI está configurada
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("AVISO: OPENAI_API_KEY não configurada!")
    client = None
else:
    client = OpenAI(api_key=openai_api_key)

app = Flask(__name__)

# Database: prefer DATABASE_URL (Render PostgreSQL) and fallback to local SQLite
database_url = os.getenv("DATABASE_URL", "sqlite:///database.db")
# Render and many providers expose postgres://; SQLAlchemy needs postgresql+psycopg2://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback-secret-key-for-development")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Ensure SSL for managed Postgres (Render) and keep healthy connections
if database_url.startswith("postgresql"):
    engine_opts = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})
    connect_args = dict(engine_opts.get("connect_args", {}))
    connect_args.setdefault("sslmode", "require")
    engine_opts["connect_args"] = connect_args
    engine_opts["pool_pre_ping"] = True
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_opts
db.init_app(app)
bcrypt.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)

app.register_blueprint(auth)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class SecureModelView(ModelView):
    def is_accessible(self):
        if not current_user.is_authenticated:
            return False
        admins = os.getenv("ADMIN_EMAILS", "").split(",")
        admins = [e.strip().lower() for e in admins if e.strip()]
        return (current_user.email or "").lower() in admins

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))


class UserAdminView(SecureModelView):
    column_searchable_list = ["email", "name", "cpf", "city", "state"]
    column_filters = ["state", "city"]
    column_list = ("id", "name", "email", "cpf", "city", "state")
    form_columns = ("name", "email", "cpf", "city", "state")

class QuestionAdminView(SecureModelView):
    column_searchable_list = ["content", "response"]
    column_filters = ["timestamp", "user_id"]
    column_list = ("id", "user_id", "timestamp", "content")

def setup_admin(app):
    admin = Admin(app, name="LexAprendiz Admin", template_mode="bootstrap4")
    admin.add_view(UserAdminView(User, db.session))
    admin.add_view(QuestionAdminView(Question, db.session))
    return admin

def _ensure_profile_columns():
    """Add new User profile columns if missing (works for Postgres and SQLite)."""
    with app.app_context():
        inspector = inspect(db.engine)
        cols = {c['name'] for c in inspector.get_columns('user')}
        # Postgres supports IF NOT EXISTS; SQLite we check first via inspector
        statements = []
        if 'name' not in cols:
            statements.append("ALTER TABLE \"user\" ADD COLUMN name VARCHAR(150)")
        if 'cpf' not in cols:
            statements.append("ALTER TABLE \"user\" ADD COLUMN cpf VARCHAR(14)")
        if 'city' not in cols:
            statements.append("ALTER TABLE \"user\" ADD COLUMN city VARCHAR(120)")
        if 'state' not in cols:
            statements.append("ALTER TABLE \"user\" ADD COLUMN state VARCHAR(2)")
        if 'cep' not in cols:
            statements.append("ALTER TABLE \"user\" ADD COLUMN cep VARCHAR(9)")
        if 'address' not in cols:
            statements.append("ALTER TABLE \"user\" ADD COLUMN address VARCHAR(200)")
        if 'number' not in cols:
            statements.append("ALTER TABLE \"user\" ADD COLUMN number VARCHAR(20)")
        if 'complement' not in cols:
            statements.append("ALTER TABLE \"user\" ADD COLUMN complement VARCHAR(100)")
        if 'neighborhood' not in cols:
            statements.append("ALTER TABLE \"user\" ADD COLUMN neighborhood VARCHAR(120)")
        for stmt in statements:
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except Exception:
                db.session.rollback()

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template("index.html")

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    resposta = ""
    pergunta = ""
    # Exigir perfil completo
    if not (current_user.name and current_user.cpf and current_user.city and current_user.state):
        flash("Complete seu perfil antes de fazer perguntas.")
        return redirect(url_for('auth.profile'))

    if request.method == "POST":
        pergunta = request.form["pergunta"]
        try:
            if not client:
                resposta = "Erro: API do OpenAI não configurada. Configure a variável OPENAI_API_KEY no Render."
            else:
                first_name = (current_user.name or "").strip().split(" ")[0] or "usuário"
                # Preparar fontes oficiais (heurística por palavra-chave)
                def official_sources(query: str):
                    q = urllib.parse.quote_plus(query)
                    bases = [
                        ("Planalto", f"https://www.planalto.gov.br/ccivil_03/leis/leis_2001/l10097.htm"),
                        ("DOU", f"https://www.in.gov.br/en/web/guest/busca/-/buscar?q={q}"),
                        ("MTE", f"https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/aprendizagem"),
                        ("MPT", f"https://mpt.mp.br/assuntos/aprendizagem"),
                        ("TST", f"https://www.tst.jus.br/busca?q={q}"),
                        ("STF", f"https://portal.stf.jus.br/busca/?sitesearch=stf.jus.br&search={q}"),
                        ("STJ", f"https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Pesquisa.aspx?termo={q}"),
                        ("CNJ", f"https://www.cnj.jus.br/?s={q}"),
                        ("Câmara", f"https://www.camara.leg.br/busca-portal?query={q}"),
                        ("Senado", f"https://www25.senado.leg.br/web/atividade/busca?_search={q}"),
                    ]
                    # Dê preferência às fontes gov.br e .jus.br
                    return bases

                def fetch_lexml_sources(query: str, limit: int = 5):
                    # LexML API de busca (Atom): https://www.lexml.gov.br/ (servicos.lexml.gov.br)
                    # Exemplo: https://servicos.lexml.gov.br/busca.atom?q=Lei%2010.097
                    url = f"https://servicos.lexml.gov.br/busca.atom?q={urllib.parse.quote_plus(query)}"
                    items = []
                    try:
                        r = requests.get(url, timeout=6)
                        if r.status_code == 200 and r.text:
                            root = ET.fromstring(r.text)
                            ns = {'atom': 'http://www.w3.org/2005/Atom'}
                            for entry in root.findall('atom:entry', ns)[:limit]:
                                title_el = entry.find('atom:title', ns)
                                link_el = entry.find('atom:link', ns)
                                title = title_el.text.strip() if title_el is not None and title_el.text else 'Documento LexML'
                                href = link_el.get('href') if link_el is not None else None
                                if href:
                                    items.append((f"LexML: {title}", href))
                    except Exception:
                        pass
                    return items

                fontes = official_sources(pergunta)
                # Enriquecer com LexML (gratuito)
                fontes_lexml = fetch_lexml_sources(pergunta)
                # Deduplicar por URL
                seen = set()
                all_fontes = []
                for nome, url in [*fontes_lexml, *fontes]:
                    if url not in seen:
                        seen.add(url)
                        all_fontes.append((nome, url))
                fontes_texto = "\n".join([f"- {nome}: {url}" for nome, url in all_fontes])

                completion = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                    messages=[
                        {"role": "system", "content": (
                            "Você é o LexAprendiz, um assistente jurídico especializado na Lei da Aprendizagem (Lei nº 10.097/2000 e normas correlatas). "
                            "Regras: \n"
                            "- Sempre cumprimente o usuário pelo primeiro nome e se apresente como 'LexAprendiz' antes da resposta.\n"
                            "- Responda com linguagem simples e objetiva.\n"
                            "- NUNCA invente informações. Se não houver fonte oficial, diga 'Não sei com segurança' e explique como encontrar.\n"
                            "- Use EXCLUSIVAMENTE as fontes fornecidas a seguir como referência. Se elas não bastarem, peça ao usuário para refinar a pergunta.\n"
                            "- SEMPRE liste as fontes oficiais no final (links para: gov.br, planalto.gov.br, mte.gov.br, camara.leg.br, senado.leg.br, mpt.mp.br, tst.jus.br, stf.jus.br, stj.jus.br).\n"
                            "- Não cite portais comerciais pagos (por exemplo: JusBrasil); priorize somente domínios .gov.br, .jus.br e .leg.br.\n"
                            "- Se a pergunta não puder ser respondida com base em fontes confiáveis, não responda e explique."
                        )},
                        {"role": "user", "content": f"Nome do usuário: {first_name}. Pergunta: {pergunta}.\nFontes oficiais sugeridas:\n{fontes_texto}"}
                    ],
                    max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500"))
                )
                core = completion.choices[0].message.content
                resposta = f"Olá, {first_name}! Eu sou o LexAprendiz.\n\n{core}"
                nova = Question(content=pergunta, response=resposta, user_id=current_user.id)
                db.session.add(nova)
                db.session.commit()
        except Exception as e:
            resposta = f"Erro ao processar sua pergunta: {str(e)}"

    historico = Question.query.filter_by(user_id=current_user.id).order_by(Question.timestamp.desc()).all()
    admins = os.getenv("ADMIN_EMAILS", "")
    is_admin = current_user.is_authenticated and (current_user.email or "").lower() in [e.strip().lower() for e in admins.split(",") if e.strip()]
    return render_template("dashboard.html", resposta=resposta, pergunta=pergunta, historico=historico, is_admin=is_admin)

# Public health check endpoint for Render
@app.route("/healthz", methods=["GET"])  # nosec - simple liveness/readiness
def healthz():
    try:
        # quick DB check (works for both SQLite and Postgres)
        with app.app_context():
            db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except Exception as exc:  # pragma: no cover
        return jsonify({"status": "error", "detail": str(exc)}), 503

# Debug endpoint to check admin configuration
@app.route("/debug/admin")
@login_required
def debug_admin():
    admin_emails = os.getenv("ADMIN_EMAILS", "")
    admin_list = [e.strip().lower() for e in admin_emails.split(",") if e.strip()]
    current_email = (current_user.email or "").lower()
    is_admin = current_email in admin_list
    
    return jsonify({
        "current_user_email": current_email,
        "admin_emails_env": admin_emails,
        "admin_list": admin_list,
        "is_admin": is_admin,
        "user_authenticated": current_user.is_authenticated
    })

with app.app_context():
    db.create_all()
    _ensure_profile_columns()
    # init admin after db
    setup_admin(app)

def _is_admin() -> bool:
    if not current_user.is_authenticated:
        return False
    admins = os.getenv("ADMIN_EMAILS", "")
    return (current_user.email or "").lower() in [e.strip().lower() for e in admins.split(",") if e.strip()]

@app.route("/admin/export/users.csv")
@login_required
def export_users_csv():
    if not _is_admin():
        return redirect(url_for('auth.login'))
    rows = User.query.with_entities(
        User.id, User.name, User.email, User.cpf, User.city, User.state,
        User.cep, User.address, User.number, User.complement, User.neighborhood
    ).order_by(User.id).all()
    def generate():
        yield "id,nome,email,cpf,cidade,estado,cep,endereco,numero,complemento,bairro\n"
        for r in rows:
            # Escape commas and quotes as needed (basic handling)
            vals = [
                str(r.id),
                (r.name or "").replace('"','""'),
                (r.email or "").replace('"','""'),
                (r.cpf or "").replace('"','""'),
                (r.city or "").replace('"','""'),
                (r.state or "").replace('"','""'),
                (r.cep or "").replace('"','""'),
                (r.address or "").replace('"','""'),
                (r.number or "").replace('"','""'),
                (r.complement or "").replace('"','""'),
                (r.neighborhood or "").replace('"','""'),
            ]
            yield ",".join([f'"{v}"' for v in vals]) + "\n"
    return Response(generate(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=usuarios_lexaprendiz.csv'
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
