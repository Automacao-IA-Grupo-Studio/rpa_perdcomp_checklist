import time
import pyautogui
import os
import re
import threading
from datetime import datetime
from src.core.vision import (
    esperar_e_clicar,
    localizar_todos,
    imagem_existe,
    esperar_sumir,
    verificar_existencia,
    human_delay,
)
from src.core.file_manager import mover_arquivos_recentes, limpar_arquivos_duplicados
from src.core.logger import logger
from src.core.exceptions import (
    CriticalImageNotFoundError,
    CNPJBlockedMessageError,
    InvalidCNPJError,
)
from src.core.playwright_manager import pw_manager

# Desativar fail-safe para evitar interrupções por movimento do mouse nos cantos
pyautogui.FAILSAFE = False

CERTIFICADOS_VALIDOS = [
    "Space W",
    "Studio Bank",
    "Aliança",
    "Audit Tecnologia",
    "Studio Store",
    "Studio Operacional 01",
    "Studio Operacional",
    "Studio Fiscal",
    "Studio Agro",
    "Studio Varejo",
    "Studio Brokers",
]

MAPA_CERTIFICADOS = {
    "Studio Varejo": 0,
    "Space W": 1,
    "Studio Bank": 2,
    "Aliança": 3,
    "Audit Tecnologia": 4,
    "Studio Store": 5,
    "Studio Operacional 01": 6,
    "Studio Operacional": 7,
    "Studio Fiscal": 8,
    "Studio Agro": 9,
    "Studio Brokers": 10,
}


def executar_fluxo_cnpj(
    cnpj_bruto,
    diretorio_base,
    nome_certificado=None,
    callback_status=None,
):
    cnpj = re.sub(r"\D", "", cnpj_bruto)

    logger.info(f"Iniciando RPA PERDCOMP para CNPJ: {cnpj}")

    # NOVO: Aguardar e clicar no pop-up inicial do Edge/eCAC se aparecer
    logger.info("Aguardando pop-up inicial (passar_pop_up.png)...")
    if esperar_e_clicar("passar_pop_up.png", timeout=15):
        logger.info("Pop-up inicial clicado.")
        human_delay(1, 2)

    if esperar_e_clicar("btn_entrar_govbr.png", timeout=30):
        logger.info("Botão Gov.br clicado.")
    else:
        logger.warning("Botão Gov.br não encontrado, tentando Enter...")
        pyautogui.press("enter")

    logger.info("Aguardando tela de escolha de login...")
    human_delay(1.5, 2.5)
    if esperar_e_clicar("btn_certificado.png", timeout=40, critical=True):
        if not automated_login_certificado(nome_certificado):
            raise CriticalImageNotFoundError(
                "certificado_digital.png", "Falha na seleção do certificado"
            )

    if not trocar_perfil_cnpj(cnpj):
        raise CriticalImageNotFoundError(
            "perfil_acesso.png", "Falha ao trocar perfil CNPJ"
        )

    # Navegar até a lista de documentos PER/DCOMP
    status_acesso = acessar_painel_perdcomp(callback_status)
    if not status_acesso:
        return False

    if status_acesso == "SEM_PEDIDOS":
        logger.info("Finalizando fluxo com sucesso: sem perdcomp para baixar.")
        return "SEM_PEDIDOS"

    # Iniciar downloads
    sucesso = processar_downloads(cnpj, diretorio_base, callback_status)
    return sucesso


def automated_login_certificado(nome_certificado=None):
    logger.info("Aguardando caixa de seleção de certificados...")
    time.sleep(2)

    if nome_certificado and nome_certificado in MAPA_CERTIFICADOS:
        quantidade_setas = MAPA_CERTIFICADOS[nome_certificado]
        logger.info(
            f"Certificado: '{nome_certificado}' -> {quantidade_setas}x Seta Baixo"
        )
    else:
        msg = f"Certificado '{nome_certificado}' não mapeado no sistema."
        logger.error(msg)
        raise CriticalImageNotFoundError("certificado_digital.png", msg)

    time.sleep(1)

    logger.info("Localizando certificado na lista...")
    for _ in range(60):
        if imagem_existe("certificado_digital.png"):
            logger.info(
                "Janela de Certificado detectada. Garantindo foco com 3 TABs..."
            )

            # Garante o foco na lista de certificados
            for _ in range(3):
                pyautogui.press("tab")
                time.sleep(0.3)

            if quantidade_setas > 0:
                logger.info(f"Navegando {quantidade_setas}x para baixo...")
                for _ in range(quantidade_setas):
                    pyautogui.press("down")
                    time.sleep(0.3)

            time.sleep(0.5)
            pyautogui.press("enter")
            time.sleep(5)
            return True
        time.sleep(1)

    logger.error("Certificado não visualizado para seleção.")
    return False


