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
        for stmt in statements:
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except Exception:
                db.session.rollback()

@app.route("/", methods=["GET", "POST"])
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
                completion = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                    messages=[
                        {"role": "system", "content": (
                            "Você é o LexAprendiz, um assistente jurídico especializado na Lei da Aprendizagem (Lei nº 10.097/2000 e normas correlatas). "
                            "Regras: \n"
                            "- Sempre cumprimente o usuário pelo primeiro nome e se apresente como 'LexAprendiz' antes da resposta.\n"
                            "- Responda com linguagem simples e objetiva.\n"
                            "- NUNCA invente informações. Se não houver fonte oficial, diga 'Não sei com segurança' e explique como encontrar.\n"
                            "- SEMPRE liste as fontes oficiais no final (links para: gov.br, planalto.gov.br, mte.gov.br, camara.leg.br, senado.leg.br, mpt.mp.br, tst.jus.br, etc.).\n"
                            "- Se a pergunta não puder ser respondida com base em fontes confiáveis, não responda e explique."
                        )},
                        {"role": "user", "content": f"Nome do usuário: {first_name}. Pergunta: {pergunta}"}
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
    rows = User.query.with_entities(User.id, User.name, User.email, User.cpf, User.city, User.state).order_by(User.id).all()
    def generate():
        yield "id,nome,email,cpf,cidade,estado\n"
        for r in rows:
            # Escape commas and quotes as needed (basic handling)
            vals = [
                str(r.id),
                (r.name or "").replace('"','""'),
                (r.email or "").replace('"','""'),
                (r.cpf or "").replace('"','""'),
                (r.city or "").replace('"','""'),
                (r.state or "").replace('"','""'),
            ]
            yield ",".join([f'"{v}"' for v in vals]) + "\n"
    return Response(generate(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=usuarios_lexaprendiz.csv'
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
