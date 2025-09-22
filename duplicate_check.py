from flask import jsonify, request
from models import User

def check_duplicates_api():
    """API para verificar duplicatas em tempo real"""
    email = request.args.get('email', '').strip().lower()
    cpf = request.args.get('cpf', '').strip()
    
    # Remove formatação do CPF
    cpf_clean = ''.join(filter(str.isdigit, cpf))
    
    result = {
        'email_exists': False,
        'cpf_exists': False,
        'can_register': True
    }
    
    if email:
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            result['email_exists'] = True
            result['can_register'] = False
    
    if cpf_clean and len(cpf_clean) == 11:
        # Verifica CPF formatado e limpo
        from utils import format_cpf
        try:
            cpf_formatted = format_cpf(cpf_clean)
            existing_cpf = User.query.filter_by(cpf=cpf_formatted).first()
            if not existing_cpf:
                existing_cpf = User.query.filter_by(cpf=cpf_clean).first()
            
            if existing_cpf:
                result['cpf_exists'] = True
                result['can_register'] = False
        except:
            pass
    
    return jsonify(result)