import pygame
import json
import math
import time
import os

# Importando os outros módulos criados
from ia.analise import calcular_metricas
from dados.database import iniciar_banco, salvar_tentativa, obter_ultimas_tentativas

# Inicialização
pygame.init()
pygame.font.init()

# Tenta iniciar o banco, sem travar o jogo se falhar
try:
    iniciar_banco()
    db_ativo = True
except Exception as e:
    print(f"Aviso: Banco de dados inativo. Rodando em modo de simulação local. Erro: {e}")
    db_ativo = False

# Janela
LARGURA, ALTURA = 800, 600
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("PlayDot")
relogio = pygame.time.Clock()

# Cores
COR_FUNDO = (245, 245, 245)
COR_GUIA = (210, 210, 210)
COR_RASTRO = (70, 130, 180)     
COR_INICIO = (46, 139, 87)      
COR_ALVO = (30, 144, 255)       
COR_TEXTO = (50, 50, 50)
COR_BOTAO = (220, 220, 220)
COR_BOTAO_HOVER = (180, 200, 220)
COR_INPUT_ATIVO = (150, 180, 220)
COR_BRANCO = (255, 255, 255)

fonte = pygame.font.SysFont("comic sans", 22)
fonte_titulo = pygame.font.SysFont("comic sans", 40, bold=True)
font_campo = pygame.font.SysFont("comic sans", 18)

# ==========================================
#  VARIÁVEIS GLOBAIS DE ESTADO E SIMULAÇÃO
# ==========================================

estado_jogo = "ABERTURA"  

pin_correto = "0000"
pin_digitado = ""
mensagem_erro_pin = ""

lista_criancas = []
crianca_selecionada = None

# Campos de digitação do cadastro
input_cadastro = {"nome": "", "nascimento": "", "sexo": "Masculino", "obs": ""}
campo_ativo = None  

configs_jogo = {
    "ruido": "Baixo",
    "brilho": 200,
    "pin": "1234"
}
campo_config_ativo = None
temp_pin_novo = ""

fase_concluida = False
jogo_finalizado = False  
resultado_rodada = {"precisao": 0.0, "tempo": 0.0, "novo_angulo": 0.0, "status": ""}
coordenadas_salvas_para_desenho = []

LIMITE_ANGULO_MAXIMO = 30.0

# --- FUNÇÕES DE AUXÍLIO DE RENDERIZAÇÃO E FORMATAÇÃO ---

def renderizar_texto_com_scroll(texto_completo, prefixo, largura_maxima_util, rect_x, rect_y):
    """
    Renderiza o prefixo fixo e realiza o corte dinâmico do texto do final para o início.
    Garante o efeito de scroll automático para a direita à medida que o usuário escreve.
    """
    img_prefixo = font_campo.render(prefixo, True, COR_TEXTO)
    largura_prefixo = img_prefixo.get_width()
    
    # Margem de segurança de 20px interna no retângulo
    largura_disponivel_texto = largura_maxima_util - largura_prefixo - 20
    
    # Adiciona o cursor visual de digitação se o campo estiver ativo
    texto_com_cursor = texto_completo + "|"
    
    # Descobre qual parte do final da string cabe no espaço do input
    texto_visivel = texto_com_cursor
    for i in range(len(texto_com_cursor) + 1):
        texto_visivel = texto_com_cursor[i:]
        img_teste = font_campo.render(texto_visivel, True, COR_TEXTO)
        if img_teste.get_width() <= largura_disponivel_texto:
            break
            
    # Blit do prefixo fixo e do texto cortado com scroll
    tela.blit(img_prefixo, (rect_x + 10, rect_y + 10))
    img_texto_final = font_campo.render(texto_visivel, True, COR_TEXTO)
    tela.blit(img_texto_final, (rect_x + 10 + largura_prefixo, rect_y + 10))

def formatar_e_validar_data(texto_atual, novo_char):
    """
    Formata a string para DD/MM/AAAA em tempo de execução e valida os limites numéricos.
    """
    apenas_numeros = "".join([c for c in texto_atual if c.isdigit()])
    
    if novo_char.isdigit():
        apenas_numeros += novo_char
        
    if len(apenas_numeros) > 8:
        apenas_numeros = apenas_numeros[:8]
        
    # Validações parciais em tempo real
    if len(apenas_numeros) >= 2:
        dia = int(apenas_numeros[0:2])
        if dia > 31: 
            return texto_atual  
        if dia == 0 and len(apenas_numeros) == 2:
            return texto_atual  
            
    if len(apenas_numeros) >= 4:
        mes = int(apenas_numeros[2:4])
        if mes > 12: 
            return texto_atual  
        if mes == 0 and len(apenas_numeros) == 4:
            return texto_atual  

    resultado = ""
    for idx, num in enumerate(apenas_numeros):
        if idx == 2 or idx == 4:
            resultado += "/"
        resultado += num
        
    return resultado

