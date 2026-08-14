import pygame
import math
import time
import os
import json

# Importando os módulos atualizados do projeto
from algoritmo.analise import calcular_metricas
from dados.database import (
    iniciar_banco, 
    salvar_tentativa, 
    obter_ultimas_tentativas, 
    salvar_crianca, 
    obter_criancas,
    remover_crianca
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

# Configuração da Janela
LARGURA, ALTURA = 1280, 720
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("PlayDot")
relogio = pygame.time.Clock()

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

LARGURA_LOGO, ALTURA_LOGO = 355, 280

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

# Estado do Som por Criança (padrão True/Ligado)
som_temp = True

# Modal de Exclusão
modal_excluir_ativo = False
crianca_para_excluir = None

cor_tracado_temp = "Azul"
ruido_temp = "Baixo"

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

# ==========================================
#  FUNÇÕES AUXILIARES
# ==========================================

def desenhar_linha_tracejada(superficie, cor, inicio, fim, largura=4, comp_traco=12, espaco=8):
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

def gerar_fase_por_angulo(id_fase, angulo_graus, comprimento=700):
    centro_x, centro_y = LARGURA // 2, ALTURA // 2
    
    angulo_rad = math.radians(angulo_graus)
    metade_comp = comprimento / 2
    
    dx = metade_comp * math.cos(angulo_rad)
    dy = metade_comp * math.sin(angulo_rad)
    
    x_init = max(100, min(int(centro_x - dx), LARGURA - 100))
    y_init = max(100, min(int(centro_y + dy), ALTURA - 100))
    x_end = max(100, min(int(centro_x + dx), LARGURA - 100))
    y_end = max(100, min(int(centro_y - dy), ALTURA - 100))
    
    return {
        "id": id_fase,
        "nome": f"Fase Adaptativa - Angulo {angulo_graus}°",
        "tipo": "reta",
        "angulo": angulo_graus,
        "ponto_inicio": [x_init, y_init],
        "ponto_fim": [x_end, y_end],
        "pontos_guia": []
    }

fase_atual = gerar_fase_por_angulo(id_fase_dinamica, angulo_atual)

# ==========================================
#  TELAS DE INTERFACE
# ==========================================

def desenhar_menu_responsavel():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    if icones.get("Logotipo"):
        rect_logo = icones["Logotipo"].get_rect(center=(LARGURA // 2, 160))
        tela.blit(icones["Logotipo"], rect_logo)
    
    L_BTN, A_BTN = 420, 65
    
    btn_jogar = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_jogar.center = (LARGURA // 2, 340)
    
    btn_configs = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_configs.center = (LARGURA // 2, 430)
    
    btn_sair = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_sair.center = (LARGURA // 2, 520)
    
    botoes = [
        (btn_jogar, "Iniciar Jogo (Criança)", COR_INICIO, COR_BRANCO),
        (btn_configs, "Configurações", COR_BOTAO, COR_TEXTO),
        (btn_sair, "Sair do Jogo", COR_ALVO, COR_BRANCO)
    ]
    
    for rect, texto, cor_padrao, cor_txt in botoes:
        cor = COR_BOTAO_HOVER if rect.collidepoint(mouse_pos) else cor_padrao
        pygame.draw.rect(tela, cor, rect, border_radius=12)
        img_texto = fonte.render(texto, True, cor_txt if cor != COR_BOTAO_HOVER else COR_TEXTO)
        tela.blit(img_texto, img_texto.get_rect(center=rect.center))
        
    return btn_jogar, btn_configs, btn_sair

def desenhar_tela_pin_acesso(titulo="Acesso do Responsável"):
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render(titulo, True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.2)))
    
    txt_instrucao = fonte.render("Insira o PIN de 4 dígitos para continuar:", True, COR_TEXTO)
    tela.blit(txt_instrucao, txt_instrucao.get_rect(center=(LARGURA // 2, ALTURA * 0.32)))
    
    caixa_senha = pygame.Rect(0, 0, 250, 60)
    caixa_senha.center = (LARGURA // 2, ALTURA * 0.43)
    pygame.draw.rect(tela, COR_BRANCO, caixa_senha, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, caixa_senha, width=3, border_radius=5)
    
    texto_escondido = "*" * len(pin_digitado)
    txt_pin = fonte_titulo.render(texto_escondido, True, COR_TEXTO)
    tela.blit(txt_pin, txt_pin.get_rect(center=caixa_senha.center))
    
    btn_confirmar = pygame.Rect(0, 0, 160, 45)
    btn_confirmar.center = (LARGURA // 2 + 100, ALTURA * 0.65)
    cor_conf = COR_BOTAO_HOVER if btn_confirmar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_conf, btn_confirmar, border_radius=10)
    txt_conf = fonte.render("Confirmar", True, COR_TEXTO)
    tela.blit(txt_conf, txt_conf.get_rect(center=btn_confirmar.center))
    
    btn_cancelar = pygame.Rect(0, 0, 160, 45)
    btn_cancelar.center = (LARGURA // 2 - 100, ALTURA * 0.65)
    cor_canc = COR_BOTAO_HOVER if btn_cancelar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_canc, btn_cancelar, border_radius=10)
    txt_canc = fonte.render("Cancelar", True, COR_TEXTO)
    tela.blit(txt_canc, txt_canc.get_rect(center=btn_cancelar.center))
    
    if mensagem_erro_pin:
        txt_erro = fonte.render(mensagem_erro_pin, True, (180, 50, 50))
        tela.blit(txt_erro, txt_erro.get_rect(center=(LARGURA // 2, ALTURA * 0.55)))
        
    return btn_confirmar, btn_cancelar

def desenhar_menu_crianca():
    global pagina_menu_crianca
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()

    img_titulo = fonte_titulo.render("Quem vai jogar hoje?", True, COR_TEXTO)
    tela.blit(img_titulo, img_titulo.get_rect(center=(LARGURA // 2, 80)))

    recs_criancas = []

    if not lista_criancas:
        img_aviso = fonte.render(
            "Nenhuma criança cadastrada ainda.", True, COR_TEXTO
        )
        tela.blit(
            img_aviso, img_aviso.get_rect(center=(LARGURA // 2, ALTURA // 2))
        )
    else:
        COLUNAS = 3
        largura_card, altura_card = 280, 110
        espacamento_x, espacamento_y = 30, 25
        inicio_y = 170

        # Lógica de Paginação (Máximo 6 crianças por página = 2 linhas x 3 colunas)
        total_paginas = (len(lista_criancas) + CRIANCAS_POR_PAGINA_MENU - 1) // CRIANCAS_POR_PAGINA_MENU
        pagina_menu_crianca = max(0, min(pagina_menu_crianca, total_paginas - 1))

        inicio_idx = pagina_menu_crianca * CRIANCAS_POR_PAGINA_MENU
        criancas_pagina = lista_criancas[inicio_idx:inicio_idx + CRIANCAS_POR_PAGINA_MENU]

        largura_total_grid = (COLUNAS * largura_card) + ((COLUNAS - 1) * espacamento_x)
        inicio_x = (LARGURA - largura_total_grid) // 2

        for idx, cr in enumerate(criancas_pagina):
            col = idx % COLUNAS
            lin = idx // COLUNAS

            x = inicio_x + col * (largura_card + espacamento_x)
            y = inicio_y + lin * (altura_card + espacamento_y)

            rect_card = pygame.Rect(x, y, largura_card, altura_card)

            sel = (
                crianca_selecionada
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
            pygame.draw.rect(
                tela, cor_borda, rect_card, width=3 if sel else 2, border_radius=15
            )

            nome = cr.get("nome", f"Criança {idx+1}")
            img_nome = fonte.render(nome, True, COR_TEXTO)
            tela.blit(
                img_nome,
                img_nome.get_rect(
                    center=(rect_card.centerx, rect_card.top + 38)
                ),
            )

            nasc = cr.get("nascimento", "")
            texto_nasc = f"Nasc: {nasc}" if nasc else ""
            if texto_nasc:
                img_nasc = font_campo.render(texto_nasc, True, (100, 100, 100))
                tela.blit(
                    img_nasc,
                    img_nasc.get_rect(
                        center=(rect_card.centerx, rect_card.top + 75)
                    ),
                )

            recs_criancas.append((rect_card, cr))

        # Botões de Setas (< e >) do Carrossel do Menu Principal
        if pagina_menu_crianca > 0:
            btn_prev_m = pygame.Rect(inicio_x - 60, inicio_y + altura_card - 20, 45, 50)
            cor_prev = COR_BOTAO_HOVER if btn_prev_m.collidepoint(mouse_pos) else COR_BOTAO
            pygame.draw.rect(tela, cor_prev, btn_prev_m, border_radius=8)
            txt_p = fonte_titulo.render("<", True, COR_TEXTO)
            tela.blit(txt_p, txt_p.get_rect(center=btn_prev_m.center))
            recs_criancas.append((btn_prev_m, "PAGINA_ANTERIOR"))

        if pagina_menu_crianca < total_paginas - 1:
            btn_next_m = pygame.Rect(inicio_x + largura_total_grid + 15, inicio_y + altura_card - 20, 45, 50)
            cor_next = COR_BOTAO_HOVER if btn_next_m.collidepoint(mouse_pos) else COR_BOTAO
            pygame.draw.rect(tela, cor_next, btn_next_m, border_radius=8)
            txt_n = fonte_titulo.render(">", True, COR_TEXTO)
            tela.blit(txt_n, txt_n.get_rect(center=btn_next_m.center))
            recs_criancas.append((btn_next_m, "PAGINA_PROXIMA"))

    btn_cont = pygame.Rect(0, 0, 220, 50)
    btn_cont.center = (LARGURA // 2 + 130, ALTURA - 70)

    btn_volt = pygame.Rect(0, 0, 220, 50)
    btn_volt.center = (LARGURA // 2 - 130, ALTURA - 70)

    cor_btn_cont = (
        COR_INICIO if crianca_selecionada else (200, 200, 200)
    )
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
    mouse_pos = pygame.mouse.get_pos()
    
    centro_x = LARGURA // 2
    inicio_x_rotulo = centro_x - 350
    inicio_x_opcao = centro_x - 110

    texto_titulo = fonte_titulo.render("Configurações", True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(centro_x, 45)))
    
    # 1. Botões de Cadastrar e Remover Criança
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

    # 2. Carrossel de Seleção de Criança
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

        # Botão Anterior (<)
        if pagina_crianca_config > 0:
            btn_prev_pag = pygame.Rect(inicio_x_opcao - 35, 150, 30, 35)
            pygame.draw.rect(tela, COR_BOTAO, btn_prev_pag, border_radius=5)
            tela.blit(font_campo.render("<", True, COR_TEXTO), font_campo.render("<", True, COR_TEXTO).get_rect(center=btn_prev_pag.center))

        # Lista de Crianças da página atual
        for idx, cr in enumerate(criancas_pagina):
            rect_cr = pygame.Rect(inicio_x_opcao + (idx * 145), 150, 135, 35)
            is_selected = crianca_config_selecionada and crianca_config_selecionada.get("id") == cr.get("id")
            cor = COR_INPUT_ATIVO if is_selected else (COR_BOTAO_HOVER if rect_cr.collidepoint(mouse_pos) else COR_BOTAO)
            pygame.draw.rect(tela, cor, rect_cr, border_radius=5)
            
            nome_curto = cr['nome'][:8] + "..." if len(cr['nome']) > 8 else cr['nome']
            txt_c = font_campo.render(nome_curto, True, COR_TEXTO)
            tela.blit(txt_c, txt_c.get_rect(center=rect_cr.center))
            botoes_criancas.append((rect_cr, cr))

        # Botão Próximo (>)
        if pagina_crianca_config < total_paginas - 1:
            btn_next_pag = pygame.Rect(inicio_x_opcao + (3 * 145), 150, 30, 35)
            pygame.draw.rect(tela, COR_BOTAO, btn_next_pag, border_radius=5)
            tela.blit(font_campo.render(">", True, COR_TEXTO), font_campo.render(">", True, COR_TEXTO).get_rect(center=btn_next_pag.center))

    pygame.draw.line(tela, COR_GUIA, (inicio_x_rotulo, 205), (inicio_x_rotulo + 700, 205), 2)

    # 3. Cor do Traçado
    tela.blit(fonte.render("Cor do Traçado:", True, COR_TEXTO), (inicio_x_rotulo, 225))
    botoes_cores = []
    x_cor = inicio_x_opcao
    for nome_cor, valor_rgb in OPCOES_CORES_TRACADO.items():
        rect_cor = pygame.Rect(x_cor, 220, 90, 35)
        is_sel = (cor_tracado_temp == nome_cor)
        if is_sel:
            pygame.draw.rect(tela, COR_TEXTO, rect_cor.inflate(4, 4), border_radius=7)
            
        pygame.draw.rect(tela, valor_rgb, rect_cor, border_radius=5)
        txt_cor = font_campo.render(nome_cor, True, COR_BRANCO if nome_cor in ["Azul", "Verde", "Vermelho"] else COR_TEXTO)
        tela.blit(txt_cor, txt_cor.get_rect(center=rect_cor.center))
        botoes_cores.append((rect_cor, nome_cor))
        x_cor += 100

    # 4. Configuração de Som (Individual por Criança)
    tela.blit(fonte.render("Efeitos Sonoros:", True, COR_TEXTO), (inicio_x_rotulo, 280))
    btn_som_on = pygame.Rect(inicio_x_opcao, 275, 110, 35)
    btn_som_off = pygame.Rect(inicio_x_opcao + 120, 275, 110, 35)
    
    pygame.draw.rect(tela, COR_INPUT_ATIVO if som_temp else COR_BOTAO, btn_som_on, border_radius=5)
    tela.blit(fonte.render("Ligado", True, COR_TEXTO), fonte.render("Ligado", True, COR_TEXTO).get_rect(center=btn_som_on.center))

    pygame.draw.rect(tela, COR_INPUT_ATIVO if not som_temp else COR_BOTAO, btn_som_off, border_radius=5)
    tela.blit(fonte.render("Mudo", True, COR_TEXTO), fonte.render("Mudo", True, COR_TEXTO).get_rect(center=btn_som_off.center))

    # 5. Seleção de Ruído
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

    # 6. Alterar PIN Parental
    tela.blit(fonte.render("Alterar PIN Parental:", True, COR_TEXTO), (inicio_x_rotulo, 400))
    rect_novo_pin = pygame.Rect(inicio_x_opcao, 395, 150, 40)
    cor_p = COR_INPUT_ATIVO if campo_config_ativo == "pin" else COR_BRANCO
    pygame.draw.rect(tela, cor_p, rect_novo_pin, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, rect_novo_pin, width=2, border_radius=5)
    renderizar_texto_com_scroll(temp_pin_novo, "", 150, inicio_x_opcao, 395)

    # Botões Salvar e Cancelar
    btn_cancelar = pygame.Rect(0, 500, 180, 45)
    btn_cancelar.centerx = centro_x - 110
    cor_ca = COR_BOTAO_HOVER if btn_cancelar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_ca, btn_cancelar, border_radius=10)
    tela.blit(fonte.render("Cancelar", True, COR_TEXTO), fonte.render("Cancelar", True, COR_TEXTO).get_rect(center=btn_cancelar.center))

    btn_confirmar = pygame.Rect(0, 500, 180, 45)
    btn_confirmar.centerx = centro_x + 110
    cor_co = COR_BOTAO_HOVER if btn_confirmar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_co, btn_confirmar, border_radius=10)
    tela.blit(fonte.render("Salvar", True, COR_TEXTO), fonte.render("Salvar", True, COR_TEXTO).get_rect(center=btn_confirmar.center))

    return btn_cadastrar_novo, btn_remover_crianca, botoes_criancas, btn_prev_pag, btn_next_pag, botoes_cores, btn_som_on, btn_som_off, btn_r_baixo, btn_r_medio, rect_novo_pin, btn_confirmar, btn_cancelar

def desenhar_modal_confirmacao(nome_crianca):
    overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    tela.blit(overlay, (0, 0))

    rect_modal = pygame.Rect(0, 0, 480, 200)
    rect_modal.center = (LARGURA // 2, ALTURA // 2)

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
    mouse_pos = pygame.mouse.get_pos()

    centro_x = LARGURA // 2
    inicio_x_campos = centro_x - 300

    texto_titulo = fonte_titulo.render("Cadastro de Criança", True, COR_TEXTO)
    tela.blit(
        texto_titulo,
        texto_titulo.get_rect(center=(centro_x, ALTURA * 0.10)),
    )

    rect_nome = pygame.Rect(inicio_x_campos, 160, 600, 40)
    cor_n = COR_INPUT_ATIVO if campo_ativo == "nome" else COR_BRANCO
    pygame.draw.rect(tela, cor_n, rect_nome, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, rect_nome, width=2, border_radius=5)
    renderizar_texto_com_scroll(
        input_cadastro["nome"], "Nome: ", 600, inicio_x_campos, 160
    )

    rect_nasc = pygame.Rect(inicio_x_campos, 230, 300, 40)
    cor_na = COR_INPUT_ATIVO if campo_ativo == "nascimento" else COR_BRANCO
    pygame.draw.rect(tela, cor_na, rect_nasc, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, rect_nasc, width=2, border_radius=5)
    renderizar_texto_com_scroll(
        input_cadastro["nascimento"],
        "Data Nasc.: ",
        300,
        inicio_x_campos,
        230,
    )

    rect_sexo_m = pygame.Rect(inicio_x_campos + 350, 230, 110, 40)
    cor_sm = (
        COR_INPUT_ATIVO
        if input_cadastro["sexo"] == "Masculino"
        else COR_BOTAO
    )
    pygame.draw.rect(tela, cor_sm, rect_sexo_m, border_radius=5)
    txt_sm = font_campo.render("Masculino", True, COR_TEXTO)
    tela.blit(txt_sm, txt_sm.get_rect(center=rect_sexo_m.center))

    rect_sexo_f = pygame.Rect(inicio_x_campos + 480, 230, 110, 40)
    cor_sf = (
        COR_INPUT_ATIVO if input_cadastro["sexo"] == "Feminino" else COR_BOTAO
    )
    pygame.draw.rect(tela, cor_sf, rect_sexo_f, border_radius=5)
    txt_sf = font_campo.render("Feminino", True, COR_TEXTO)
    tela.blit(txt_sf, txt_sf.get_rect(center=rect_sexo_f.center))

    btn_cancelar = pygame.Rect(0, 480, 180, 45)
    btn_cancelar.centerx = (centro_x) - 110
    cor_ca = (
        COR_BOTAO_HOVER if btn_cancelar.collidepoint(mouse_pos) else COR_BOTAO
    )
    pygame.draw.rect(tela, cor_ca, btn_cancelar, border_radius=10)
    txt_ca = fonte.render("Cancelar", True, COR_TEXTO)
    tela.blit(txt_ca, txt_ca.get_rect(center=btn_cancelar.center))

    btn_confirmar = pygame.Rect(0, 480, 180, 45)
    btn_confirmar.centerx = (centro_x) + 110
    cor_co = (
        COR_BOTAO_HOVER if btn_confirmar.collidepoint(mouse_pos) else COR_BOTAO
    )
    pygame.draw.rect(tela, cor_co, btn_confirmar, border_radius=10)
    txt_co = fonte.render("Confirmar", True, COR_TEXTO)
    tela.blit(txt_co, txt_co.get_rect(center=btn_confirmar.center))

    return (
        rect_nome,
        rect_nasc,
        rect_sexo_m,
        rect_sexo_f,
        btn_confirmar,
        btn_cancelar,
    )

def desenhar_tela_estatisticas():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render("Estatísticas de Desempenho", True, COR_TEXTO)
    rect_titulo = texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.12))
    tela.blit(texto_titulo, rect_titulo)
    
    dados = []
    if db_ativo:
        try: dados = obter_ultimas_tentativas(5)
        except Exception: dados = []

    colunasY = int(ALTURA * 0.25)
    titulos_colunas = ["Fase", "Tempo", "Precisão", "Taxa de Erro"]
    posicoes_x = [50, 300, 480, 640]
    
    for i, col_nome in enumerate(titulos_colunas):
        txt_col = fonte.render(col_nome, True, COR_TEXTO)
        tela.blit(txt_col, (posicoes_x[i], colunasY))
        
    pygame.draw.line(tela, COR_GUIA, (50, colunasY + 30), (750, colunasY + 30), 2)
    
    if not dados:
        txt_vazio = fonte.render("Sem dados de teste gravados no banco local.", True, (150, 150, 150))
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
            
            cor_erro = (180, 50, 50) if taxa_erro_val > 30.0 else COR_TEXTO
            tela.blit(fonte.render(taxa_erro, True, cor_erro), (posicoes_x[3], linhaY))

    btn_voltar_rect = pygame.Rect(0, 0, 200, 50)
    btn_voltar_rect.center = (LARGURA // 2, ALTURA * 0.88)
    cor = COR_BOTAO_HOVER if btn_voltar_rect.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor, btn_voltar_rect, border_radius=10)
    
    txt_voltar = fonte.render("Voltar ao Menu", True, COR_TEXTO)
    tela.blit(txt_voltar, txt_voltar.get_rect(center=btn_voltar_rect.center))
    
    return btn_voltar_rect

# ==========================================
#             LOOP PRINCIPAL
# ==========================================
rodando = True
while rodando:

    # ------------------ MENU PRINCIPAL ------------------
    if estado_jogo == "MENU_RESPONSAVEL":
        btn_jogar, btn_configs, btn_sair = desenhar_menu_responsavel()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_jogar.collidepoint(evento.pos):
                    lista_criancas = obter_criancas() if db_ativo else []
                    estado_jogo = "MENU_CRIANCA"
                elif btn_configs.collidepoint(evento.pos):
                    destino_apos_pin = "CONFIGURACOES"
                    estado_jogo = "PIN_ACESSO"
                    pin_digitado = ""
                    mensagem_erro_pin = ""
                elif btn_sair.collidepoint(evento.pos):
                    rodando = False

    # ------------------ MENU SELEÇÃO DE CRIANÇA ------------------
    # ------------------ MENU SELEÇÃO DE CRIANÇA ------------------
    elif estado_jogo == "MENU_CRIANCA":
        # Chama a função ajustada (retorna exatamente 3 valores)
        recs_criancas, btn_cont, btn_volt = desenhar_menu_crianca()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False

            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                # 1. Verifica cliques nos cards de crianças E nas setas de página
                for rect, item in recs_criancas:
                    if rect.collidepoint(evento.pos):
                        
                        # Se clicou na seta de voltar página
                        if item == "PAGINA_ANTERIOR":
                            pagina_menu_crianca -= 1
                            
                        # Se clicou na seta de avançar página
                        elif item == "PAGINA_PROXIMA":
                            pagina_menu_crianca += 1
                            
                        # Se clicou em um card de criança válido
                        elif isinstance(item, dict):
                            crianca_selecionada = item

                # 2. Clique no botão Voltar (Menu Responsável)
                if btn_volt.collidepoint(evento.pos):
                    pagina_menu_crianca = 0  # Reseta a página ao sair
                    estado_jogo = "MENU_RESPONSAVEL"

                # 3. Clique no botão Continuar
                elif btn_cont.collidepoint(evento.pos):
                    # Garante que crianca_selecionada é um dicionário e existe na lista
                    ids_validos = [c["id"] for c in lista_criancas if isinstance(c, dict) and "id" in c]

                    if (isinstance(crianca_selecionada, dict) and 
                        crianca_selecionada.get("id") in ids_validos):

                        id_str = str(crianca_selecionada["id"])
                        cfg_cr = configs_jogo.get("config_criancas", {}).get(id_str, {})

                        cor_tracado_atual = cfg_cr.get("cor_tracado", "Azul")
                        som_ativo_atual = cfg_cr.get("som", True)

                        # Transição para o jogo
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
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_BACKSPACE:
                    pin_digitado = pin_digitado[:-1]
                elif len(pin_digitado) < 4 and evento.unicode.isdigit():
                    pin_digitado += evento.unicode
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_confirmar.collidepoint(evento.pos):
                    if pin_digitado == configs_jogo["pin"]:
                        if destino_apos_pin == "CONFIGURACOES":
                            temp_pin_novo = configs_jogo["pin"]
                            ruido_temp = configs_jogo.get("ruido", "Baixo")
                            lista_criancas = obter_criancas() if db_ativo else []
                            crianca_config_selecionada = lista_criancas[0] if lista_criancas else None
                            
                            if crianca_config_selecionada and isinstance(crianca_config_selecionada, dict):
                                id_str = str(crianca_config_selecionada.get("id", ""))
                                cor_tracado_temp = configs_jogo.get("config_criancas", {}).get(id_str, {}).get("cor_tracado", "Azul")
                            else:
                                cor_tracado_temp = "Azul"
                                
                            campo_config_ativo = None
                        
                        estado_jogo = destino_apos_pin
                    else:
                        mensagem_erro_pin = "PIN inválido! Digite o PIN correto."
                        pin_digitado = ""
                elif btn_cancelar.collidepoint(evento.pos):
                    estado_jogo = "MENU_RESPONSAVEL"

    # ------------------ CADASTRO DE CRIANÇA ------------------
    elif estado_jogo == "CADASTRO_CRIANCA":
        r_nome, r_nasc, r_sm, r_sf, btn_conf, btn_canc = desenhar_cadastro_crianca()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if r_nome.collidepoint(evento.pos):
                    campo_ativo = "nome"
                elif r_nasc.collidepoint(evento.pos):
                    campo_ativo = "nascimento"
                elif r_sm.collidepoint(evento.pos):
                    input_cadastro["sexo"] = "Masculino"
                elif r_sf.collidepoint(evento.pos):
                    input_cadastro["sexo"] = "Feminino"
                elif btn_conf.collidepoint(evento.pos):
                    if input_cadastro["nome"].strip():
                        if db_ativo:
                            try:
                                salvar_crianca(
                                    input_cadastro["nome"],
                                    input_cadastro["nascimento"],
                                    input_cadastro["sexo"],
                                    input_cadastro["obs"]
                                )
                                lista_criancas = obter_criancas()
                            except Exception as e:
                                print(f"Erro ao salvar no banco local: {e}")
                    estado_jogo = "CONFIGURACOES"
                elif btn_canc.collidepoint(evento.pos):
                    estado_jogo = "CONFIGURACOES"
            elif evento.type == pygame.KEYDOWN and campo_ativo:
                if evento.key == pygame.K_BACKSPACE:
                    if campo_ativo == "nascimento" and len(input_cadastro["nascimento"]) > 0:
                        if input_cadastro["nascimento"][-1] == "/":
                            input_cadastro["nascimento"] = input_cadastro["nascimento"][:-2]
                        else:
                            input_cadastro["nascimento"] = input_cadastro["nascimento"][:-1]
                    else:
                        input_cadastro[campo_ativo] = input_cadastro[campo_ativo][:-1]
                else:
                    if campo_ativo == "nome":
                        if not evento.unicode.isdigit():
                            input_cadastro["nome"] += evento.unicode
                    elif campo_ativo == "nascimento":
                        input_cadastro["nascimento"] = formatar_e_validar_data(input_cadastro["nascimento"], evento.unicode)
                    else:
                        input_cadastro[campo_ativo] += evento.unicode

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
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if modal_excluir_ativo and crianca_config_selecionada:
                    if btn_sim_del and btn_sim_del.collidepoint(evento.pos):
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

                    elif btn_nao_del and btn_nao_del.collidepoint(evento.pos):
                        modal_excluir_ativo = False

                else:
                    if btn_cad.collidepoint(evento.pos):
                        input_cadastro = {"nome": "", "nascimento": "", "sexo": "Masculino", "obs": ""}
                        campo_ativo = None
                        estado_jogo = "CADASTRO_CRIANCA"
                    
                    elif btn_del.collidepoint(evento.pos):
                        if crianca_config_selecionada:
                            modal_excluir_ativo = True

                    elif btn_prev_p and btn_prev_p.collidepoint(evento.pos):
                        pagina_crianca_config = max(0, pagina_crianca_config - 1)
                    elif btn_next_p and btn_next_p.collidepoint(evento.pos):
                        pagina_crianca_config += 1

                    for r_c, cr in btns_cr:
                        if r_c.collidepoint(evento.pos):
                            crianca_config_selecionada = cr
                            id_str = str(cr.get("id", ""))
                            cfg_cr = configs_jogo.get("config_criancas", {}).get(id_str, {})
                            cor_tracado_temp = cfg_cr.get("cor_tracado", "Azul")
                            som_temp = cfg_cr.get("som", True)
                    
                    for r_cor, nome_cor in btns_cor:
                        if r_cor.collidepoint(evento.pos):
                            cor_tracado_temp = nome_cor

                    if btn_s_on.collidepoint(evento.pos):
                        som_temp = True
                    elif btn_s_off.collidepoint(evento.pos):
                        som_temp = False
                    
                    elif btn_rb.collidepoint(evento.pos):
                        ruido_temp = "Baixo"
                        ajustar_volume_ruido("Baixo")
                    elif btn_rm.collidepoint(evento.pos):
                        ruido_temp = "Médio"
                        ajustar_volume_ruido("Médio")

                    elif r_pin.collidepoint(evento.pos):
                        campo_config_ativo = "pin"

                    elif btn_conf.collidepoint(evento.pos):
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

                    elif btn_canc.collidepoint(evento.pos):
                        configs_jogo = carregar_configuracoes()
                        estado_jogo = "MENU_RESPONSAVEL"
            
            elif evento.type == pygame.KEYDOWN and campo_config_ativo == "pin":
                if evento.key == pygame.K_BACKSPACE:
                    temp_pin_novo = temp_pin_novo[:-1]
                elif len(temp_pin_novo) < 4 and evento.unicode.isdigit():
                    temp_pin_novo += evento.unicode

    # ------------------ TELA DE ESTATÍSTICAS ------------------
    elif estado_jogo == "ESTATISTICAS":
        btn_voltar = desenhar_tela_estatisticas()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_voltar.collidepoint(evento.pos):
                    estado_jogo = "MENU_RESPONSAVEL"

    # ------------------ TELA DE JOGO ------------------
    elif estado_jogo == "JOGANDO":
        if crianca_selecionada and isinstance(crianca_selecionada, dict):
            ids_validos = [c["id"] for c in lista_criancas if isinstance(c, dict) and "id" in c]
            if crianca_selecionada.get("id") not in ids_validos:
                crianca_selecionada = None

        p_init = fase_atual["ponto_inicio"]
        p_end = fase_atual["ponto_fim"]
        mouse_pos = pygame.mouse.get_pos()

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
        btn_sair_jogo = pygame.Rect(LARGURA - largura_btn_sair - 25, 20, largura_btn_sair, 35)
        
        texto_fim = "Voltar ao Menu Principal"
        texto_fim_largura, texto_fim_altura = fonte.size(texto_fim)
        btn_menu_fim = pygame.Rect(0, 0, texto_fim_largura + 50, texto_fim_altura + 20)
        btn_menu_fim.center = (LARGURA // 2, 510)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
                
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if jogo_finalizado:
                    if btn_menu_fim.collidepoint(evento.pos):
                        if som_ruido:
                            som_ruido.stop()
                        estado_jogo = "MENU_RESPONSAVEL"
                else:
                    if btn_sair_jogo.collidepoint(evento.pos):
                        if som_ruido:
                            som_ruido.stop()
                        estado_jogo = "MENU_RESPONSAVEL"
                    else:
                        dist_inicio = math.sqrt((evento.pos[0] - p_init[0])**2 + (evento.pos[1] - p_init[1])**2)
                        if dist_inicio <= 35:
                            desenhando = True
                            coordenadas_usuario = [evento.pos]
                            coordenadas_salvas_para_desenho = []
                            tempos_toque = [time.time()]
                        
            elif evento.type == pygame.MOUSEMOTION and desenhando:
                coordenadas_usuario.append(evento.pos)
                tempos_toque.append(time.time())
                
            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1 and desenhando:
                desenhando = False
                dist_alvo = math.sqrt((evento.pos[0] - p_end[0])**2 + (evento.pos[1] - p_end[1])**2)
                
                if dist_alvo <= 35:
                    precisao, hesitacao = calcular_metricas(
                        fase_atual["tipo"], p_init, p_end,
                        fase_atual.get("pontos_guia", []), coordenadas_usuario, tempos_toque
                    )
                    tempo_total = tempos_toque[-1] - tempos_toque[0] if tempos_toque else 0.0
                    
                    if db_ativo:
                        try: salvar_tentativa(fase_atual["nome"], tempo_total, precisao, hesitacao)
                        except: pass
                    
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
        
        desenhar_linha_tracejada(tela, COR_GUIA, p_init, p_end, largura=6, comp_traco=15, espaco=10)
        
        if len(coordenadas_usuario) > 1:
            desenhar_rastro_tracejada(tela, cor_rastro_atual, coordenadas_usuario, largura=5, comp_traco=10, espaco=6)

        img_casinha = icones["Casinha"]
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
            cor_mf = COR_BOTAO_HOVER if btn_menu_fim.collidepoint(mouse_pos) else COR_INICIO
            pygame.draw.rect(tela, cor_mf, btn_menu_fim, border_radius=10)
            txt_fim_img = fonte.render(texto_fim, True, COR_BRANCO)
            tela.blit(txt_fim_img, txt_fim_img.get_rect(center=btn_menu_fim.center))
        else:
            cor_sj = COR_BOTAO_HOVER if btn_sair_jogo.collidepoint(mouse_pos) else COR_BOTAO
            pygame.draw.rect(tela, cor_sj, btn_sair_jogo, border_radius=5)
            txt_sair_img = fonte.render("Sair", True, COR_TEXTO)
            tela.blit(txt_sair_img, txt_sair_img.get_rect(center=btn_sair_jogo.center))

        tela.blit(fonte.render(mensagem_status, True, COR_TEXTO), (20, 20))
        tela.blit(fonte.render(f"Fase Atual: Ângulo {angulo_atual}° | Cor Traço: {cor_nome} | Progresso: {len(tentativas_precisoes)}/5", True, COR_TEXTO), (20, ALTURA - 40))

    # Atualiza o quadro da tela
    pygame.display.flip()
    relogio.tick(60)

pygame.quit()