import pygame
import json
import math
import time
import os

# Importando os outros módulos criados por você
from ia.analise import calcular_metricas
from dados.database import iniciar_banco, salvar_tentativa, obter_ultimas_tentativas

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

# --- SISTEMA DE GERAÇÃO E ADAPTAÇÃO PROCEDURAL DE FASES ---

def gerar_fase_por_angulo(id_fase, angulo_graus, comprimento=550):
    """
    Gera dinamicamente uma fase baseada em um ângulo, mantendo a reta
    perfeitamente centralizada na tela de 800x600.
    """
    # Centro da tela
    centro_x = 400
    centro_y = 300
    
    # Conversão do ângulo para radianos
    angulo_rad = math.radians(angulo_graus)
    
    # Metade do comprimento para cada lado a partir do centro
    metade_comp = comprimento / 2
    
    # Calcula o deslocamento em X e Y usando cosseno e seno
    dx = metade_comp * math.cos(angulo_rad)
    dy = metade_comp * math.sin(angulo_rad)
    
    # Ponto inicial (esquerda/baixo) e Ponto final (direita/cima)
    # Subtraímos o dy no ponto final para a linha "subir" no Pygame
    x_init = int(centro_x - dx)
    y_init = int(centro_y + dy)
    
    x_end = int(centro_x + dx)
    y_end = int(centro_y - dy)
    
    # Garante limites de segurança para os círculos não encostarem nas bordas extremas
    x_init = max(50, min(x_init, 750))
    y_init = max(50, min(y_init, 550))
    x_end = max(50, min(x_end, 750))
    y_end = max(50, min(y_end, 550))
    
    return {
        "id": id_fase,
        "nome": f"Fase Adaptativa - Angulo {angulo_graus}graus",
        "tipo": "reta",
        "angulo": angulo_graus,
        "ponto_inicio": [x_init, y_init],
        "ponto_fim": [x_end, y_end],
        "pontos_guia": []
    }

def calcular_proximo_passo(precisao_anterior, angulo_atual):
    """
    Aplica as regras do time de pesquisa:
    - Abaixo de 30%: Volta duas fases (máximo 10°)
    - De 30% a 49%: Volta uma fase (máximo 5°)
    - De 50% a 59%: Repete a fase atual
    - 60% ou mais: Avança para a próxima (+5°)
    """
    if precisao_anterior >= 60.0:
        novo_angulo = min(45, angulo_atual + 2.5) # Limita a 45 graus (diagonal)
        status = "AVANCAR"
    elif 50.0 <= precisao_anterior < 60.0:
        novo_angulo = angulo_atual
        status = "REPETIR"
    elif 30.0 <= precisao_anterior < 50.0:
        novo_angulo = max(0, angulo_atual - 2.5)
        status = "VOLTAR_UMA"
    else: # Abaixo de 30%
        novo_angulo = max(0, angulo_atual - 5)
        status = "VOLTAR_DUAS"
        
    return novo_angulo, status

# Variáveis de Estado do Jogo
estado_jogo = "MENU" # Estados possíveis: "MENU", "JOGANDO", "OPCOES", "ESTATISTICAS"

# Controle das Fases Dinâmicas
angulo_atual = 0  # Inicia em 0 graus (reta perfeitamente horizontal)
id_fase_dinamica = 1
fase_atual = gerar_fase_por_angulo(id_fase_dinamica, angulo_atual)

