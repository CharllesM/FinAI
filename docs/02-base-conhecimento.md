# 02. Base de Conhecimento e Estratégia de Dados

Este documento descreve a organização, os schemas e o fluxo de preparação dos dados utilizados pelo **FinAI**, seguindo a estrutura do repositório [digitalinnovationone/dio-lab-bia-do-futuro](https://github.com/digitalinnovationone/dio-lab-bia-do-futuro).

## 1. Visão Geral dos Arquivos (`data/`)

| Arquivo | Formato | Papel no Raciocínio do Agente |
| :--- | :--- | :--- |
| `data/transacoes.csv` | CSV | Permite auditar entradas, saídas, gastos por categoria e saldo disponível no mês |
| `data/historico_atendimento.csv` | CSV | Preserva a memória de longo prazo sobre dúvidas anteriores e combinados com o cliente |
| `data/perfil_investidor.json` | JSON | Define o perfil de risco (`Moderado`), patrimônio atual (`R$ 64.000,00`), metas e limites |
| `data/produtos_financeiros.json` | JSON | Catálogo fechado de produtos financeiros elegíveis para simulação e recomendação |

## 2. Detalhamento dos Schemas e Dados Mockados

### 2.1. Histórico de Transações (`data/transacoes.csv`)
Contém as movimentações financeiras de outubro de 2026 do cliente **Carlos Eduardo Mendes**:
- **Receita Total**: `R$ 12.500,00` (Salário Mensal Tech Lead).
- **Saídas Totais (incluindo aporte)**: `R$ 10.429,90` (sendo `R$ 8.929,90` em despesas correntes e `R$ 1.500,00` já aportados no Tesouro Selic Reserva).
- **Saldo Líquido Disponível no Mês**: `R$ 2.070,10`.
- **Destaque de Orçamento**: A categoria `Alimentação` soma `R$ 2.460,00` (`R$ 1.450,00` de supermercado + `R$ 1.010,00` de delivery/restaurantes), superando o alerta de `R$ 2.000,00` para alimentação total e o teto de `R$ 800,00` para delivery registrado no histórico de atendimento.

### 2.2. Histórico de Atendimento (`data/historico_atendimento.csv`)
Registra 4 interações prévias entre agosto e outubro de 2026:
- Orientação sobre **Reserva de Emergência** (agosto/2026).
- Comparativo entre **LCI/LCA e CDB pós-fixado** para prazo de 12 meses (setembro/2026).
- Consulta sobre alocação de até **5% da carteira em criptoativos via ETF regulado na B3** (setembro/2026).
- Solicitação de **alerta mensal quando gastos com delivery ultrapassarem R$ 800,00** (outubro/2026).

### 2.3. Perfil do Investidor (`data/perfil_investidor.json`)
Estrutura hierárquica em JSON contendo:
- **Patrimônio Atual (`R$ 64.000,00`)**:
  - Reserva de Emergência: `R$ 28.500,00` (44,53%)
  - Renda Fixa Pós-Fixada: `R$ 18.000,00` (28,13%)
  - Renda Fixa IPCA+: `R$ 9.500,00` (14,84%)
  - Fundos Imobiliários: `R$ 6.000,00` (9,38%)
  - Criptoativos (ETF): `R$ 2.000,00` (3,12%)
- **Exposição Atual em Renda Variável**: `12,50%` (`R$ 8.000,00` somando FIIs e ETF Cripto), dentro do limite máximo de `25%` do perfil.
- **Metas Financeiras**:
  1. Completar Reserva de Emergência: alvo `R$ 36.000,00` (faltam `R$ 7.500,00`, prazo 5 meses, prioridade Alta).
  2. Certificação Internacional Cloud & AI e intercâmbio: alvo `R$ 25.000,00` (faltam `R$ 15.500,00`, prazo 14 meses, prioridade Média).
  3. Construção de Renda Passiva de Longo Prazo: alvo `R$ 250.000,00` (atual `R$ 26.000,00`, prazo 60 meses, prioridade Média).

### 2.4. Catálogo de Produtos Financeiros (`data/produtos_financeiros.json`)
Inclui 6 produtos com regras claras de liquidez, risco, tributação e aplicação mínima:
- `PROD-001`: **Tesouro Selic 2029** (Risco Baixo, Liquidez D+0, mín. R$ 150,00)
- `PROD-002`: **CDB Liquidez Diária Banco Sólido** (102% CDI, FGC, Liquidez D+0, mín. R$ 100,00)
- `PROD-003`: **LCI Tech Agro 12 Meses** (93% CDI, Isento de IR, Liquidez 360 dias, mín. R$ 1.000,00)
- `PROD-004`: **Tesouro IPCA+ 2035** (IPCA + 6,25% a.a., Longo Prazo, mín. R$ 50,00)
- `PROD-005`: **Carteira Recomendada FIIs Logística & Recebíveis** (Risco Médio, DY ref. 9,8% a.a., D+2, mín. R$ 110,00)
- `PROD-006`: **ETF HASH11 (Índice Nasdaq Crypto Index na B3)** (Risco Alto, D+2, mín. R$ 50,00, teto recomendado de 5% da carteira para perfil Moderado)

## 3. Como os Dados São Carregados no Agente

No arquivo `src/agent.py`, a classe `KnowledgeBase` realiza a leitura segura dos quatro arquivos com codificação `UTF-8`, valida a integridade dos campos e gera um **Resumo Analítico Determinístico** que é injetado diretamente no contexto do modelo, garantindo 100% de precisão numérica nas respostas.
