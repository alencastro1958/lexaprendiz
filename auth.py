from flask import Blueprint, render_template, redirect, request, flash, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from flask_bcrypt import Bcrypt
from utils import validate_cpf, clean_cpf, format_cpf

auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))
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
        
        # Validações básicas
        if not (email and cpf_raw and password_raw):
            flash("E-mail, CPF e senha são obrigatórios.")
            return render_template("register.html")
        
        # Limpa e valida CPF
        cpf_clean = clean_cpf(cpf_raw)
        print(f"DEBUG: CPF raw: '{cpf_raw}', CPF clean: '{cpf_clean}', Valid: {validate_cpf(cpf_clean)}")
        if not validate_cpf(cpf_clean):
            flash("CPF inválido. Por favor, verifique os números digitados.")
            return render_template("register.html")
        
        # Formata CPF para armazenamento consistente
        cpf_formatted = format_cpf(cpf_clean)
        
        # Verifica se email já existe
        if User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado. Use outro e-mail ou faça login.")
            return render_template("register.html")
        
        # Verifica se CPF já existe
        if User.query.filter_by(cpf=cpf_formatted).first():
            flash("CPF já cadastrado. Cada CPF pode ter apenas uma conta.")
            return render_template("register.html")
        
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
            
            flash("Cadastro realizado com sucesso! Faça login para acessar o LexAprendiz.")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            flash("Erro ao criar conta. Tente novamente.")
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
