import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(name="PERDCOMP", log_dir="logs"):
    """
    Configura e retorna um logger profissional com saída para arquivo e console.
    Inclui rotação de arquivos para evitar consumo excessivo de disco.
    """
    script_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    log_path = os.path.join(script_dir, log_dir)

    if not os.path.exists(log_path):
        os.makedirs(log_path)

    today = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"rpa_{today}.log"
    log_file = os.path.join(log_path, log_filename)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Evita duplicidade de handlers em reinicializações
    if logger.handlers:
        return logger

    # Handler para arquivo com rotação (5MB por arquivo, mantém 5 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formato Profissional (Estilo DARF/DCTFWeb)
    # Ex: [2024-03-24 15:30:00] | INFO     | PERDCOMP     | Mensagem...
    formatter = logging.Formatter(
        "[%(asctime)s] | %(levelname)-8s | %(name)-12s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("-" * 80)
    logger.info(f"Sessão iniciada: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("-" * 80)

    return logger


# Instância global para o projeto
logger = setup_logger()