def trocar_perfil_cnpj(cnpj_bruto):
    cnpj = re.sub(r"\D", "", cnpj_bruto)
    logger.info(f"Alterando perfil: {cnpj}")

    if not esperar_e_clicar("alterar_perfil.png", timeout=30, critical=True):
        return False

    human_delay(0.8, 1.5)
    if not esperar_e_clicar("campo_cnpj.png", timeout=15, critical=True):
        return False

    pyautogui.write(cnpj, interval=0.01)
    time.sleep(1)
    pyautogui.press("tab")

    if not esperar_e_clicar(
        "btn_alterar.png", timeout=10, confianca=0.9, critical=True
    ):
        return False

    # 3. Esperar o btn_alterar sumir da tela antes de continuar.
    logger.info(
        "Aguardando confirmação da troca de perfil (botão Alterar deve sumir)..."
    )
    esperar_sumir("btn_alterar.png", timeout=20)

    # Verificação de erros fatais de CNPJ
    # Usamos verificar_existencia com timeout porque a mensagem pode demorar um segundo para carregar
    if verificar_existencia("mensagem_cnpj.png", timeout=8):
        logger.error(
            "Detectada mensagem de pendência no CNPJ. Encerrando com Status 14."
        )
        raise CNPJBlockedMessageError()

    if verificar_existencia("cnpj_invalido.png", timeout=2):
        logger.error("CNPJ informado é inválido no portal. Encerrando com Status 15.")
        raise InvalidCNPJError()

    logger.info("Perfil de acesso atualizado com sucesso.")
    human_delay(1, 2)
    return True


def acessar_painel_perdcomp(callback_status=None):
    logger.info("Acessando Menu 'Restituição'...")
    if not esperar_e_clicar(
        "menu_restituicao.png", timeout=20, confianca=0.8, critical=True
    ):
        return False

    logger.info("Clicando em 'Acessar PER/DCOMP'...")
    if not esperar_e_clicar("acessar_perdcomp.png", timeout=20, critical=True):
        return False

    logger.info("Aguardando carregamento (tela de loading)...")
    esperar_sumir("loading.png", timeout=30)

    if callback_status:
        callback_status(4)  # Status: Processando

    logger.info("Acessando 'Visualizar Documentos'...")
    if not esperar_e_clicar("visualizar_docs.png", timeout=20, critical=True):
        return False

    logger.info("Selecionando 'Documentos Entregues'...")
    if not esperar_e_clicar("menu_docs_entregues.png", timeout=20, critical=True):
        return False

    logger.info("Preenchendo intervalo de datas...")
    if esperar_e_clicar("data_inicio.png", timeout=15, critical=True):
        human_delay(0.5, 1.2)
        # Preenche data de início: 01012021
        pyautogui.write("01012021", interval=0.01)
        pyautogui.press("tab")
        time.sleep(0.5)

        # Preenche data final: data atual
        data_atual = datetime.now().strftime("%d%m%Y")
        pyautogui.write(data_atual, interval=0.01)
        pyautogui.press("enter")
        time.sleep(3)

        # Opcional: aguardar por loading
        esperar_sumir("processando.png", timeout=15)
        esperar_sumir("loading.png", timeout=15)
        time.sleep(1)

        if imagem_existe("sem_perdcomp.png"):
            logger.info("Aviso 'sem_perdcomp' detectado. Nenhum documento disponível.")
            return "SEM_PEDIDOS"

    return True


