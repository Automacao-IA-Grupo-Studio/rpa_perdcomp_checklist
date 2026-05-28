import os
import sys
import time

# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright


def rastrear_tela():
    print("==================================================================")
    print(" INICIANDO MODO ESPIÃO - PERDCOMP (eCAC) ")
    print("==================================================================")

    # 1. Abre o Edge NATIVAMENTE para o Certificado funcionar!
    # Adicionamos a porta de depuração (9222) para plugar o Playwright depois.
    import tempfile

    TEMP_PROFILE_DIR = os.path.join(
        tempfile.gettempdir(), "Edge_Debug_Profile_Perdcomp"
    )
    os.system("taskkill /F /IM msedge.exe /T 2>nul")
    time.sleep(1)

    # URL do eCAC
    comando = f'start msedge --remote-debugging-port=9222 --user-data-dir="{TEMP_PROFILE_DIR}" "https://cav.receita.fazenda.gov.br/autenticacao/login"'
    os.system(comando)

    print("\n>>> O navegador abriu NATIVAMENTE (sem bloqueios do eCAC).")
    print(">>> INSTRUÇÕES:")
    print("1. Faça o Login pelo gov.br/certificado digital normalmente.")
    print(
        "2. Navegue manualmente até a tela de Documentos Entregues do PER/DCOMP onde a lista (grade) aparece."
    )
    print(
        "3. Aguarde aqui... Em 60 segundos eu vou 'plugar' o Playwright, extrair o HTML e listar os seletores."
    )

    for i in range(60, 0, -1):
        if i in [50, 40, 30, 20, 10]:
            print(f"... Faltam {i} segundos para eu plugar e rastrear.")
        time.sleep(1)

    print("\n>>> TEMPO ESGOTADO! Conectando o Playwright no Edge aberto...")

    with sync_playwright() as p:
        try:
            # 2. Conecta no navegador nativo que já está aberto!
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0]

            html_path = os.path.join(os.getcwd(), "perdcomp_spy.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())

            print("\n>>> HTML Completo salvo:", html_path)

            with open("perdcomp_botoes.txt", "w", encoding="utf-8") as f:
                links = page.locator("a, button, span, img, td").all()
                encontrados = 0
                for link in links:
                    try:
                        title = link.get_attribute("title")
                        cls = link.get_attribute("class")
                        text_val = link.inner_text()

                        target_words = [
                            "download",
                            "baixar",
                            "próxima",
                            "prox",
                            "paginate",
                            "seguinte",
                            "next",
                        ]

                        is_target = False
                        if title and any(w in title.lower() for w in target_words):
                            is_target = True
                        if cls and any(w in cls.lower() for w in target_words):
                            is_target = True
                        if text_val and any(
                            w in text_val.lower() for w in target_words
                        ):
                            is_target = True

                        if is_target:
                            f.write(
                                f"Title: {title} | Class: {cls} | Text: {text_val}\nHTML: {link.evaluate('node => node.outerHTML')}\n\n"
                            )
                            encontrados += 1
                    except Exception:
                        pass

            print(
                f">>> Analisado com sucesso! Mapeamos {encontrados} botões promissores no arquivo 'perdcomp_botoes.txt'"
            )
            browser.close()
        except Exception as e:
            print(
                "Erro ao plugar o Playwright (O navegador continuou aberto? Você usou a porta 9222?):",
                e,
            )


if __name__ == "__main__":
    rastrear_tela()
