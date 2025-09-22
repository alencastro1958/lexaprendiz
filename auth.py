from flask import Blueprint, render_template, redirect, request, flash, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from flask_bcrypt import Bcrypt
import re

# Importação com fallback para validação CPF
try:
    from utils import validate_cpf, clean_cpf, format_cpf
    print("DEBUG: Import utils.py SUCCESS")
except ImportError as e:
    print(f"DEBUG: Import utils.py FAILED: {e}")
    # Fallback: implementação inline
    def validate_cpf(cpf):
        cpf = re.sub(r'[^0-9]', '', cpf)
        if len(cpf) != 11:
            return False
        if cpf == cpf[0] * 11:
            return False
        sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digit1 = (sum1 * 10) % 11
        if digit1 == 10:
            digit1 = 0
        if digit1 != int(cpf[9]):
            return False
        sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digit2 = (sum2 * 10) % 11
        if digit2 == 10:
            digit2 = 0
        return digit2 == int(cpf[10])
    
    def clean_cpf(cpf):
        return re.sub(r'[^0-9]', '', cpf) if cpf else ""
    
    def format_cpf(cpf):
        cpf = re.sub(r'[^0-9]', '', cpf)
        if len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return cpf

auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        print(f"DEBUG LOGIN: Tentativa de login para email: {email}")
        user = User.query.filter_by(email=email).first()
        print(f"DEBUG LOGIN: Usuário encontrado: {user is not None}")
        if user:
            print(f"DEBUG LOGIN: Verificando senha...")
            password_valid = bcrypt.check_password_hash(user.password, password)
            print(f"DEBUG LOGIN: Senha válida: {password_valid}")
            if password_valid:
                login_user(user)
                print(f"DEBUG LOGIN: Login realizado com sucesso")
                return redirect(url_for("dashboard"))
        print(f"DEBUG LOGIN: Login falhou")
        flash("Login inválido.")
    return render_template("login.html")

@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form["email"].strip().lower()
        cpf_raw = request.form.get("cpf", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip().upper()
        password_raw = request.form.get("password", "")
        
        # Validações básicas obrigatórias
        if not (email and cpf_raw and password_raw and name):
            flash("Nome, E-mail, CPF e senha são obrigatórios.")
            return render_template("register.html")
        
        # Validação de email formato
        if '@' not in email or '.' not in email:
            flash("Formato de e-mail inválido.")
            return render_template("register.html")
        
        # Limpa e valida CPF
        cpf_clean = clean_cpf(cpf_raw)
        print(f"DEBUG: CPF raw: '{cpf_raw}', CPF clean: '{cpf_clean}', Tamanho: {len(cpf_clean)}, Valid: {validate_cpf(cpf_clean)}")
        
        # Validação rigorosa de CPF
        if len(cpf_clean) != 11:
            flash(f"CPF deve ter exatamente 11 dígitos. Você digitou {len(cpf_clean)} dígitos.")
            return render_template("register.html")
            
        if not validate_cpf(cpf_clean):
            flash("CPF inválido. Digite um CPF válido com 11 dígitos.")
            return render_template("register.html")
        
        # Formata CPF para armazenamento consistente
        cpf_formatted = format_cpf(cpf_clean)
        
        # Verificação rigorosa de duplicatas com logs detalhados
        print(f"DEBUG DUPLICATAS: Verificando email: {email}")
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            print(f"DEBUG DUPLICATAS: Email {email} já existe (ID: {existing_email.id})")
            flash("Este e-mail já está cadastrado. Use outro e-mail ou faça login.")
            return render_template("register.html")
        
        print(f"DEBUG DUPLICATAS: Verificando CPF formatado: {cpf_formatted}")
        existing_cpf = User.query.filter_by(cpf=cpf_formatted).first()
        if existing_cpf:
            print(f"DEBUG DUPLICATAS: CPF formatado {cpf_formatted} já existe (ID: {existing_cpf.id})")
            flash("Este CPF já está cadastrado. Cada CPF pode ter apenas uma conta.")
            return render_template("register.html")
        
        print(f"DEBUG DUPLICATAS: Verificando CPF limpo: {cpf_clean}")
        existing_cpf_clean = User.query.filter_by(cpf=cpf_clean).first()
        if existing_cpf_clean:
            print(f"DEBUG DUPLICATAS: CPF limpo {cpf_clean} já existe (ID: {existing_cpf_clean.id})")
            flash("Este CPF já está cadastrado. Cada CPF pode ter apenas uma conta.")
            return render_template("register.html")
        
        # Verificação adicional case-insensitive para email
        print(f"DEBUG DUPLICATAS: Verificação case-insensitive email")
        existing_email_ci = User.query.filter(User.email.ilike(email)).first()
        if existing_email_ci:
            print(f"DEBUG DUPLICATAS: Email case-insensitive {email} já existe (ID: {existing_email_ci.id})")
            flash("Este e-mail já está cadastrado. Use outro e-mail ou faça login.")
            return render_template("register.html")
        
        print(f"DEBUG DUPLICATAS: Nenhuma duplicata encontrada, prosseguindo com cadastro")
        
        # Gera hash da senha
        password = bcrypt.generate_password_hash(password_raw).decode("utf-8")
        
        # Endereço
        cep = request.form.get("cep", "").strip()
        address = request.form.get("address", "").strip()
        number = request.form.get("number", "").strip()
        complement = request.form.get("complement", "").strip()
        neighborhood = request.form.get("neighborhood", "").strip()

        try:
            user = User(
                email=email, 
                password=password, 
                name=name, 
                cpf=cpf_formatted, 
                city=city, 
                state=state,
                cep=cep, 
                address=address, 
                number=number, 
                complement=complement, 
                neighborhood=neighborhood
            )
            db.session.add(user)
            db.session.commit()
            
            # Login automático após cadastro
            login_user(user)
            flash("Cadastro realizado com sucesso! Bem-vindo ao LexAprendiz!")
            return redirect(url_for("dashboard"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar conta: {str(e)}. Tente novamente.")
            return render_template("register.html")
    
    return render_template("register.html")

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

@auth.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    from flask_login import current_user
    if request.method == "POST":
        current_user.name = request.form.get("name", "").strip()
        current_user.cpf = request.form.get("cpf", "").strip()
        current_user.city = request.form.get("city", "").strip()
        current_user.state = request.form.get("state", "").strip().upper()
        current_user.cep = request.form.get("cep", "").strip()
        current_user.address = request.form.get("address", "").strip()
        current_user.number = request.form.get("number", "").strip()
        current_user.complement = request.form.get("complement", "").strip()
        current_user.neighborhood = request.form.get("neighborhood", "").strip()
        db.session.commit()
        flash("Perfil atualizado com sucesso!")
        return redirect(url_for("dashboard"))
    return render_template("profile.html")
