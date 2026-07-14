import pygame
import json
import math
import time
import os

# Importando os outros módulos criados por você
from ia.analise import calcular_metricas
from dados.database import iniciar_banco, salvar_tentativa

# Inicialização
pygame.init()
pygame.font.init()
iniciar_banco() 

# Janela (Pode ser redimensionada futuramente para Mobile)
LARGURA, ALTURA = 800, 600
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("PlayDot")
relogio = pygame.time.Clock()

# Cores (Mantendo o padrão de baixo ruído visual para TEA)
COR_FUNDO = (245, 245, 245)
COR_GUIA = (210, 210, 210)
COR_RASTRO = (70, 130, 180)     
COR_INICIO = (46, 139, 87)      
COR_ALVO = (30, 144, 255)       
COR_TEXTO = (50, 50, 50)
COR_BOTAO = (220, 220, 220)
COR_BOTAO_HOVER = (180, 200, 220) # Cor quando o mouse passa por cima

fonte = pygame.font.SysFont("comic sans", 22)
fonte_titulo = pygame.font.SysFont("comic sans", 40, bold=True)

# Carregando Fases
caminho_json = os.path.join('dados', 'fases.json')
with open(caminho_json, 'r') as f:
    fases = json.load(f)

# Variáveis de Estado do Jogo
estado_jogo = "MENU" # Estados possíveis: "MENU", "JOGANDO", "OPCOES", "ESTATISTICAS"

# Variáveis do Jogo (Fases)
fase_atual_idx = 0
coordenadas_usuario = []
tempos_toque = []
desenhando = False
mensagem_status = "Conecte o ponto Verde ao Alvo Azul"

# --- FUNÇÕES DO MENU ---

