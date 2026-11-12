#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo principal do Agente Financeiro Inteligente (FinAI).
Responsável por:
1. Carregar automaticamente variáveis de um arquivo .env (se existir);
2. Carregar e validar a Base de Conhecimento (pasta data/);
3. Calcular indicadores financeiros determinísticos (evitando erros matemáticos de LLMs);
4. Construir o System Prompt e o contexto RAG local;
5. Conectar via HTTP nativo (sem conflito de SDK) ao Google Gemini API,
   LM Studio (OpenAI Local em http://localhost:1234/v1) ou OpenAI Cloud,
   com diagnóstico transparente de erros e Fallback Determinístico Local.
"""

from __future__ import annotations

import csv
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_dotenv_file() -> None:
    """Carrega variáveis do arquivo .env (se existir na raiz do projeto) sem depender de pacotes externos."""
    env_candidates = [
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_candidates:
        if env_path.is_file():
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ and val and not val.startswith("sua_chave_"):
                    os.environ[key] = val


load_dotenv_file()


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
    """
    Agente Virtual Consultivo com suporte a:
    - Google Gemini API via REST nativo (sem depender de versão de SDK);
    - LM Studio / Servidor Local compatível com OpenAI (http://localhost:1234/v1);
    - OpenAI API Cloud (https://api.openai.com/v1);
    - Motor Consultivo Local (RAG Determinístico Offline).
    """

    def __init__(
        self,
        kb: Optional[KnowledgeBase] = None,
        provider: str = "auto",
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.kb = kb or KnowledgeBase()
        self.provider = provider
        self.gemini_api_key = (gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.openai_api_key = (openai_api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        self.openai_base_url = (
            openai_base_url
            or os.getenv("OPENAI_BASE_URL", "")
            or ("http://localhost:1234/v1" if provider == "lmstudio" else "https://api.openai.com/v1")
        ).strip().rstrip("/")
        self.model_name = (model_name or os.getenv("LLM_MODEL_NAME", "")).strip()

    def get_system_prompt(self) -> str:
        return (
            "Você é o FinAI, um Assistente Virtual Consultivo de Finanças Pessoais, Investimentos e Criptoativos Regulados.\n"
            "Responda sempre em português do Brasil, de forma clara, acolhedora e bem formatada em Markdown.\n"
            "REGRAS OBRIGATÓRIAS (ANTI-ALUCINAÇÃO):\n"
            "1. Responda EXCLUSIVAMENTE com base nos dados do bloco abaixo.\n"
            "2. Nunca invente produtos financeiros, taxas ou dados de outros períodos não presentes na base.\n"
            "3. Respeite o perfil Moderado do cliente (limite de 25% em renda variável e até 5% em criptoativos via ETF HASH11).\n"
            "4. Se não houver informação suficiente na base, declare isso com transparência.\n"
            "5. Sempre finalize sugerindo um '**Próximo passo sugerido:**' prático para apoiar a decisão da pessoa usuária.\n\n"
            + self.kb.build_context_summary()
        )

    def _call_gemini_rest(self, user_query: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Chama a API REST oficial do Google Gemini diretamente via urllib (sem depender de google-genai).
        Testa em cascata os modelos disponíveis para garantir compatibilidade com qualquer chave do Google AI Studio.
        Retorna: (texto_resposta, nome_motor, erro_se_houver)
        """
        if not self.gemini_api_key:
            return None, None, "Chave GEMINI_API_KEY vazia."

        candidate_models = (
            [self.model_name]
            if self.model_name
            else ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        )
        last_err = None

        for model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
            payload = {
                "systemInstruction": {
                    "parts": [{"text": self.get_system_prompt()}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_query}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                },
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    candidates = body.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts).strip()
                        if text:
                            return text, f"Google Gemini API ({model})", None
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                try:
                    err_json = json.loads(err_body)
                    msg = err_json.get("error", {}).get("message", err_body)
                except Exception:
                    msg = err_body
                last_err = f"HTTP {e.code} no modelo {model}: {msg}"
                # Se a chave for inválida (400 API_KEY_INVALID ou 403), não adianta tentar outro modelo
                if e.code in (401, 403) or "API_KEY_INVALID" in err_body:
                    break
            except Exception as e:
                last_err = f"Falha de conexão com Google Gemini ({model}): {e}"

        return None, None, last_err

    def _detect_openai_local_model(self, base_url: str, api_key: str) -> str:
        """Consulta GET /v1/models no LM Studio ou servidor compatível para descobrir o ID do modelo carregado."""
        if self.model_name:
            return self.model_name
        url = f"{base_url}/models"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                models = body.get("data", [])
                # Filtra modelos de embedding caso o LM Studio tenha ambos carregados
                chat_models = [
                    m.get("id")
                    for m in models
                    if m.get("id") and "embed" not in m.get("id", "").lower()
                ]
                if chat_models:
                    return chat_models[0]
                if models and models[0].get("id"):
                    return models[0]["id"]
        except Exception:
            pass
        return "local-model" if ("localhost" in base_url or "127.0.0.1" in base_url) else "gpt-4o-mini"

    def _call_openai_compatible_rest(
        self, user_query: str, base_url: str, api_key: str, provider_label: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Chama qualquer servidor compatível com OpenAI (/v1/chat/completions),
        incluindo LM Studio (http://localhost:1234/v1), Ollama (http://localhost:11434/v1) e OpenAI Cloud.
        """
        effective_key = api_key if api_key else "lm-studio"
        model_id = self._detect_openai_local_model(base_url, effective_key)
        url = f"{base_url}/chat/completions"

        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": user_query},
            ],
            "temperature": 0.2,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {effective_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                choices = body.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "").strip()
                    if text:
                        return text, f"{provider_label} ({model_id})", None
                return None, None, f"Resposta vazia de {url}."
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return None, None, f"HTTP {e.code} em {url} (modelo '{model_id}'): {err_body}"
        except Exception as e:
            return (
                None,
                None,
                f"Não foi possível conectar a {url} ({e}). Verifique se o servidor local do LM Studio está iniciado (Start Server na porta 1234) e com um modelo carregado.",
            )

    def answer(self, user_query: str) -> Dict[str, str]:
        """
        Retorna um dicionário com:
          - 'response': texto da resposta ao usuário
          - 'engine': identificador do motor utilizado
          - 'error': mensagem de diagnóstico caso a API selecionada tenha falhado (opcional)
        """
        diagnostics: List[str] = []

        # 1. Provedor Google Gemini explícito ou automático com chave presente
        if self.provider == "gemini" or (self.provider == "auto" and self.gemini_api_key):
            text, engine, err = self._call_gemini_rest(user_query)
            if text and engine:
                return {"response": text, "engine": engine, "error": ""}
            if err:
                diagnostics.append(f"[Google Gemini] {err}")

        # 2. Provedor LM Studio explícito (ou auto quando OPENAI_BASE_URL aponta para localhost)
        if self.provider == "lmstudio" or (
            self.provider == "auto"
            and ("localhost" in self.openai_base_url or "127.0.0.1" in self.openai_base_url)
            and os.getenv("OPENAI_BASE_URL")
        ):
            lm_url = (
                self.openai_base_url
                if ("localhost" in self.openai_base_url or "127.0.0.1" in self.openai_base_url or self.provider == "lmstudio")
                else "http://localhost:1234/v1"
            )
            text, engine, err = self._call_openai_compatible_rest(
                user_query=user_query,
                base_url=lm_url,
                api_key=self.openai_api_key or "lm-studio",
                provider_label="LM Studio Local API",
            )
            if text and engine:
                return {"response": text, "engine": engine, "error": ""}
            if err:
                diagnostics.append(f"[LM Studio] {err}")

        # 3. Provedor OpenAI Cloud (ou endpoint OpenAI customizado)
        if self.provider == "openai" or (self.provider == "auto" and self.openai_api_key):
            if not self.openai_api_key and "api.openai.com" in self.openai_base_url:
                diagnostics.append("[OpenAI] Chave OPENAI_API_KEY não informada para api.openai.com.")
            else:
                text, engine, err = self._call_openai_compatible_rest(
                    user_query=user_query,
                    base_url=self.openai_base_url,
                    api_key=self.openai_api_key,
                    provider_label="OpenAI Compatible API",
                )
                if text and engine:
                    return {"response": text, "engine": engine, "error": ""}
                if err:
                    diagnostics.append(f"[OpenAI] {err}")

        # 4. Fallback: Motor Consultivo Determinístico Local (100% fundamentado na pasta data/)
        error_msg = " | ".join(diagnostics) if diagnostics else ""
        return {
            "response": self._local_consultative_engine(user_query),
            "engine": "Motor Consultivo Local (RAG Determinístico Offline)",
            "error": error_msg,
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