import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==============================================================================
# 2. CONFIGURAÇÃO DE ACESSO NATIVO AO GOOGLE SHEETS
# ==============================================================================
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19xe6ySfOGbylZOtW4tULojW3AFLC6KR1TankzLx3cYQ/edit"

def ler_dados_sheets(aba, dados_padrao):
    """Lê a aba da planilha e converte de DataFrame para a estrutura de dicionário do app."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet=aba, ttl=0)
        
        if df.empty or df.dropna(how='all').empty:
            return dados_padrao
        
        resultado = {}
        if aba == "usuarios":
            for _, row in df.iterrows():
                if pd.notna(row.get('id')):
                    id_user = str(row['id']).strip().lower()
                    resultado[id_user] = {
                        "nome": str(row.get('nome', id_user)),
                        "senha": str(row.get('senha', '')),
                        "perfil": str(row.get('perfil', 'Aluno'))
                    }
            return resultado if resultado else dados_padrao
            
        elif aba in ["provas", "entregas"]:
            for _, row in df.iterrows():
                if pd.notna(row.get('aluno_alvo')):
                    aluno = str(row['aluno_alvo']).strip().lower()
                    dados_linha = row.to_dict()
                    dados_linha.pop('aluno_alvo', None)
                    dados_linha = {k: (None if pd.isna(v) else v) for k, v in dados_linha.items()}
                    resultado[aluno] = dados_linha
            return resultado
            
    except Exception:
        return dados_padrao

def salvar_dados_sheets(aba, dados):
    """Converte a estrutura de dicionário do app para DataFrame e atualiza a planilha."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        if aba == "usuarios":
            linhas = [{"id": k, "nome": v["nome"], "senha": v["senha"], "perfil": v["perfil"]} for k, v in dados.items()]
            df = pd.DataFrame(linhas)
            
        elif aba in ["provas", "entregas"]:
            linhas = [{"aluno_alvo": k, **v} for k, v in dados.items()]
            df = pd.DataFrame(linhas)
            
        conn.update(spreadsheet=URL_PLANILHA, worksheet=aba, data=df)
        return True
    except Exception as e:
        st.error(f"🔴 Erro ao salvar dados na aba '{aba}': {str(e)}")
        return False

# ==============================================================================
# 3. CONTROLE DE ESTADO DA SESSÃO
# ==============================================================================
USUARIOS_PADRAO = {
    "sn1084433": {"nome": "Benedito Ricardo dos Santos", "senha": "Celina2610**", "perfil": "Gestor/Diretor"},
    "sn1220001": {"nome": "Professor de Testes SENAI", "senha": "122", "perfil": "Professor"},
    "aluno_ricardo": {"nome": "Ricardo (Aluno)", "senha": "123", "perfil": "Aluno"},
    "aluno_elizandra": {"nome": "Elizandra (Aluna)", "senha": "123", "perfil": "Aluno"},
    "coord_teste": {"nome": "Coordenador Técnico", "senha": "122", "perfil": "Coordenador"}
}

if 'usuario_logado' not in st.session_state: st.session_state.usuario_logado = None
if 'perfil_logado' not in st.session_state: st.session_state.perfil_logado = None
if 'nome_exibicao' not in st.session_state: st.session_state.nome_exibicao = None

# Sincronização Dinâmica Pós-Login
if st.session_state.usuario_logado is not None:
    if 'usuarios_cadastrados' not in st.session_state: st.session_state.usuarios_cadastrados = ler_dados_sheets("usuarios", USUARIOS_PADRAO)
    if 'provas_geradas' not in st.session_state: st.session_state.provas_geradas = ler_dados_sheets("provas", {})
    if 'entregas_sistema' not in st.session_state: st.session_state.entregas_sistema = ler_dados_sheets("entregas", {})
else:
    st.session_state.usuarios_cadastrados = USUARIOS_PADRAO
    st.session_state.provas_geradas = {}
    st.session_state.entregas_sistema = {}

# ==============================================================================
# 4. INTERFACE VISUAL
# ==============================================================================
st.set_page_config(page_title="SUATS | SENAI-122", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0F111A; color: #F4F4F6; }
    [data-testid="stSidebar"] { background-color: #161925; border-right: 2px solid #D4AF37; }
    h1, h2, h3 { color: #D4AF37 !important; }
    .stButton > button { background-color: #D4AF37 !important; color: #0F111A !important; font-weight: bold !important; border-radius: 6px !important; }
    .stTextInput > div > div > input, .stSelectbox > div > div, .stTextArea textarea { background-color: #1E2233 !important; color: #F4F4F6 !important; border: 1px solid #D4AF37 !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 5. PORTAL DE LOGIN
# ==============================================================================
if st.session_state.usuario_logado is None:
    st.markdown("<h2 style='text-align:center;'>🔐 SUATS | Portal de Acesso</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u_in = st.text_input("Login Corporativo:").strip().lower()
        s_in = st.text_input("Senha de Acesso:", type="password")
        if st.button("🔓 Autenticar no Sistema"):
            dados_drive = ler_dados_sheets("usuarios", USUARIOS_PADRAO)
            user_data = dados_drive.get(u_in)
            if user_data and user_data["senha"] == s_in:
                st.session_state.usuario_logado = u_in
                st.session_state.perfil_logado = user_data["perfil"]
                st.session_state.nome_exibicao = user_data.get("nome", u_in)
                st.session_state.usuarios_cadastrados = dados_drive
                st.session_state.provas_geradas = ler_dados_sheets("provas", {})
                st.session_state.entregas_sistema = ler_dados_sheets("entregas", {})
                st.rerun()
            else:
                st.error("Login ou senha incorretos.")
else:
    # AQUI ENTRA O SEU CÓDIGO DE NAVEGAÇÃO QUE VOCÊ JÁ TINHA (DA LINHA 175 EM DIANTE)
    # Como o espaço aqui é limitado, certifique-se de copiar abaixo do bloco de login acima.
    pass # (Substitua este pass pelo restante do seu código original de menu e renderização)
