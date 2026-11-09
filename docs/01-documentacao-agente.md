# 01. Documentação do Agente — FinAI (Consultor Financeiro & Cripto Inteligente)

Este documento detalha a concepção, persona, arquitetura e mecanismos de segurança do **FinAI**, desenvolvido como projeto prático para o desafio [Construa Seu Assistente Virtual Com Inteligência Artificial](https://github.com/digitalinnovationone/dio-lab-bia-do-futuro) da Digital Innovation One (DIO).

## 1. Problema e Caso de Uso

### Qual problema financeiro o agente resolve?
Muitas pessoas acumulam transações bancárias, assinaturas e aplicações avulsas sem conseguir conectar seu fluxo de caixa mensal às suas metas de curto, médio e longo prazo. Além disso, investidores de perfil moderado frequentemente têm dúvidas sobre como equilibrar a **reserva de emergência** com produtos isentos de imposto (como LCI/LCA) e uma exposição controlada a **ativos digitais regulados** (como ETFs de criptoativos na B3) sem cair em promessas irreais de rentabilidade.

### Objetivos Principais do FinAI
- **Diagnosticar o fluxo de caixa mensal**: Analisar receitas, despesas por categoria e capacidade real de aporte com base em `data/transacoes.csv`.
- **Monitorar alertas de orçamento**: Identificar desvios de gastos (como o teto de alimentação e delivery acordado em `data/historico_atendimento.csv` e `data/perfil_investidor.json`).
- **Apoiar decisões de alocação com base em dados**: Sugerir produtos exclusivamente presentes no catálogo homologado (`data/produtos_financeiros.json`) que respeitem o perfil de risco do cliente (`Moderado`).
- **Prevenir alucinações e recomendações imprudentes**: Recusar previsões especulativas de mercado, cálculos sem base nos dados fornecidos ou indicação de ativos fora da base de conhecimento.

## 2. Persona e Tom de Voz

| Atributo | Definição |
| :--- | :--- |
| **Nome do Assistente** | **FinAI** — Educador e Consultor Financeiro Inteligente |
| **Público-Alvo** | Clientes bancários e profissionais que buscam organizar orçamento pessoal, concluir a reserva de emergência e diversificar investimentos com segurança |
| **Arquétipo** | Consultor analítico, didático, transparente e parceiro |
| **Tom de Voz** | Claro, objetivo, acolhedor e livre de jargões excessivos (explica siglas como CDI, Selic, FGC, IPCA e ETF quando citadas) |
| **Postura Consultiva** | Nunca impõe decisões; apresenta cenários com números extraídos da base do cliente e propõe o próximo passo prático |

### Exemplos de Linguagem
- **Como o FinAI fala**: *"Analisando suas transações de outubro de 2026, seus gastos com Alimentação somaram R$ 2.460,00 (ultrapassando em R$ 460,00 sua meta de R$ 2.000,00). Se redirecionarmos R$ 400,00 do delivery para o Tesouro Selic 2029, você conclui sua reserva de emergência mais rápido."*
- **Como o FinAI NÃO fala**: *"Compre criptomoedas agora porque vão dobrar de valor no próximo mês!"* ou *"Acredito que a taxa Selic cairá para 8% na próxima reunião."*

## 3. Arquitetura da Solução

O FinAI utiliza o padrão de **Injeção Estruturada de Contexto + RAG Local (Retrieval-Augmented Generation)** sobre os arquivos da pasta `data/`, combinado com validação determinística prévia em Python (cálculo exato de saldos, categorias e metas) antes da geração da resposta pelo LLM.

```mermaid
flowchart TD
    U[Pessoa Usuária] -->|Pergunta no Chat| UI[Interface Streamlit - src/app.py]
    UI --> ENG[Motor do Agente - src/agent.py]
    
    subgraph Base de Conhecimento Local - data/
        T[(transacoes.csv)]
        H[(historico_atendimento.csv)]
        P[(perfil_investidor.json)]
        F[(produtos_financeiros.json)]
    end
    
    T & H & P & F --> CALC[Agregador Determinístico Python
Cálculo exato de receitas, despesas e metas]
    CALC --> ENG
    
    ENG -->|System Prompt + Contexto Auditado| LLM{Provedor LLM Configurado?}
    LLM -->|Google Gemini / OpenAI / Ollama| API[Geração via Modelo Generativo]
    LLM -->|Sem API Key / Modo Offline| FALLBACK[Motor Consultivo Determinístico Local]
    
    API --> GUARD[Guardrails Anti-Alucinação & Validação]
    FALLBACK --> GUARD
    GUARD -->|Resposta Fundamentada + Próximo Passo| UI
```

## 4. Segurança e Governança Anti-Alucinação

Para garantir respostas auditáveis no contexto financeiro, o FinAI implementa quatro camadas de proteção:

1. **Cálculo Matemático Determinístico em Python**: Modelos de linguagem não devem somar faturas no improviso. O módulo `src/agent.py` calcula previamente o total de entradas (`R$ 12.500,00`), saídas (`R$ 10.429,90`), aportes já realizados (`R$ 1.500,00`), saldo livre (`R$ 2.070,10`) e totais por categoria antes de montar o prompt.
2. **Restrição Estrita de Catálogo (Closed-World Assumption)**: O agente só pode mencionar os 6 produtos cadastrados em `data/produtos_financeiros.json`. Qualquer pergunta sobre ações individuais, opções, alavancagem ou ativos não listados aciona uma recusa transparente.
3. **Respeito ao Limite de Risco do Perfil**: Como o cliente possui perfil **Moderado** e limite máximo de 25% em renda variável (e recomendação de até 5% em criptoativos via `ETF HASH11`), o agente bloqueia sugestões que violem essa política.
4. **Disclaimer Regulatório e Transparência**: O agente informa explicitamente quando não possui dados suficientes (por exemplo, faturas de meses anteriores a outubro de 2026 ou cotações em tempo real) e lembra que simulações educativas não substituem recomendação formal certificada (CVM/ANBIMA).
