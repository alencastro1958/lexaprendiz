import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_required, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from dotenv import load_dotenv
from openai import OpenAI
from models import db, User, Question
from auth import auth
from sqlalchemy import text

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


def setup_admin(app):
    admin = Admin(app, name="LexAprendiz Admin", template_mode="bootstrap4")
    admin.add_view(SecureModelView(User, db.session))
    admin.add_view(SecureModelView(Question, db.session))
    return admin

@app.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    resposta = ""
    pergunta = ""

    if request.method == "POST":
        pergunta = request.form["pergunta"]
        try:
            if not client:
                resposta = "Erro: API do OpenAI não configurada. Configure a variável OPENAI_API_KEY no Render."
            else:
                completion = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                    messages=[
                        {"role": "system", "content": "Você é um especialista na Lei da Aprendizagem."},
                        {"role": "user", "content": pergunta}
                    ],
                    max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500"))
                )
                resposta = completion.choices[0].message.content
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
    # init admin after db
    setup_admin(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
