import os
import sys
import json
from datetime import datetime
import streamlit as st
import pandas as pd
import requests

# ==============================================================================
# 1. CONFIGURAÇÃO E CONEXÃO SEGURA AO SUPABASE
# ==============================================================================
SUPABASE_URL = "https://hjtqqshmxpeleywwzgca.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqdHFxc2hteHBlbGV5d3d6Z2NhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0OTY1NDgsImV4cCI6MjA5NTA3MjU0OH0.4v_EyCfUyE2ZEgqOYdnFNZlHVhG8_Quc9otQ7o8Di_s"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

USUARIOS_PADRAO = {
    "sn1084433": {"nome": "Benedito Ricardo dos Santos", "senha": "Celina2610**", "perfil": "Gestor/Diretor"},
    "sn1220001": {"nome": "Professor de Testes SENAI", "senha": "122", "perfil": "Professor"},
    "aluno_ricardo": {"nome": "Ricardo (Aluno)", "senha": "123", "perfil": "Aluno"},
    "aluno_elizandra": {"nome": "Elizandra (Aluna)", "senha": "123", "perfil": "Aluno"},
    "coord_teste": {"nome": "Coordenador Técnico", "senha": "122", "perfil": "Coordenador"},
    "sn1220002": {"nome": "Elizandra pascoalino", "senha": "123", "perfil": "Professor"}
}

def ler_dados_supabase(tabela):
    try:
        url = f"{SUPABASE_URL}/rest/v1/{tabela}?select=*"
        resposta = requests.get(url, headers=HEADERS, timeout=5)
        if resposta.status_code == 200:
            dados_lista = resposta.json()
            if not dados_lista: return {}
            resultado = {}
            if tabela == "usuarios":
                for item in dados_lista:
                    u_id = str(item.get('id', '')).strip().lower()
                    if u_id: resultado[u_id] = {"nome": item.get('nome', u_id), "senha": item.get('senha', ''), "perfil": item.get('perfil', 'Aluno')}
                return resultado
            elif tabela in ["provas", "entregas"]:
                for item in dados_lista:
                    aluno_alvo = str(item.get('id_alvo', '')).strip().lower()
                    if aluno_alvo: resultado[aluno_alvo] = {k: v for k, v in item.items() if k != 'id_alvo'}
                return resultado
        return {}
    except: return {}

def salvar_dados_supabase(tabela, dados):
    try:
        linhas = []
        if tabela == "usuarios":
            for k, v in dados.items(): linhas.append({"id": k, "nome": v["nome"], "senha": v["senha"], "perfil": v["perfil"]})
        elif tabela in ["provas", "entregas"]:
            for k, v in dados.items():
                linha = {"id_alvo": k}
                linha.update(v)
                linhas.append(linha)
        if not linhas: return True
        url = f"{SUPABASE_URL}/rest/v1/{tabela}"
        h = HEADERS.copy()
        h["Prefer"] = "resolution=merge-duplicates"
        resposta = requests.post(url, headers=h, json=linhas, timeout=5)
        return resposta.status_code in [200, 201]
    except: return False

# ==============================================================================
# 2. INICIALIZAÇÃO DE ESTADO
# ==============================================================================
if 'usuario_logado' not in st.session_state: st.session_state.usuario_logado = None
if 'perfil_logado' not in st.session_state: st.session_state.perfil_logado = None
if 'nome_exibicao' not in st.session_state: st.session_state.nome_exibicao = None

if st.session_state.usuario_logado is not None:
    if 'usuarios_cadastrados' not in st.session_state or not st.session_state.usuarios_cadastrados:
        d = ler_dados_supabase("usuarios")
        st.session_state.usuarios_cadastrados = d if d else USUARIOS_PADRAO
    if 'provas_geradas' not in st.session_state: st.session_state.provas_geradas = ler_dados_supabase("provas")
    if 'entregas_sistema' not in st.session_state: st.session_state.entregas_sistema = ler_dados_supabase("entregas")
else:
    st.session_state.usuarios_cadastrados = USUARIOS_PADRAO
    st.session_state.provas_geradas = {}
    st.session_state.entregas_sistema = {}

# ==============================================================================
# 3. INTERFACE VISUAL
# ==============================================================================
st.set_page_config(page_title="SUATS | SENAI-122", page_icon="🏆", layout="wide")
st.markdown("""<style>.stApp {background-color: #0F111A; color: #F4F4F6;} [data-testid="stSidebar"] {background-color: #161925; border-right: 2px solid #D4AF37;} h1, h2, h3, h4, h5, h6 {color: #D4AF37 !important;} .stButton > button {background-color: #D4AF37 !important; color: #0F111A !important; font-weight: bold !important; border-radius: 6px !important; border: 1px solid #D4AF37 !important;} .stTextInput > div > div > input, .stSelectbox > div > div, .stTextArea textarea {background-color: #1E2233 !important; color: #F4F4F6 !important; border: 1px solid #D4AF37 !important;}</style>""", unsafe_allow_html=True)

