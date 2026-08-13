import sqlite3
import os
from datetime import datetime

# Localiza a pasta raiz do projeto (onde projeto_tea.sql ou este módulo está localizado)
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))

# Se este arquivo estiver dentro de uma subpasta (ex: 'dados/database.py'), 
# desce um nível para salvar o banco na raiz. Se estiver na raiz, usa a própria pasta.
NOME_ARQUIVO = "dados_playdot.db"

# Procura a pasta do projeto (onde está o arquivo projeto_tea.sql)
pasta_raiz = DIRETORIO_ATUAL
if os.path.exists(os.path.join(DIRETORIO_ATUAL, "..", "projeto_tea.sql")):
    pasta_raiz = os.path.abspath(os.path.join(DIRETORIO_ATUAL, ".."))
elif os.path.exists(os.path.join(DIRETORIO_ATUAL, "projeto_tea.sql")):
    pasta_raiz = DIRETORIO_ATUAL

CAMINHO_BANCO = os.path.join(pasta_raiz, NOME_ARQUIVO)

def obter_conexao():
    """Conecta ao arquivo de banco de dados SQLite local no diretório especificado."""
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

def iniciar_banco():
    """Cria o arquivo do banco na mesma pasta e as tabelas caso ainda não existam."""
    conn = obter_conexao()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tentativas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fase TEXT,
            timestamp TEXT,
            tempo_execucao REAL,
            precisao REAL,
            indice_hesitacao REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS criancas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            nascimento TEXT,
            sexo TEXT,
            obs TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def salvar_tentativa(fase, tempo, precisao, hesitacao):
    conn = obter_conexao()
    cursor = conn.cursor()
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO tentativas (fase, timestamp, tempo_execucao, precisao, indice_hesitacao)
        VALUES (?, ?, ?, ?, ?)
    ''', (fase, agora, tempo, precisao, hesitacao))
    
    conn.commit()
    conn.close()

def obter_ultimas_tentativas(limite=5):
    conn = obter_conexao()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT fase, tempo_execucao, precisao, indice_hesitacao 
        FROM tentativas 
        ORDER BY id DESC 
        LIMIT ?
    ''', (limite,))
    
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def salvar_crianca(nome, nascimento, sexo, obs):
    conn = obter_conexao()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO criancas (nome, nascimento, sexo, obs) VALUES (?, ?, ?, ?)",
        (nome, nascimento, sexo, obs)
    )
    
    conn.commit()
    conn.close()

def obter_criancas():
    conn = obter_conexao()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, nome, nascimento, sexo, obs FROM criancas")
    linhas = cursor.fetchall()
    
    resultados = [dict(linha) for linha in linhas]
    
    conn.close()
    return resultados


"""Deleta uma criança do banco de dados pelo ID"""
def deletar_crianca(id_crianca):
    import sqlite3
    conn = sqlite3.connect('dados/playdot.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM criancas WHERE id = ?", (id_crianca,))
    conn.commit()
    conn.close()
    return True