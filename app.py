import streamlit as st
import pandas as pd
import requests

# ==============================================================================
# 1. CONFIGURAÇÕES E CREDENCIAIS
# ==============================================================================
st.set_page_config(page_title="SUATS | SENAI-122", page_icon="🏆", layout="wide")

SUPABASE_URL = "https://hjtqqshmxpeleywwzgca.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqdHFxc2hteHBlbGV5d3d6Z2NhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0OTY1NDgsImV4cCI6MjA5NTA3MjU0OH0.4v_EyCfUyE2ZEgqOYdnFNZlHVhG8_Quc9otQ7o8Di_s"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ==============================================================================
# 2. INICIALIZAÇÃO SEGURA (EVITA ERRO DE ATRIBUTO)
# ==============================================================================
def init_state():
    defaults = {
        'usuario_logado': None,
        'perfil_logado': None,
        'nome_exibicao': None,
        'usuarios_cadastrados': {},
        'provas_geradas': {},
        'entregas_sistema': {}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# ==============================================================================
# 3. FUNÇÕES DE BANCO DE DADOS (DENTRO DO MESMO ARQUIVO)
# ==============================================================================
def ler_dados_supabase(tabela):
    try:
        url = f"{SUPABASE_URL}/rest/v1/{tabela}?select=*"
        resposta = requests.get(url, headers=HEADERS, timeout=10)
        if resposta.status_code == 200:
            dados = resposta.json()
            if tabela == "usuarios":
                return {str(i['id']).strip().lower(): i for i in dados}
            return {str(i.get('id_alvo', '')).strip().lower(): i for i in dados}
        return {}
    except: return {}

def salvar_dados_supabase(tabela, dados):
    try:
        url = f"{SUPABASE_URL}/rest/v1/{tabela}"
        h = HEADERS.copy()
        h["Prefer"] = "resolution=merge-duplicates"
        # Converte dicionário para a lista que o Supabase espera
        payload = []
        for k, v in dados.items():
            reg = v.copy()
            reg['id' if tabela == 'usuarios' else 'id_alvo'] = k
            payload.append(reg)
        resp = requests.post(url, headers=h, json=payload, timeout=10)
        return resp.status_code in [200, 201]
    except: return False

# ==============================================================================
# 4. INTERFACE E LÓGICA DE LOGIN
# ==============================================================================
if st.session_state.usuario_logado is None:
    st.markdown("<h2 style='text-align:center;'>🔐 Portal de Acesso SUATS</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        u_in = st.text_input("Login Corporativo:").strip().lower()
        s_in = st.text_input("Senha:", type="password").strip()
        if st.button("🔓 Entrar"):
            base = ler_dados_supabase("usuarios")
            usuario = base.get(u_in)
            if usuario and str(usuario.get("senha", "")).strip() == s_in:
                st.session_state.usuario_logado = u_in
                st.session_state.perfil_logado = usuario.get("perfil")
                st.session_state.nome_exibicao = usuario.get("nome", u_in)
                st.session_state.usuarios_cadastrados = base
                st.rerun()
            else:
                st.error("Login ou senha incorretos.")
else:
    # --- ÁREA LOGADA ---
    with st.sidebar:
        st.write(f"Conectado: **{st.session_state.nome_exibicao}**")
        if st.button("🚪 Encerrar Sessão"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    st.title("Sistema Unificado de Avaliações (SUATS)")
    
    # Exemplo de lógica de navegação (Você pode expandir a partir daqui)
    menu = ["🏠 Dashboard", "📝 Minhas Avaliações", "⚙ Configurações"]
    opcao = st.radio("Navegação", menu)
    
    if "Dashboard" in opcao:
        st.write("Bem-vindo ao Painel.")
        # Adicione aqui sua lógica de dashboard
