# 🤖 FinAI — Assistente Virtual Consultivo de Finanças & Criptoativos com IA Generativa

Projeto prático desenvolvido para o desafio **[Construa Seu Assistente Virtual Com Inteligência Artificial](https://github.com/digitalinnovationone/dio-lab-bia-do-futuro)** da **Digital Innovation One (DIO)**.

O **FinAI** é um agente financeiro inteligente capaz de analisar o histórico de transações da pessoa usuária, identificar desvios de orçamento proativamente, acompanhar metas financeiras e recomendar produtos de investimento (incluindo renda fixa e exposição controlada a criptoativos regulados na B3) com **zero alucinação** numérica.

## 🎯 Objetivo e Diferenciais do Projeto

Assistentes virtuais financeiros precisam ir além de respostas genéricas: eles devem respeitar o perfil de risco do investidor, fazer contas exatas e jamais inventar produtos ou rentabilidades. O **FinAI** resolve esse problema combinando:

- **Agregação Determinística em Python (`src/agent.py`)**: Todas as somas de receitas, despesas por categoria, saldo livre e distância até as metas são calculadas matematicamente antes de compor o prompt da IA.
- **Base de Conhecimento Estruturada (`data/`)**: Contexto alimentado por 4 arquivos (`transacoes.csv`, `historico_atendimento.csv`, `perfil_investidor.json` e `produtos_financeiros.json`).
- **Guardrails Anti-Alucinação**: O agente opera sob restrição estrita de catálogo (*Closed-World Assumption*), recusa previsões especulativas de mercado e bloqueia alocações incompatíveis com o perfil **Moderado**.
- **Arquitetura Híbrida (Online + Offline)**: Suporta integração com [Google Gemini API](https://ai.google.dev/gemini-api/docs) e [OpenAI API](https://platform.openai.com/docs), além de contar com um **Motor Consultivo Local (RAG Determinístico Offline)** para que qualquer avaliador possa testar a aplicação imediatamente em [Streamlit](https://docs.streamlit.io/), mesmo sem chaves de API.

## 🗂️ Estrutura do Repositório (6 Passos do Desafio)

```text
assistente-virtual-ia/
├── README.md                          # Apresentação geral, arquitetura e guia de execução
├── requirements.txt                   # Dependências do projeto Python
├── .env.example                       # Exemplo de variáveis de ambiente para chaves de API
├── .gitignore                         # Arquivos ignorados pelo controle de versão
├── data/                              # [PASSO 2] Base de Conhecimento Estruturada
│   ├── transacoes.csv                 # Histórico de receitas, despesas e aportes do mês
│   ├── historico_atendimento.csv      # Memória de atendimentos e alertas solicitados pelo cliente
│   ├── perfil_investidor.json         # Perfil Moderado, composição patrimonial e 3 metas financeiras
│   └── produtos_financeiros.json      # Catálogo homologado de 6 produtos (Tesouro, CDB, LCI, FIIs, HASH11)
├── docs/                              # [PASSOS 1, 2, 3, 5 e 6] Documentação Técnica e Roteiro
│   ├── 01-documentacao-agente.md      # Caso de uso, Persona, Arquitetura Mermaid e Segurança
│   ├── 02-base-conhecimento.md        # Estratégia de dados, schemas e cálculo determinístico
│   ├── 03-prompts.md                  # System Prompt, Few-Shot Prompting e Edge Cases
│   ├── 04-metricas.md                 # Metodologia de avaliação e matriz de testes automatizados
│   └── 05-pitch.md                    # Roteiro estruturado do Pitch de 3 minutos
└── src/                               # [PASSO 4] Aplicação Funcional e Avaliação
    ├── app.py                         # Chatbot interativo e dashboard em Streamlit
    ├── agent.py                       # Motor do agente, RAG local e guardrails anti-alucinação
    └── evaluate.py                    # Suíte automatizada de testes e métricas (6 cenários)
```

## 🧭 Resumo dos 6 Passos Entregues

| Passo | Entrega no Repositório | Destaque Técnico |
| :--- | :--- | :--- |
| **1. Documentação** | `docs/01-documentacao-agente.md` | Define a persona consultiva **FinAI**, fluxo arquitetural em Mermaid e 4 camadas anti-alucinação |
| **2. Base de Conhecimento** | `data/*` + `docs/02-base-conhecimento.md` | Dados correlacionados do cliente Carlos Eduardo Mendes (Perfil Moderado, R$ 12.500 de renda, R$ 64.000 de patrimônio) |
| **3. Prompts** | `docs/03-prompts.md` | System Prompt com injeção de resumo auditado, exemplos Few-Shot e tabela de tratamento de Edge Cases |
| **4. Aplicação Funcional** | `src/app.py` + `src/agent.py` | Interface em Streamlit com KPIs, botões de perguntas rápidas, explorador da pasta `data/` e modo híbrido |
| **5. Avaliação e Métricas** | `docs/04-metricas.md` + `src/evaluate.py` | Script automatizado que valida 6 cenários de teste (100% de precisão numérica e segurança anti-alucinação) |
| **6. Pitch** | `docs/05-pitch.md` | Roteiro cronometrado de 3 minutos cobrindo Problema, Solução, Demonstração e Valor |

## 🚀 Como Executar o Projeto Localmente

### 1. Clonar o repositório e instalar dependências
```bash
git clone https://github.com/CharllesM/FinAI
cd FinAI
pip install -r requirements.txt
```

### 2. Executar a Aplicação Interativa (Streamlit)
```bash
streamlit run src/app.py
```
> **Dica**: A aplicação já abre pronta para uso no modo **Automático / Motor Consultivo Local**. Se desejar conectar ao Google Gemini ou OpenAI, basta informar sua chave de API na barra lateral da própria interface ou configurar um arquivo `.env`.

### 3. Executar a Suíte de Avaliação e Métricas (CLI)
```bash
python3 src/evaluate.py
```

Saída esperada no terminal:
```text
==============================================================================
AVALIAÇÃO AUTOMATIZADA DE QUALIDADE E ANTI-ALUCINAÇÃO — FINAI (DIO LAB)
==============================================================================
[TC-01] Resumo de Fluxo de Caixa e Saldo Livre: APROVADO
[TC-02] Alerta Proativo de Gastos com Alimentação e Delivery: APROVADO
[TC-03] Diagnóstico de Metas e Reserva de Emergência: APROVADO
[TC-04] Recomendação de Produtos do Catálogo e Cripto Regulado: APROVADO
[TC-05] Guardrail Contra Desvio de Perfil (Reserva em Cripto): APROVADO
[TC-06] Abstinência Segura em Dados Inexistentes (Anti-Alucinação): APROVADO
------------------------------------------------------------------------------
RESULTADO FINAL: 6/6 cenários aprovados (100.0% de assertividade e segurança)
==============================================================================
```

## 👨‍💻 Autor

Desenvolvido por **Charlles Franco** como projeto de portfólio na [Digital Innovation One (DIO)](https://www.dio.me/).
- **GitHub**: [github.com/CharllesM](https://github.com/CharllesM)
- **LinkedIn**: [linkedin.com/in/charlles-franco](https://www.linkedin.com/in/charlles-franco)