def desenhar_menu():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    # 1. Título
    texto_titulo = fonte_titulo.render("PlayDot", True, COR_TEXTO)
    rect_titulo = texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.15))
    tela.blit(texto_titulo, rect_titulo)
    
    # 2. Configurações base dos botões (Largura, Altura)
    L_BTN, A_BTN = 250, 50
    
    # Criando os Retângulos espalhados pela altura da tela
    btn_jogar_rect = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_jogar_rect.center = (LARGURA // 2, ALTURA * 0.4)
    
    btn_opcoes_rect = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_opcoes_rect.center = (LARGURA // 2, ALTURA * 0.52)
    
    btn_estat_rect = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_estat_rect.center = (LARGURA // 2, ALTURA * 0.64)
    
    btn_sair_rect = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_sair_rect.center = (LARGURA // 2, ALTURA * 0.76)
    
    # Lista auxiliar para desenhar todos de uma vez usando um laço de repetição (Loop)
    botoes = [
        (btn_jogar_rect, "Iniciar Jogo"),
        (btn_opcoes_rect, "Opções"),
        (btn_estat_rect, "Estatísticas"),
        (btn_sair_rect, "Sair")
    ]
    
    # Aplica o efeito Hover individualmente
    for rect, texto in botoes:
        cor = COR_BOTAO_HOVER if rect.collidepoint(mouse_pos) else COR_BOTAO
        pygame.draw.rect(tela, cor, rect, border_radius=10)
        
        # Renderiza o texto centralizado no botão
        img_texto = fonte.render(texto, True, COR_TEXTO)
        rect_texto = img_texto.get_rect(center=rect.center)
        tela.blit(img_texto, rect_texto)
        
    # RETORNA OS 4 RETÂNGULOS
    return btn_jogar_rect, btn_opcoes_rect, btn_estat_rect, btn_sair_rect

def desenhar_tela_opcoes():
    """Desenha a tela de configurações/opções."""
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    # Título da página
    texto_titulo = fonte_titulo.render("Opções", True, COR_TEXTO)
    rect_titulo = texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.15))
    tela.blit(texto_titulo, rect_titulo)
    
    # Texto explicativo (exemplo de configuração que você pode adicionar)
    txt_config = fonte.render("Aqui você poderá configurar o volume ou a sensibilidade.", True, COR_TEXTO)
    rect_config = txt_config.get_rect(center=(LARGURA // 2, ALTURA * 0.4))
    tela.blit(txt_config, rect_config)
    
    # Botão "Voltar" (Posicionado no rodapé)
    btn_voltar_rect = pygame.Rect(0, 0, 200, 50)
    btn_voltar_rect.center = (LARGURA // 2, ALTURA * 0.8)
    
    cor = COR_BOTAO_HOVER if btn_voltar_rect.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor, btn_voltar_rect, border_radius=10)
    
    txt_voltar = fonte.render("Voltar ao Menu", True, COR_TEXTO)
    rect_txt_voltar = txt_voltar.get_rect(center=btn_voltar_rect.center)
    tela.blit(txt_voltar, rect_txt_voltar)
    
    return btn_voltar_rect


def desenhar_tela_estatisticas():
    """Desenha a tela de Estatísticas."""
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render("Estatísticas", True, COR_TEXTO)
    rect_titulo = texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.15))
    tela.blit(texto_titulo, rect_titulo)
    
    # Exemplo de texto informativo
    txt_info = fonte.render("Os dados de desempenho são salvos diretamente no seu MySQL.", True, COR_TEXTO)
    rect_info = txt_info.get_rect(center=(LARGURA // 2, ALTURA * 0.4))
    tela.blit(txt_info, rect_info)
    
    # Botão "Voltar"
    btn_voltar_rect = pygame.Rect(0, 0, 200, 50)
    btn_voltar_rect.center = (LARGURA // 2, ALTURA * 0.8)
    
    cor = COR_BOTAO_HOVER if btn_voltar_rect.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor, btn_voltar_rect, border_radius=10)
    
    txt_voltar = fonte.render("Voltar ao Menu", True, COR_TEXTO)
    rect_txt_voltar = txt_voltar.get_rect(center=btn_voltar_rect.center)
    tela.blit(txt_voltar, rect_txt_voltar)
    
    return btn_voltar_rect

# --- LOOP PRINCIPAL ---
rodando = True
while rodando:
    
    if estado_jogo == "MENU":
        # Renderiza o menu e captura os retângulos dos botões para checar o clique
        btn_jogar, btn_opções, btn_estat, btn_sair = desenhar_menu()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
                
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    if btn_jogar.collidepoint(evento.pos):
                        estado_jogo = "JOGANDO"
                    elif btn_opções.collidepoint(evento.pos):
                        estado_jogo = "OPCOES" 
                    elif btn_estat.collidepoint(evento.pos):
                        estado_jogo = "ESTATISTICAS" 
                    elif btn_sair.collidepoint(evento.pos):
                        rodando = False

   
    elif estado_jogo == "OPCOES":
        btn_voltar = desenhar_tela_opcoes()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    if btn_voltar.collidepoint(evento.pos):
                        estado_jogo = "MENU" 

    elif estado_jogo == "ESTATISTICAS":
        btn_voltar = desenhar_tela_estatisticas()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    if btn_voltar.collidepoint(evento.pos):
                        estado_jogo = "MENU" 
 
    # --- LÓGICA DO JOGO ---
    elif estado_jogo == "JOGANDO":
        fase = fases[fase_atual_idx]
        p_init = fase["ponto_inicio"]
        p_end = fase["ponto_fim"]
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
                
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    pos = evento.pos
                    dist_inicio = math.sqrt((pos[0] - p_init[0])**2 + (pos[1] - p_init[1])**2)
                    if dist_inicio <= 20: 
                        desenhando = True
                        coordenadas_usuario = [pos]
                        tempos_toque = [time.time()]
                        
            elif evento.type == pygame.MOUSEMOTION and desenhando:
                coordenadas_usuario.append(evento.pos)
                tempos_toque.append(time.time())
                
            elif evento.type == pygame.MOUSEBUTTONUP:
                if evento.button == 1 and desenhando:
                    desenhando = False
                    pos_final = evento.pos
                    dist_alvo = math.sqrt((pos_final[0] - p_end[0])**2 + (pos_final[1] - p_end[1])**2)
                    
                    if dist_alvo <= 25:
                        precisao, hesitacao = calcular_metricas(
                            fase["tipo"], p_init, p_end, 
                            fase.get("pontos_guia", []), 
                            coordenadas_usuario, tempos_toque
                        )
                        tempo_total = tempos_toque[-1] - tempos_toque[0] if tempos_toque else 0.0
                        
                        salvar_tentativa(fase["nome"], tempo_total, precisao, hesitacao)
                        
                        if precisao >= 70.0:
                            fase_atual_idx += 1
                            if fase_atual_idx < len(fases):
                                mensagem_status = "Muito bem! Gravado no MySQL. Indo para a próxima fase!"
                            else:
                                mensagem_status = "Excelente! Todas as fases concluídas e salvas!"
                                estado_jogo = "MENU" # Retorna ao menu ao acabar tudo
                                fase_atual_idx = 0 
                        else:
                            mensagem_status = f"Tentativa salva no BD. Precisão baixa ({precisao:.1f}%). Tente de novo!"
                        
                        coordenadas_usuario = []
                        tempos_toque = []
                    else:
                        mensagem_status = "Soltou fora do alvo! Tente de novo."
                        coordenadas_usuario = []
                        tempos_toque = []
                        
        # Renderização da Fase
        tela.fill(COR_FUNDO)
        pygame.draw.line(tela, COR_GUIA, p_init, p_end, 6)
        pygame.draw.circle(tela, COR_INICIO, p_init, 20)
        pygame.draw.circle(tela, COR_ALVO, p_end, 25)
        
        if len(coordenadas_usuario) > 1:
            pygame.draw.lines(tela, COR_RASTRO, False, coordenadas_usuario, 4)
            
        txt_status = fonte.render(mensagem_status, True, COR_TEXTO)
        tela.blit(txt_status, (20, 20))
        
        txt_fase = fonte.render(f"Fase: {fase['nome']}", True, COR_TEXTO)
        tela.blit(txt_fase, (20, ALTURA - 40))

    pygame.display.flip()
    relogio.tick(60)

pygame.quit()