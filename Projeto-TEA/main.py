import pygame
import json
import math
import time
import os

# Importando os outros módulos que criamos
from ia.analise import calcular_metricas
from dados.database import iniciar_banco, salvar_tentativa

# Inicialização
pygame.init()
pygame.font.init()
iniciar_banco() 

# Janela
LARGURA, ALTURA = 800, 600
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("PlayDot - Integrado com MySQL")
relogio = pygame.time.Clock()

# Cores (Baixo ruído visual)
COR_FUNDO = (245, 245, 245)
COR_GUIA = (210, 210, 210)
COR_RASTRO = (70, 130, 180)     
COR_INICIO = (46, 139, 87)      
COR_ALVO = (30, 144, 255)       
COR_TEXTO = (50, 50, 50)

fonte = pygame.font.SysFont("Arial", 22)

# Carregando Fases
caminho_json = os.path.join('dados', 'fases.json')
with open(caminho_json, 'r') as f:
    fases = json.load(f)

fase_atual_idx = 0
coordenadas_usuario = []
tempos_toque = []
desenhando = False
mensagem_status = "Clique no ponto VERDE e arraste até o AZUL"

# Loop do Jogo
rodando = True
while rodando:
    tela.fill(COR_FUNDO)
    
    fase = fases[fase_atual_idx]
    p_init = fase["ponto_inicio"]
    p_end = fase["ponto_fim"]
    
    # Desenha guias e rastros
    pygame.draw.line(tela, COR_GUIA, p_init, p_end, 5)
    if len(coordenadas_usuario) > 1:
        pygame.draw.lines(tela, COR_RASTRO, False, coordenadas_usuario, 6)
        
    pygame.draw.circle(tela, COR_INICIO, p_init, 20)
    pygame.draw.circle(tela, COR_ALVO, p_end, 20)
    
    # Textos
    txt_fase = fonte.render(f"Fase: {fase['nome']}", True, COR_TEXTO)
    txt_status = fonte.render(mensagem_status, True, COR_TEXTO)
    tela.blit(txt_fase, (20, 20))
    tela.blit(txt_status, (20, 550))

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False
            
        elif evento.type == pygame.MOUSEBUTTONDOWN:
            dist = math.sqrt((evento.pos[0] - p_init[0])**2 + (evento.pos[1] - p_init[1])**2)
            if dist < 45:
                desenhando = True
                coordenadas_usuario = [evento.pos]
                tempos_toque = [time.time()]
                mensagem_status = "Arrastando..."
                
        elif evento.type == pygame.MOUSEMOTION and desenhando:
            coordenadas_usuario.append(evento.pos)
            tempos_toque.append(time.time())
            
        elif evento.type == pygame.MOUSEBUTTONUP and desenhando:
            desenhando = False
            dist_fim = math.sqrt((evento.pos[0] - p_end[0])**2 + (evento.pos[1] - p_end[1])**2)
            
            if dist_fim < 45:
                # 1. Calcula as métricas com a IA estatística
                precisao, hesitacao = calcular_metricas(
                    fase["tipo"], p_init, p_end, 
                    fase.get("pontos_guia", []), 
                    coordenadas_usuario, tempos_toque
                )
                
                # 2. Calcula o tempo
                tempo_total = tempos_toque[-1] - tempos_toque[0] if tempos_toque else 0.0
                
                # 3. SALVA NO MYSQL LOCAL DO XAMPP
                salvar_tentativa(fase["nome"], tempo_total, precisao, hesitacao)
                
                # 4. Muda de fase ou avisa se a precisão foi baixa
                if precisao >= 70.0:
                    fase_atual_idx += 1
                    if fase_atual_idx < len(fases):
                        mensagem_status = f"Muito bem! Gravado no MySQL. Indo para a próxima fase!"
                    else:
                        mensagem_status = "Excelente! Todas as fases concluídas e salvas!"
                        fase_atual_idx = 0 
                else:
                    mensagem_status = f"Tentativa salva no BD. Precisão baixa ({precisao:.1f}%). Tente de novo!"
                
                coordenadas_usuario = []
                tempos_toque = []
            else:
                mensagem_status = "Soltou fora do alvo! Tente de novo."
                coordenadas_usuario = []
                tempos_toque = []

    pygame.display.flip()
    relogio.tick(60)

pygame.quit()