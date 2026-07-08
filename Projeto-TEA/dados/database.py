import mysql.connector
from datetime import datetime

def obter_conexao():
    """Conecta diretamente ao banco de dados projeto_tea que você criou no XAMPP."""
    return mysql.connector.connect(
        host="localhost",
        user="root",       # Usuário padrão do XAMPP
        password="",       # Senha padrão do XAMPP (em branco)
        database="projeto_tea"
    )

def iniciar_banco():
    """Cria a tabela onde serão salvas as tentativas da criança, caso ela não exista."""
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tentativas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fase VARCHAR(100),
            timestamp DATETIME,
            tempo_execucao FLOAT,
            precisao FLOAT,
            indice_hesitacao FLOAT
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def salvar_tentativa(fase, tempo, precisao, hesitacao):
    """Grava os resultados da sessão no MySQL."""
    conn = obter_conexao()
    cursor = conn.cursor()
    
    comando = '''
        INSERT INTO tentativas (fase, timestamp, tempo_execucao, precisao, indice_hesitacao)
        VALUES (%s, %s, %s, %s, %s)
    '''
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    valores = (fase, agora, tempo, precisao, hesitacao)
    
    cursor.execute(comando, valores)
    conn.commit()
    cursor.close()
    conn.close()