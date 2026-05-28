import pyautogui
import time
import os
import random
from datetime import datetime
from src.core.logger import logger
from src.core.exceptions import CriticalImageNotFoundError

IMAGES_PATH = "assets/images"


def human_delay(min_s=0.5, max_s=1.5):
    """Introduz um atraso aleatório para simular comportamento humano."""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def clicar_imagem(
    nome, confianca=0.8, offset_x=0, offset_y=0, grayscale=False, critical=False
):
    """Localiza e clica no centro de uma imagem com timing profissional."""
    caminho = os.path.join(IMAGES_PATH, nome)

    if not os.path.exists(caminho):
        logger.error(f"Arquivo não encontrado: {caminho}")
        if critical:
            raise CriticalImageNotFoundError(nome, "Arquivo ausente")
        return False

    try:
        local = pyautogui.locateCenterOnScreen(
            caminho, confidence=confianca, grayscale=grayscale
        )
        if local:
            pyautogui.click(local.x + offset_x, local.y + offset_y)
            human_delay(0.4, 0.8)
            return True

        if critical:
            raise CriticalImageNotFoundError(nome, "Não visível")
        return False

    except Exception as e:
        if critical:
            raise CriticalImageNotFoundError(nome, str(e))
        return False


def esperar_e_clicar(
    nome,
    timeout=30,
    confianca=0.8,
    offset_x=0,
    offset_y=0,
    grayscale=False,
    critical=False,
):
    """Aguarda a imagem aparecer por até 'timeout' segundos e clica com timing profissional."""
    logger.info(f"Aguardando '{nome}' (max {timeout}s)...")
    caminho = os.path.join(IMAGES_PATH, nome)

    if not os.path.exists(caminho):
        logger.error(f"Arquivo ausente: {caminho}")
        if critical:
            raise CriticalImageNotFoundError(nome, "Arquivo ausente")
        return False

    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            local = pyautogui.locateCenterOnScreen(
                caminho, confidence=confianca, grayscale=grayscale
            )
            if local:
                logger.info(f"Imagem '{nome}' encontrada em ({local.x}, {local.y}). Clicando...")
                pyautogui.click(local.x + offset_x, local.y + offset_y)
                logger.debug(f"Clique: {nome}")
                human_delay(0.5, 1.2)
                return True
        except Exception:
            pass
        time.sleep(0.5) # Intervalo de busca mais rápido e profissional

    logger.warning(f"Timeout: '{nome}' não encontrada.")
    if critical:
        raise CriticalImageNotFoundError(nome, f"Timeout {timeout}s")
    return False


def localizar_todos(nome, confianca=0.8, grayscale=False):
    """Retorna o centro de todas as instâncias da imagem na tela."""
    caminho = os.path.join(IMAGES_PATH, nome)
    try:
        locais = list(
            pyautogui.locateAllOnScreen(
                caminho, confidence=confianca, grayscale=grayscale
            )
        )
        return [(pyautogui.center(box).x, pyautogui.center(box).y) for box in locais]
    except Exception:
        return []


def mover_para_imagem(nome, timeout=10, confianca=0.8):
    """Move o cursor sobre a imagem sem clicar com movimento suave."""
    logger.info(f"Posicionando cursor: '{nome}'")
    caminho = os.path.join(IMAGES_PATH, nome)

    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            local = pyautogui.locateCenterOnScreen(caminho, confidence=confianca)
            if local:
                pyautogui.moveTo(local.x, local.y, duration=random.uniform(0.3, 0.6))
                human_delay(0.3, 0.7)
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def verificar_existencia(nome, timeout=5, confianca=0.8):
    """Verifica se uma imagem existe na tela dentro do tempo estipulado."""
    inicio = time.time()
    while time.time() - inicio < timeout:
        if imagem_existe(nome, confianca=confianca):
            return True
        time.sleep(0.5)
    return False


def imagem_existe(nome, confianca=0.8):
    """Verifica a presença da imagem na tela."""
    caminho = os.path.join(IMAGES_PATH, nome)
    if not os.path.exists(caminho):
        return False
    try:
        return pyautogui.locateOnScreen(caminho, confidence=confianca) is not None
    except Exception:
        return False


def esperar_sumir(nome, timeout=15, confianca=0.8, critical=False):
    """Aguarda até que a imagem suma da tela."""
    logger.info(f"Aguardando '{nome}' sumir (max {timeout}s)...")
    inicio = time.time()
    while time.time() - inicio < timeout:
        if not imagem_existe(nome, confianca=confianca):
            logger.debug(f"Imagem '{nome}' sumiu da tela.")
            return True
        time.sleep(0.5)

    logger.warning(f"Timeout: '{nome}' ainda está na tela após {timeout}s.")
    return False


def salvar_print_erro(nome_base="erro"):
    """Tira um print da tela e salva na pasta logs/screenshots com timestamp."""
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        screenshot_dir = os.path.join(script_dir, "logs", "screenshots")
        
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
            
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        caminho_final = os.path.join(screenshot_dir, f"{nome_base}_{timestamp}.png")
        
        pyautogui.screenshot(caminho_final)
        logger.info(f"📸 Screenshot do erro salvo em: {caminho_final}")
        return caminho_final
    except Exception as e:
        logger.error(f"Erro ao tentar salvar screenshot: {e}")
        return None
