# Banco Ágil - Atendimento

Este projeto é uma solução de atendimento bancário automatizado baseado em agentes de Inteligência Artificial.
O sistema simula a interação com o **Banco Ágil**, um banco digital fictício, oferecendo serviços de triagem, consulta/aumento de crédito, entrevista financeira para ajuste de score e consulta de câmbio em tempo real.

---

## Visão Geral do Projeto

O sistema utiliza uma arquitetura multi-agente para proporcionar uma experiência de conversa fluida e integrada. O cliente interage com uma única interface de chat, enquanto nos bastidores, diferentes especialistas (agentes) assumem o controle da conversa conforme a necessidade identificada. 

A solução foca em segurança (autenticação obrigatória), inteligência de negócios (regras de crédito e score) e utilidade prática (câmbio em tempo real).

---

## Arquitetura do Sistema

A arquitetura foi construída utilizando **LangGraph**, que permite a criação de fluxos de agentes baseados em grafos de estado.

### Agentes e Responsabilidades:

1.  **Agente de Triagem:** O ponto de entrada. Responsável por coletar e validar CPF e data de nascimento do cliente contra a base `clientes.csv`. Possui lógica de redirecionamento baseada na intenção do usuário após a autenticação.
2.  **Agente Analista de Crédito:** Informa o limite disponível e processa solicitações de aumento. Ele utiliza a tabela `score_limite.csv` para decidir pela aprovação ou rejeição automática.
3.  **Agente de Entrevista de Crédito:** Conduz uma entrevista estruturada de 5 perguntas (renda, emprego, despesas, dependentes, dívidas) para coletar dados financeiros e recalcular o score do cliente.
4.  **Agente de Câmbio:** Fornece cotações de moedas em tempo real através de busca via TavilyAPI.

### Fluxo de Dados:

*   **Estado Centralizado (`EstadoAgil`):** Um objeto de estado que transita entre os agentes, contendo o histórico de mensagens, dados do cliente autenticado, progresso da entrevista e flags de controle.
*   **Manipulação de Dados:** O sistema utiliza **Pandas** para ler e escrever em arquivos CSV localizados na pasta `resources/`. 
    *   `clientes.csv`: Dados cadastrais e saldos.
    *   `score_limite.csv`: Tabela de referência para aprovação de crédito.
    *   `solicitacoes_aumento_limite.csv`: Log de todas as solicitações processadas.

---

## Funcionalidades Implementadas

*   **Autenticação Segura:** Fluxo de validação de CPF e data de nascimento com limite de 3 tentativas consecutivas.
*   **Consulta de Limite:** Informa o limite de crédito de forma personalizada.
*   **Aumento de Limite Inteligente:** Processa pedidos de aumento comparando o valor solicitado com o limite permitido para o score atual do cliente.
*   **Entrevista Conversacional:** Coleta de dados financeiros para atualização de perfil de crédito.
*   **Cálculo Dinâmico de Score:** Implementação de fórmula matemática baseada em pesos para garantir o cálculo do score.
*   **Cotação de Câmbio em Tempo Real:** Integração com API de busca (Tavily) para retornar valores atualizados de moedas.
*   **Interrupção de Conversa:** O usuário pode encerrar o atendimento a qualquer momento de forma natural (ex: "tchau", "encerrar").
*   **Interface Streamlit:** UI intuitiva para facilitar a interação e testes do sistema.

---

## Desafios Enfrentados e Soluções
*   **Persistência de Estado no Streamlit:** Devido ao reload do streamlit, manter o estado do graph foi um desafio.
    *   *Solução:* Armazenamento do objeto de estado do LangGraph dentro do `st.session_state` e uso do `MemorySaver` para garantir que o contexto não fosse perdido entre as mensagens.
*   **Tratamento de Erros:** Falhas em qualquer operação.
    *   *Solução:* Implementação de blocos `try/except` com Command retornando uma mensagem de erro e armazenamento das informações do erro em um arquivo JSON para depuração, incluindo todo o EstadoAgil no momento do erro, facilitando a depuração.

---

## Escolhas Técnicas e Justificativas

*   **LangGraph:** Escolhido pela sua capacidade superior de gerenciar fluxos cíclicos e manter um estado compartilhado, o que é ideal para sistemas multi-agentes complexos e já estava familiarizado com LangChain.
*   **Google Gemini (2.5 Flash):** Selecionado pelo excelente custo-benefício, grande janela de contexto, suporte nativo a chamadas de ferramentas e saídas estruturadas e por eu já usar no meu dia a dia.
*   **Tavily Search:** Escolhida para o agente de câmbio por ser uma ferramenta de busca otimizada para agentes de IA, retornando resultados limpos e fáceis de processar pelo LLM.

---

## 6. Tutorial de Execução e Testes

### Pré-requisitos
*   Python 3.10 ou superior.
*   Uma chave de API do **Google Gemini**.
*   Uma chave de API do **Tavily**.

### Configuração do Ambiente

1. Clone o repositório.
2. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
   ```env
   GOOGLE_API_KEY=sua_chave_aqui
   TAVILY_API_KEY=sua_chave_aqui
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### Execução da Aplicação

Para iniciar o chat do Banco Ágil, execute:
```bash
streamlit run app.py
```

### Execução de Testes Unitários

Para validar as ferramentas de manipulação de dados e regras de negócio:
```bash
pytest tests/test_tools.py
```