# ==============================================================================
# 4. PORTAL DE LOGIN
# ==============================================================================
if st.session_state.usuario_logado is None:
    st.markdown("<h2 style='text-align:center;'>🔐 SUATS | Portal de Acesso</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        u_in = st.text_input("Login Corporativo:").strip().lower()
        s_in = st.text_input("Senha de Acesso:", type="password").strip()
        if st.button("🔓 Autenticar no Sistema"):
            d_d = ler_dados_supabase("usuarios")
            u_d = d_d.get(u_in) if d_d else USUARIOS_PADRAO.get(u_in)
            if u_d and str(u_d.get("senha", "")).strip() == s_in:
                st.session_state.usuario_logado = u_in
                st.session_state.perfil_logado = u_d["perfil"]
                st.session_state.nome_exibicao = u_d.get("nome", u_in)
                st.session_state.usuarios_cadastrados = d_d if d_d else USUARIOS_PADRAO
                st.session_state.provas_geradas = ler_dados_supabase("provas")
                st.session_state.entregas_sistema = ler_dados_supabase("entregas")
                st.rerun()
            else: st.error("Login ou senha incorretos.")
else:
    with st.sidebar:
        st.markdown(f"<h3 style='text-align:center;'>🏆 SENAI-122</h3>", unsafe_allow_html=True)
        st.write(f"Conectado: **{st.session_state.nome_exibicao}**")
        st.write(f"Perfil: *{st.session_state.perfil_logado}*")
        st.write("---")
        if st.session_state.perfil_logado == "Gestor/Diretor":
            opcao_menu = st.radio("Menu", ["🏠 Dashboard Geral", "👥 Usuários", "🏫 Turmas", "👨‍🏫 Professores", "📝 Avaliações", "📊 Analytics", "📁 Relatórios", "🛡 Auditoria", "⚙ Configurações"])
        elif st.session_state.perfil_logado == "Professor":
            opcao_menu = st.radio("Menu", ["🏠 Dashboard", "➕ Criar Avaliação", "📚 Banco de Questões", "📝 Avaliações Ativas", "📤 Entregas", "📊 Relatórios", "⚙ Configurações"])
        elif st.session_state.perfil_logado == "Aluno":
            opcao_menu = st.radio("Menu", ["🏠 Início", "📝 Minhas Avaliações", "📥 Downloads", "📤 Upload", "📈 Histórico", "💬 Feedbacks"])
        else:
            opcao_menu = st.radio("Menu", ["🏠 Dashboard", "🏫 Turmas", "📊 Analytics", "📁 Relatórios"])
        st.write("---")
        if st.button("🚪 Encerrar Sessão"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    st.title("Sistema Unificado de Avaliações Técnicas (SUATS)")
    st.markdown(f"**Navegação Ativa:** {opcao_menu}")
    st.markdown("---")

    # ==============================================================================
    # 5/6/7/8. LÓGICA DE MÓDULOS
    # ==============================================================================
    if st.session_state.perfil_logado == "Gestor/Diretor":
        if "🏠 Dashboard Geral" in opcao_menu:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Alunos", len([u for u in st.session_state.usuarios_cadastrados.values() if u['perfil']=='Aluno']))
            c2.metric("Professores", len([u for u in st.session_state.usuarios_cadastrados.values() if u['perfil']=='Professor']))
            c3.metric("Provas", len(st.session_state.provas_geradas))
            c4.metric("Entregas", len(st.session_state.entregas_sistema))
        elif "👥 Usuários" in opcao_menu:
            col1, col2 = st.columns([1, 2])
            with col1:
                with st.form("form_u", clear_on_submit=True):
                    id_u = st.text_input("Login:").strip().lower()
                    nome_u = st.text_input("Nome:")
                    senha_u = st.text_input("Senha:", type="password")
                    perfil_u = st.selectbox("Perfil:", ["Aluno", "Professor", "Coordenador", "Gestor/Diretor"])
                    if st.form_submit_button("Salvar"):
                        if id_u and nome_u and senha_u:
                            if salvar_dados_supabase("usuarios", {id_u: {"nome": nome_u, "senha": senha_u, "perfil": perfil_u}}):
                                st.session_state.usuarios_cadastrados[id_u] = {"nome": nome_u, "senha": senha_u, "perfil": perfil_u}
                                st.success("Salvo!")
            with col2:
                df = pd.DataFrame([{"ID": k, **v} for k, v in st.session_state.usuarios_cadastrados.items()])
                st.dataframe(df)

    elif st.session_state.perfil_logado == "Professor":
        if "➕ Criar Avaliação" in opcao_menu:
            with st.form("form_p", clear_on_submit=True):
                materia = st.text_input("Disciplina:")
                aluno = st.selectbox("Aluno:", [k for k, v in st.session_state.usuarios_cadastrados.items() if v["perfil"] == "Aluno"])
                if st.form_submit_button("Liberar"):
                    dados = {"materia": materia, "status": "Liberada"}
                    if salvar_dados_supabase("provas", {aluno: dados}):
                        st.session_state.provas_geradas[aluno] = dados
                        st.success("Prova liberada!")

    elif st.session_state.perfil_logado == "Aluno":
        if "📝 Minhas Avaliações" in opcao_menu:
            a_a = st.session_state.usuario_logado
            if a_a in st.session_state.provas_geradas:
                p = st.session_state.provas_geradas[a_a]
                st.info(f"Prova: {p['materia']}")
                arquivo = st.file_uploader("Upload Resposta:")
                if arquivo and st.button("Enviar"):
                    e = {"materia": p['materia'], "status": "Enviado", "arquivo": arquivo.name}
                    if salvar_dados_supabase("entregas", {a_a: e}):
                        st.session_state.entregas_sistema[a_a] = e
                        st.success("Enviado!")
            else: st.warning("Nenhuma prova pendente.")

    elif st.session_state.perfil_logado == "Coordenador":
        if "🏠 Dashboard" in opcao_menu:
            st.write("Visão da Coordenação")
            st.dataframe(pd.DataFrame(st.session_state.provas_geradas).T)
