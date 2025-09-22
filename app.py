import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, flash
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv
from openai import OpenAI
from models import db, User, Question
from auth import auth, bcrypt
from admin_auth import admin_auth
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
app.register_blueprint(admin_auth)

# Filtro personalizado para quebras de linha
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Converte quebras de linha em <br>"""
    if text:
        return text.replace('\n', '<br>')
    return text

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

@app.route("/debug/validation")
def debug_validation():
    """Endpoint para testar se a validação está funcionando"""
    try:
        from utils import validate_cpf, clean_cpf
        utils_imported = True
    except:
        utils_imported = False
    
    test_cpf = "23232323232323"
    
    if utils_imported:
        cpf_clean = clean_cpf(test_cpf)
        is_valid = validate_cpf(cpf_clean)
    else:
        # Fallback validation
        import re
        cpf_clean = re.sub(r'[^0-9]', '', test_cpf)
        is_valid = len(cpf_clean) == 11
    
    return jsonify({
        "utils_imported": utils_imported,
        "test_cpf": test_cpf,
        "cpf_clean": cpf_clean,
        "cpf_length": len(cpf_clean),
        "is_valid": is_valid,
        "timestamp": str(__import__('datetime').datetime.now()),
        "version": "35892ac"
    })

@app.route("/api/check-duplicates")
def check_duplicates():
    """API para verificar duplicatas em tempo real"""
    email = request.args.get('email', '').strip().lower()
    cpf = request.args.get('cpf', '').strip()
    
    # Remove formatação do CPF
    cpf_clean = ''.join(filter(str.isdigit, cpf))
    
    result = {
        'email_exists': False,
        'cpf_exists': False,
        'can_register': True,
        'message': ''
    }
    
    if email:
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            result['email_exists'] = True
            result['can_register'] = False
            result['message'] = 'Este e-mail já está cadastrado'
    
    if cpf_clean and len(cpf_clean) == 11:
        # Verifica CPF formatado e limpo
        try:
            from utils import format_cpf
            cpf_formatted = format_cpf(cpf_clean)
            existing_cpf = User.query.filter_by(cpf=cpf_formatted).first()
            if not existing_cpf:
                existing_cpf = User.query.filter_by(cpf=cpf_clean).first()
            
            if existing_cpf:
                result['cpf_exists'] = True
                result['can_register'] = False
                result['message'] = 'Este CPF já está cadastrado'
        except Exception as e:
            print(f"Erro ao verificar CPF: {e}")
    
    return jsonify(result)

@app.route("/debug/database")
def debug_database():
    """Endpoint para verificar estado do banco de dados"""
    try:
        total_users = User.query.count()
        
        # Últimos 10 usuários
        recent_users = User.query.order_by(User.id.desc()).limit(10).all()
        users_data = []
        for user in recent_users:
            users_data.append({
                'id': user.id,
                'email': user.email,
                'cpf': user.cpf[:3] + '***' + user.cpf[-2:] if user.cpf else None,  # Mascarado
                'name': user.name[:10] + '...' if user.name and len(user.name) > 10 else user.name
            })
        
        # Duplicatas
        email_duplicates = db.session.query(User.email, db.func.count(User.email).label('count')).group_by(User.email).having(db.func.count(User.email) > 1).all()
        cpf_duplicates = db.session.query(User.cpf, db.func.count(User.cpf).label('count')).group_by(User.cpf).having(db.func.count(User.cpf) > 1).all()
        
        return jsonify({
            "total_users": total_users,
            "recent_users": users_data,
            "email_duplicates": len(email_duplicates),
            "cpf_duplicates": len(cpf_duplicates),
            "email_duplicate_details": [{"email": email, "count": count} for email, count in email_duplicates],
            "cpf_duplicate_details": [{"cpf": cpf[:3] + '***' + cpf[-2:] if cpf else None, "count": count} for cpf, count in cpf_duplicates],
            "timestamp": str(__import__('datetime').datetime.now()),
            "version": "510b505"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": str(__import__('datetime').datetime.now())
        })

@app.route("/test/simple-register", methods=["GET", "POST"])
def test_simple_register():
    """Teste simples de cadastro para debug"""
    if request.method == "GET":
        return '''
        <html>
        <body>
        <h2>Teste Simples de Cadastro</h2>
        <form method="POST">
            Email: <input name="email" type="email" required><br><br>
            CPF: <input name="cpf" type="text" required><br><br>
            Nome: <input name="name" type="text" required><br><br>
            Senha: <input name="password" type="password" required><br><br>
            <button type="submit">Cadastrar Teste</button>
        </form>
        </body>
        </html>
        '''
    
    # POST - processar cadastro
    try:
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        name = request.form.get('name')
        password = request.form.get('password')
        
        # Hash da senha
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        
        # Criar usuário
        user = User(email=email, cpf=cpf, name=name, password=password_hash)
        db.session.add(user)
        db.session.commit()
        
        return f"<h2>SUCESSO!</h2><p>Usuário criado com ID: {user.id}</p><p>Email: {user.email}</p><p>CPF: {user.cpf}</p>"
        
    except Exception as e:
        return f"<h2>ERRO!</h2><p>{str(e)}</p>"

@app.route("/test/create-test-user")
def create_test_user():
    """Cria um usuário de teste para debug"""
    try:
        # Verificar se já existe
        existing = User.query.filter_by(email="teste@teste.com").first()
        if existing:
            return f"<h2>USUÁRIO JÁ EXISTE!</h2><p>Email: {existing.email}</p><p><a href='/test/auto-login'>Fazer Login</a></p>"
        
        # Criar usuário de teste
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        password_hash = bcrypt.generate_password_hash("123456").decode("utf-8")
        
        user = User(
            email="teste@teste.com",
            password=password_hash,
            name="Usuário Teste",
            cpf="12345678901",
            city="São Paulo",
            state="SP"
        )
        
        db.session.add(user)
        db.session.commit()
        
        return f'''
        <h2>USUÁRIO CRIADO COM SUCESSO!</h2>
        <p>Email: teste@teste.com</p>
        <p>Senha: 123456</p>
        <p>ID: {user.id}</p>
        <p><a href="/test/auto-login">Login Automático</a></p>
        <p><a href="/login">Login Manual</a></p>
        '''
    except Exception as e:
        return f"<h2>ERRO!</h2><p>{str(e)}</p>"

@app.route("/test/auto-login")
def test_auto_login():
    """Testa login automático para debug"""
    from flask_login import login_user
    try:
        # Buscar o primeiro usuário
        user = User.query.first()
        if user:
            login_user(user, remember=True)
            return f'''
            <h2>LOGIN AUTOMÁTICO REALIZADO!</h2>
            <p>Usuário: {user.email}</p>
            <p>Autenticado: {current_user.is_authenticated}</p>
            <p><a href="/dashboard">Ir para Dashboard</a></p>
            <p><a href="/test/login-redirect">Testar Redirecionamento</a></p>
            '''
        else:
            return "<h2>NENHUM USUÁRIO ENCONTRADO</h2><p>Primeiro registre um usuário em /test/simple-register</p>"
    except Exception as e:
        return f"<h2>ERRO!</h2><p>{str(e)}</p>"

@app.route("/test/login-redirect")
@login_required
def test_login_redirect():
    """Teste para verificar se o login funciona"""
    return f'''
    <h2>LOGIN FUNCIONANDO!</h2>
    <p>Usuário autenticado: {current_user.is_authenticated}</p>
    <p>Email: {current_user.email}</p>
    <p>Nome: {current_user.name}</p>
    <p>ID: {current_user.id}</p>
    <a href="/dashboard">Ir para Dashboard</a>
    '''

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    resposta = ""
    pergunta = ""
    # Perfil não é mais obrigatório para fazer perguntas

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
    return render_template("dashboard.html", resposta=resposta, pergunta=pergunta, historico=historico)

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
