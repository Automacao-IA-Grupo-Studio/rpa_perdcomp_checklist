import os
import mysql.connector
from dotenv import load_dotenv
from src.core.logger import logger

# Carrega variáveis do arquivo .env-
load_dotenv()

class DBHandler:
    def __init__(self):
        self.config = {
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "database": os.getenv("DB_NAME"),
            "port": int(os.getenv("DB_PORT", 3306)),
        }

    def _get_connection(self):
        try:
            conn = mysql.connector.connect(**self.config)
            return conn
        except mysql.connector.Error as err:
            logger.error(f"Erro ao conectar no Banco de Dados: {err}")
            return None

    def connect(self):
        conn = self._get_connection()
        if conn:
            conn.close()
            return True
        return False

    def close(self):
        pass

    def buscar_solicitacoes_pendentes(self):
        """Busca solicitações pendentes de PERDCOMP (id_tipo_arquivo = 5)."""
        query = "SELECT * FROM pjdocs_sol_baixa_arquivos WHERE id_tipo_arquivo = 5 AND id_status NOT IN (5, 11, 14, 15)"
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            resultados = cursor.fetchall()
            cursor.close()
            conn.close()
            return resultados
        except mysql.connector.Error as err:
            logger.error(f"Erro ao buscar solicitações: {err}")
            return []

    def atualizar_status(self, id_solicitacao, novo_status, etapa_erro=None):
        """Atualiza o status e a etapa de erro na tabela principal."""
        query = "UPDATE pjdocs_sol_baixa_arquivos SET id_status = %s, updated_at = NOW()"
        params = [novo_status]

        if etapa_erro:
            query += ", etapa_erro = %s"
            params.append(str(etapa_erro)[:255])

        query += " WHERE id = %s"
        params.append(id_solicitacao)

        conn = self._get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except mysql.connector.Error as err:
            logger.error(f"Erro ao atualizar status: {err}")
            return False

    def buscar_nome_certificado(self, id_certificado):
        """Busca o nome do certificado na tabela pjdocs_certificados."""
        if not id_certificado:
            return None
        query = "SELECT certificado FROM pjdocs_certificados WHERE id = %s"
        conn = self._get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (id_certificado,))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            return resultado.get("certificado") if resultado else None
        except mysql.connector.Error as err:
            logger.error(f"Erro ao buscar nome do certificado: {err}")
            return None
