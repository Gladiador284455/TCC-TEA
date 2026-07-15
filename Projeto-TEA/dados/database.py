import mysql.connector
from datetime import datetime

def obter_conexao():
    """Estabelece a ligação direta com o banco de dados MySQL."""
    return mysql.connector.connect(
        host="localhost",       # No mobile, substituirá pelo IP do servidor cloud
        user="root",            # Utilizador padrão do XAMPP
        password="",            # Senha padrão do XAMPP (vazia)
        database="projeto_tea"
    )

def iniciar_banco():
    """Cria a tabela de tentativas caso ela ainda não exista no sistema."""
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
    """Grava os resultados analíticos da sessão da criança no MySQL."""
    conn = obter_conexao()
    cursor = conn.cursor()
    
    comando = '''
        INSERT INTO tentativas (fase, timestamp, tempo_execucao, precisao, indice_hesitacao)
        VALUES (%s, %s, %s, %s, %s)
    '''
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    dados = (fase, agora, tempo, precisao, hesitacao)
    
    cursor.execute(comando, dados)
    conn.commit()
    cursor.close()
    conn.close()

def obter_ultimas_tentativas(limite=5):
    """Busca as últimas tentativas salvas no banco de dados para exibir na interface."""
    conn = obter_conexao()
    cursor = conn.cursor()
    
    comando = '''
        SELECT fase, tempo_execucao, precisao, indice_hesitacao 
        FROM tentativas 
        ORDER BY id DESC 
        LIMIT %s
    '''
    cursor.execute(comando, (limite,))
    resultados = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return resultados