# --- FUNÇÕES DE FASE PROCEDURAL ---

def gerar_fase_por_angulo(id_fase, angulo_graus, comprimento=550):
    centro_x = 400
    centro_y = 300
    angulo_rad = math.radians(angulo_graus)
    metade_comp = comprimento / 2
    
    dx = metade_comp * math.cos(angulo_rad)
    dy = metade_comp * math.sin(angulo_rad)
    
    x_init = int(centro_x - dx)
    y_init = int(centro_y + dy)
    x_end = int(centro_x + dx)
    y_end = int(centro_y - dy)
    
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
    if precisao_anterior >= 80.0:
        novo_angulo = min(LIMITE_ANGULO_MAXIMO, angulo_atual + 2.5)
        status = "AVANCAR_RAPIDO"
    elif 60.0 <= precisao_anterior < 80.0:
        novo_angulo = min(LIMITE_ANGULO_MAXIMO, angulo_atual + 1.25)
        status = "AVANCAR_SUAVE"
    elif 50.0 <= precisao_anterior < 60.0:
        novo_angulo = angulo_atual
        status = "REPETIR"
    elif 30.0 <= precisao_anterior < 50.0:
        novo_angulo = max(0, angulo_atual - 2.5)
        status = "VOLTAR_UMA"
    else:
        novo_angulo = max(0, angulo_atual - 5)
        status = "VOLTAR_DUAS"
        
    return novo_angulo, status

# Inicialização do loop adaptativo
angulo_atual = 0  
id_fase_dinamica = 1
fase_atual = gerar_fase_por_angulo(id_fase_dinamica, angulo_atual)

coordenadas_usuario = []
tempos_toque = []
desenhando = False
mensagem_status = "Conecte o ponto Verde ao Alvo Azul"

# ==========================================
#  FUNÇÕES DE DESENHO E INTERFACES DE TELA
# ==========================================

