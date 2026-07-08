import math

def calcular_metricas(tipo_fase, p_init, p_end, pontos_guia, coordenadas_usuario, tempos_toque):
    if not coordenadas_usuario or len(coordenadas_usuario) < 2:
        return 0.0, 0.0

    desvios = []
    
    # 1. Cálculo do Desvio Vetorial
    for x_u, y_u in coordenadas_usuario:
        if tipo_fase == "reta":
            num = abs((p_end[1] - p_init[1]) * x_u - (p_end[0] - p_init[0]) * y_u + p_end[0] * p_init[1] - p_end[1] * p_init[0])
            den = math.sqrt((p_end[1] - p_init[1]) ** 2 + (p_end[0] - p_init[0]) ** 2)
            distancia = num / den if den > 0 else 0
        else:
            distancia = min([math.sqrt((x_u - pg[0])**2 + (y_u - pg[1])**2) for pg in pontos_guia])
            
        desvios.append(distancia)
            
    desvio_medio = sum(desvios) / len(desvios) if desvios else 100
    precisao = max(0.0, 100.0 - (desvio_medio * 2.5))

    # 2. Índice de Hesitação (Variação de velocidade)
    velocidades = []
    for i in range(1, len(coordenadas_usuario)):
        dist = math.sqrt((coordenadas_usuario[i][0] - coordenadas_usuario[i-1][0])**2 + 
                         (coordenadas_usuario[i][1] - coordenadas_usuario[i-1][1])**2)
        dt = tempos_toque[i] - tempos_toque[i-1]
        if dt > 0:
            velocidades.append(dist / dt)
            
    if velocidades:
        media_vel = sum(velocidades) / len(velocidades)
        variancia = sum((v - media_vel) ** 2 for v in velocidades) / len(velocidades)
        indice_hesitacao = math.sqrt(variancia)
    else:
        indice_hesitacao = 0.0

    return precisao, indice_hesitacao