# Variáveis de Traçado do Usuário
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
    """Desenha a tela de Estatísticas com dados dinâmicos recuperados do MySQL."""
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    # Título da página
    texto_titulo = fonte_titulo.render("Estatísticas de Desempenho", True, COR_TEXTO)
    rect_titulo = texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.12))
    tela.blit(texto_titulo, rect_titulo)
    
    # Busca tentativas no MySQL de forma segura
    try:
        dados = obter_ultimas_tentativas(5)
    except Exception:
        dados = []

    # Cabeçalho da Tabela
    colunasY = int(ALTURA * 0.25)
    titulos_colunas = ["Fase", "Tempo", "Precisão", "Taxa de Erro"]
    posicoes_x = [50, 300, 480, 640]
    
    for i, col_nome in enumerate(titulos_colunas):
        txt_col = fonte.render(col_nome, True, COR_TEXTO)
        tela.blit(txt_col, (posicoes_x[i], colunasY))
        
    pygame.draw.line(tela, COR_GUIA, (50, colunasY + 30), (750, colunasY + 30), 2)
    
    # Exibe linhas de estatísticas
    if not dados:
        txt_vazio = fonte.render("Sem dados gravados ou MySQL inativo.", True, (150, 150, 150))
        tela.blit(txt_vazio, (50, colunasY + 60))
    else:
        distancia_linha = 40
        for idx, registro in enumerate(dados):
            linhaY = colunasY + 50 + (idx * distancia_linha)
            
            nome_fase = registro[0]
            tempo = f"{registro[1]:.1f}s"
            precisao_val = registro[2]
            precisao = f"{precisao_val:.1f}%"
            taxa_erro_val = 100.0 - precisao_val
            taxa_erro = f"{taxa_erro_val:.1f}%"
            
            if len(nome_fase) > 18:
                nome_fase = nome_fase[:15] + "..."
                
            tela.blit(fonte.render(nome_fase, True, COR_TEXTO), (posicoes_x[0], linhaY))
            tela.blit(fonte.render(tempo, True, COR_TEXTO), (posicoes_x[1], linhaY))
            tela.blit(fonte.render(precisao, True, COR_TEXTO), (posicoes_x[2], linhaY))
            
            # Pinta a taxa de erro de vermelho se estiver muito alta (acima de 30%)
            cor_erro = (180, 50, 50) if taxa_erro_val > 30.0 else COR_TEXTO
            tela.blit(fonte.render(taxa_erro, True, cor_erro), (posicoes_x[3], linhaY))

    # Botão "Voltar"
    btn_voltar_rect = pygame.Rect(0, 0, 200, 50)
    btn_voltar_rect.center = (LARGURA // 2, ALTURA * 0.88)
    
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
        btn_jogar, btn_opcoes, btn_estat, btn_sair = desenhar_menu()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
                
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    if btn_jogar.collidepoint(evento.pos):
                        estado_jogo = "JOGANDO"
                    elif btn_opcoes.collidepoint(evento.pos):
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
 
    # --- LÓGICA DO JOGO (ADAPTATIVA) ---
    elif estado_jogo == "JOGANDO":
        p_init = fase_atual["ponto_inicio"]
        p_end = fase_atual["ponto_fim"]
        
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
                        # 1. Calcula as estatísticas
                        precisao, hesitacao = calcular_metricas(
                            fase_atual["tipo"], p_init, p_end, 
                            fase_atual.get("pontos_guia", []), 
                            coordenadas_usuario, tempos_toque
                        )
                        tempo_total = tempos_toque[-1] - tempos_toque[0] if tempos_toque else 0.0
                        
                        # 2. Salva no MySQL
                        salvar_tentativa(fase_atual["nome"], tempo_total, precisao, hesitacao)
                        
                        # 3. Processa o algoritmo de Adaptação com base na precisão
                        novo_angulo, status = calcular_proximo_passo(precisao, angulo_atual)
                        
                        if status == "AVANCAR":
                            angulo_atual = novo_angulo
                            id_fase_dinamica += 1
                            mensagem_status = f"Muito bem! Precisão: {precisao:.1f}%. Avançou para o ângulo {angulo_atual}°!"
                        elif status == "REPETIR":
                            mensagem_status = f"Quase lá! Precisão: {precisao:.1f}%. Vamos repetir para treinar!"
                        elif status == "VOLTAR_UMA":
                            angulo_atual = novo_angulo
                            id_fase_dinamica = max(1, id_fase_dinamica - 1)
                            mensagem_status = f"Foco! Precisão: {precisao:.1f}%. Voltamos 1 nível para ajudar."
                        elif status == "VOLTAR_DUAS":
                            angulo_atual = novo_angulo
                            id_fase_dinamica = max(1, id_fase_dinamica - 2)
                            mensagem_status = f"Foco! Precisão: {precisao:.1f}%. Voltamos 2 níveis para praticar."
                        
                        # 4. Gera a nova fase com o ângulo ajustado
                        fase_atual = gerar_fase_por_angulo(id_fase_dinamica, angulo_atual)
                        
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
        
        txt_fase = fonte.render(f"Fase: {fase_atual['nome']}", True, COR_TEXTO)
        tela.blit(txt_fase, (20, ALTURA - 40))

    pygame.display.flip()
    relogio.tick(60)

pygame.quit()