def processar_downloads(cnpj, diretorio_base, callback_status=None):
    logger.info("Iniciando processo de downloads via Playwright...")
    dir_cnpj = os.path.join(diretorio_base, cnpj)
    diretorio_destino = os.path.join(dir_cnpj, "PERDCOMP")

    if not os.path.exists(diretorio_destino):
        try:
            os.makedirs(diretorio_destino)
            logger.info(f"Pasta criada: {diretorio_destino}")
        except Exception as e:
            logger.error(f"Erro ao criar pasta {diretorio_destino}: {e}")

    logger.info("Plugando robô Headless (Playwright) na tela visual...")
    page = pw_manager.connect(port=9222)

    if not page:
        logger.error("Falha ao conectar Playwright na porta 9222.")
        return False

    total_arquivos = 0
    pagina = 1

    while True:
        logger.info(f"=== Processando Página {pagina} ===")

        # Define o Frame principal onde o sistema Angular está renderizado
        frame = page.frame_locator("#frmApp")

        try:
            # Aguarda renderizar o ícone de ação dentro do frame
            frame.locator("i.iconeAcao").first.wait_for(state="visible", timeout=15000)
        except Exception:
            logger.warning(
                "Grade de documentos não carregou ou sem ícones em 15s. Finalizando downloads."
            )
            break

        time.sleep(2)

        try:
            botoes = None
            # Seletores abrangentes baseados no padrão do eCAC
            seletores_download = [
                "i.iconeAcao.icon-print",  # Seletor mapeado do print (Angular DOM)
                "i.iconeAcao",
                ".icone-baixar",
                "a[title*='Baixar arquivo']",
                "a[title*='Download']",
                "a:has(i.fa-download)",
            ]

            for sel in seletores_download:
                b = frame.locator(sel).all()
                if len(b) > 0:
                    botoes = b
                    break

            if not botoes:
                logger.info(
                    "Nenhum botão de download encontrado com os seletores configurados."
                )
                botoes = []

            logger.info(
                f"Encontrados {len(botoes)} arquivos prontos no código-fonte para baixar."
            )

            for idx, botao in enumerate(botoes):
                try:
                    logger.info(f"Disparando download {idx + 1}/{len(botoes)}...")
                    with page.expect_download(timeout=60000) as down_info:
                        botao.click()

                    download = down_info.value
                    nome_original = download.suggested_filename

                    novo_nome = f"{cnpj}_{nome_original}"
                    destino_final = os.path.join(diretorio_destino, novo_nome)

                    if os.path.exists(destino_final):
                        import time as _time

                        base, ext = os.path.splitext(novo_nome)
                        destino_final = os.path.join(
                            diretorio_destino, f"{base}_{int(_time.time())}{ext}"
                        )

                    download.save_as(destino_final)
                    total_arquivos += 1
                    logger.info(f"Arquivo salvo com sucesso: {destino_final}")
                except Exception as e:
                    logger.error(f"Erro ao baixar arquivo {idx + 1}: {e}")

        except Exception as err:
            logger.error(f"Erro ao capturar botões da página {pagina}: {err}")

        # Tentar avançar página
        clicou_proxima = False
        try:
            btn_prox = None
            seletores_prox_pagina = [
                "li.page-item:not(.disabled) a[aria-label='Próximo']",  # Mapeado do print (estrutura Angular ul.pagination > li)
                "a.page-link[aria-label='Próximo']",
                "a.paginate_button.next:not(.disabled)",
                "a[title='Próxima']:not(.disabled)",
                "a[title='Página Seguinte']:not(.disabled)",
                "a:has-text('Próxima')",
            ]

            for sel in seletores_prox_pagina:
                locator = frame.locator(sel)
                if locator.count() > 0:
                    btn_prox = locator.first
                    break

            if btn_prox and btn_prox.is_visible():
                logger.info("Botão de Próxima Página localizado. Clicando...")
                btn_prox.click()
                clicou_proxima = True

                time.sleep(3)
                try:
                    esperar_sumir("processando.png", timeout=20)
                    esperar_sumir("loading.png", timeout=10)
                except:
                    pass
                pagina += 1
            else:
                logger.info(
                    "Botão de avançar página não encontrado ou está desabilitado. Fim das páginas."
                )
        except Exception as e:
            logger.error(f"Falha técnica ao ir para próxima página: {e}")

        if not clicou_proxima:
            break

    logger.info("Procurando e removendo arquivos duplicados...")
    limpar_arquivos_duplicados(diretorio_destino)

    logger.info(
        f"Processamento concluído com sucesso. {total_arquivos} arquivos baixados no total."
    )
    pw_manager.stop()
    return True
