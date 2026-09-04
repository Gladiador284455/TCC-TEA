import math

LARGURA_TELA, ALTURA_TELA = 800, 600

import math

def gerar_fase_por_angulo(id_fase, angulo_deg, largura_original=1280, altura_original=720):
    margem_esquerda = 80
    y_centro = altura_original // 2

    comprimento = largura_original - (margem_esquerda * 2)

    rad = math.radians(angulo_deg)

    dx = (comprimento / 2) * math.cos(rad)
    dy = (comprimento / 2) * math.sin(rad)

    x_centro = margem_esquerda + (comprimento / 2)

    ponto_inicio = (int(x_centro - dx), int(y_centro + dy))
    ponto_fim = (int(x_centro + dx), int(y_centro - dy))

    return {
        "id": id_fase,
        "nome": f"Fase Ângulo {angulo_deg}°",
        "tipo": "reta",
        "ponto_inicio": ponto_inicio,
        "ponto_fim": ponto_fim,
        "pontos_guia": [ponto_inicio, ponto_fim]
    }

def calcular_proximo_passo(precisao_anterior, angulo_atual):
    """
    Determina o próximo ângulo com base no desempenho do usuário.
    """
    if precisao_anterior >= 60.0:
        novo_angulo = min(90, angulo_atual + 5)
        status = "AVANCAR"
    elif 50.0 <= precisao_anterior < 60.0:
        novo_angulo = angulo_atual
        status = "REPETIR"
    elif 30.0 <= precisao_anterior < 50.0:
        novo_angulo = max(0, angulo_atual - 5)
        status = "VOLTAR_UMA"
    else:
        novo_angulo = max(0, angulo_atual - 10)
        status = "VOLTAR_DUAS"
        
    return novo_angulo, status


def calcular_distancia_ponto_segmento(ponto, p1, p2):
    """
    Função auxiliar para calcular a menor distância entre o traço do usuário
    e a reta exata calculada pelo ângulo (usada dentro de calcular_metricas).
    """
    x0, y0 = ponto
    x1, y1 = p1
    x2, y2 = p2
    
    dx = x2 - x1
    dy = y2 - y1
    
    if dx == 0 and dy == 0:
        return math.hypot(x0 - x1, y0 - y1)
        
    t = ((x0 - x1) * dx + (y0 - y1) * dy) / float(dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    
    return math.hypot(x0 - proj_x, y0 - proj_y)