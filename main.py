import os
import sys
import time
import traceback

from dotenv import load_dotenv

# Workspace setup (must be before local imports)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.browser import ensure_browser_closed, open_browser
from src.core.exceptions import (
    BusinessError,
    CriticalImageNotFoundError,
)
from src.core.logger import logger
from src.core.retry import retry_on_exception
from src.core.vision import salvar_print_erro
from src.database.db_handler import DBHandler
from src.workflow.workflow_perdcomp import CERTIFICADOS_VALIDOS, executar_fluxo_cnpj

# Carrega variáveis de ambiente
load_dotenv()

IMAGES_PATH = "assets/images"


def verificar_arquivos():
    imagens = [
        "btn_entrar_govbr.png",
        "btn_certificado.png",
        "certificado_digital.png",
        "alterar_perfil.png",
        "campo_cnpj.png",
        "btn_alterar.png",
        "menu_restituicao.png",
        "acessar_perdcomp.png",
        "loading.png",
        "visualizar_docs.png",
        "menu_docs_entregues.png",
        "data_inicio.png",
        "icone_download.png",
        "passar_pagina.png",
        "passar_pagina2.png",
        "final.png",
        "aviso_varios_download.png",
        "btn_permitir.png",
        "passar_pop_up.png",
    ]

    faltando = []
    logger.info("Realizando pré-checagem de arquivos essenciais...")

    if not os.path.exists(IMAGES_PATH):
        logger.error(f"Pasta de ativos não encontrada: {IMAGES_PATH}")
        return False

    for img in imagens:
        if not os.path.exists(os.path.join(IMAGES_PATH, img)):
            faltando.append(img)

    if faltando:
        logger.error(f"Imagens fundamentais ausentes: {', '.join(faltando)}")
        return False

    return True


# Funções de controle do Chrome removidas em favor do src.core.browser


@retry_on_exception(retries=3, initial_delay=5, backoff=2, exceptions=(Exception,))
def processar_solicitacao(req, db, path_docs):
    id_req = req["id"]
    cnpj_db = req["cnpj"]

    logger.info("=" * 50)
    logger.info(f"INICIANDO SOLICITACAO ID {id_req} | CNPJ: {cnpj_db}")
    logger.info("=" * 50)

    id_certificado = req.get("id_certificado")
    if not id_certificado:
        logger.error("id_certificado não encontrado na solicitação.")
        db.atualizar_status(id_req, 6, "id_certificado não informado")
        return False, "id_certificado não informado", True

    nome_certificado = db.buscar_nome_certificado(id_certificado)

    if not nome_certificado:
        logger.error(f"Certificado com ID {id_certificado} não encontrado no banco.")
        db.atualizar_status(
            id_req, 6, f"Certificado ID {id_certificado} não encontrado"
        )
        return False, f"Certificado ID {id_certificado} não encontrado", True

    if nome_certificado not in CERTIFICADOS_VALIDOS:
        logger.error(f"Certificado '{nome_certificado}' não está mapeado no sistema.")
        db.atualizar_status(id_req, 6, f"Certificado '{nome_certificado}' não mapeado")
        return False, f"Certificado '{nome_certificado}' não mapeado", True

    logger.info(f"Certificado validado: {nome_certificado} (ID: {id_certificado})")

    logger.info("Atualizando status para 8 (Acessando)...")
    db.atualizar_status(id_req, 8)

    def update_status_download(status_code):
        db.atualizar_status(id_req, status_code)

    ensure_browser_closed()
    time.sleep(2)

    url_login = "https://cav.receita.fazenda.gov.br/autenticacao/login"
    if not open_browser(url_login):
        db.atualizar_status(id_req, 6, "Erro ao abrir Edge")
        return False, "Erro ao abrir Edge", False

    time.sleep(5)

    sucesso = False
    erro_msg = None
    status_atualizado = False

    try:
        sucesso = executar_fluxo_cnpj(
            cnpj_db,
            path_docs,
            nome_certificado=nome_certificado,
            callback_status=update_status_download,
        )

    except BusinessError as e:
        logger.error(f"Erro de Negócio: {e}")
        salvar_print_erro(f"erro_negocio_req_{id_req}")
        db.atualizar_status(id_req, getattr(e, 'status_id', 6), str(e))
        status_atualizado = True
        return False, str(e), True

    except CriticalImageNotFoundError as e:
        erro_msg = str(e)
        logger.error(f"Falha Visual: {erro_msg}")
        salvar_print_erro(f"falha_visual_req_{id_req}")
        sucesso = False

    except Exception as e:
        erro_msg = str(e)
        logger.error(f"Erro Inesperado: {erro_msg}")
        salvar_print_erro(f"erro_inesperado_req_{id_req}")
        traceback.print_exc()
        sucesso = False

    finally:
        time.sleep(2)
        ensure_browser_closed()

        if sucesso:
            if sucesso == "SEM_PEDIDOS":
                msg_final = "sem perdcomp no periodo (status 11)"
                db.atualizar_status(id_req, 11, msg_final)
            else:
                msg_final = "Finalizado com sucesso"
                db.atualizar_status(id_req, 5, msg_final)
            
            logger.info(f"Solicitação concluída: {msg_final}")
        elif not status_atualizado:
            msg_final = erro_msg if erro_msg else "Falha no fluxo ou inconsistência"
            logger.error(f"Solicitação interrompida: {msg_final}")
            db.atualizar_status(id_req, 6, msg_final[:255])

        time.sleep(1)

    return sucesso, erro_msg, False


def main():
    logger.info("#" * 60)
    logger.info("   ROBO DE ACESSO AO eCAC (EDGE) - RPA PERDCOMP")
    logger.info("#" * 60)

    if not verificar_arquivos():
        logger.error("Automação abortada por falta de arquivos.")
        time.sleep(5)
        return

    logger.info("Testando conexão com Banco de Dados...")
    db = DBHandler()
    if not db.connect():
        logger.error("Falha na conexão com o banco.")
        return

    logger.info("Buscando solicitações pendentes (id_tipo_arquivo = 6, id_status = 1)...")
    requests = db.buscar_solicitacoes_pendentes()

    if not requests:
        logger.info("Nenhuma solicitação pendente encontrada. Encerrando.")
        return

    logger.info(f"Total de solicitações encontradas: {len(requests)}")

    path_docs = os.getenv("DOCUMENTS_PATH", os.path.join(os.path.expanduser("~"), "Documents"))

    # O retry agora é gerenciado pelo decorador @retry_on_exception em processar_solicitacao
    for req in requests:
        sucesso, erro_msg, fatal = processar_solicitacao(req, db, path_docs)
        if not sucesso and fatal:
            logger.warning(f"ID {req['id']} interrompido por erro fatal. Pulando para o próximo.")

    logger.info("Automação finalizada.")


if __name__ == "__main__":
    main()
