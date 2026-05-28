import logging
import os
import shutil
import subprocess
import tempfile
import time

logger = logging.getLogger(__name__)

# Diretório para perfil temporário do Edge (conforme padrão eSocial)
TEMP_PROFILE_DIR = os.path.join(tempfile.gettempdir(), "Edge_Workspace_Data")


def ensure_browser_closed():
    """
    Encerra forçadamente processos do Microsoft Edge para garantir uma sessão limpa.
    """
    logger.info("Encerrando processos do Microsoft Edge para garantir limpeza...")
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "msedge.exe", "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.debug(f"Aviso ao encerrar processos: {e}")

    time.sleep(2)

    # Exclui o perfil temporário se existir
    try:
        if os.path.exists(TEMP_PROFILE_DIR):
            logger.info("Deletando perfil temporário do Edge...")
            shutil.rmtree(TEMP_PROFILE_DIR, ignore_errors=True)
    except Exception as e:
        logger.error(f"Erro ao deletar perfil temporário: {e}")


def open_browser(url: str):
    """
    Abre o Microsoft Edge diretamente na URL usando um perfil temporário.
    """
    ensure_browser_closed()
    logger.info("Abrindo Microsoft Edge com perfil temporário exclusivo...")

    # Garante que o diretório não exista e cria vazio
    os.makedirs(TEMP_PROFILE_DIR, exist_ok=True)

    # Comando para abrir o Edge com perfil temporário e sem verificações iniciais
    comando = f'start msedge --remote-debugging-port=9222 --user-data-dir="{TEMP_PROFILE_DIR}" --start-maximized --no-first-run --no-default-browser-check "{url}"'
    os.system(comando)

    # Aguarda brevemente a criação da janela
    time.sleep(5)

    logger.info("Navegador Microsoft Edge aberto.")
    return True
