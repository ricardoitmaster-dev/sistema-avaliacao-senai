import streamlit as st
import pandas as pd
import requests

# ==============================================================================
# CONFIGURAÇÃO E INICIALIZAÇÃO
# ==============================================================================
st.set_page_config(page_title="SUATS | SENAI-122", page_icon="🏆", layout="wide")

# Inicialização segura das variáveis de sessão
def init_state():
    if 'usuario_logado' not in st.session_state: st.session_state.usuario_logado = None
    if 'perfil_logado' not in st.session_state: st.session_state.perfil_logado = None
    if 'nome_exibicao' not in st.session_state: st.session_state.nome_exibicao = None
    if 'usuarios_cadastrados' not in st.session_state: st.session_state.usuarios_cadastrados = {}
    if 'provas_geradas' not in st.session_state: st.session_state.provas_geradas = {}

init_state()

# Supabase Config
SUPABASE_URL = "https://hjtqqshmxpeleywwzgca.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqdHFxc2hteHBlbGV5d3d6Z2NhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0OTY1NDgsImV4cCI6MjA5NTA3MjU0OH0.4v_EyCfUyE2ZEgqOYdnFNZlHVhG8_Quc9otQ7o8Di_s"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

def ler_supabase(tabela):
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{tabela}?select=*", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if tabela == "usuarios": return {str(i['id']).strip().lower(): i for i in data}
            return {str(i.get('id_alvo', '')).strip().lower(): i for i in data}
    except: return {}
    return {}

# ==============================================================================
# INTERFACE E LOGIN
# ==============================================================================
if st.session_state.usuario_logado is None:
    st.markdown("<h2 style='text-align:center;'>🔐 Portal de Acesso</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u_in = st.text_input("Login Corporativo:").strip().lower()
        s_in = st.text_input("Senha:", type="password").strip()
        if st.button("🔓 Entrar"):
            base = ler_supabase("usuarios")
            usuario = base.get(u_in)
            if usuario and str(usuario.get("senha", "")).strip() == s_in:
                st.session_state.usuario_logado = u_in
                st.session_state.perfil_logado = usuario.get("perfil")
                st.session_state.nome_exibicao = usuario.get("nome", u_in)
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
else:
    # Sidebar
    with st.sidebar:
        st.write(f"Conectado: **{st.session_state.nome_exibicao}**")
        if st.button("🚪 Sair"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        
        # Menu dinâmico
        perfil = st.session_state.perfil_logado
        if perfil == "Gestor/Diretor":
            opcao = st.radio("Menu", ["🏠 Dashboard", "👥 Usuários", "📝 Avaliações"])
        elif perfil == "Professor":
            opcao = st.radio("Menu", ["🏠 Dashboard", "➕ Criar Avaliação", "📝 Avaliações"])
        else:
            opcao = st.radio("Menu", ["🏠 Dashboard", "📝 Minhas Avaliações"])

    # Conteúdo Principal
    st.title(f"Bem-vindo, {st.session_state.nome_exibicao}")
    st.write(f"Você está navegando em: {opcao}")
    
    # Aqui você pode expandir com o resto da lógica do seu app...
