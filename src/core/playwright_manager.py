import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class PlaywrightManager:
    """
    Singleton para gerenciar a instância do Playwright acoplada
    a um navegador Edge aberto nativamente via CDP (Porta 9222).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlaywrightManager, cls).__new__(cls)
            cls._instance.playwright_context = None
            cls._instance.browser = None
            cls._instance.page = None
        return cls._instance

    def connect(self, port=9222):
        """
        Conecta o Playwright ao navegador Edge nativo.
        """
        if self.playwright_context is not None:
            return self.page

        logger.info(f"Conectando Playwright ao Edge nativo (Porta {port})...")
        self.playwright_context = sync_playwright().start()
        
        try:
            self.browser = self.playwright_context.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            context = self.browser.contexts[0]
            self.page = context.pages[0]
            logger.info("Playwright conectado com sucesso ao Edge nativo.")
            return self.page
        except Exception as e:
            logger.error(f"Falha ao conectar Playwright na porta {port}. O navegador foi aberto com debug? Erro: {e}")
            self.stop()
            return None

    def get_page(self):
        return self.page

    def stop(self):
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
            
        if self.playwright_context:
            try:
                self.playwright_context.stop()
            except Exception:
                pass
            self.playwright_context = None
            self.page = None
        
        logger.info("Conexão Playwright encerrada.")

pw_manager = PlaywrightManager()
