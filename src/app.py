#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicação Funcional em Streamlit — FinAI (Assistente Virtual Financeiro & Cripto com IA).
Desafio de Projeto DIO: Construa Seu Assistente Virtual Com Inteligência Artificial
Repositório Base: https://github.com/digitalinnovationone/dio-lab-bia-do-futuro
"""

import os
import streamlit as st
import pandas as pd
from agent import FinAIAgent, KnowledgeBase, format_brl

st.set_page_config(
    page_title="FinAI | Assistente Financeiro Inteligente (DIO)",
    page_icon="🤖",
    layout="wide",
)


@st.cache_resource
def load_kb() -> KnowledgeBase:
    return KnowledgeBase()


kb = load_kb()
metrics = kb.metrics

# Barra Lateral: Painel do Cliente e Configuração de LLM
with st.sidebar:
    st.title("🤖 FinAI — Configuração")
    st.caption("Desafio de Projeto DIO • Assistente Virtual com IA")

    provider = st.selectbox(
        "Motor de IA (LLM)",
        options=["auto", "local", "gemini", "openai"],
        format_func=lambda x: {
            "auto": "Automático (API ou Fallback Local)",
            "local": "Motor Consultivo Local (Offline/Auditado)",
            "gemini": "Google Gemini API (gemini-2.5-flash)",
            "openai": "OpenAI API (gpt-4o-mini)",
        }[x],
    )

    if provider in ("gemini", "auto"):
        gemini_key = st.text_input("GEMINI_API_KEY (opcional)", type="password")
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key

    if provider in ("openai", "auto"):
        openai_key = st.text_input("OPENAI_API_KEY (opcional)", type="password")
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key

    st.divider()
    st.subheader("👤 Perfil Carregado (`data/`)")
    st.markdown(
        f"**Cliente:** {kb.perfil['nome']}  \n"
        f"**Perfil de Risco:** `{kb.perfil['perfil_risco']}`  \n"
        f"**Patrimônio Total:** `{format_brl(metrics['total_patrimonio'])}`  \n"
        f"**Exposição Renda Variável:** `{metrics['pct_rv']}%` (Teto: 25%)  \n"
        f"**Exposição Cripto (ETF):** `{metrics['pct_cripto']}%` (Teto: 5%)"
    )

    st.divider()
    st.subheader("💡 Perguntas Rápidas de Teste")
    sample_questions = [
        "Qual é o resumo das minhas receitas, despesas e saldo livre no mês?",
        "Como ficaram meus gastos de alimentação e delivery neste mês?",
        "Quanto falta para completar minha reserva de emergência e minhas metas?",
        "Onde devo investir meu saldo livre considerando meu perfil Moderado e cripto?",
        "Posso transferir toda a minha reserva de emergência para criptomoedas?",
        "Quanto gastei em março de 2023 e qual ação vai dobrar amanhã?",
    ]
    selected_sample = None
    for sq in sample_questions:
        if st.button(sq, use_container_width=True):
            selected_sample = sq

# Cabeçalho Principal e KPIs
st.title("🤖 FinAI — Assistente Virtual Consultivo de Finanças & Investimentos")
st.markdown(
    "Protótipo funcional conectado à **Base de Conhecimento (`data/`)** com cálculo determinístico "
    "de orçamento e **guardrails anti-alucinação**."
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Receita Mensal (Out/2026)", format_brl(metrics["entradas"]))
col2.metric("Despesas Correntes", format_brl(metrics["saidas_despesas"]))
col3.metric("Aporte Já Realizado", format_brl(metrics["aportes_mes"]))
col4.metric("Saldo Livre para Alocar", format_brl(metrics["saldo_livre"]))

tab_chat, tab_data = st.tabs(["💬 Conversar com o FinAI", "📊 Explorar Base de Conhecimento (`data/`)"])

with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    f"Olá, **{kb.perfil['nome']}**! Sou o **FinAI**, seu assistente financeiro inteligente. "
                    "Já carreguei suas transações de outubro de 2026, suas metas e o nosso catálogo de investimentos. "
                    "Como posso apoiar sua próxima decisão hoje?"
                ),
                "engine": "Sistema Inicializado",
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("engine"):
                st.caption(f"⚙️ Processado por: {msg['engine']}")

    user_input = st.chat_input("Digite sua dúvida financeira ou clique em uma pergunta rápida na barra lateral...")
    prompt_to_run = selected_sample or user_input

    if prompt_to_run:
        st.session_state.messages.append({"role": "user", "content": prompt_to_run})
        with st.chat_message("user"):
            st.markdown(prompt_to_run)

        agent = FinAIAgent(kb=kb, provider=provider)
        result = agent.answer(prompt_to_run)

        with st.chat_message("assistant"):
            st.markdown(result["response"])
            st.caption(f"⚙️ Processado por: {result['engine']}")

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["response"],
                "engine": result["engine"],
            }
        )

with tab_data:
    st.subheader("1. Histórico de Transações (`data/transacoes.csv`)")
    st.dataframe(pd.DataFrame(kb.transacoes), use_container_width=True)

    st.subheader("2. Catálogo de Produtos Homologados (`data/produtos_financeiros.json`)")
    st.dataframe(pd.DataFrame(kb.produtos), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("3. Metas Financeiras (`data/perfil_investidor.json`)")
        st.dataframe(pd.DataFrame(kb.perfil["metas_financeiras"]), use_container_width=True)
    with col_b:
        st.subheader("4. Histórico de Atendimento (`data/historico_atendimento.csv`)")
        st.dataframe(pd.DataFrame(kb.historico), use_container_width=True)
