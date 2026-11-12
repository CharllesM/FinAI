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
        options=["auto", "gemini", "lmstudio", "openai", "local"],
        format_func=lambda x: {
            "auto": "Automático (API ou Fallback Local)",
            "gemini": "Google Gemini API (REST Nativo)",
            "lmstudio": "LM Studio (API OpenAI Local - Porta 1234)",
            "openai": "OpenAI API (Cloud ou URL Customizada)",
            "local": "Motor Consultivo Local (RAG Determinístico Offline)",
        }[x],
    )

    gemini_key_input = ""
    openai_key_input = ""
    openai_base_url_input = ""
    model_name_input = ""

    if provider in ("gemini", "auto"):
        gemini_key_input = st.text_input(
            "GEMINI_API_KEY (Google AI Studio)",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Cole sua chave do Google AI Studio (aistudio.google.com). Usa REST nativo e tenta automaticamente gemini-2.5-flash, gemini-2.0-flash e gemini-1.5-flash.",
        )
        if provider == "gemini":
            model_name_input = st.text_input(
                "Modelo Gemini (deixe em branco p/ auto)",
                value=os.getenv("LLM_MODEL_NAME", ""),
                placeholder="Ex: gemini-2.0-flash",
            )

    if provider == "lmstudio":
        openai_base_url_input = st.text_input(
            "URL do Servidor Local LM Studio",
            value=os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1"),
            help="No LM Studio, vá na aba 'Developer' (ou Local Server) e clique em 'Start Server' (porta padrão 1234).",
        )
        model_name_input = st.text_input(
            "ID do Modelo no LM Studio (opcional)",
            value=os.getenv("LLM_MODEL_NAME", ""),
            placeholder="Auto-detectado via /v1/models se vazio",
        )

    if provider == "openai":
        openai_base_url_input = st.text_input(
            "OpenAI Base URL",
            value=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            help="Para OpenAI oficial use https://api.openai.com/v1. Para LM Studio use http://localhost:1234/v1.",
        )
        openai_key_input = st.text_input(
            "OPENAI_API_KEY",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            help="Para servidores locais (LM Studio / Ollama), pode deixar em branco ou digitar 'lm-studio'.",
        )
        model_name_input = st.text_input(
            "Modelo (opcional)",
            value=os.getenv("LLM_MODEL_NAME", ""),
            placeholder="Ex: gpt-4o-mini ou deixe vazio p/ auto",
        )

    if st.button("🔌 Testar Conexão do Motor", use_container_width=True):
        test_agent = FinAIAgent(
            kb=kb,
            provider=provider,
            gemini_api_key=gemini_key_input,
            openai_api_key=openai_key_input,
            openai_base_url=openai_base_url_input,
            model_name=model_name_input,
        )
        test_res = test_agent.answer("Responda em uma frase curta: qual é o meu saldo livre em outubro de 2026?")
        if test_res.get("error"):
            st.error(f"Falha na conexão com a API:\n{test_res['error']}")
            st.info(f"Fallback acionado com sucesso: {test_res['engine']}")
        else:
            st.success(f"Conectado com sucesso via: {test_res['engine']}")

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
            if msg.get("error"):
                st.warning(f"⚠️ Diagnóstico da API (Fallback Local utilizado): {msg['error']}")
            if msg.get("engine"):
                st.caption(f"⚙️ Processado por: {msg['engine']}")

    user_input = st.chat_input("Digite sua dúvida financeira ou clique em uma pergunta rápida na barra lateral...")
    prompt_to_run = selected_sample or user_input

    if prompt_to_run:
        st.session_state.messages.append({"role": "user", "content": prompt_to_run})
        with st.chat_message("user"):
            st.markdown(prompt_to_run)

        agent = FinAIAgent(
            kb=kb,
            provider=provider,
            gemini_api_key=gemini_key_input,
            openai_api_key=openai_key_input,
            openai_base_url=openai_base_url_input,
            model_name=model_name_input,
        )
        result = agent.answer(prompt_to_run)

        with st.chat_message("assistant"):
            st.markdown(result["response"])
            if result.get("error"):
                st.warning(f"⚠️ Diagnóstico da API (Fallback Local utilizado): {result['error']}")
            st.caption(f"⚙️ Processado por: {result['engine']}")

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["response"],
                "engine": result["engine"],
                "error": result.get("error", ""),
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