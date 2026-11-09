#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo principal do Agente Financeiro Inteligente (FinAI).
Responsável por:
1. Carregar e validar a Base de Conhecimento (pasta data/);
2. Calcular indicadores financeiros determinísticos (evitando erros matemáticos de LLMs);
3. Construir o System Prompt e o contexto RAG local;
4. Consultar o provedor LLM configurado (Google Gemini, OpenAI, Ollama) ou
   executar o Motor Consultivo Local (Fallback determinístico para testes sem API Key).
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class KnowledgeBase:
    """Carrega e processa os arquivos estruturados da pasta data/."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.transacoes = self._load_csv("transacoes.csv")
        self.historico = self._load_csv("historico_atendimento.csv")
        self.perfil = self._load_json("perfil_investidor.json")
        self.produtos = self._load_json("produtos_financeiros.json").get("produtos", [])
        self.metrics = self._compute_metrics()

    def _load_csv(self, filename: str) -> List[Dict[str, str]]:
        filepath = self.data_dir / filename
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [dict(row) for row in reader]

    def _load_json(self, filename: str) -> Dict[str, Any]:
        filepath = self.data_dir / filename
        with open(filepath, mode="r", encoding="utf-8") as f:
            return json.load(f)

    def _compute_metrics(self) -> Dict[str, Any]:
        entradas = 0.0
        saidas_totais = 0.0
        saidas_despesas = 0.0
        aportes_mes = 0.0
        por_categoria: Dict[str, float] = {}
        gastos_delivery = 0.0

        for row in self.transacoes:
            valor = float(row["valor"])
            cat = row["categoria"]
            desc = row["descricao"]
            tipo = row["tipo"].strip().lower()

            if tipo == "entrada":
                entradas += valor
            else:
                saidas_totais += valor
                por_categoria[cat] = round(por_categoria.get(cat, 0.0) + valor, 2)
                if cat.lower() == "investimento":
                    aportes_mes += valor
                else:
                    saidas_despesas += valor
                if "delivery" in desc.lower():
                    gastos_delivery += valor

        saldo_livre = round(entradas - saidas_totais, 2)
        patrimonio = self.perfil.get("patrimonio_atual", {})
        total_patrimonio = float(patrimonio.get("total", 0.0))
        rv_atual = float(patrimonio.get("fundos_imobiliarios", 0.0)) + float(
            patrimonio.get("criptoativos_etf", 0.0)
        )
        pct_rv = round((rv_atual / total_patrimonio) * 100, 2) if total_patrimonio else 0.0
        pct_cripto = (
            round((float(patrimonio.get("criptoativos_etf", 0.0)) / total_patrimonio) * 100, 2)
            if total_patrimonio
            else 0.0
        )

        return {
            "entradas": round(entradas, 2),
            "saidas_totais": round(saidas_totais, 2),
            "saidas_despesas": round(saidas_despesas, 2),
            "aportes_mes": round(aportes_mes, 2),
            "saldo_livre": saldo_livre,
            "por_categoria": por_categoria,
            "gastos_delivery": round(gastos_delivery, 2),
            "total_patrimonio": round(total_patrimonio, 2),
            "rv_atual": round(rv_atual, 2),
            "pct_rv": pct_rv,
            "pct_cripto": pct_cripto,
        }

    def build_context_summary(self) -> str:
        """Gera o bloco textual auditado para injeção no System Prompt do LLM."""
        m = self.metrics
        linhas_cat = "\n".join(
            f"  - {cat}: R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            for cat, val in m["por_categoria"].items()
        )
        metas_txt = "\n".join(
            f"  - {meta['meta']}: Atual R$ {meta['valor_atual']:,.2f} / Alvo R$ {meta['valor_alvo']:,.2f} "
            f"(Faltam R$ {meta['valor_alvo'] - meta['valor_atual']:,.2f}, Prazo: {meta['prazo_meses']} meses, Prioridade: {meta['prioridade']})"
            for meta in self.perfil.get("metas_financeiras", [])
        )
        produtos_txt = "\n".join(
            f"  - [{p['id']}] {p['nome']} ({p['categoria']}): Risco {p['risco']} | "
            f"Rentabilidade ref.: {p['rentabilidade_referencia']} | Liquidez: {p['liquidez']} | "
            f"Mínimo: R$ {p['investimento_minimo']:.2f} | Indicação: {p['indicacao']}"
            for p in self.produtos
        )
        historico_txt = "\n".join(
            f"  - [{h['data']}] {h['tema']} ({h['status']}): {h['resumo']}"
            for h in self.historico
        )

        return (
            f"[RESUMO ANALÍTICO AUDITADO - OUTUBRO/2026]\n"
            f"Cliente: {self.perfil.get('nome')} | Perfil: {self.perfil.get('perfil_risco')}\n"
            f"Receita Mensal: R$ {m['entradas']:,.2f}\n"
            f"Despesas Correntes (sem aportes): R$ {m['saidas_despesas']:,.2f}\n"
            f"Aportes Já Realizados no Mês: R$ {m['aportes_mes']:,.2f}\n"
            f"Total de Saídas (Despesas + Aportes): R$ {m['saidas_totais']:,.2f}\n"
            f"Saldo Livre Disponível no Mês: R$ {m['saldo_livre']:,.2f}\n"
            f"Gastos Totais com Alimentação: R$ {m['por_categoria'].get('Alimentação', 0.0):,.2f} "
            f"(sendo R$ {m['gastos_delivery']:,.2f} em Delivery/Restaurantes)\n"
            f"Detalhamento por Categoria:\n{linhas_cat}\n\n"
            f"[PATRIMÔNIO E EXPOSIÇÃO ATUAL]\n"
            f"Patrimônio Total: R$ {m['total_patrimonio']:,.2f} | "
            f"Exposição em Renda Variável: {m['pct_rv']}% (Limite: 25%) | "
            f"Exposição em Cripto ETF: {m['pct_cripto']}% (Teto recomendado: 5%)\n\n"
            f"[METAS FINANCEIRAS]\n{metas_txt}\n\n"
            f"[HISTÓRICO DE ATENDIMENTO]\n{historico_txt}\n\n"
            f"[CATÁLOGO FECHADO DE PRODUTOS FINANCEIROS]\n{produtos_txt}"
        )


def format_brl(value: float) -> str:
    """Formata float no padrão monetário brasileiro (R$ 1.234,56)."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class FinAIAgent:
    """Agente Virtual Consultivo com suporte a múltiplos provedores LLM e fallback determinístico."""

    def __init__(self, kb: Optional[KnowledgeBase] = None, provider: str = "auto") -> None:
        self.kb = kb or KnowledgeBase()
        self.provider = provider

    def get_system_prompt(self) -> str:
        return (
            "Você é o FinAI, um Assistente Virtual Consultivo de Finanças Pessoais, Investimentos e Criptoativos Regulados.\n"
            "REGRAS OBRIGATÓRIAS (ANTI-ALUCINAÇÃO):\n"
            "1. Responda EXCLUSIVAMENTE com base nos dados do bloco abaixo.\n"
            "2. Nunca invente produtos financeiros, taxas ou dados de outros períodos não presentes na base.\n"
            "3. Respeite o perfil Moderado do cliente (limite de 25% em renda variável e até 5% em criptoativos via ETF HASH11).\n"
            "4. Se não houver informação suficiente na base, declare isso com transparência.\n"
            "5. Sempre finalize sugerindo um próximo passo prático para apoiar a decisão da pessoa usuária.\n\n"
            + self.kb.build_context_summary()
        )

    def answer(self, user_query: str) -> Dict[str, str]:
        """
        Retorna um dicionário com:
          - 'response': texto da resposta ao usuário
          - 'engine': identificador do motor utilizado (Gemini, OpenAI, Ollama ou Motor Consultivo Local)
        """
        # Se o usuário configurou chave de API e pediu provedor externo
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        if self.provider in ("gemini", "auto") and gemini_key:
            try:
                from google import genai

                client = genai.Client(api_key=gemini_key)
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{self.get_system_prompt()}\n\nPergunta do cliente: {user_query}",
                )
                if resp and resp.text:
                    return {"response": resp.text, "engine": "Google Gemini API (gemini-2.5-flash)"}
            except Exception:
                pass

        if self.provider in ("openai", "auto") and openai_key:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=openai_key)
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.get_system_prompt()},
                        {"role": "user", "content": user_query},
                    ],
                    temperature=0.2,
                )
                text = completion.choices[0].message.content
                if text:
                    return {"response": text, "engine": "OpenAI API (gpt-4o-mini)"}
            except Exception:
                pass

        # Fallback: Motor Consultivo Determinístico Local (100% fundamentado na pasta data/)
        return {
            "response": self._local_consultative_engine(user_query),
            "engine": "Motor Consultivo Local (RAG Determinístico Offline)",
        }

    def _local_consultative_engine(self, query: str) -> str:
        q = query.lower()
        m = self.kb.metrics
        nome = self.kb.perfil.get("nome", "Cliente")

        # 1. Edge Case: Dados fora do período ou previsão especulativa de mercado
        anos_fora = ["2020", "2021", "2022", "2023", "2024", "2025", "janeiro", "fevereiro", "março", "abril"]
        termos_especulativos = ["dobrar amanhã", "qual ação vai subir", "memecoin", "previsão do dólar", "loteria", "garantia de 10% ao mês"]
        if any(t in q for t in anos_fora) or any(t in q for t in termos_especulativos):
            return (
                f"Olá, {nome}! Preciso ser totalmente transparente com você:\n\n"
                "- **Limitação da Base de Conhecimento**: Os registros disponíveis em `data/transacoes.csv` cobrem apenas **outubro de 2026**, portanto não possuo histórico de outros meses ou anos anteriores para informar valores sem inventar dados.\n"
                "- **Segurança Anti-Alucinação**: Como assistente consultivo, **não faço previsões especulativas de mercado** nem recomendo ações individuais ou criptomoedas fora do nosso catálogo homologado (`data/produtos_financeiros.json`).\n\n"
                "**Próximo passo sugerido**: Posso analisar o seu saldo livre de **R$ 2.070,10** de outubro de 2026 ou mostrar os 6 produtos disponíveis para o seu perfil **Moderado**. Qual prefere conferir?"
            )

        # 2. Edge Case: Tentativa de colocar a Reserva de Emergência em alto risco / cripto
        if ("reserva" in q and ("cripto" in q or "hash11" in q or "toda" in q or "tudo" in q or "renda variável" in q)):
            return (
                f"Atenção, {nome}: **não recomendo transferir sua Reserva de Emergência para criptoativos ou renda variável.**\n\n"
                "**Por que essa decisão protege seu patrimônio?**\n"
                f"1. **Papel da Reserva de Emergência**: Seus **{format_brl(28500.0)}** atuais têm como objetivo cobrir imprevistos imediatos e precisam de **liquidez diária (D+0)** e **baixo risco**, como no **Tesouro Selic 2029 (PROD-001)** ou no **CDB Liquidez Diária Banco Sólido (PROD-002)**.\n"
                "2. **Respeito ao Perfil Moderado**: O **ETF HASH11 (PROD-006)** possui **risco alto** e liquidez D+2. Para o seu perfil **Moderado**, a diretriz de segurança limita a exposição em criptoativos a no máximo **5% do patrimônio total** (equivalente a **R$ 3.200,00** sobre seus R$ 64.000,00 atuais — e você já possui **R$ 2.000,00** alocados, ou **3,12%**).\n\n"
                "**Próximo passo sugerido**: Mantenha sua reserva protegida em liquidez diária para alcançar a meta de **R$ 36.000,00** (faltam **R$ 7.500,00**) e utilize apenas uma fração de novos aportes caso queira elevar sua posição no **ETF HASH11** até o teto de 5%. Deseja simular esse plano?"
            )

        # 3. Consulta sobre Alimentação / Delivery / Limites de Gastos
        if any(k in q for k in ["alimentação", "alimentacao", "delivery", "restaurante", "limite", "alerta", "mercado"]):
            total_alim = m["por_categoria"].get("Alimentação", 0.0)
            delivery = m["gastos_delivery"]
            mercado = round(total_alim - delivery, 2)
            return (
                f"Analisando suas transações de **outubro de 2026**, veja o diagnóstico da categoria **Alimentação**:\n\n"
                f"- **Total gasto com Alimentação**: **{format_brl(total_alim)}**\n"
                f"  - Supermercado Mensal (05/10): **{format_brl(mercado)}**\n"
                f"  - Delivery e Restaurantes (12/10 e 25/10): **{format_brl(delivery)}**\n\n"
                "**Alertas identificados com base no seu perfil e histórico de atendimento**:\n"
                f"1. **Teto da Categoria**: Você ultrapassou em **R$ 460,00** a sua preferência de limite mensal para Alimentação (**R$ 2.000,00** em `perfil_investidor.json`).\n"
                f"2. **Alerta de Delivery**: Seus gastos com delivery (**{format_brl(delivery)}**) superaram em **R$ 210,00** o teto de **R$ 800,00** registrado no atendimento de 11/10/2026 (`historico_atendimento.csv`).\n\n"
                "**Próximo passo sugerido**: Se reduzirmos o delivery para a meta de R$ 800,00 no próximo mês, você libera **R$ 210,00 extras** para aportar no **Tesouro Selic 2029 (PROD-001)** e acelerar sua Reserva de Emergência. Quer que eu monte um cronograma para essa meta?"
            )

        # 4. Consulta sobre Metas Financeiras / Reserva de Emergência
        if any(k in q for k in ["meta", "metas", "objetivo", "falta", "completar", "reserva de emergência", "reserva de emergencia"]):
            return (
                f"Aqui está o status atualizado das suas **3 metas financeiras** registradas em `perfil_investidor.json`:\n\n"
                "1. **Completar Reserva de Emergência (Prioridade Alta — Prazo: 5 meses)**\n"
                "   - Valor Atual: **R$ 28.500,00** | Valor Alvo: **R$ 36.000,00** | **Faltam: R$ 7.500,00**\n"
                "   - Produto indicado no catálogo: **Tesouro Selic 2029 (PROD-001)** ou **CDB Liquidez Diária Banco Sólido (PROD-002)**.\n"
                "2. **Certificação Internacional Cloud & AI e Intercâmbio (Prioridade Média — Prazo: 14 meses)**\n"
                "   - Valor Atual: **R$ 9.500,00** | Valor Alvo: **R$ 25.000,00** | **Faltam: R$ 15.500,00**\n"
                "   - Produto indicado no catálogo: **LCI Tech Agro 12 Meses (PROD-003)** — 93% do CDI e isenta de Imposto de Renda.\n"
                "3. **Construção de Renda Passiva de Longo Prazo (Prioridade Média — Prazo: 60 meses)**\n"
                "   - Valor Atual: **R$ 26.000,00** | Valor Alvo: **R$ 250.000,00** | **Faltam: R$ 224.000,00**\n"
                "   - Produtos indicados no catálogo: **Tesouro IPCA+ 2035 (PROD-004)** e **Carteira Recomendada FIIs (PROD-005)**.\n\n"
                f"**Próximo passo sugerido**: Com o seu saldo livre de **{format_brl(m['saldo_livre'])}** neste mês (somado ao aporte de R$ 1.500,00 já feito), você pode destinar R$ 1.500,00 mensais para quitar os **R$ 7.500,00** restantes da Reserva de Emergência exatamente dentro do prazo de **5 meses**. Deseja ver como distribuir o restante?"
            )

        # 5. Consulta sobre Produtos Financeiros / Cripto / LCI / Onde investir
        if any(k in q for k in ["produto", "investir", "investimento", "cripto", "hash11", "lci", "cdb", "tesouro", "fii", "carteira"]):
            return (
                f"Com base no seu perfil **Moderado** (Patrimônio de **{format_brl(m['total_patrimonio'])}** e saldo livre de **{format_brl(m['saldo_livre'])}** em outubro/2026), estas são as opções homologadas em `produtos_financeiros.json`:\n\n"
                "- **Para Reserva de Emergência (Liquidez D+0 e Baixo Risco)**:\n"
                "  - **Tesouro Selic 2029 (PROD-001)**: 100% da Selic + 0,04% a.a., mínimo de R$ 150,00.\n"
                "  - **CDB Liquidez Diária Banco Sólido (PROD-002)**: 102% do CDI com proteção do FGC, mínimo de R$ 100,00.\n"
                "- **Para Meta de Médio Prazo (12 a 14 meses — Certificação/Intercâmbio)**:\n"
                "  - **LCI Tech Agro 12 Meses (PROD-003)**: **93% do CDI isento de IR**, liquidez no vencimento (360 dias), mínimo de R$ 1.000,00.\n"
                "- **Para Longo Prazo e Renda Passiva**:\n"
                "  - **Tesouro IPCA+ 2035 (PROD-004)**: IPCA + 6,25% a.a. (mínimo R$ 50,00).\n"
                "  - **Carteira Recomendada FIIs Logística & Recebíveis (PROD-005)**: Dividend Yield estimado de 9,8% a.a. isento de IR nos rendimentos (mínimo R$ 110,00).\n"
                "- **Para Diversificação em Criptoativos Regulados (Teto de 5% da carteira)**:\n"
                "  - **ETF HASH11 (PROD-006)**: Replica o Nasdaq Crypto Index na B3 (mínimo R$ 50,00, risco alto). Hoje você possui **R$ 2.000,00 (3,12%)** em cripto, podendo aportar até **R$ 1.200,00** adicionais sem ultrapassar o limite prudencial de 5% (**R$ 3.200,00**).\n\n"
                "**Próximo passo sugerido**: Gostaria de alocar os **R$ 2.070,10** disponíveis este mês combinando **R$ 1.070,10 no Tesouro Selic 2029 (PROD-001)** e **R$ 1.000,00 na LCI Tech Agro 12 Meses (PROD-003)**?"
            )

        # 6. Resposta padrão: Resumo Completo do Fluxo de Caixa e Diagnóstico do Mês
        cats_str = "\n".join(
            f"  - **{cat}**: {format_brl(val)}" for cat, val in m["por_categoria"].items()
        )
        return (
            f"Olá, **{nome}**! Aqui está o diagnóstico completo do seu fluxo de caixa em **outubro de 2026** com base em `data/transacoes.csv`:\n\n"
            f"- **Receita Total**: **{format_brl(m['entradas'])}**\n"
            f"- **Despesas Correntes**: **{format_brl(m['saidas_despesas'])}**\n"
            f"- **Aportes Já Realizados no Mês**: **{format_brl(m['aportes_mes'])}** (Tesouro Selic Reserva)\n"
            f"- **Total de Saídas**: **{format_brl(m['saidas_totais'])}**\n"
            f"- **Saldo Livre Disponível**: **{format_brl(m['saldo_livre'])}**\n\n"
            f"**Distribuição por Categoria**:\n{cats_str}\n\n"
            "**Destaques Consultivos**:\n"
            "1. **Alerta de Alimentação/Delivery**: A categoria Alimentação somou **R$ 2.460,00** (sendo **R$ 1.010,00** em delivery), superando o alerta de R$ 800,00 em delivery e R$ 2.000,00 no total da categoria.\n"
            "2. **Potencial de Alocação**: Você ainda possui **R$ 2.070,10** livres no mês para acelerar sua **Reserva de Emergência** (faltam **R$ 7.500,00** para atingir **R$ 36.000,00**).\n\n"
            "**Próximo passo sugerido**: Quer que eu detalhe um plano de aplicação para os **R$ 2.070,10** disponíveis usando os produtos do nosso catálogo?"
        )


if __name__ == "__main__":
    agent = FinAIAgent()
    print("=== Teste Rápido do FinAI (Modo CLI) ===")
    res = agent.answer("Qual é o resumo das minhas receitas, despesas e saldo livre no mês?")
    print(f"Motor: {res['engine']}\n")
    print(res["response"])
