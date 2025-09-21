from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password = db.Column(db.String(150), nullable=False)
    # Perfil
    name = db.Column(db.String(150))  # Nome completo
    cpf = db.Column(db.String(14), unique=True, index=True)  # 000.000.000-00 ou somente dígitos
    city = db.Column(db.String(120))
    state = db.Column(db.String(2))   # UF (ex.: SP, RJ)
    # Endereço
    cep = db.Column(db.String(9), index=True)  # 00000-000
    address = db.Column(db.String(200))        # Logradouro (ex.: Rua X)
    number = db.Column(db.String(20))          # Número
    complement = db.Column(db.String(100))     # Complemento
    neighborhood = db.Column(db.String(120))   # Bairro

    questions = db.relationship('Question', backref='user', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
