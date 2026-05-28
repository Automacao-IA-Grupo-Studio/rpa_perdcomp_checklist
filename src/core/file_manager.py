import os
import shutil
import time
import re
from src.core.logger import logger


def mover_arquivos_recentes(diretorio_destino, extensao=".pdf", prefixo=""):
    """
    Move os arquivos baixados recentemente da pasta Downloads para o destino.

    Args:
        diretorio_destino: Pasta de destino para os arquivos
        extensao: Extensão dos arquivos a serem movidos
        prefixo: Prefixo a ser adicionado no nome do arquivo

    Returns:
        Caminho completo do arquivo movido ou None se não encontrou
    """
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")

    if not os.path.exists(diretorio_destino):
        os.makedirs(diretorio_destino)
        logger.info(f"Pasta de destino criada: {diretorio_destino}")

    try:
        arquivos = [
            os.path.join(downloads_path, f)
            for f in os.listdir(downloads_path)
            if f.endswith(extensao)
        ]
        arquivos.sort(key=os.path.getmtime, reverse=True)

        if not arquivos:
            return None

        melhor_arquivo = arquivos[0]

        if time.time() - os.path.getmtime(melhor_arquivo) < 20:
            nome_arquivo = os.path.basename(melhor_arquivo)
            novo_nome = f"{prefixo}{nome_arquivo}" if prefixo else nome_arquivo
            destino_completo = os.path.join(diretorio_destino, novo_nome)

            base, ext = os.path.splitext(destino_completo)
            counter = 1
            while os.path.exists(destino_completo):
                destino_completo = f"{base}_{counter}{ext}"
                counter += 1

            shutil.move(melhor_arquivo, destino_completo)
            logger.info(
                f"Arquivo movido: {nome_arquivo} -> {os.path.basename(destino_completo)}"
            )
            return destino_completo

    except Exception as e:
        logger.warning(f"Erro ao mover arquivo: {e}")

    return None

def limpar_arquivos_duplicados(diretorio_destino):
    """
    Remove arquivos duplicados que foram renomeados com sufixos _1, _2, etc.
    Suporta arquivos com prefixo de CNPJ.
    """
    if not os.path.exists(diretorio_destino):
        return

    arquivos = os.listdir(diretorio_destino)
    removidos = 0
    
    # Procura por _ seguido de números antes da extensão .pdf no final do nome
    # Ex: 02912729000160_Documento_1.pdf -> base seria 02912729000160_Documento
    padrao_duplicado = re.compile(r"(.+)_(\d+)\.pdf$", re.IGNORECASE)
    
    for arquivo in arquivos:
        caminho_completo = os.path.join(diretorio_destino, arquivo)
        if os.path.isfile(caminho_completo):
            match = padrao_duplicado.match(arquivo)
            if match:
                base_name = match.group(1)
                # Verifica se o arquivo original (sem o _1) existe
                arquivo_original = f"{base_name}.pdf"
                caminho_original = os.path.join(diretorio_destino, arquivo_original)
                
                # Se o arquivo original existe, apaga a duplicata
                if os.path.exists(caminho_original):
                    try:
                        os.remove(caminho_completo)
                        logger.info(f"Monitor: Duplicata removida: {arquivo}")
                        removidos += 1
                    except Exception as e:
                        logger.warning(f"Erro ao remover duplicata {arquivo}: {e}")
                        
    if removidos > 0:
        logger.info(f"Limpeza concluída: {removidos} arquivo(s) removido(s).")
    else:
        logger.info("Nenhuma duplicata encontrada.")
