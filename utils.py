import re

def validate_cpf(cpf):
    """
    Valida um CPF brasileiro
    Retorna True se o CPF for válido, False caso contrário
    """
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais (CPF inválido)
    if cpf == cpf[0] * 11:
        return False
    
    # Cálculo do primeiro dígito verificador
    sum1 = 0
    for i in range(9):
        sum1 += int(cpf[i]) * (10 - i)
    
    digit1 = (sum1 * 10) % 11
    if digit1 == 10:
        digit1 = 0
    
    # Verifica o primeiro dígito
    if digit1 != int(cpf[9]):
        return False
    
    # Cálculo do segundo dígito verificador
    sum2 = 0
    for i in range(10):
        sum2 += int(cpf[i]) * (11 - i)
    
    digit2 = (sum2 * 10) % 11
    if digit2 == 10:
        digit2 = 0
    
    # Verifica o segundo dígito
    if digit2 != int(cpf[10]):
        return False
    
    return True

def format_cpf(cpf):
    """
    Formata um CPF no padrão 000.000.000-00
    """
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf

def clean_cpf(cpf):
    """
    Remove formatação do CPF, mantendo apenas números
    """
    return re.sub(r'[^0-9]', '', cpf) if cpf else ""