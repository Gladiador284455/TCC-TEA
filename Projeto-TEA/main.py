import pygame
import math
import time
import os
import json

# Importando os módulos atualizados do projeto
from algoritmo.analise import calcular_metricas
from algoritmo.controle_fases import gerar_fase_por_angulo, calcular_proximo_passo
from dados.database import (
    iniciar_banco, 
    salvar_tentativa, 
    obter_ultimas_tentativas, 
    salvar_crianca, 
    obter_criancas,
    remover_crianca,
    obter_desempenho_crianca
)

# Inicialização do Pygame
pygame.init()
pygame.font.init()
pygame.mixer.init()

# Inicializa o banco SQLite offline
lista_criancas = []
try:
    iniciar_banco()
    db_ativo = True
    lista_criancas = obter_criancas()
except Exception as e:
    print(f"Aviso: Erro ao iniciar banco local. Erro: {e}")
    db_ativo = False

# ==========================================
#  SISTEMA DE RESOLUÇÃO VIRTUAL & ESCALA
# ==========================================
LARGURA_ORIGINAL, ALTURA_ORIGINAL = 1280, 720
LARGURA, ALTURA = 1280, 720

# Janela física (redimensionável)
tela_real = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
pygame.display.set_caption("PlayDot")

# Canvas virtual (onde todo o jogo é desenhado no tamanho original)
tela = pygame.Surface((LARGURA_ORIGINAL, ALTURA_ORIGINAL))
relogio = pygame.time.Clock()

def obter_parametros_escala():
    """Calcula a proporção, deslocamentos (offsets) e retângulo do canvas virtual na tela real."""
    largura_real, altura_real = tela_real.get_size()
    escala = min(largura_real / LARGURA_ORIGINAL, altura_real / ALTURA_ORIGINAL)
    
    nova_largura = int(LARGURA_ORIGINAL * escala)
    nova_altura = int(ALTURA_ORIGINAL * escala)
    
    offset_x = (largura_real - nova_largura) // 2
    offset_y = (altura_real - nova_altura) // 2
    
    rect_destino = pygame.Rect(offset_x, offset_y, nova_largura, nova_altura)
    return escala, offset_x, offset_y, rect_destino

def converter_pos_mouse(pos_real):
    """Converte a posição física do clique do mouse para as coordenadas da tela virtual."""
    escala, offset_x, offset_y, _ = obter_parametros_escala()
    x_real, y_real = pos_real
    
    x_virtual = (x_real - offset_x) / escala
    y_virtual = (y_real - offset_y) / escala
    
    return int(x_virtual), int(y_virtual)

def truncar_texto(texto, fonte, largura_maxima):
    if fonte.size(texto)[0] <= largura_maxima:
        return texto
    
    texto_truncado = texto
    while texto_truncado and fonte.size(texto_truncado + "...")[0] > largura_maxima:
        texto_truncado = texto_truncado[:-1]
        
    return texto_truncado + "..." if texto_truncado else "..."

# ==========================================
#  PALETA DE CORES
# ==========================================
COR_FUNDO = (217, 249, 252)
COR_GUIA = (210, 210, 210)
COR_INICIO = (140, 184, 122)
COR_ALVO = (246, 141, 141)
COR_DESTAQUE = (255, 212, 112)
COR_TEXTO = (50, 50, 50)
COR_BOTAO = (255, 255, 255)
COR_BOTAO_HOVER = (255, 212, 112)
COR_INPUT_ATIVO = (125, 193, 200)
COR_BRANCO = (255, 255, 255)

OPCOES_CORES_TRACADO = {
    "Verde": (140, 184, 122),
    "Azul": (125, 193, 200),
    "Rosa": (246, 141, 141),
    "Amarelo": (255, 212, 112)
}

# ==========================================
#  CARREGAMENTO DE FONTES
# ==========================================
NOME_FONTE_COINY = os.path.join("assets", "fontes", "Coiny-Regular.ttf")
NOME_FONTE_MPLUS = os.path.join("assets", "fontes", "MPLUS1p-Regular.ttf")

if os.path.exists(NOME_FONTE_MPLUS):
    fonte = pygame.font.Font(NOME_FONTE_MPLUS, 22)
else:
    fonte = pygame.font.SysFont("MPLUS 1p", 22)

if os.path.exists(NOME_FONTE_COINY):
    fonte_titulo = pygame.font.Font(NOME_FONTE_COINY, 36)
    font_campo = pygame.font.Font(NOME_FONTE_COINY, 18)
else:
    fonte_titulo = pygame.font.SysFont("coiny", 36, bold=True)
    font_campo = pygame.font.SysFont("coiny", 18)

# ==========================================
#  PERSISTÊNCIA DE CONFIGURAÇÕES
# ==========================================
ARQUIVO_CONFIG = os.path.join("dados", "config.json")

def carregar_configuracoes():
    configs_padrao = {
        "ruido": "Baixo",
        "pin": "0000",
        "config_criancas": {}
    }
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                dados_salvos = json.load(f)
                configs_padrao.update(dados_salvos)
        except Exception as e:
            print(f"Erro ao carregar configurações salvas: {e}")
    return configs_padrao