def desenhar_tela_abertura():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    pygame.draw.circle(tela, COR_ALVO, (LARGURA // 2, ALTURA * 0.32), 60)
    pygame.draw.circle(tela, COR_INICIO, (LARGURA // 2 - 35, ALTURA * 0.32 + 20), 20)
    
    texto_logo = fonte_titulo.render("PlayDot", True, COR_TEXTO)
    tela.blit(texto_logo, texto_logo.get_rect(center=(LARGURA // 2, ALTURA * 0.48)))
    
    # Botão Iniciar
    btn_iniciar = pygame.Rect(0, 0, 220, 50)
    btn_iniciar.center = (LARGURA // 2, ALTURA * 0.68)
    cor_i = COR_BOTAO_HOVER if btn_iniciar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_i, btn_iniciar, border_radius=10)
    txt_btn = fonte.render("Iniciar", True, COR_TEXTO)
    tela.blit(txt_btn, txt_btn.get_rect(center=btn_iniciar.center))
    
    # Botão Sair
    btn_sair = pygame.Rect(0, 0, 220, 50)
    btn_sair.center = (LARGURA // 2, ALTURA * 0.78)
    cor_s = (240, 180, 180) if btn_sair.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_s, btn_sair, border_radius=10)
    txt_sair = fonte.render("Sair do Jogo", True, COR_TEXTO)
    tela.blit(txt_sair, txt_sair.get_rect(center=btn_sair.center))
    
    return btn_iniciar, btn_sair

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
    
    # Botões Confirmar e Cancelar Centralizados Corretamente
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

def desenhar_selecao_perfil():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render("Quem está acessando?", True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.25)))
    
    btn_resp = pygame.Rect(0, 0, 250, 80)
    btn_resp.center = (LARGURA // 2 - 150, ALTURA * 0.52)
    cor_resp = COR_BOTAO_HOVER if btn_resp.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_resp, btn_resp, border_radius=15)
    txt_resp = fonte.render("Responsável", True, COR_TEXTO)
    tela.blit(txt_resp, txt_resp.get_rect(center=btn_resp.center))
    
    btn_crianca = pygame.Rect(0, 0, 250, 80)
    btn_crianca.center = (LARGURA // 2 + 150, ALTURA * 0.52)
    cor_cri = COR_BOTAO_HOVER if btn_crianca.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_cri, btn_crianca, border_radius=15)
    txt_cri = fonte.render("Criança", True, COR_TEXTO)
    tela.blit(txt_cri, txt_cri.get_rect(center=btn_crianca.center))

    btn_voltar = pygame.Rect(0, 0, 160, 45)
    btn_voltar.center = (LARGURA // 2, ALTURA * 0.78)
    cor_volt = COR_BOTAO_HOVER if btn_voltar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_volt, btn_voltar, border_radius=10)
    txt_volt = fonte.render("Voltar", True, COR_TEXTO)
    tela.blit(txt_volt, txt_volt.get_rect(center=btn_voltar.center))
    
    return btn_resp, btn_crianca, btn_voltar

def desenhar_menu_responsavel():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render("Painel do Responsável", True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.15)))
    
    L_BTN, A_BTN = 300, 50
    
    btn_cadastrar = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_cadastrar.center = (LARGURA // 2, ALTURA * 0.35)
    
    btn_configs = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_configs.center = (LARGURA // 2, ALTURA * 0.47)
    
    btn_estats = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_estats.center = (LARGURA // 2, ALTURA * 0.59)
    
    btn_sair = pygame.Rect(0, 0, L_BTN, A_BTN)
    btn_sair.center = (LARGURA // 2, ALTURA * 0.71)
    
    botoes = [
        (btn_cadastrar, "Cadastrar Criança"),
        (btn_configs, "Configurações"),
        (btn_estats, "Estatísticas de Desempenho"),
        (btn_sair, "Sair / Voltar")
    ]
    
    for rect, texto in botoes:
        cor = COR_BOTAO_HOVER if rect.collidepoint(mouse_pos) else COR_BOTAO
        pygame.draw.rect(tela, cor, rect, border_radius=10)
        img_texto = fonte.render(texto, True, COR_TEXTO)
        tela.blit(img_texto, img_texto.get_rect(center=rect.center))
        
    return btn_cadastrar, btn_configs, btn_estats, btn_sair

def desenhar_cadastro_crianca():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render("Cadastro de Criança", True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.10)))
    
    # Campo Nome
    rect_nome = pygame.Rect(100, 160, 600, 40)
    cor_n = COR_INPUT_ATIVO if campo_ativo == "nome" else COR_BRANCO
    pygame.draw.rect(tela, cor_n, rect_nome, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, rect_nome, width=2, border_radius=5)
    renderizar_texto_com_scroll(input_cadastro['nome'], "Nome: ", 600, 100, 160)
    
    # Campo Data Nascimento
    rect_nasc = pygame.Rect(100, 230, 300, 40)
    cor_na = COR_INPUT_ATIVO if campo_ativo == "nascimento" else COR_BRANCO
    pygame.draw.rect(tela, cor_na, rect_nasc, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, rect_nasc, width=2, border_radius=5)
    renderizar_texto_com_scroll(input_cadastro['nascimento'], "Data Nasc.: ", 300, 100, 230)
    
    # Botões Sexo
    rect_sexo_m = pygame.Rect(450, 230, 110, 40)
    cor_sm = COR_INPUT_ATIVO if input_cadastro["sexo"] == "Masculino" else COR_BOTAO
    pygame.draw.rect(tela, cor_sm, rect_sexo_m, border_radius=5)
    tela.blit(font_campo.render("Masculino", True, COR_TEXTO), (460, 240))
    
    rect_sexo_f = pygame.Rect(580, 230, 110, 40)
    cor_sf = COR_INPUT_ATIVO if input_cadastro["sexo"] == "Feminino" else COR_BOTAO
    pygame.draw.rect(tela, cor_sf, rect_sexo_f, border_radius=5)
    tela.blit(font_campo.render("Feminino", True, COR_TEXTO), (595, 240))
    
    # Campo Observações
    rect_obs = pygame.Rect(100, 310, 600, 100)
    cor_o = COR_INPUT_ATIVO if campo_ativo == "obs" else COR_BRANCO
    pygame.draw.rect(tela, cor_o, rect_obs, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, rect_obs, width=2, border_radius=5)
    renderizar_texto_com_scroll(input_cadastro['obs'], "Observações: ", 600, 100, 310)
    
    # BOTÕES CENTRALIZADOS SIMETRICAMENTE EM RELAÇÃO À LARGURA DA TELA
    btn_cancelar = pygame.Rect(0, 480, 180, 45)
    btn_cancelar.centerx = (LARGURA // 2) - 110  
    cor_ca = COR_BOTAO_HOVER if btn_cancelar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_ca, btn_cancelar, border_radius=10)
    txt_ca = fonte.render("Cancelar", True, COR_TEXTO)
    tela.blit(txt_ca, txt_ca.get_rect(center=btn_cancelar.center))
    
    btn_confirmar = pygame.Rect(0, 480, 180, 45)
    btn_confirmar.centerx = (LARGURA // 2) + 110  
    cor_co = COR_BOTAO_HOVER if btn_confirmar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_co, btn_confirmar, border_radius=10)
    txt_co = fonte.render("Confirmar", True, COR_TEXTO)
    tela.blit(txt_co, txt_co.get_rect(center=btn_confirmar.center))
    
    return rect_nome, rect_nasc, rect_sexo_m, rect_sexo_f, rect_obs, btn_confirmar, btn_cancelar

def desenhar_tela_configuracoes():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render("Configurações", True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.10)))
    
    tela.blit(fonte.render("Seleção de Ruído:", True, COR_TEXTO), (100, 160))
    btn_r_baixo = pygame.Rect(320, 150, 110, 40)
    cor_rb = COR_INPUT_ATIVO if configs_jogo["ruido"] == "Baixo" else COR_BOTAO
    pygame.draw.rect(tela, cor_rb, btn_r_baixo, border_radius=5)
    tela.blit(fonte.render("Baixo", True, COR_TEXTO), (350, 158))
    
    btn_r_medio = pygame.Rect(450, 150, 110, 40)
    cor_rm = COR_INPUT_ATIVO if configs_jogo["ruido"] == "Médio" else COR_BOTAO
    pygame.draw.rect(tela, cor_rm, btn_r_medio, border_radius=5)
    tela.blit(fonte.render("Médio", True, COR_TEXTO), (480, 158))
    
    tela.blit(fonte.render(f"Brilho do Traço: {configs_jogo['brilho']}", True, COR_TEXTO), (100, 230))
    btn_brilho_menos = pygame.Rect(320, 220, 50, 40)
    pygame.draw.rect(tela, COR_BOTAO, btn_brilho_menos, border_radius=5)
    tela.blit(fonte.render("-", True, COR_TEXTO), (340, 225))
    
    btn_brilho_mais = pygame.Rect(400, 220, 50, 40)
    pygame.draw.rect(tela, COR_BOTAO, btn_brilho_mais, border_radius=5)
    tela.blit(fonte.render("+", True, COR_TEXTO), (420, 225))
    
    tela.blit(fonte.render("Alterar PIN Parental:", True, COR_TEXTO), (100, 300))
    rect_novo_pin = pygame.Rect(320, 290, 150, 40)
    cor_p = COR_INPUT_ATIVO if campo_config_ativo == "pin" else COR_BRANCO
    pygame.draw.rect(tela, cor_p, rect_novo_pin, border_radius=5)
    pygame.draw.rect(tela, COR_GUIA, rect_novo_pin, width=2, border_radius=5)
    renderizar_texto_com_scroll(temp_pin_novo, "", 150, 320, 290)
    
    # Botões Confirmar e Cancelar Alinhados Simetricamente
    btn_cancelar = pygame.Rect(0, 480, 180, 45)
    btn_cancelar.centerx = (LARGURA // 2) - 110
    cor_ca = COR_BOTAO_HOVER if btn_cancelar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_ca, btn_cancelar, border_radius=10)
    txt_ca = fonte.render("Cancelar", True, COR_TEXTO)
    tela.blit(txt_ca, txt_ca.get_rect(center=btn_cancelar.center))
    
    btn_confirmar = pygame.Rect(0, 480, 180, 45)
    btn_confirmar.centerx = (LARGURA // 2) + 110
    cor_co = COR_BOTAO_HOVER if btn_confirmar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_co, btn_confirmar, border_radius=10)
    txt_co = fonte.render("Confirmar", True, COR_TEXTO)
    tela.blit(txt_co, txt_co.get_rect(center=btn_confirmar.center))
    
    return btn_r_baixo, btn_r_medio, btn_brilho_menos, btn_brilho_mais, rect_novo_pin, btn_confirmar, btn_cancelar

def desenhar_menu_crianca():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render("Selecione a Criança", True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.15)))
    
    retangulos_criancas = []
    
    if not lista_criancas:
        txt_vazio = fonte.render("Nenhuma criança cadastrada. Acesse o painel do Responsável.", True, (150, 150, 150))
        tela.blit(txt_vazio, txt_vazio.get_rect(center=(LARGURA // 2, ALTURA * 0.45)))
    else:
        for idx, crianca in enumerate(lista_criancas):
            rect_p = pygame.Rect(150, 200 + (idx * 80), 500, 60)
            
            if crianca_selecionada and crianca_selecionada["id"] == crianca["id"]:
                cor = COR_INPUT_ATIVO
            else:
                cor = COR_BOTAO_HOVER if rect_p.collidepoint(mouse_pos) else COR_BOTAO
                
            pygame.draw.rect(tela, cor, rect_p, border_radius=10)
            txt_nome = fonte.render(f"{crianca['nome']} ({crianca['nascimento']})", True, COR_TEXTO)
            tela.blit(txt_nome, (180, 215 + (idx * 80)))
            
            retangulos_criancas.append((rect_p, crianca))
        
    btn_continuar = pygame.Rect(0, 0, 220, 50)
    btn_continuar.center = (LARGURA // 2, ALTURA * 0.78)
    
    cor_btn = COR_BOTAO
    if crianca_selecionada:
        cor_btn = COR_BOTAO_HOVER if btn_continuar.collidepoint(mouse_pos) else COR_INICIO
        
    pygame.draw.rect(tela, cor_btn, btn_continuar, border_radius=10)
    txt_btn = fonte.render("Continuar", True, COR_BRANCO if crianca_selecionada else COR_TEXTO)
    tela.blit(txt_btn, txt_btn.get_rect(center=btn_continuar.center))
    
    # Botão Voltar Posicionado de Forma Limpa
    btn_voltar = pygame.Rect(50, 500, 120, 40)
    cor_voltar = COR_BOTAO_HOVER if btn_voltar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_voltar, btn_voltar, border_radius=10)
    tela.blit(fonte.render("Voltar", True, COR_TEXTO), (85, 508))
    
    return retangulos_criancas, btn_continuar, btn_voltar

def desenhar_seletor_jogador():
    tela.fill(COR_FUNDO)
    mouse_pos = pygame.mouse.get_pos()
    
    texto_titulo = fonte_titulo.render("Quem irá jogar?", True, COR_TEXTO)
    tela.blit(texto_titulo, texto_titulo.get_rect(center=(LARGURA // 2, ALTURA * 0.2)))
    
    btn_sozinha = pygame.Rect(0, 0, 320, 80)
    btn_sozinha.center = (LARGURA // 2, ALTURA * 0.42)
    cor_s = COR_BOTAO_HOVER if btn_sozinha.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_s, btn_sozinha, border_radius=15)
    txt_s = fonte.render("Criança (Treinar sozinho)", True, COR_TEXTO)
    tela.blit(txt_s, txt_s.get_rect(center=btn_sozinha.center))
    
    btn_mediado = pygame.Rect(0, 0, 320, 80)
    btn_mediado.center = (LARGURA // 2, ALTURA * 0.60)
    cor_m = COR_BOTAO_HOVER if btn_mediado.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_m, btn_mediado, border_radius=15)
    txt_m = fonte.render("Criança + Mediador", True, COR_TEXTO)
    tela.blit(txt_m, txt_m.get_rect(center=btn_mediado.center))
    
    btn_voltar = pygame.Rect(0, 0, 200, 45)
    btn_voltar.center = (LARGURA // 2, ALTURA * 0.82)
    cor_v = COR_BOTAO_HOVER if btn_voltar.collidepoint(mouse_pos) else COR_BOTAO
    pygame.draw.rect(tela, cor_v, btn_voltar, border_radius=10)
    txt_v = fonte.render("Cancelar", True, COR_TEXTO)
    tela.blit(txt_v, txt_v.get_rect(center=btn_voltar.center))
    
    return btn_sozinha, btn_mediado, btn_voltar

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
        txt_vazio = fonte.render("Sem dados de teste gravados no MySQL local.", True, (150, 150, 150))
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
    
    # ------------------ TELA 1: ABERTURA ------------------
    if estado_jogo == "ABERTURA":
        btn_iniciar, btn_sair = desenhar_tela_abertura()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_iniciar.collidepoint(evento.pos):
                    estado_jogo = "SELECAO_PERFIL"
                elif btn_sair.collidepoint(evento.pos):
                    rodando = False  

    # ------------------ TELA 3: SELEÇÃO DE PERFIL ------------------
    elif estado_jogo == "SELECAO_PERFIL":
        btn_resp, btn_crianca, btn_voltar = desenhar_selecao_perfil()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_resp.collidepoint(evento.pos):
                    estado_jogo = "PIN_ACESSO"
                    pin_digitado = ""
                    mensagem_erro_pin = ""
                elif btn_crianca.collidepoint(evento.pos):
                    estado_jogo = "MENU_CRIANCA"
                elif btn_voltar.collidepoint(evento.pos):
                    estado_jogo = "ABERTURA"  

    # ------------------ TELAS 2 E 4: SISTEMA DE PIN ------------------
    elif estado_jogo == "PIN_ACESSO":
        btn_confirmar, btn_cancelar = desenhar_tela_pin_acesso("Controle Parental")
        
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
                        estado_jogo = "MENU_RESPONSAVEL"
                    else:
                        mensagem_erro_pin = "PIN inválido! Digite o PIN correto."
                        pin_digitado = ""
                elif btn_cancelar.collidepoint(evento.pos):
                    estado_jogo = "SELECAO_PERFIL"

    # ------------------ TELA 5: MENU DO RESPONSÁVEL ------------------
    elif estado_jogo == "MENU_RESPONSAVEL":
        btn_cadastrar, btn_configs, btn_estats, btn_sair = desenhar_menu_responsavel()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_cadastrar.collidepoint(evento.pos):
                    estado_jogo = "CADASTRO_CRIANCA"
                    input_cadastro = {"nome": "", "nascimento": "", "sexo": "Masculino", "obs": ""}
                    campo_ativo = None
                elif btn_configs.collidepoint(evento.pos):
                    estado_jogo = "CONFIGURACOES"
                    temp_pin_novo = configs_jogo["pin"]
                    campo_config_ativo = None
                elif btn_estats.collidepoint(evento.pos):
                    estado_jogo = "ESTATISTICAS"
                elif btn_sair.collidepoint(evento.pos):
                    estado_jogo = "SELECAO_PERFIL"

    # ------------------ TELA 6: CADASTRO DE CRIANÇA ------------------
    elif estado_jogo == "CADASTRO_CRIANCA":
        r_nome, r_nasc, r_sm, r_sf, r_obs, btn_conf, btn_canc = desenhar_cadastro_crianca()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if r_nome.collidepoint(evento.pos):
                    campo_ativo = "nome"
                elif r_nasc.collidepoint(evento.pos):
                    campo_ativo = "nascimento"
                elif r_obs.collidepoint(evento.pos):
                    campo_ativo = "obs"
                elif r_sm.collidepoint(evento.pos):
                    input_cadastro["sexo"] = "Masculino"
                elif r_sf.collidepoint(evento.pos):
                    input_cadastro["sexo"] = "Feminino"
                elif btn_conf.collidepoint(evento.pos):
                    if input_cadastro["nome"].strip():
                        novo_id = len(lista_criancas) + 1
                        lista_criancas.append({
                            "id": novo_id,
                            "nome": input_cadastro["nome"],
                            "nascimento": input_cadastro["nascimento"],
                            "sexo": input_cadastro["sexo"],
                            "obs": input_cadastro["obs"]
                        })
                    estado_jogo = "MENU_RESPONSAVEL"
                elif btn_canc.collidepoint(evento.pos):
                    estado_jogo = "MENU_RESPONSAVEL"
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
                        # NOVO: Bloqueia qualquer caractere numérico no nome
                        if not evento.unicode.isdigit():
                            input_cadastro["nome"] += evento.unicode
                    elif campo_ativo == "nascimento":
                        input_cadastro["nascimento"] = formatar_e_validar_data(input_cadastro["nascimento"], evento.unicode)
                    else:
                        input_cadastro[campo_ativo] += evento.unicode

    # ------------------ TELA 7: CONFIGURAÇÕES ------------------
    elif estado_jogo == "CONFIGURACOES":
        btn_rb, btn_rm, btn_b_menos, btn_b_mais, r_pin, btn_conf, btn_canc = desenhar_tela_configuracoes()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_rb.collidepoint(evento.pos):
                    configs_jogo["ruido"] = "Baixo"
                elif btn_rm.collidepoint(evento.pos):
                    configs_jogo["ruido"] = "Médio"
                elif btn_b_menos.collidepoint(evento.pos):
                    configs_jogo["brilho"] = max(50, configs_jogo["brilho"] - 25)
                elif btn_b_mais.collidepoint(evento.pos):
                    configs_jogo["brilho"] = min(255, configs_jogo["brilho"] + 25)
                elif r_pin.collidepoint(evento.pos):
                    campo_config_ativo = "pin"
                elif btn_conf.collidepoint(evento.pos):
                    if len(temp_pin_novo) == 4:
                        configs_jogo["pin"] = temp_pin_novo
                    estado_jogo = "MENU_RESPONSAVEL"
                elif btn_canc.collidepoint(evento.pos):
                    estado_jogo = "MENU_RESPONSAVEL"
            elif evento.type == pygame.KEYDOWN and campo_config_ativo == "pin":
                if evento.key == pygame.K_BACKSPACE:
                    temp_pin_novo = temp_pin_novo[:-1]
                elif len(temp_pin_novo) < 4 and evento.unicode.isdigit():
                    temp_pin_novo += evento.unicode

    # ------------------ TELA 8: SELEÇÃO DA CRIANÇA ------------------
    elif estado_jogo == "MENU_CRIANCA":
        recs_criancas, btn_cont, btn_volt = desenhar_menu_crianca()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                for rect, crianca in recs_criancas:
                    if rect.collidepoint(evento.pos):
                        crianca_selecionada = crianca
                if btn_volt.collidepoint(evento.pos):
                    estado_jogo = "SELECAO_PERFIL"
                elif btn_cont.collidepoint(evento.pos) and crianca_selecionada:
                    estado_jogo = "SELETOR_JOGADOR"

    # ------------------ TELA 9: SELETOR DE MODALIDADE ------------------
    elif estado_jogo == "SELETOR_JOGADOR":
        btn_soz, btn_med, btn_volt = desenhar_seletor_jogador()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_volt.collidepoint(evento.pos):
                    estado_jogo = "MENU_CRIANCA"
                elif btn_soz.collidepoint(evento.pos) or btn_med.collidepoint(evento.pos):
                    estado_jogo = "JOGANDO"
                    angulo_atual = 0
                    id_fase_dinamica = 1
                    fase_atual = gerar_fase_por_angulo(id_fase_dinamica, angulo_atual)
                    fase_concluida = False
                    jogo_finalizado = False
                    coordenadas_usuario = []
                    tempos_toque = []
                    desenhando = False
                    mensagem_status = "Conecte o ponto Verde ao Alvo Azul"

    # ------------------ TELA DE ESTATÍSTICAS ------------------
    elif estado_jogo == "ESTATISTICAS":
        btn_voltar = desenhar_tela_estatisticas()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_voltar.collidepoint(evento.pos):
                    estado_jogo = "MENU_RESPONSAVEL"

    # ------------------ TELA 10: AMBIENTE DE JOGO ------------------
    elif estado_jogo == "JOGANDO":
        p_init = fase_atual["ponto_inicio"]
        p_end = fase_atual["ponto_fim"]
        mouse_pos = pygame.mouse.get_pos()
        
        # 1. BOTÃO SAIR (Ancorado estritamente em relação à margem direita da tela)
        largura_btn_sair = 110
        btn_sair_jogo = pygame.Rect(LARGURA - largura_btn_sair - 25, 20, largura_btn_sair, 35)
        
        # 2. ALINHAMENTO DINÂMICO DOS BOTÕES "REPETIR FASE" E "AVANÇAR"
        largura_botoes_fase = 180
        altura_botoes_fase = 45
        espacamento_botoes = 40
        largura_conjunto = (largura_botoes_fase * 2) + espacamento_botoes
        
        # Centraliza o bloco na horizontal e fixa no rodapé
        pos_inicial_x = (LARGURA - largura_conjunto) // 2
        y_botoes_fase = 495
        
        btn_repetir = pygame.Rect(pos_inicial_x, y_botoes_fase, largura_botoes_fase, altura_botoes_fase)
        btn_continuar = pygame.Rect(pos_inicial_x + largura_botoes_fase + espacamento_botoes, y_botoes_fase, largura_botoes_fase, altura_botoes_fase)
        
        # 3. BOTÃO "VOLTAR AO MENU PRINCIPAL" DINÂMICO (Impede texto saindo da borda)
        texto_fim = "Voltar ao Menu Principal"
        texto_fim_largura, texto_fim_altura = fonte.size(texto_fim)
        
        # Padding interno (margem interna de conforto de 50px de largura e 20px de altura)
        largura_btn_fim = texto_fim_largura + 50
        altura_btn_fim = texto_fim_altura + 20
        
        # Centralização simétrica na tela
        btn_menu_fim = pygame.Rect(0, 0, largura_btn_fim, altura_btn_fim)
        btn_menu_fim.center = (LARGURA // 2, y_botoes_fase + (altura_botoes_fase // 2))

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
                
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if jogo_finalizado:
                    if btn_menu_fim.collidepoint(evento.pos):
                        estado_jogo = "SELECAO_PERFIL"
                
                elif fase_concluida:
                    if btn_repetir.collidepoint(evento.pos):
                        fase_concluida = False
                        coordenadas_usuario = []
                        tempos_toque = []
                        mensagem_status = "Treinando novamente a mesma fase!"
                    elif btn_continuar.collidepoint(evento.pos):
                        angulo_atual = resultado_rodada["novo_angulo"]
                        
                        if angulo_atual >= LIMITE_ANGULO_MAXIMO:
                            jogo_finalizado = True
                            mensagem_status = f"Desafio Concluído! Limite de {LIMITE_ANGULO_MAXIMO}° vencido!"
                        else:
                            if "AVANCAR" in resultado_rodada["status"]:
                                id_fase_dinamica += 1
                            elif resultado_rodada["status"] == "VOLTAR_UMA":
                                id_fase_dinamica = max(1, id_fase_dinamica - 1)
                            elif resultado_rodada["status"] == "VOLTAR_DUAS":
                                id_fase_dinamica = max(1, id_fase_dinamica - 2)
                                
                            fase_atual = gerar_fase_por_angulo(id_fase_dinamica, angulo_atual)
                            fase_concluida = False
                            coordenadas_usuario = []
                            tempos_toque = []
                            mensagem_status = "Conecte o ponto Verde ao Alvo Azul"
                else:
                    if btn_sair_jogo.collidepoint(evento.pos):
                        estado_jogo = "SELECAO_PERFIL"
                        
                    dist_inicio = math.sqrt((evento.pos[0] - p_init[0])**2 + (evento.pos[1] - p_init[1])**2)
                    if dist_inicio <= 20: 
                        desenhando = True
                        coordenadas_usuario = [evento.pos]
                        tempos_toque = [time.time()]
                        
            elif evento.type == pygame.MOUSEMOTION and desenhando:
                coordenadas_usuario.append(evento.pos)
                tempos_toque.append(time.time())
                
            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1 and desenhando:
                desenhando = False
                dist_alvo = math.sqrt((evento.pos[0] - p_end[0])**2 + (evento.pos[1] - p_end[1])**2)
                
                if dist_alvo <= 25:
                    precisao, hesitacao = calcular_metricas(
                        fase_atual["tipo"], p_init, p_end, 
                        fase_atual.get("pontos_guia", []), coordenadas_usuario, tempos_toque
                    )
                    tempo_total = tempos_toque[-1] - tempos_toque[0] if tempos_toque else 0.0
                    
                    if db_ativo:
                        try: salvar_tentativa(fase_atual["nome"], tempo_total, precisao, hesitacao)
                        except: pass
                    
                    novo_ang, status = calcular_proximo_passo(precisao, angulo_atual)
                    
                    resultado_rodada = {
                        "precisao": precisao,
                        "tempo": tempo_total,
                        "novo_angulo": novo_ang,
                        "status": status
                    }
                    
                    coordenadas_salvas_para_desenho = list(coordenadas_usuario)
                    
                    if status == "REPETIR":
                        coordenadas_usuario = []
                        tempos_toque = []
                        mensagem_status = f"Precisão: {precisao:.1f}%. Repetindo fase automaticamente..."
                    else:
                        fase_concluida = True
                        mensagem_status = f"Traçado Realizado! Precisão: {precisao:.1f}%"
                else:
                    mensagem_status = "Soltou fora do alvo! Repetindo automaticamente."
                    coordenadas_usuario = []
                    tempos_toque = []
                    
        # --- DESENHO DO AMBIENTE ---
        tela.fill(COR_FUNDO)
        
        pygame.draw.line(tela, COR_GUIA, p_init, p_end, 6)
        pygame.draw.circle(tela, COR_INICIO, p_init, 20)
        pygame.draw.circle(tela, COR_ALVO, p_end, 25)
        
        if fase_concluida or jogo_finalizado:
            if len(coordenadas_salvas_para_desenho) > 1:
                pygame.draw.lines(tela, COR_RASTRO, False, coordenadas_salvas_para_desenho, 4)
        else:
            if len(coordenadas_usuario) > 1:
                pygame.draw.lines(tela, COR_RASTRO, False, coordenadas_usuario, 4)
                
        if jogo_finalizado:
            cor_mf = COR_BOTAO_HOVER if btn_menu_fim.collidepoint(mouse_pos) else COR_INICIO
            pygame.draw.rect(tela, cor_mf, btn_menu_fim, border_radius=10)
            
            # Centraliza o texto dinamicamente no interior do botão "Voltar ao Menu Principal"
            txt_fim_img = fonte.render(texto_fim, True, COR_BRANCO)
            tela.blit(txt_fim_img, txt_fim_img.get_rect(center=btn_menu_fim.center))
            
        elif fase_concluida:
            # Botão "Repetir"
            cor_rep = COR_BOTAO_HOVER if btn_repetir.collidepoint(mouse_pos) else COR_BOTAO
            pygame.draw.rect(tela, cor_rep, btn_repetir, border_radius=10)
            txt_rep_img = fonte.render("Repetir Fase", True, COR_TEXTO)
            tela.blit(txt_rep_img, txt_rep_img.get_rect(center=btn_repetir.center))
            
            # Botão "Avançar"
            cor_av = COR_BOTAO_HOVER if btn_continuar.collidepoint(mouse_pos) else COR_INICIO
            pygame.draw.rect(tela, cor_av, btn_continuar, border_radius=10)
            txt_av_img = fonte.render("Avançar", True, COR_BRANCO)
            tela.blit(txt_av_img, txt_av_img.get_rect(center=btn_continuar.center))
        else:
            # Botão "Sair" do ambiente de jogo ativo
            cor_sj = COR_BOTAO_HOVER if btn_sair_jogo.collidepoint(mouse_pos) else COR_BOTAO
            pygame.draw.rect(tela, cor_sj, btn_sair_jogo, border_radius=5)
            txt_sair_img = fonte.render("Sair", True, COR_TEXTO)
            tela.blit(txt_sair_img, txt_sair_img.get_rect(center=btn_sair_jogo.center))

        tela.blit(fonte.render(mensagem_status, True, COR_TEXTO), (20, 20))
        tela.blit(fonte.render(f"Fase Atual: Ângulo {angulo_atual}°", True, COR_TEXTO), (20, ALTURA - 40))

    pygame.display.flip()
    relogio.tick(60)

pygame.quit()