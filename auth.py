from flask import Blueprint, render_template, redirect, request, flash, url_for
from flask_login import login_user, logout_user, login_required
from models import db, User
from flask_bcrypt import Bcrypt

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
        cpf = request.form.get("cpf", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip().upper()
        password_raw = request.form.get("password", "")
        if not (email and cpf and password_raw):
            flash("E-mail, CPF e senha são obrigatórios.")
            return render_template("register.html")
        password = bcrypt.generate_password_hash(password_raw).decode("utf-8")
        # Endereço
        cep = request.form.get("cep", "").strip()
        address = request.form.get("address", "").strip()
        number = request.form.get("number", "").strip()
        complement = request.form.get("complement", "").strip()
        neighborhood = request.form.get("neighborhood", "").strip()

        if User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.")
            return render_template("register.html")
        if cpf and User.query.filter_by(cpf=cpf).first():
            flash("CPF já cadastrado.")
            return render_template("register.html")

        user = User(
            email=email, password=password, name=name, cpf=cpf, city=city, state=state,
            cep=cep, address=address, number=number, complement=complement, neighborhood=neighborhood
        )
        db.session.add(user)
        db.session.commit()
        flash("Cadastro realizado com sucesso!")
        return redirect(url_for("auth.login"))
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
