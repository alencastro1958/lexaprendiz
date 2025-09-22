from flask import Blueprint, render_template, redirect, request, flash, url_for, session, Response
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from flask_bcrypt import Bcrypt
import os

admin_auth = Blueprint('admin_auth', __name__, url_prefix='/admin')
bcrypt = Bcrypt()

class AdminUser:
    """Classe simples para representar um administrador autenticado"""
    def __init__(self, username):
        self.username = username
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return f"admin_{self.username}"

def is_admin_authenticated():
    """Verifica se há um admin logado na sessão"""
    return session.get('admin_logged_in', False)

def get_admin_credentials():
    """Obtém credenciais de admin das variáveis de ambiente"""
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    return admin_user, admin_pass

@admin_auth.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        
        admin_user, admin_pass = get_admin_credentials()
        
        if username == admin_user and password == admin_pass:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash("Login administrativo realizado com sucesso!", "success")
            return redirect(url_for("admin_auth.admin_dashboard"))
        else:
            flash("Credenciais administrativas inválidas.", "error")
    
    return render_template("admin_login.html")

@admin_auth.route("/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash("Logout administrativo realizado.", "info")
    return redirect(url_for("admin_auth.admin_login"))

@admin_auth.route("/")
@admin_auth.route("/dashboard")
def admin_dashboard():
    if not is_admin_authenticated():
        return redirect(url_for('admin_auth.admin_login'))
    
    # Estatísticas básicas
    total_users = User.query.count()
    users_with_profile = User.query.filter(
        User.name.isnot(None), 
        User.cpf.isnot(None)
    ).count()
    
    recent_users = User.query.order_by(User.id.desc()).limit(10).all()
    
    return render_template("admin_dashboard.html", 
                         total_users=total_users,
                         users_with_profile=users_with_profile,
                         recent_users=recent_users)

@admin_auth.route("/users")
def admin_users():
    if not is_admin_authenticated():
        return redirect(url_for('admin_auth.admin_login'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = User.query
    if search:
        query = query.filter(
            (User.name.contains(search)) |
            (User.email.contains(search)) |
            (User.cpf.contains(search))
        )
    
    users = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template("admin_users.html", users=users, search=search)

@admin_auth.route("/users/<int:user_id>")
def admin_user_detail(user_id):
    if not is_admin_authenticated():
        return redirect(url_for('admin_auth.admin_login'))
    
    user = User.query.get_or_404(user_id)
    questions = user.questions.order_by(db.desc(db.text('timestamp'))).limit(10).all()
    
    return render_template("admin_user_detail.html", user=user, questions=questions)

@admin_auth.route("/export/users.csv")
def export_users_csv():
    if not is_admin_authenticated():
        return redirect(url_for('admin_auth.admin_login'))
    
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

@admin_auth.route('/cleanup-duplicates', methods=['GET', 'POST'])
def cleanup_duplicates():
    """Remove duplicatas do banco de dados"""
    if not is_admin_authenticated():
        return redirect(url_for('admin_auth.admin_login'))
    
    if request.method == 'GET':
        # Listar duplicatas para revisão
        # Emails duplicados
        email_duplicates = db.session.query(User.email, db.func.count(User.email).label('count')).group_by(User.email).having(db.func.count(User.email) > 1).all()
        
        # CPFs duplicados
        cpf_duplicates = db.session.query(User.cpf, db.func.count(User.cpf).label('count')).group_by(User.cpf).having(db.func.count(User.cpf) > 1).all()
        
        return render_template('admin_cleanup.html', 
                               email_duplicates=email_duplicates, 
                               cpf_duplicates=cpf_duplicates)
    
    elif request.method == 'POST':
        try:
            removed_count = 0
            
            # Remove duplicatas de email (mantém o mais antigo)
            email_duplicates = db.session.query(User.email).group_by(User.email).having(db.func.count(User.email) > 1).all()
            for (email,) in email_duplicates:
                duplicate_users = User.query.filter_by(email=email).order_by(User.id).all()
                # Mantém o primeiro, remove os demais
                for user in duplicate_users[1:]:
                    db.session.delete(user)
                    removed_count += 1
            
            # Remove duplicatas de CPF (mantém o mais antigo)
            cpf_duplicates = db.session.query(User.cpf).group_by(User.cpf).having(db.func.count(User.cpf) > 1).all()
            for (cpf,) in cpf_duplicates:
                if cpf:  # Ignora CPFs nulos
                    duplicate_users = User.query.filter_by(cpf=cpf).order_by(User.id).all()
                    # Mantém o primeiro, remove os demais
                    for user in duplicate_users[1:]:
                        db.session.delete(user)
                        removed_count += 1
            
            db.session.commit()
            flash(f"Limpeza concluída! {removed_count} registros duplicados removidos.")
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erro durante limpeza: {str(e)}")
        
        return redirect(url_for('admin_auth.cleanup_duplicates'))