# Documentação Técnica - RPA PERDCOMP

Esta documentação detalha o funcionamento interno, as funções e a lógica do robô **RPA PERDCOMP**. Ela foi criada para servir como guia técnico de manutenção, mantendo o código fonte limpo de comentários extensos.

---

## 🏗️ 1. Módulo Core (`src/core`)

O módulo core contém as funções de utilidade reutilizáveis que formam a base da automação.

### `vision.py` (Visão Computacional)
Responsável por toda a interação baseada em reconhecimento de imagem.

- **`clicar_imagem(nome, ...)`**: Localiza o centro de uma imagem na pasta `assets/images` e realiza um clique. Possui parâmetros de `confianca`, `offset` (ajuste de pixels) e flag `critical` (levanta erro fatal se não encontrar).
- **`esperar_e_clicar(nome, timeout=30, ...)`**: Essencial para sincronização. Aguarda a imagem aparecer por até N segundos antes de interagir. Loop interno com pausas otimizadas para baixo consumo de CPU.
- **`imagem_existe(nome, ...)`**: Retorna booleano simples sobre a presença de um elemento na tela.
- **`esperar_sumir(nome, ...)`**: Bloqueia a execução até que um elemento (ex: Modal de Loading) desapareça.
- **`salvar_print_erro(nome_base)`**: Captura a tela inteira em caso de falha e salva em `logs/screenshots/` com timestamp.

### `browser.py`
Gerencia a vida útil do Microsoft Edge.
- **`open_browser(url)`**: Inicia o processo do Edge limpo.
- **`ensure_browser_closed()`**: Mata processos remanescentes do Edge para evitar conflitos entre solicitações.

---

## 🗄️ 2. Módulo de Banco de Dados (`src/database`)

### `db_handler.py` (Classe `DBHandler`)
Gerencia a persistência e o controle de fila no MySQL.

- **`buscar_solicitacoes_pendentes()`**:
    - Filtra por `id_tipo_arquivo = 5` (específico para PERDCOMP).
    - Ignora status finais: `5` (Sucesso), `11` (Sem Documentos), `14` (Pendência), `15` (Inválido).
- **`atualizar_status(id, novo_status, etapa_erro)`**:
    - Atualiza o progresso da solicitação.
    - `etapa_erro` é limitado a 255 caracteres para evitar estouro no banco.
- **`buscar_nome_certificado(id_certificado)`**: Converte IDs numéricos do banco no nome textual do certificado instalado no Windows.

---

## 🔄 3. Módulo de Fluxo (`src/workflow`)

### `workflow_perdcomp.py`
Contém a lógica de negócio e os passos sequenciais do portal eCAC.

#### Classe `MonitorDownloads` (Threading)
Funciona como um processo paralelo ("Daemon") que observa a pasta de downloads do Windows.
- **Lógica de Estabilização**: Antes de mover um arquivo, ele verifica o tamanho repetidamente. Se o tamanho não mudar por X segundos, o download é considerado concluído.
- **Padronização**: Renomeia arquivos para `CNPJ_NomeOriginal.pdf`.
- **Controle de Slots**: Limita a 3 downloads simultâneos para não sobrecarregar a conexão ou o navegador.

#### Funções Principais
- **`executar_fluxo_cnpj(...)`**: Orquestrador do fluxo. Realiza login, troca de perfil e aciona a navegação.
- **`automated_login_certificado(nome)`**: Simula o teclado (TAB e Setas) para selecionar o certificado nominal na janela pop-up do navegador. Utiliza o `MAPA_CERTIFICADOS` para saber quantas vezes pressionar a seta para baixo.
- **`trocar_perfil_cnpj(cnpj)`**: Insere o CNPJ no campo de perfil e verifica imediatamente se apareceram mensagens de erro exclusivas do eCAC (como bloqueios ou CNPJ inválido).
- **`acessar_painel_perdcomp()`**: Navega entre menus de 2º e 3º nível: *Restituição e Compensação -> Acessar PER/DCOMP -> Visualizar Documentos*. Preenche as datas automaticamente (padrão: 01/01/2021 até Data Atual).
- **`processar_downloads(...)`**: Itera sobre a tabela de resultados. Realiza o scroll da página, identifica os ícones de download via OpenCV e clica. Gerencia a paginação clicando no botão "Próxima" (o mais à direita na tela).

---

## 🚀 4. Orquestração Principal (`main.py`)

O arquivo raiz coordena a execução global:

1.  **Pré-checagem (`verificar_arquivos`)**: Valida se todos os assets visuais estão disponíveis antes de abrir o browser.
2.  **Loop de Processamento**:
    - Obtém a fila do banco.
    - Chama `processar_solicitacao` para cada item.
    - **Retry Logic**: Utiliza o decorador `@retry_on_exception` para tentar novamente (até 3 vezes) caso ocorra um erro técnico inesperado.
3.  **Finalização**: Garante o fechamento do navegador e a limpeza de recursos ao fim de cada ciclo.

---

## 📝 5. Tabela de Status e Erros

| Status | Descrição |
| :--- | :--- |
| **8** | **Acessando**: Robô iniciou a tentativa de login. |
| **4** | **Processando**: Robô já está dentro do painel PERDCOMP. |
| **5** | **Sucesso**: Download concluído e confirmado no disco. |
| **11** | **Sem Eventos**: Portal informou que não há documentos no período. |
| **6** | **Erro**: Falha técnica, imagem não encontrada ou erro inesperado. |
| **14** | **Pendência**: CNPJ possui bloqueio ou mensagem impeditiva. |
| **15** | **Inválido**: CNPJ não cadastrado ou erro de digitação no pedido. |

---
*Fim da Documentação Técnica.*
