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
Gerencia a persistência e o controle de fila no PostgreSQL (Supabase).

- **`buscar_solicitacoes_pendentes()`**:
    - Filtra por `id_tipo_arquivo = 6` (específico para PERDCOMP).
    - Busca apenas registros com `id_status = 1` (Pendente).
    - Faz JOIN com a tabela `pjdocs_sol_baixa_arqs_perdcomp` para obter períodos.
- **`atualizar_status(id, novo_status, etapa_erro)`**:
    - Atualiza o progresso da solicitação.
    - Mapeia o status detalhado do robô para o status geral do painel (1-4).
    - Atualiza também a tabela detalhe `pjdocs_sol_baixa_arqs_perdcomp`.
    - `etapa_erro` é limitado a 255 caracteres para evitar estouro no banco.
- **`buscar_detalhes_perdcomp(id_solicitacao)`**: Busca os detalhes (períodos) da solicitação PERDCOMP.
- **`buscar_nome_certificado(id_certificado)`**: Busca o `profile_key` do certificado pelo UUID na tabela `certificates`.

---

## 🔄 3. Módulo de Fluxo (`src/workflow`)

### `workflow_perdcomp.py`
Contém a lógica de negócio e os passos sequenciais do portal eCAC.

#### Funções Principais
- **`executar_fluxo_cnpj(...)`**: Orquestrador do fluxo. Realiza login, troca de perfil e aciona a navegação.
- **`automated_login_certificado(nome)`**: Simula o teclado (TAB e Setas) para selecionar o certificado nominal na janela pop-up do navegador. Utiliza o `MAPA_CERTIFICADOS` para saber quantas vezes pressionar a seta para baixo.
- **`trocar_perfil_cnpj(cnpj)`**: Insere o CNPJ no campo de perfil e verifica imediatamente se apareceram mensagens de erro exclusivas do eCAC (como bloqueios ou CNPJ inválido).
- **`acessar_painel_perdcomp()`**: Navega entre menus de 2º e 3º nível: *Restituição e Compensação -> Acessar PER/DCOMP -> Visualizar Documentos*. Preenche as datas automaticamente (padrão: 01/01/2021 até Data Atual).
- **`processar_downloads(...)`**: Utiliza o Playwright conectado via CDP na porta 9222 para localizar botões de download no DOM (dentro de um iframe `#frmApp`). Itera sobre todas as páginas da tabela de resultados e salva os arquivos no padrão `CNPJ_NomeOriginal.pdf`.

---

## 🚀 4. Orquestração Principal (`main.py`)

O arquivo raiz coordena a execução global:

1.  **Pré-checagem (`verificar_arquivos`)**: Valida se todos os assets visuais estão disponíveis antes de abrir o browser.
2.  **Loop de Processamento**:
    - Obtém a fila do banco (filtrando `id_tipo_arquivo = 6` e `id_status = 1`).
    - Chama `processar_solicitacao` para cada item.
    - **Retry Logic**: Utiliza o decorador `@retry_on_exception` para tentar novamente (até 3 vezes) caso ocorra um erro técnico inesperado.
3.  **Finalização**: Garante o fechamento do navegador e a limpeza de recursos ao fim de cada ciclo.

---

## 📝 5. Tabela de Status

### Status Gerais (Tabela `pjdocs_sol_baixa_arquivos_status`)

Estes são os únicos valores válidos na tabela principal `pjdocs_sol_baixa_arquivos`:

| ID | Descrição |
| :--- | :--- |
| **1** | **Pendente** |
| **2** | **Em Processamento** |
| **3** | **Concluído** |
| **4** | **Erro** |

### Status Detalhados (Tabela `pjdocs_sol_baixa_arqs_perdcomp`)

O robô utiliza status detalhados internamente, que são mapeados para os status gerais:

| Status Detalhe | Descrição | Status Geral |
| :--- | :--- | :--- |
| **8** | **Acessando**: Robô iniciou a tentativa de login. | 2 (Em Processamento) |
| **4** | **Processando**: Robô já está dentro do painel PERDCOMP. | 2 (Em Processamento) |
| **5** | **Sucesso**: Download concluído e confirmado no disco. | 3 (Concluído) |
| **11** | **Sem Eventos**: Portal informou que não há documentos no período. | 3 (Concluído) |
| **6** | **Erro**: Falha técnica, imagem não encontrada ou erro inesperado. | 4 (Erro) |
| **14** | **Pendência**: CNPJ possui bloqueio ou mensagem impeditiva. | 4 (Erro) |
| **15** | **Inválido**: CNPJ não cadastrado ou erro de digitação no pedido. | 4 (Erro) |

---
*Fim da Documentação Técnica.*