def salvar_configuracoes(configs):
    try:
        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump(configs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar configurações no arquivo: {e}")

# ==========================================
#  CARREGAMENTO DE SONS
# ==========================================
CAMINHO_RUIDO = os.path.join("assets", "sons", "ruido.mp3")

if os.path.exists(CAMINHO_RUIDO):
    try:
        som_ruido = pygame.mixer.Sound(CAMINHO_RUIDO)
        som_ruido.set_volume(0.3)
    except Exception as e:
        print(f"Erro ao carregar o som: {e}")
        som_ruido = None
else:
    som_ruido = None
    print("Aviso: arquivo de ruído não encontrado.")

def ajustar_volume_ruido(nivel):
    global som_ruido
    if som_ruido:
        volumes = {
            "Baixo": 0.15,
            "Médio": 0.4
        }
        volume = volumes.get(nivel, 0.3)
        som_ruido.set_volume(volume)
        print(f" Volume do ruído ajustado para: {nivel}")

# ==========================================
#  CARREGAMENTO DE ÍCONES
# ==========================================
TAMANHO_ICONE = (50, 50)

def carregar_e_dimensionar(caminho, tamanho=TAMANHO_ICONE):
    if os.path.exists(caminho):
        try:
            img = pygame.image.load(caminho).convert_alpha()
            return pygame.transform.smoothscale(img, tamanho)
        except Exception as e:
            print(f"Erro ao carregar imagem {caminho}: {e}")
    return None

LARGURA_LOGO, ALTURA_LOGO = 400, 400

icones = {
    "Logotipo": carregar_e_dimensionar(
        os.path.join("assets", "imagens", "Logotipo.png"),
        (LARGURA_LOGO, ALTURA_LOGO)
    ),
    "Cão": carregar_e_dimensionar(os.path.join("assets", "imagens", "Cão.png")),
    "Casinha": carregar_e_dimensionar(os.path.join("assets", "imagens", "Casinha.png"))
}

# ==========================================
#  VARIÁVEIS GLOBAIS DE ESTADO
# ==========================================
estado_jogo = "MENU_RESPONSAVEL"
destino_apos_pin = "MENU_RESPONSAVEL"

pin_digitado = ""
mensagem_erro_pin = ""
crianca_selecionada = None
crianca_config_selecionada = None

input_cadastro = {"nome": "", "nascimento": "", "sexo": "Masculino", "obs": ""}
campo_ativo = None

configs_jogo = carregar_configuracoes()
campo_config_ativo = None
temp_pin_novo = ""

# Controle do Carrossel de Crianças
pagina_menu_crianca = 0
CRIANCAS_POR_PAGINA_MENU = 6

pagina_crianca_config = 0
CRIANCAS_POR_PAGINA = 3

# Estado do Som por Criança
som_temp = True

# Modal de Exclusão
modal_excluir_ativo = False
crianca_para_excluir = None

cor_tracado_temp = "Azul"
ruido_temp = "Baixo"

# Estado da Execução do Jogo
TOTAL_TENTATIVAS = 5
tentativa_atual = 0
sucessos_fase_atual = 0
angulo_fase_atual = 0.0
cor_tracado_atual = "Azul"
nome_inicio = "Cão"
nome_fim = "Casinha"

ponto_inicio = (100, ALTURA_ORIGINAL // 2)
ponto_alvo = (LARGURA_ORIGINAL - 100, ALTURA_ORIGINAL // 2)
pontos_desenhados = []

VOLUMES_RUIDO = {
    "Baixo": 0.2,
    "Médio": 0.5,
}

LIMITE_ANGULO_MAXIMO = 30.0
angulo_atual = 0.0
id_fase_dinamica = 1

tentativas_precisoes = []
tentativa_atual_num = 1

jogo_finalizado = False
coordenadas_usuario = []
tempos_toque = []
coordenadas_salvas_para_desenho = []
desenhando = False
mensagem_status = "Conecte o mascote à Casinha!"

# Estado da Tela de Estatísticas
crianca_estatistica_selecionada = None
angulos_expandidos = {}  
scroll_y_estatisticas = 0  
LISTA_ANGULOS = [round(i * 1.5, 1) for i in range(21)]  

scroll_x_criancas = 0

# ==========================================
#  FUNÇÕES AUXILIARES
# ==========================================

def desenhar_linha_pontilhada(superficie, cor, inicio, fim, largura=4, comp_traco=12, espaco=8):
    x1, y1 = inicio
    x2, y2 = fim
    distancia = math.hypot(x2 - x1, y2 - y1)
    if distancia == 0:
        return
    
    dx = (x2 - x1) / distancia
    dy = (y2 - y1) / distancia
    
    comprimento_total = comp_traco + espaco
    num_passos = int(distancia // comprimento_total)
    
    for i in range(num_passos + 1):
        p1_x = x1 + dx * (i * comprimento_total)
        p1_y = y1 + dy * (i * comprimento_total)
        p2_x = x1 + dx * min(i * comprimento_total + comp_traco, distancia)
        p2_y = y1 + dy * min(i * comprimento_total + comp_traco, distancia)
        pygame.draw.line(superficie, cor, (int(p1_x), int(p1_y)), (int(p2_x), int(p2_y)), largura)

def desenhar_rastro_tracejada(superficie, cor, pontos, largura=5, comp_traco=10, espaco=6):
    if len(pontos) < 2:
        return

    dist_acumulada = 0.0
    desenhando_segmento = True
    
    for i in range(len(pontos) - 1):
        p1 = pontos[i]
        p2 = pontos[i + 1]
        dist_seg = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if dist_seg == 0:
            continue
            
        dx = (p2[0] - p1[0]) / dist_seg
        dy = (p2[1] - p1[1]) / dist_seg
        
        progresso_seg = 0.0
        while progresso_seg < dist_seg:
            limite_fase = comp_traco if desenhando_segmento else espaco
            restante_fase = limite_fase - dist_acumulada
            passo = min(restante_fase, dist_seg - progresso_seg)
            
            p_inicio_sub = (p1[0] + dx * progresso_seg, p1[1] + dy * progresso_seg)
            progresso_seg += passo
            p_fim_sub = (p1[0] + dx * progresso_seg, p1[1] + dy * progresso_seg)
            
            if desenhando_segmento:
                pygame.draw.line(superficie, cor, p_inicio_sub, p_fim_sub, largura)
                
            dist_acumulada += passo
            if dist_acumulada >= limite_fase:
                dist_acumulada = 0.0
                desenhando_segmento = not desenhando_segmento

def renderizar_texto_com_scroll(texto_completo, prefixo, largura_maxima_util, rect_x, rect_y):
    img_prefixo = font_campo.render(prefixo, True, COR_TEXTO)
    largura_prefixo = img_prefixo.get_width()
    
    largura_disponivel_texto = largura_maxima_util - largura_prefixo - 20
    texto_com_cursor = texto_completo + "|"
    
    texto_visivel = texto_com_cursor
    for i in range(len(texto_com_cursor) + 1):
        texto_visivel = texto_com_cursor[i:]
        img_teste = font_campo.render(texto_visivel, True, COR_TEXTO)
        if img_teste.get_width() <= largura_disponivel_texto:
            break
            
    tela.blit(img_prefixo, (rect_x + 10, rect_y + 10))
    img_texto_final = font_campo.render(texto_visivel, True, COR_TEXTO)
    tela.blit(img_texto_final, (rect_x + 10 + largura_prefixo, rect_y + 10))

def formatar_e_validar_data(texto_atual, novo_char):
    apenas_numeros = "".join([c for c in texto_atual if c.isdigit()])
    if novo_char.isdigit():
        apenas_numeros += novo_char
    if len(apenas_numeros) > 8:
        apenas_numeros = apenas_numeros[:8]
    if len(apenas_numeros) >= 2:
        dia = int(apenas_numeros[0:2])
        if dia > 31 or (dia == 0 and len(apenas_numeros) == 2):
            return texto_atual
    if len(apenas_numeros) >= 4:
        mes = int(apenas_numeros[2:4])
        if mes > 12 or (mes == 0 and len(apenas_numeros) == 4):
            return texto_atual

    resultado = ""
    for idx, num in enumerate(apenas_numeros):
        if idx == 2 or idx == 4:
            resultado += "/"
        resultado += num
    return resultado

fase_atual = gerar_fase_por_angulo(id_fase_dinamica, angulo_atual, LARGURA_ORIGINAL, ALTURA_ORIGINAL)

# ==========================================
#   TELAS DE INTERFACE
# ==========================================

def desenhar_tela_jogo():
    tela.fill(COR_FUNDO)
    
    # Usa a posição do mouse mapeada no canvas virtual
    mouse_pos = mouse_pos_virtual if 'mouse_pos_virtual' in globals() else pygame.mouse.get_pos()
    
    # 1. Instrução Superior
    num_tentativa = min(tentativa_atual + 1, TOTAL_TENTATIVAS)
    txt_instrucao = f"Tentativa {num_tentativa} de {TOTAL_TENTATIVAS}: Leve o {nome_inicio} até a {nome_fim}!"
    img_instrucao = fonte.render(txt_instrucao, True, COR_TEXTO)
    tela.blit(img_instrucao, (40, 35))
    
    # 2. Botão Sair (Canto superior direito fixo nas dimensões virtuais)
    btn_sair = pygame.Rect(LARGURA_ORIGINAL - 140, 30, 100, 45)
    cor_sair = COR_BOTAO_HOVER if btn_sair.collidepoint(mouse_pos) else COR_BRANCO
    pygame.draw.rect(tela, cor_sair, btn_sair, border_radius=10)
    img_sair = fonte.render("Sair", True, COR_TEXTO)
    tela.blit(img_sair, img_sair.get_rect(center=btn_sair.center))
    
    # 3. Linha Guia Pontilhada (Caminho entre início e alvo)
    if 'ponto_inicio' in globals() and 'ponto_alvo' in globals():
        desenhar_linha_pontilhada(tela, COR_GUIA, ponto_inicio, ponto_alvo, largura=6, espaco=12)
        
    # 4. Traçado do Jogador
    if 'pontos_desenhados' in globals() and len(pontos_desenhados) > 1:
        cor_rgb = OPCOES_CORES_TRACADO.get(cor_tracado_atual, (0, 102, 204))
        pygame.draw.lines(tela, cor_rgb, False, pontos_desenhados, 6)
        
    # 5. Ícones de Início (Cão) e Alvo (Casinha)
    if icones.get(nome_inicio) and 'ponto_inicio' in globals():
        rect_inicio = icones[nome_inicio].get_rect(center=ponto_inicio)
        tela.blit(icones[nome_inicio], rect_inicio)
        
    if icones.get(nome_fim) and 'ponto_alvo' in globals():
        rect_alvo = icones[nome_fim].get_rect(center=ponto_alvo)
        tela.blit(icones[nome_fim], rect_alvo)
        
    # 6. Rodapé Informativo (Fase, Cor do Traço e Progresso)
    txt_rodape = f"Fase Atual: Ângulo {angulo_fase_atual:.1f}° | Cor Traço: {cor_tracado_atual} | Progresso: {sucessos_fase_atual}/{TOTAL_TENTATIVAS}"
    img_rodape = fonte.render(txt_rodape, True, COR_TEXTO)
    tela.blit(img_rodape, (40, ALTURA_ORIGINAL - 50))
    
    return btn_sair

def desenhar_menu_responsavel():
    tela.fill(COR_FUNDO)
    
    # Usa mouse_pos_virtual calculada no loop principal
    mouse_pos = mouse_pos_virtual if 'mouse_pos_virtual' in globals() else pygame.mouse.get_pos()
    
    if icones.get("Logotipo"):
        rect_logo = icones["Logotipo"].get_rect(center=(LARGURA_ORIGINAL // 2, 160))
        tela.blit(icones["Logotipo"], rect_logo)
    
    L_BTN, A_BTN = 420, 65
    
    btn_jogar = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_jogar.center = (LARGURA_ORIGINAL // 2, 350)
    
    btn_estatisticas = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_estatisticas.center = (LARGURA_ORIGINAL // 2, 435)

    btn_configs = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_configs.center = (LARGURA_ORIGINAL // 2, 520)
    
    btn_sair = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_sair.center = (LARGURA_ORIGINAL // 2, 605)
    
    botoes = [
        (btn_jogar, "Iniciar Jogo (Criança)", COR_INICIO, COR_BRANCO),
        (btn_estatisticas, "Estatísticas", COR_BOTAO, COR_TEXTO),
        (btn_configs, "Configurações", COR_BOTAO, COR_TEXTO),
        (btn_sair, "Sair do Jogo", COR_ALVO, COR_BRANCO)
    ]
    
    for rect, texto, cor_padrao, cor_txt in botoes:
        cor = COR_BOTAO_HOVER if rect.collidepoint(mouse_pos) else cor_padrao
        pygame.draw.rect(tela, cor, rect, border_radius=12)
        img_texto = fonte.render(texto, True, cor_txt if cor != COR_BOTAO_HOVER else COR_TEXTO)
        tela.blit(img_texto, img_texto.get_rect(center=rect.center))
        
    return btn_jogar, btn_estatisticas, btn_configs, btn_sair

def desenhar_tela_pin_acesso(titulo="Acesso do Responsável"):
    tela.fill(COR_FUNDO)
    mouse_pos = mouse_pos_virtual if 'mouse_pos_virtual' in globals() else pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render(titulo, True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(LARGURA_ORIGINAL // 2, 140)))
    
    txt_instrucao = fonte.render("Insira o PIN de 4 dígitos para continuar:", True, COR_TEXTO)
    tela.blit(txt_instrucao, txt_instrucao.get_rect(center=(LARGURA_ORIGINAL // 2, 230)))
    
    caixa_senha = pygame.Rect(0, 0, 250, 60)
    caixa_senha.center = (LARGURA_ORIGINAL // 2, 310)
    pygame.draw.rect(tela, COR_BRANCO, caixa_senha, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, caixa_senha, width=3, border_radius=5)
    
    texto_escondido = "*" * len(pin_digitado)
    txt_pin = fonte_titulo.render(texto_escondido, True, COR_TEXTO)
    tela.blit(txt_pin, txt_pin.get_rect(center=caixa_senha.center))
    
    btn_confirmar = pygame.Rect(0, 0, 160, 45)
    btn_confirmar.center = (LARGURA_ORIGINAL // 2 + 100, 470)
    cor_conf = COR_BOTAO_HOVER if btn_confirmar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_conf, btn_confirmar, border_radius=10)
    txt_conf = fonte.render("Confirmar", True, COR_TEXTO)
    tela.blit(txt_conf, txt_conf.get_rect(center=btn_confirmar.center))
    
    btn_cancelar = pygame.Rect(0, 0, 160, 45)
    btn_cancelar.center = (LARGURA_ORIGINAL // 2 - 100, 470)
    cor_canc = COR_BOTAO_HOVER if btn_cancelar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_canc, btn_cancelar, border_radius=10)
    txt_canc = fonte.render("Cancelar", True, COR_TEXTO)
    tela.blit(txt_canc, txt_canc.get_rect(center=btn_cancelar.center))
    
    if mensagem_erro_pin:
        txt_erro = fonte.render(mensagem_erro_pin, True, (180, 50, 50))
        tela.blit(txt_erro, txt_erro.get_rect(center=(LARGURA_ORIGINAL // 2, 396)))
        
    return btn_confirmar, btn_cancelar

def desenhar_menu_crianca():
    global pagina_menu_crianca
    tela.fill(COR_FUNDO)
    mouse_pos = mouse_pos_virtual if 'mouse_pos_virtual' in globals() else pygame.mouse.get_pos()

    img_titulo = fonte_titulo.render("Quem vai jogar hoje?", True, COR_TEXTO)
    tela.blit(img_titulo, img_titulo.get_rect(center=(LARGURA_ORIGINAL // 2, 80)))

    recs_criancas = []

    if not lista_criancas:
        img_aviso = fonte.render("Nenhuma criança cadastrada ainda.", True, COR_TEXTO)
        tela.blit(img_aviso, img_aviso.get_rect(center=(LARGURA_ORIGINAL // 2, ALTURA_ORIGINAL // 2)))
    else:
        COLUNAS = 3
        largura_card = 260
        altura_card = 120
        
        espacamento_x = 25
        espacamento_y = 20
        inicio_y = 160

        total_paginas = (len(lista_criancas) + CRIANCAS_POR_PAGINA_MENU - 1) // CRIANCAS_POR_PAGINA_MENU
        pagina_menu_crianca = max(0, min(pagina_menu_crianca, total_paginas - 1))

        inicio_idx = pagina_menu_crianca * CRIANCAS_POR_PAGINA_MENU
        criancas_pagina = lista_criancas[inicio_idx:inicio_idx + CRIANCAS_POR_PAGINA_MENU]

        largura_total_grid = (COLUNAS * largura_card) + ((COLUNAS - 1) * espacamento_x)
        inicio_x = (LARGURA_ORIGINAL - largura_total_grid) // 2

        for idx, cr in enumerate(criancas_pagina):
            col = idx % COLUNAS
            lin = idx // COLUNAS

            x = inicio_x + col * (largura_card + espacamento_x)
            y = inicio_y + lin * (altura_card + espacamento_y)

            rect_card = pygame.Rect(x, y, largura_card, altura_card)

            sel = (
                crianca_selecionada
                and isinstance(crianca_selecionada, dict)
                and crianca_selecionada.get("id") == cr.get("id")
            )
            if sel:
                cor_fundo = COR_INPUT_ATIVO
                cor_borda = COR_DESTAQUE
            elif rect_card.collidepoint(mouse_pos):
                cor_fundo = COR_BOTAO_HOVER
                cor_borda = COR_GUIA
            else:
                cor_fundo = COR_BRANCO
                cor_borda = COR_GUIA

            pygame.draw.rect(tela, cor_fundo, rect_card, border_radius=15)
            pygame.draw.rect(tela, cor_borda, rect_card, width=3 if sel else 2, border_radius=15)

            nome = cr.get("nome", f"Criança {idx+1}")
            img_nome = fonte.render(nome, True, COR_TEXTO)
            tela.blit(img_nome, img_nome.get_rect(center=rect_card.center))

            recs_criancas.append((rect_card, cr))

        if pagina_menu_crianca > 0:
            btn_prev_m = pygame.Rect(inicio_x - 60, inicio_y + (altura_card // 2) + 20, 45, 50)
            cor_prev = COR_BOTAO_HOVER if btn_prev_m.collidepoint(mouse_pos) else COR_BOTAO
            pygame.draw.rect(tela, cor_prev, btn_prev_m, border_radius=8)
            txt_p = fonte_titulo.render("<", True, COR_TEXTO)
            tela.blit(txt_p, txt_p.get_rect(center=btn_prev_m.center))
            recs_criancas.append((btn_prev_m, "PAGINA_ANTERIOR"))

        if pagina_menu_crianca < total_paginas - 1:
            btn_next_m = pygame.Rect(inicio_x + largura_total_grid + 15, inicio_y + (altura_card // 2) + 20, 45, 50)
            cor_next = COR_BOTAO_HOVER if btn_next_m.collidepoint(mouse_pos) else COR_BOTAO
            pygame.draw.rect(tela, cor_next, btn_next_m, border_radius=8)
            txt_n = fonte_titulo.render(">", True, COR_TEXTO)
            tela.blit(txt_n, txt_n.get_rect(center=btn_next_m.center))
            recs_criancas.append((btn_next_m, "PAGINA_PROXIMA"))

    largura_btn = 220
    pos_y_rodape = 620

    btn_cont = pygame.Rect(0, 0, largura_btn, 50)
    btn_cont.center = (LARGURA_ORIGINAL // 2 + 120, pos_y_rodape)

    btn_volt = pygame.Rect(0, 0, largura_btn, 50)
    btn_volt.center = (LARGURA_ORIGINAL // 2 - 120, pos_y_rodape)

    cor_btn_cont = COR_INICIO if crianca_selecionada else (200, 200, 200)
    pygame.draw.rect(tela, cor_btn_cont, btn_cont, border_radius=10)
    img_c = fonte.render("Continuar", True, COR_BRANCO)
    tela.blit(img_c, img_c.get_rect(center=btn_cont.center))

    pygame.draw.rect(tela, COR_ALVO, btn_volt, border_radius=10)
    img_v = fonte.render("Voltar", True, COR_BRANCO)
    tela.blit(img_v, img_v.get_rect(center=btn_volt.center))

    return recs_criancas, btn_cont, btn_volt

def desenhar_tela_configuracoes():
    global pagina_crianca_config, som_temp
    
    tela.fill(COR_FUNDO)
    mouse_pos = mouse_pos_virtual if 'mouse_pos_virtual' in globals() else pygame.mouse.get_pos()
    
    centro_x = LARGURA_ORIGINAL // 2
    inicio_x_rotulo = centro_x - 350
    inicio_x_opcao = centro_x - 110

    texto_titulo = fonte_titulo.render("Configurações", True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(centro_x, 45)))
    
    btn_cadastrar_novo = pygame.Rect(inicio_x_rotulo, 90, 220, 40)
    cor_cad = COR_BOTAO_HOVER if btn_cadastrar_novo.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_cad, btn_cadastrar_novo, border_radius=8)
    tela.blit(font_campo.render("Cadastrar Criança", True, COR_TEXTO), (inicio_x_rotulo + 25, 100))

    btn_remover_crianca = pygame.Rect(inicio_x_rotulo + 240, 90, 200, 40)
    if crianca_config_selecionada:
        cor_rem = (240, 100, 100) if btn_remover_crianca.collidepoint(mouse_pos) else COR_ALVO
        pygame.draw.rect(tela, cor_rem, btn_remover_crianca, border_radius=8)
        txt_rem = font_campo.render("Remover Criança", True, COR_BRANCO)
        tela.blit(txt_rem, txt_rem.get_rect(center=btn_remover_crianca.center))

    tela.blit(fonte.render("Selecionar Criança:", True, COR_TEXTO), (inicio_x_rotulo, 155))
    botoes_criancas = []
    btn_prev_pag, btn_next_pag = None, None

    if not lista_criancas:
        tela.blit(font_campo.render("Nenhuma criança cadastrada.", True, (150, 150, 150)), (inicio_x_opcao, 158))
    else:
        CRIANCAS_POR_PAGINA = 3
        total_paginas = (len(lista_criancas) + CRIANCAS_POR_PAGINA - 1) // CRIANCAS_POR_PAGINA
        pagina_crianca_config = max(0, min(pagina_crianca_config, total_paginas - 1))
        
        inicio_idx = pagina_crianca_config * CRIANCAS_POR_PAGINA
        criancas_pagina = lista_criancas[inicio_idx:inicio_idx + CRIANCAS_POR_PAGINA]

        if pagina_crianca_config > 0:
            btn_prev_pag = pygame.Rect(inicio_x_opcao - 35, 150, 30, 35)
            pygame.draw.rect(tela, COR_BOTAO, btn_prev_pag, border_radius=5)
            tela.blit(font_campo.render("<", True, COR_TEXTO), font_campo.render("<", True, COR_TEXTO).get_rect(center=btn_prev_pag.center))

        for idx, cr in enumerate(criancas_pagina):
            rect_cr = pygame.Rect(inicio_x_opcao + (idx * 145), 150, 135, 35)
            is_selected = crianca_config_selecionada and crianca_config_selecionada.get("id") == cr.get("id")
            cor = COR_INPUT_ATIVO if is_selected else (COR_BOTAO_HOVER if rect_cr.collidepoint(mouse_pos) else COR_BOTAO)
            pygame.draw.rect(tela, cor, rect_cr, border_radius=5)
            
            nome_curto = cr['nome'][:8] + "..." if len(cr['nome']) > 8 else cr['nome']
            txt_c = font_campo.render(nome_curto, True, COR_TEXTO)
            tela.blit(txt_c, txt_c.get_rect(center=rect_cr.center))
            botoes_criancas.append((rect_cr, cr))

        if pagina_crianca_config < total_paginas - 1:
            btn_next_pag = pygame.Rect(inicio_x_opcao + (3 * 145), 150, 30, 35)
            pygame.draw.rect(tela, COR_BOTAO, btn_next_pag, border_radius=5)
            tela.blit(font_campo.render(">", True, COR_TEXTO), font_campo.render(">", True, COR_TEXTO).get_rect(center=btn_next_pag.center))

    pygame.draw.line(tela, COR_GUIA, (inicio_x_rotulo, 205), (inicio_x_rotulo + 700, 205), 2)

    tela.blit(fonte.render("Cor do Traçado:", True, COR_TEXTO), (inicio_x_rotulo, 225))
    botoes_cores = []
    x_cor = inicio_x_opcao
    for nome_cor, valor_rgb in OPCOES_CORES_TRACADO.items():
        rect_cor = pygame.Rect(x_cor, 220, 90, 35)
        is_sel = (cor_tracado_temp == nome_cor)
        if is_sel:
            pygame.draw.rect(tela, COR_TEXTO, rect_cor.inflate(4, 4), border_radius=7)
            
        pygame.draw.rect(tela, valor_rgb, rect_cor, border_radius=5)
        txt_cor = font_campo.render(nome_cor, True, COR_BRANCO if nome_cor in ["Azul", "Verde"] else COR_TEXTO)
        tela.blit(txt_cor, txt_cor.get_rect(center=rect_cor.center))
        botoes_cores.append((rect_cor, nome_cor))
        x_cor += 100

    tela.blit(fonte.render("Efeitos Sonoros:", True, COR_TEXTO), (inicio_x_rotulo, 280))
    btn_som_on = pygame.Rect(inicio_x_opcao, 275, 110, 35)
    btn_som_off = pygame.Rect(inicio_x_opcao + 120, 275, 110, 35)
    
    pygame.draw.rect(tela, COR_INPUT_ATIVO if som_temp else COR_BOTAO, btn_som_on, border_radius=5)
    tela.blit(fonte.render("Ligado", True, COR_TEXTO), fonte.render("Ligado", True, COR_TEXTO).get_rect(center=btn_som_on.center))

    pygame.draw.rect(tela, COR_INPUT_ATIVO if not som_temp else COR_BOTAO, btn_som_off, border_radius=5)
    tela.blit(fonte.render("Mudo", True, COR_TEXTO), fonte.render("Mudo", True, COR_TEXTO).get_rect(center=btn_som_off.center))

    tela.blit(fonte.render("Seleção de Ruído:", True, COR_TEXTO), (inicio_x_rotulo, 335))
    btn_r_baixo = pygame.Rect(inicio_x_opcao, 330, 110, 35)
    cor_rb = COR_INPUT_ATIVO if ruido_temp == "Baixo" else COR_BOTAO
    pygame.draw.rect(tela, cor_rb, btn_r_baixo, border_radius=5)
    tela.blit(fonte.render("Baixo", True, COR_TEXTO), fonte.render("Baixo", True, COR_TEXTO).get_rect(center=btn_r_baixo.center))

    btn_r_medio = pygame.Rect(inicio_x_opcao + 120, 330, 110, 35)
    cor_rm = COR_INPUT_ATIVO if ruido_temp == "Médio" else COR_BOTAO
    pygame.draw.rect(tela, cor_rm, btn_r_medio, border_radius=5)
    tela.blit(fonte.render("Médio", True, COR_TEXTO), fonte.render("Médio", True, COR_TEXTO).get_rect(center=btn_r_medio.center))

    pygame.draw.line(tela, COR_GUIA, (inicio_x_rotulo, 380), (inicio_x_rotulo + 700, 380), 2)

    tela.blit(fonte.render("Alterar PIN Parental:", True, COR_TEXTO), (inicio_x_rotulo, 400))
    rect_novo_pin = pygame.Rect(inicio_x_opcao, 395, 150, 40)
    cor_p = COR_INPUT_ATIVO if campo_config_ativo == "pin" else COR_BRANCO
    pygame.draw.rect(tela, cor_p, rect_novo_pin, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, rect_novo_pin, width=2, border_radius=5)
    renderizar_texto_com_scroll(temp_pin_novo, "", 150, inicio_x_opcao, 395)

    btn_cancelar = pygame.Rect(0, 560, 180, 45)
    btn_cancelar.centerx = centro_x - 110
    cor_ca = COR_BOTAO_HOVER if btn_cancelar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_ca, btn_cancelar, border_radius=10)
    tela.blit(fonte.render("Cancelar", True, COR_TEXTO), fonte.render("Cancelar", True, COR_TEXTO).get_rect(center=btn_cancelar.center))

    btn_confirmar = pygame.Rect(0, 560, 180, 45)
    btn_confirmar.centerx = centro_x + 110
    cor_co = COR_BOTAO_HOVER if btn_confirmar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_co, btn_confirmar, border_radius=10)
    tela.blit(fonte.render("Salvar", True, COR_TEXTO), fonte.render("Salvar", True, COR_TEXTO).get_rect(center=btn_confirmar.center))

    return btn_cadastrar_novo, btn_remover_crianca, botoes_criancas, btn_prev_pag, btn_next_pag, botoes_cores, btn_som_on, btn_som_off, btn_r_baixo, btn_r_medio, rect_novo_pin, btn_confirmar, btn_cancelar

def desenhar_modal_confirmacao(nome_crianca):
    overlay = pygame.Surface((LARGURA_ORIGINAL, ALTURA_ORIGINAL), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    tela.blit(overlay, (0, 0))

    rect_modal = pygame.Rect(0, 0, 480, 200)
    rect_modal.center = (LARGURA_ORIGINAL // 2, ALTURA_ORIGINAL // 2)

    pygame.draw.rect(tela, COR_BRANCO, rect_modal, border_radius=12)
    pygame.draw.rect(tela, COR_GUIA, rect_modal, width=2, border_radius=12)

    txt_tit = fonte_titulo.render("Tem certeza?", True, COR_TEXTO)
    tela.blit(txt_tit, txt_tit.get_rect(center=(rect_modal.centerx, rect_modal.top + 35)))

    txt_sub = font_campo.render(f"Deseja excluir o perfil de '{nome_crianca}'?", True, (100, 100, 100))
    tela.blit(txt_sub, txt_sub.get_rect(center=(rect_modal.centerx, rect_modal.top + 80)))

    btn_sim = pygame.Rect(0, 0, 140, 40)
    btn_sim.center = (rect_modal.centerx - 80, rect_modal.bottom - 45)

    btn_nao = pygame.Rect(0, 0, 140, 40)
    btn_nao.center = (rect_modal.centerx + 80, rect_modal.bottom - 45)

    pygame.draw.rect(tela, COR_ALVO, btn_sim, border_radius=8)
    tela.blit(fonte.render("Excluir", True, COR_BRANCO), fonte.render("Excluir", True, COR_BRANCO).get_rect(center=btn_sim.center))

    pygame.draw.rect(tela, COR_INICIO, btn_nao, border_radius=8)
    tela.blit(fonte.render("Cancelar", True, COR_BRANCO), fonte.render("Cancelar", True, COR_BRANCO).get_rect(center=btn_nao.center))

    return btn_sim, btn_nao

def desenhar_cadastro_crianca():
    tela.fill(COR_FUNDO)
    mouse_pos = mouse_pos_virtual if 'mouse_pos_virtual' in globals() else pygame.mouse.get_pos()

    centro_x = LARGURA_ORIGINAL // 2
    largura_campo = 500
    inicio_x_campos = centro_x - (largura_campo // 2)

    texto_titulo = fonte_titulo.render("Cadastro de Criança", True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(centro_x, 100)))

    pos_y_nome = 200
    rect_nome = pygame.Rect(inicio_x_campos, pos_y_nome, largura_campo, 45)
    cor_n = COR_INPUT_ATIVO if campo_ativo == "nome" else COR_BRANCO
    pygame.draw.rect(tela, cor_n, rect_nome, border_radius=8)
    pygame.draw.rect(tela, COR_GUIA, rect_nome, width=2, border_radius=8)
    renderizar_texto_com_scroll(
        input_cadastro["nome"], "Nome: ", largura_campo, inicio_x_campos, pos_y_nome
    )

    pos_y_sexo = 300
    largura_btn_sexo = (largura_campo - 20) // 2

    rect_sexo_m = pygame.Rect(inicio_x_campos, pos_y_sexo, largura_btn_sexo, 45)
    cor_sm = COR_INPUT_ATIVO if input_cadastro["sexo"] == "Masculino" else COR_BOTAO
    pygame.draw.rect(tela, cor_sm, rect_sexo_m, border_radius=8)
    txt_sm = font_campo.render("Masculino", True, COR_TEXTO)
    tela.blit(txt_sm, txt_sm.get_rect(center=rect_sexo_m.center))

    rect_sexo_f = pygame.Rect(inicio_x_campos + largura_btn_sexo + 20, pos_y_sexo, largura_btn_sexo, 45)
    cor_sf = COR_INPUT_ATIVO if input_cadastro["sexo"] == "Feminino" else COR_BOTAO
    pygame.draw.rect(tela, cor_sf, rect_sexo_f, border_radius=8)
    txt_sf = font_campo.render("Feminino", True, COR_TEXTO)
    tela.blit(txt_sf, txt_sf.get_rect(center=rect_sexo_f.center))

    pos_y_botoes = 480
    largura_btn_acao = 180

    btn_cancelar = pygame.Rect(0, 0, largura_btn_acao, 50)
    btn_cancelar.center = (centro_x - (largura_btn_acao // 2) - 15, pos_y_botoes)
    cor_ca = COR_BOTAO_HOVER if btn_cancelar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_ca, btn_cancelar, border_radius=10)
    txt_ca = fonte.render("Cancelar", True, COR_TEXTO)
    tela.blit(txt_ca, txt_ca.get_rect(center=btn_cancelar.center))

    btn_confirmar = pygame.Rect(0, 0, largura_btn_acao, 50)
    btn_confirmar.center = (centro_x + (largura_btn_acao // 2) + 15, pos_y_botoes)
    cor_co = COR_BOTAO_HOVER if btn_confirmar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_co, btn_confirmar, border_radius=10)
    txt_co = fonte.render("Confirmar", True, COR_TEXTO)
    tela.blit(txt_co, txt_co.get_rect(center=btn_confirmar.center))

    return (
        rect_nome,
        None,
        rect_sexo_m,
        rect_sexo_f,
        btn_confirmar,
        btn_cancelar,
    )

def desenhar_tela_estatisticas(dados_banco):
    global scroll_y_estatisticas, scroll_x_criancas
    tela.fill(COR_FUNDO)
    
    mouse_pos = mouse_pos_virtual if 'mouse_pos_virtual' in globals() else pygame.mouse.get_pos()
    
    # --- BOTÃO VOLTAR ---
    btn_voltar = pygame.Rect(30, 20, 100, 40)
    cor_v = COR_BOTAO_HOVER if btn_voltar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_v, btn_voltar, border_radius=5)
    txt_voltar = fonte.render("Voltar", True, COR_TEXTO)
    tela.blit(txt_voltar, txt_voltar.get_rect(center=btn_voltar.center))

    # --- TÍTULO ---
    txt_titulo = fonte_titulo.render("Estatísticas de Desempenho", True, COR_TEXTO)
    tela.blit(txt_titulo, (150, 25))

    # --- 1. SELEÇÃO DE CRIANÇAS (CARROSSEL HORIZONTAL) ---
    btns_criancas = []
    lista_c = obter_criancas() if db_ativo else []

    largura_btn = 120
    espacamento = 15
    y_criancas = 80
    altura_btn = 35
    x_inicial = 60
    area_carrossel_largura = LARGURA_ORIGINAL - 120

    # Seta Esquerda (<)
    btn_seta_esq = pygame.Rect(15, y_criancas, 35, altura_btn)
    pygame.draw.rect(tela, COR_BOTAO_HOVER if btn_seta_esq.collidepoint(mouse_pos) else COR_BOTAO, btn_seta_esq, border_radius=5)
    txt_esq = fonte.render("<", True, COR_TEXTO)
    tela.blit(txt_esq, txt_esq.get_rect(center=btn_seta_esq.center))

    # Seta Direita (>)
    btn_seta_dir = pygame.Rect(LARGURA_ORIGINAL - 50, y_criancas, 35, altura_btn)
    pygame.draw.rect(tela, COR_BOTAO_HOVER if btn_seta_dir.collidepoint(mouse_pos) else COR_BOTAO, btn_seta_dir, border_radius=5)
    txt_dir = fonte.render(">", True, COR_TEXTO)
    tela.blit(txt_dir, txt_dir.get_rect(center=btn_seta_dir.center))

    # Recorte da tela para impedir os botões de vazarem nas laterais
    clip_original = tela.get_clip()
    tela.set_clip(pygame.Rect(x_inicial, y_criancas, area_carrossel_largura, altura_btn))

    for idx, c in enumerate(lista_c):
        pos_x = x_inicial + idx * (largura_btn + espacamento) - scroll_x_criancas
        rect_c = pygame.Rect(pos_x, y_criancas, largura_btn, altura_btn)
        
        selecionada = (crianca_estatistica_selecionada and crianca_estatistica_selecionada.get("id") == c.get("id"))
        cor_c = COR_INICIO if selecionada else (COR_BOTAO_HOVER if rect_c.collidepoint(mouse_pos) else COR_BOTAO)
        
        pygame.draw.rect(tela, cor_c, rect_c, border_radius=5)
        
        # Nome truncado com reticências para não estourar a caixa
        nome_original = c.get("nome", "Criança")
        nome_exibicao = truncar_texto(nome_original, fonte, largura_btn - 10)
        
        txt_nome = fonte.render(nome_exibicao, True, COR_BRANCO if selecionada else COR_TEXTO)
        tela.blit(txt_nome, txt_nome.get_rect(center=rect_c.center))
        btns_criancas.append((rect_c, c))

    tela.set_clip(clip_original)

    if not crianca_estatistica_selecionada:
        txt = fonte.render("Selecione uma criança acima para ver o desempenho.", True, COR_TEXTO)
        tela.blit(txt, (50, 150))
        return btn_voltar, btns_criancas, [], btn_seta_esq, btn_seta_dir, area_carrossel_largura, len(lista_c)

    # --- 2. LISTA DE ÂNGULOS E TENTATIVAS (COM SCROLL) ---
    area_clique_angulos = []
    y_atual = 140 - scroll_y_estatisticas

    for angulo in LISTA_ANGULOS:
        if 130 <= y_atual <= ALTURA_ORIGINAL - 50:
            rect_card = pygame.Rect(50, y_atual, LARGURA_ORIGINAL - 100, 40)
            pygame.draw.rect(tela, COR_BRANCO, rect_card, border_radius=5)
            pygame.draw.rect(tela, COR_BOTAO, rect_card, width=1, border_radius=5)

            tentativas_ang = dados_banco.get(angulo, [])
            if tentativas_ang:
                media = sum(tentativas_ang) / len(tentativas_ang)
                txt_media = f"{media:.2f}%"
            else:
                txt_media = "--"

            str_ang = f"No ângulo de {angulo}°, média de acerto: {txt_media}"
            tela.blit(fonte.render(str_ang, True, COR_TEXTO), (65, y_atual + 7))

            esta_aberto = angulos_expandidos.get(angulo, False)
            seta_txt = "/\\" if esta_aberto else "V"
            lbl_seta = fonte.render(seta_txt, True, COR_TEXTO)
            rect_seta = lbl_seta.get_rect(right=LARGURA_ORIGINAL - 75, centery=y_atual + 20)
            tela.blit(lbl_seta, rect_seta)

            area_clique_angulos.append((rect_card, angulo))

        y_atual += 45

        if angulos_expandidos.get(angulo, False):
            tentativas_ang = dados_banco.get(angulo, [])
            for i in range(5):
                if 130 <= y_atual <= ALTURA_ORIGINAL - 50:
                    val_tentativa = f"{tentativas_ang[i]:.2f}%" if i < len(tentativas_ang) else "--"
                    txt_sub = f"   └─ {val_tentativa} na {i+1}ª tentativa"
                    tela.blit(fonte.render(txt_sub, True, (80, 80, 80)), (90, y_atual + 5))
                y_atual += 30

    return btn_voltar, btns_criancas, area_clique_angulos, btn_seta_esq, btn_seta_dir, area_carrossel_largura, len(lista_c)

# ==========================================
#             LOOP PRINCIPAL
# ==========================================
rodando = True
while rodando:

    # Mapeia eventos do mouse para converter a posição em tempo real para a resolução virtual
    mouse_pos_virtual = converter_pos_mouse(pygame.mouse.get_pos())

    # ------------------ MENU PRINCIPAL ------------------
    if estado_jogo == "MENU_RESPONSAVEL":
        btn_jogar, btn_estatisticas, btn_configs, btn_sair = desenhar_menu_responsavel()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE:
                LARGURA, ALTURA = evento.w, evento.h
                tela_real = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_v = converter_pos_mouse(evento.pos)
                if btn_jogar and btn_jogar.collidepoint(pos_v):
                    lista_criancas = obter_criancas() if db_ativo else []
                    estado_jogo = "MENU_CRIANCA"
                elif btn_estatisticas and btn_estatisticas.collidepoint(pos_v):
                    destino_apos_pin = "ESTATISTICAS"
                    estado_jogo = "PIN_ACESSO"
                    pin_digitado = ""
                    mensagem_erro_pin = ""
                elif btn_configs and btn_configs.collidepoint(pos_v):
                    destino_apos_pin = "CONFIGURACOES"
                    estado_jogo = "PIN_ACESSO"
                    pin_digitado = ""
                    mensagem_erro_pin = ""
                elif btn_sair and btn_sair.collidepoint(pos_v):
                    rodando = False

    # ------------------ MENU SELEÇÃO DE CRIANÇA ------------------
    elif estado_jogo == "MENU_CRIANCA":
        recs_criancas, btn_cont, btn_volt = desenhar_menu_crianca()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE:
                LARGURA, ALTURA = evento.w, evento.h
                tela_real = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_v = converter_pos_mouse(evento.pos)
                for rect, item in recs_criancas:
                    if rect.collidepoint(pos_v):
                        if item == "PAGINA_ANTERIOR":
                            pagina_menu_crianca -= 1
                        elif item == "PAGINA_PROXIMA":
                            pagina_menu_crianca += 1
                        elif isinstance(item, dict):
                            crianca_selecionada = item

                if btn_volt.collidepoint(pos_v):
                    pagina_menu_crianca = 0
                    estado_jogo = "MENU_RESPONSAVEL"

                elif btn_cont.collidepoint(pos_v):
                    ids_validos = [c["id"] for c in lista_criancas if isinstance(c, dict) and "id" in c]

                    if (isinstance(crianca_selecionada, dict) and 
                        crianca_selecionada.get("id") in ids_validos):

                        id_str = str(crianca_selecionada["id"])
                        cfg_cr = configs_jogo.get("config_criancas", {}).get(id_str, {})

                        cor_tracado_atual = cfg_cr.get("cor_tracado", "Azul")
                        som_ativo_atual = cfg_cr.get("som", True)

                        estado_jogo = "JOGANDO"
                        angulo_atual = 0.0
                        id_fase_dinamica = 1
                        tentativas_precisoes = []
                        tentativa_atual_num = 1
                        fase_atual = gerar_fase_por_angulo(id_fase_dinamica, angulo_atual)
                        jogo_finalizado = False
                        coordenadas_usuario = []
                        coordenadas_salvas_para_desenho = []
                        tempos_toque = []
                        desenhando = False
                        mensagem_status = "Tentativa 1 de 5: Leve o Cão até a Casinha!"
                    else:
                        crianca_selecionada = None

    # ------------------ SISTEMA DE PIN ------------------
    elif estado_jogo == "PIN_ACESSO":
        btn_confirmar, btn_cancelar = desenhar_tela_pin_acesso("Acesso do Responsável")
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE:
                LARGURA, ALTURA = evento.w, evento.h
                tela_real = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_BACKSPACE:
                    pin_digitado = pin_digitado[:-1]
                elif len(pin_digitado) < 4 and evento.unicode.isdigit():
                    pin_digitado += evento.unicode
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_v = converter_pos_mouse(evento.pos)
                if btn_confirmar.collidepoint(pos_v):
                    if pin_digitado == configs_jogo["pin"]:
                        if destino_apos_pin == "CONFIGURACOES":
                            temp_pin_novo = configs_jogo["pin"]
                            ruido_temp = configs_jogo.get("ruido", "Baixo")
                            lista_criancas = obter_criancas() if db_ativo else []
                            crianca_config_selecionada = lista_criancas[0] if lista_criancas else None
                            
                            if crianca_config_selecionada and isinstance(crianca_config_selecionada, dict):
                                id_str = str(crianca_config_selecionada.get("id", ""))
                                cor_tracado_temp = configs_jogo.get("config_criancas", {}).get(id_str, {}).get("cor_tracado", "Azul")
                                som_temp = configs_jogo.get("config_criancas", {}).get(id_str, {}).get("som", True)
                            else:
                                cor_tracado_temp = "Azul"
                                som_temp = True
                                
                            campo_config_ativo = None
                        
                        estado_jogo = destino_apos_pin
                    else:
                        mensagem_erro_pin = "PIN inválido! Digite o PIN correto."
                        pin_digitado = ""
                elif btn_cancelar.collidepoint(pos_v):
                    estado_jogo = "MENU_RESPONSAVEL"

    # ------------------ CADASTRO DE CRIANÇA ------------------
    elif estado_jogo == "CADASTRO_CRIANCA":
        r_nome, _, r_sm, r_sf, btn_conf, btn_canc = desenhar_cadastro_crianca()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE:
                LARGURA, ALTURA = evento.w, evento.h
                tela_real = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_v = converter_pos_mouse(evento.pos)
                if r_nome.collidepoint(pos_v):
                    campo_ativo = "nome"
                elif r_sm.collidepoint(pos_v):
                    input_cadastro["sexo"] = "Masculino"
                elif r_sf.collidepoint(pos_v):
                    input_cadastro["sexo"] = "Feminino"
                elif btn_conf.collidepoint(pos_v):
                    if input_cadastro["nome"].strip():
                        if db_ativo:
                            try:
                                salvar_crianca(
                                    input_cadastro["nome"],
                                    "",
                                    input_cadastro["sexo"],
                                    input_cadastro["obs"]
                                )
                                lista_criancas = obter_criancas()
                            except Exception as e:
                                print(f"Erro ao salvar no banco local: {e}")
                    estado_jogo = "CONFIGURACOES"
                elif btn_canc.collidepoint(pos_v):
                    estado_jogo = "CONFIGURACOES"
            elif evento.type == pygame.KEYDOWN and campo_ativo == "nome":
                if evento.key == pygame.K_BACKSPACE:
                    input_cadastro["nome"] = input_cadastro["nome"][:-1]
                else:
                    if not evento.unicode.isdigit():
                        input_cadastro["nome"] += evento.unicode

    # ------------------ CONFIGURAÇÕES ------------------
    elif estado_jogo == "CONFIGURACOES":
        (btn_cad, btn_del, btns_cr, btn_prev_p, btn_next_p, 
         btns_cor, btn_s_on, btn_s_off, btn_rb, btn_rm, 
         r_pin, btn_conf, btn_canc) = desenhar_tela_configuracoes()
        
        btn_sim_del, btn_nao_del = None, None
        if modal_excluir_ativo and crianca_config_selecionada:
            btn_sim_del, btn_nao_del = desenhar_modal_confirmacao(crianca_config_selecionada.get("nome", ""))

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE:
                LARGURA, ALTURA = evento.w, evento.h
                tela_real = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_v = converter_pos_mouse(evento.pos)
                if modal_excluir_ativo and crianca_config_selecionada:
                    if btn_sim_del and btn_sim_del.collidepoint(pos_v):
                        id_del = crianca_config_selecionada["id"]
                        id_str = str(id_del)
                        
                        if db_ativo:
                            try:
                                remover_crianca(id_del)
                            except Exception as e:
                                print(f"Erro ao remover do banco: {e}")
                        
                        lista_criancas = [c for c in lista_criancas if c.get("id") != id_del]
                        
                        if "config_criancas" in configs_jogo and id_str in configs_jogo["config_criancas"]:
                            del configs_jogo["config_criancas"][id_str]
                            salvar_configuracoes(configs_jogo)
                        
                        if crianca_config_selecionada and crianca_config_selecionada.get("id") == id_del:
                            crianca_config_selecionada = None
                        if crianca_selecionada and crianca_selecionada.get("id") == id_del:
                            crianca_selecionada = None
                            
                        modal_excluir_ativo = False

                    elif btn_nao_del and btn_nao_del.collidepoint(pos_v):
                        modal_excluir_ativo = False

                else:
                    if btn_cad.collidepoint(pos_v):
                        input_cadastro = {"nome": "", "nascimento": "", "sexo": "Masculino", "obs": ""}
                        campo_ativo = None
                        estado_jogo = "CADASTRO_CRIANCA"
                    
                    elif btn_del.collidepoint(pos_v):
                        if crianca_config_selecionada:
                            modal_excluir_ativo = True

                    elif btn_prev_p and btn_prev_p.collidepoint(pos_v):
                        pagina_crianca_config = max(0, pagina_crianca_config - 1)
                    elif btn_next_p and btn_next_p.collidepoint(pos_v):
                        pagina_crianca_config += 1

                    for r_c, cr in btns_cr:
                        if r_c.collidepoint(pos_v):
                            crianca_config_selecionada = cr
                            id_str = str(cr.get("id", ""))
                            cfg_cr = configs_jogo.get("config_criancas", {}).get(id_str, {})
                            cor_tracado_temp = cfg_cr.get("cor_tracado", "Azul")
                            som_temp = cfg_cr.get("som", True)
                    
                    for r_cor, nome_cor in btns_cor:
                        if r_cor.collidepoint(pos_v):
                            cor_tracado_temp = nome_cor

                    if btn_s_on and btn_s_on.collidepoint(pos_v):
                        som_temp = True
                    elif btn_s_off and btn_s_off.collidepoint(pos_v):
                        som_temp = False
                    
                    elif btn_rb and btn_rb.collidepoint(pos_v):
                        ruido_temp = "Baixo"
                        ajustar_volume_ruido("Baixo")
                    elif btn_rm and btn_rm.collidepoint(pos_v):
                        ruido_temp = "Médio"
                        ajustar_volume_ruido("Médio")

                    elif r_pin and r_pin.collidepoint(pos_v):
                        campo_config_ativo = "pin"

                    elif btn_conf and btn_conf.collidepoint(pos_v):
                        if len(temp_pin_novo) == 4:
                            configs_jogo["pin"] = temp_pin_novo
                        configs_jogo["ruido"] = ruido_temp
                        
                        if crianca_config_selecionada:
                            id_str = str(crianca_config_selecionada["id"])
                            if "config_criancas" not in configs_jogo:
                                configs_jogo["config_criancas"] = {}
                            configs_jogo["config_criancas"][id_str] = {
                                "cor_tracado": cor_tracado_temp,
                                "som": som_temp
                            }
                        
                        salvar_configuracoes(configs_jogo)
                        estado_jogo = "MENU_RESPONSAVEL"

                    elif btn_canc and btn_canc.collidepoint(pos_v):
                        configs_jogo = carregar_configuracoes()
                        estado_jogo = "MENU_RESPONSAVEL"
            
            elif evento.type == pygame.KEYDOWN and campo_config_ativo == "pin":
                if evento.key == pygame.K_BACKSPACE:
                    temp_pin_novo = temp_pin_novo[:-1]
                elif len(temp_pin_novo) < 4 and evento.unicode.isdigit():
                    temp_pin_novo += evento.unicode

  # ------------------ TELA DE ESTATÍSTICAS ------------------
    elif estado_jogo == "ESTATISTICAS":
        if not isinstance(crianca_estatistica_selecionada, dict):
            lista_criancas = obter_criancas() if db_ativo else []
            crianca_estatistica_selecionada = lista_criancas[0] if lista_criancas and isinstance(lista_criancas[0], dict) else None

        dados_banco = {}
        if isinstance(crianca_estatistica_selecionada, dict) and "id" in crianca_estatistica_selecionada:
            if db_ativo:
                dados_banco = obter_desempenho_crianca(crianca_estatistica_selecionada["id"])

        btn_voltar, btns_criancas, area_angulos, btn_seta_esq, btn_seta_dir, area_carrossel_largura, total_criancas = desenhar_tela_estatisticas(dados_banco)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE:
                LARGURA, ALTURA = evento.w, evento.h
                tela_real = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)

            elif evento.type == pygame.MOUSEWHEEL:
                scroll_y_estatisticas -= evento.y * 20
                scroll_y_estatisticas = max(0, min(scroll_y_estatisticas, 800))

            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_v = converter_pos_mouse(evento.pos)
                
                # Voltar ao menu principal
                if btn_voltar and btn_voltar.collidepoint(pos_v):
                    estado_jogo = "MENU_RESPONSAVEL"
                
                # Seta esquerda do carrossel
                elif btn_seta_esq and btn_seta_esq.collidepoint(pos_v):
                    scroll_x_criancas = max(0, scroll_x_criancas - 150)
                
                # Seta direita do carrossel
                elif btn_seta_dir and btn_seta_dir.collidepoint(pos_v):
                    limite_maximo = max(0, (total_criancas * 135) - area_carrossel_largura)
                    scroll_x_criancas = min(limite_maximo, scroll_x_criancas + 150)

                # Clique em uma criança
                else:
                    for rect_c, c in btns_criancas:
                        if rect_c.collidepoint(pos_v) and isinstance(c, dict):
                            crianca_estatistica_selecionada = c
                            angulos_expandidos.clear()
                            scroll_y_estatisticas = 0
                            break

                    # Clique em um card de ângulo para expandir/recolher
                    for rect_ang, angulo in area_angulos:
                        if rect_ang.collidepoint(pos_v):
                            angulos_expandidos[angulo] = not angulos_expandidos.get(angulo, False)
                            break

   # ------------------ TELA DE JOGO ------------------
    elif estado_jogo == "JOGANDO":
        if crianca_selecionada and isinstance(crianca_selecionada, dict):
            ids_validos = [c["id"] for c in lista_criancas if isinstance(c, dict) and "id" in c]
            if crianca_selecionada.get("id") not in ids_validos:
                crianca_selecionada = None

        p_init = fase_atual["ponto_inicio"]
        p_end = fase_atual["ponto_fim"]

        som_permitido = True
        cor_nome = "Azul"

        if crianca_selecionada and isinstance(crianca_selecionada, dict) and "id" in crianca_selecionada:
            id_str = str(crianca_selecionada["id"])
            cfg_cr = configs_jogo.get("config_criancas", {}).get(id_str, {})
            cor_nome = cfg_cr.get("cor_tracado", "Azul")
            som_permitido = cfg_cr.get("som", True)

        if som_ruido:
            if som_permitido and not pygame.mixer.get_busy():
                nivel_ruido = configs_jogo.get("ruido", "Baixo")
                ajustar_volume_ruido(nivel_ruido)  
                som_ruido.play(loops=-1)
            elif not som_permitido:
                som_ruido.stop()

        cor_rastro_atual = OPCOES_CORES_TRACADO.get(cor_nome, (70, 130, 180))

        largura_btn_sair = 110
        btn_sair_jogo = pygame.Rect(LARGURA_ORIGINAL - largura_btn_sair - 25, 20, largura_btn_sair, 35)
        
        texto_fim = "Voltar ao Menu Principal"
        texto_fim_largura, texto_fim_altura = fonte.size(texto_fim)
        btn_menu_fim = pygame.Rect(0, 0, texto_fim_largura + 50, texto_fim_altura + 20)
        btn_menu_fim.center = (LARGURA_ORIGINAL // 2, 510)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE:
                LARGURA, ALTURA = evento.w, evento.h
                tela_real = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
                
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_v = converter_pos_mouse(evento.pos)
                if jogo_finalizado:
                    if btn_menu_fim.collidepoint(pos_v):
                        if som_ruido:
                            som_ruido.stop()
                        estado_jogo = "MENU_RESPONSAVEL"
                else:
                    if btn_sair_jogo.collidepoint(pos_v):
                        if som_ruido:
                            som_ruido.stop()
                        estado_jogo = "MENU_RESPONSAVEL"
                    else:
                        dist_inicio = math.sqrt((pos_v[0] - p_init[0])**2 + (pos_v[1] - p_init[1])**2)
                        if dist_inicio <= 35:
                            desenhando = True
                            coordenadas_usuario = [pos_v]
                            coordenadas_salvas_para_desenho = []
                            tempos_toque = [time.time()]
                        
            elif evento.type == pygame.MOUSEMOTION and desenhando:
                pos_v = converter_pos_mouse(evento.pos)
                coordenadas_usuario.append(pos_v)
                tempos_toque.append(time.time())
                
            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1 and desenhando:
                pos_v = converter_pos_mouse(evento.pos)
                desenhando = False
                dist_alvo = math.sqrt((pos_v[0] - p_end[0])**2 + (pos_v[1] - p_end[1])**2)
                
                if dist_alvo <= 35:
                    precisao, hesitacao = calcular_metricas(
                        fase_atual["tipo"], p_init, p_end,
                        fase_atual.get("pontos_guia", []), coordenadas_usuario, tempos_toque
                    )
                    tempo_total = tempos_toque[-1] - tempos_toque[0] if tempos_toque else 0.0
                    
                    # --- ALTERAÇÃO AQUI: adicionado angulo_atual ao salvar ---
                    if db_ativo and crianca_selecionada and isinstance(crianca_selecionada, dict):
                        try: 
                            id_c = crianca_selecionada.get("id")
                            salvar_tentativa(id_c, fase_atual["nome"], tempo_total, precisao, hesitacao, angulo_atual)
                        except Exception as e:
                            print(f"Erro ao salvar tentativa: {e}")
                    
                    tentativas_precisoes.append(precisao)
                    coordenadas_usuario = []
                    coordenadas_salvas_para_desenho = []
                    tempos_toque = []
                    
                    if len(tentativas_precisoes) >= 5:
                        media_precisao = sum(tentativas_precisoes) / 5.0
                        
                        if media_precisao >= 50.0:
                            angulo_atual = min(LIMITE_ANGULO_MAXIMO, angulo_atual + 1.5)
                            id_fase_dinamica += 1
                            
                            if angulo_atual >= LIMITE_ANGULO_MAXIMO:
                                jogo_finalizado = True
                                mensagem_status = f"Parabéns! Média {media_precisao:.1f}%. Limite de {LIMITE_ANGULO_MAXIMO}° alcançado!"
                            else:
                                mensagem_status = f"Média: {media_precisao:.1f}% (>=50%). Subindo +1.5° -> Ângulo: {angulo_atual}°"
                        else:
                            angulo_atual = max(0.0, angulo_atual - 1.5)
                            mensagem_status = f"Média: {media_precisao:.1f}% (<50%). Voltando -1.5° -> Ângulo: {angulo_atual}°"
                        
                        tentativas_precisoes = []
                        tentativa_atual_num = 1
                        fase_atual = gerar_fase_por_angulo(id_fase_dinamica, angulo_atual)
                    else:
                        tentativa_atual_num = len(tentativas_precisoes) + 1
                        mensagem_status = f"Tentativa {tentativa_atual_num} de 5 (Última precisão: {precisao:.1f}%)"
                else:
                    mensagem_status = f"Soltou fora da Casinha! Repetindo tentativa {tentativa_atual_num} de 5."
                    coordenadas_usuario = []
                    coordenadas_salvas_para_desenho = []
                    tempos_toque = []
                    
        # DESENHO DA TELA DE JOGO
        tela.fill(COR_FUNDO)
        
        desenhar_linha_pontilhada(tela, COR_GUIA, p_init, p_end, largura=6, comp_traco=15, espaco=10)
        
        if len(coordenadas_usuario) > 1:
            desenhar_rastro_tracejada(tela, cor_rastro_atual, coordenadas_usuario, largura=5, comp_traco=10, espaco=6)

        img_casinha = icones.get("Casinha")
        if img_casinha:
            rect_casinha = img_casinha.get_rect(center=p_end)
            tela.blit(img_casinha, rect_casinha)
        else:
            pygame.draw.circle(tela, COR_ALVO, p_end, 25)

        img_mascote = icones.get("Cão")
        pos_mascote = p_init
        if desenhando and len(coordenadas_usuario) > 0:
            pos_mascote = coordenadas_usuario[-1]
            
        if img_mascote:
            rect_mascote = img_mascote.get_rect(center=pos_mascote)
            tela.blit(img_mascote, rect_mascote)
        else:
            pygame.draw.circle(tela, COR_INICIO, pos_mascote, 20)
                
        if jogo_finalizado:
            cor_mf = COR_BOTAO_HOVER if btn_menu_fim.collidepoint(mouse_pos_virtual) else COR_INICIO
            pygame.draw.rect(tela, cor_mf, btn_menu_fim, border_radius=10)
            txt_fim_img = fonte.render(texto_fim, True, COR_BRANCO)
            tela.blit(txt_fim_img, txt_fim_img.get_rect(center=btn_menu_fim.center))
        else:
            cor_sj = COR_BOTAO_HOVER if btn_sair_jogo.collidepoint(mouse_pos_virtual) else COR_BOTAO
            pygame.draw.rect(tela, cor_sj, btn_sair_jogo, border_radius=5)
            txt_sair_img = fonte.render("Sair", True, COR_TEXTO)
            tela.blit(txt_sair_img, txt_sair_img.get_rect(center=btn_sair_jogo.center))

        tela.blit(fonte.render(mensagem_status, True, COR_TEXTO), (20, 20))
        tela.blit(fonte.render(f"Fase Atual: Ângulo {angulo_atual}° | Cor Traço: {cor_nome} | Progresso: {len(tentativas_precisoes)}/5", True, COR_TEXTO), (20, ALTURA_ORIGINAL - 40))

    # ==========================================
    #   RENDERIZAÇÃO ESCALONADA NA TELA REAL
    # ==========================================
    # 1. Preenche as bordas com a cor de fundo padrão (Letterbox/Pillarbox)
    tela_real.fill(COR_FUNDO)
    
    # 2. Calcula a nova proporção e a posição centralizada na janela física
    escala, offset_x, offset_y, rect_destino = obter_parametros_escala()
    
    # 3. Redimensiona o canvas virtual proporcionalmente e desenha no centro da tela real
    tela_redimensionada = pygame.transform.smoothscale(tela, (rect_destino.width, rect_destino.height))
    tela_real.blit(tela_redimensionada, rect_destino.topleft)

    # Atualiza o quadro da tela
    pygame.display.flip()
    relogio.tick(60)

pygame.quit()