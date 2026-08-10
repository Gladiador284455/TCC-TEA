import math
import random

LARGURA_TELA, ALTURA_TELA = 800, 600

def gerar_fase_por_angulo(id_fase, angulo_graus, comprimento=400):

    x_init = 150
    y_init = 300
    
    angulo_rad = math.radians(angulo_graus)
    
    x_end = int(x_init + comprimento * math.cos(angulo_rad))
    y_end = int(y_init - comprimento * math.sin(angulo_rad))
    
    x_end = max(100, min(x_end, 700))
    y_end = max(100, min(y_end, 500))
    
    return {
        "id": id_fase,
        "nome": f"Fase Adaptativa - Angulo {angulo_graus}°",
        "tipo": "reta",
        "angulo": angulo_graus,
        "ponto_inicio": [x_init, y_init],
        "ponto_fim": [x_end, y_end],
        "pontos_guia": []
    }

def calcular_proximo_passo(precisao_anterior, angulo_atual):
    """
    - Acima de 60%: Progride (+5° de inclinação)
    - Entre 50% e 59%: Repete o mesmo ângulo
    - Abaixo de 50% (mas >= 30%): Volta 1 nível (-5° de inclinação)
    - Abaixo de 30%: Volta 2 níveis (-10° de inclinação)
    """
    if precisao_anterior >= 60.0:
        # Prossegue para a próxima: aumenta o ângulo em 5 graus (máximo)
        novo_angulo = angulo_atual + 5
        status = "AVANCAR"
    elif 50.0 <= precisao_anterior < 60.0:
        # Repete a fase atual
        novo_angulo = angulo_atual
        status = "REPETIR"
    elif 30.0 <= precisao_anterior < 50.0:
        # Volta uma fase (reduz 5 graus)
        novo_angulo = max(0, angulo_atual - 5)
        status = "VOLTAR_UMA"
    else: # Volta duas fases (reduz 10 graus)
        novo_angulo = max(0, angulo_atual - 10)
        status = "VOLTAR_DUAS"
        
    return novo_angulo, status