import os
import psycopg2
from psycopg2.extras import RealDictCursor
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from src.core.logger import logger

# Carrega variáveis do arquivo .env
load_dotenv()

class DBHandler:
    def __init__(self):
        self.config = {
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "database": os.getenv("DB_NAME"),
            "port": int(os.getenv("DB_PORT", 5432)),
        }

    def _get_connection(self):
        try:
            conn = psycopg2.connect(**self.config)
            return conn
        except Exception as err:
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
        query = """
            SELECT p.id, p.cnpj, p.razao_social, p.profile_key, p.id_certificado,
                   d.periodo_ini, d.periodo_fim
            FROM pjdocs_sol_baixa_arquivos p
            JOIN pjdocs_sol_baixa_arqs_perdcomp d ON d.id_solicitacao = p.id
            WHERE p.id_status = 1
            AND p.id_tipo_arquivo = 6
            ORDER BY p.created_at ASC
        """

        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query)
            resultados = cursor.fetchall()
            cursor.close()
            conn.close()
            # Converte RealDictRow para dict comum para garantir compatibilidade
            return [dict(row) for row in resultados]
        except Exception as err:
            logger.error(f"Erro ao buscar solicitacoes: {err}")
            if conn:
                conn.close()
            return []

    def buscar_detalhes_perdcomp(self, id_solicitacao):
        query = "SELECT * FROM pjdocs_sol_baixa_arqs_perdcomp WHERE id_solicitacao = %s"

        conn = self._get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, (id_solicitacao,))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            return dict(resultado) if resultado else None
        except Exception as err:
            logger.error(f"Erro ao buscar detalhes da PerdComp: {err}")
            if conn:
                conn.close()
            return None

    def atualizar_status(self, id_solicitacao, novo_status, etapa_erro=None, traceback_str=None, file_url=None):
        # Mapeamento do status detalhado (robô) para o status geral do painel (pjdocs_sol_baixa_arquivos_status)
        # 1: Pendente
        # 2: Em Processamento
        # 3: Concluído
        # 4: Erro
        status_map = {
            1: 1,   # Pendente -> Pendente
            2: 2,   # Em Processamento -> Em Processamento
            3: 3,   # Concluído -> Concluído
            4: 2,   # Processando -> Em Processamento
            5: 3,   # Sucesso -> Concluído
            6: 4,   # Erro -> Erro
            8: 2,   # Acessando -> Em Processamento
            11: 3,  # Sem Eventos -> Concluído
            14: 4,  # Pendência -> Erro
            15: 4,  # Inválido -> Erro
        }
        parent_status = status_map.get(novo_status, 4)

        query = "UPDATE pjdocs_sol_baixa_arquivos SET id_status = %s, updated_at = NOW()"
        params = [parent_status]

        if etapa_erro is not None:
            query += ", etapa_erro = %s"
            params.append(etapa_erro)

        if traceback_str is not None:
            query += ", traceback = %s"
            params.append(traceback_str)

        if file_url is not None:
            query += ", file_url = %s"
            params.append(file_url)

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

            self.atualizar_status_detalhe(id_solicitacao, novo_status)
            return True
        except Exception as err:
            logger.error(f"Erro ao atualizar status: {err}")
            if conn:
                conn.close()
            return False

    def buscar_nome_certificado(self, id_certificado):
        query = "SELECT profile_key FROM certificates WHERE id = %s"

        conn = self._get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, (id_certificado,))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()

            if resultado:
                return resultado.get("profile_key")
            return None
        except Exception as err:
            logger.error(f"Erro ao buscar nome do certificado: {err}")
            if conn:
                conn.close()
            return None

    def atualizar_status_detalhe(self, id_solicitacao, novo_status):
        query = "UPDATE pjdocs_sol_baixa_arqs_perdcomp SET id_status = %s WHERE id_solicitacao = %s"

        conn = self._get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(query, (novo_status, id_solicitacao))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as err:
            logger.error(f"Erro ao atualizar status detalhe: {err}")
            if conn:
                conn.close()

    def registrar_robo(self, robot_id, display_name):
        query = """
            INSERT INTO rpa_robot_status
            (robot_id, display_name, status, last_heartbeat, schedule_start, schedule_end)
            VALUES (%s, %s, 'idle', NOW(), '00:00', '08:00')
            ON CONFLICT (robot_id) DO UPDATE
            SET display_name = EXCLUDED.display_name,
                schedule_start = EXCLUDED.schedule_start,
                schedule_end = EXCLUDED.schedule_end
        """
        conn = self._get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute(query, (robot_id, display_name))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as err:
            logger.error(f"Erro ao registrar robo {robot_id}: {err}")
            if conn:
                conn.close()
            return False

    def iniciar_execucao_robo(self, robot_id):
        query = """
            UPDATE rpa_robot_status
            SET status = 'running',
                last_heartbeat = NOW(),
                last_run_at = NOW(),
                last_error = NULL
            WHERE robot_id = %s
        """
        conn = self._get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute(query, (robot_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as err:
            logger.error(f"Erro ao iniciar execucao do robo {robot_id}: {err}")
            if conn:
                conn.close()
            return False

    def finalizar_sucesso_robo(self, robot_id):
        query = """
            UPDATE rpa_robot_status
            SET status = 'idle',
                last_heartbeat = NOW(),
                next_run_at = NOW() + INTERVAL '1 day'
            WHERE robot_id = %s
        """
        conn = self._get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute(query, (robot_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as err:
            logger.error(f"Erro ao finalizar sucesso do robo {robot_id}: {err}")
            if conn:
                conn.close()
            return False

    def finalizar_erro_robo(self, robot_id, erro_msg):
        query = """
            UPDATE rpa_robot_status
            SET status = 'error',
                last_heartbeat = NOW(),
                last_error = %s
            WHERE robot_id = %s
        """
        conn = self._get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute(query, (erro_msg, robot_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as err:
            logger.error(f"Erro ao finalizar erro do robo {robot_id}: {err}")
            if conn:
                conn.close()
            return False
