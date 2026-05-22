import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==============================================================================
# CONFIGURAÇÃO DE ACESSO AO GOOGLE SHEETS
# ==============================================================================
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19xe6ySfOGbylZOtW4tULojW3AFLC6KR1TankzLx3cYQ/edit"

def ler_dados_sheets(aba, dados_padrao):
    """Lê a aba da planilha com tratamento de erro."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet=aba, ttl=0)
        
        if df.empty or df.dropna(how='all').empty:
            return dados_padrao
        
        resultado = {}
        # Lógica para Usuários
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
            
        # Lógica para Provas/Entregas
        elif aba in ["provas", "entregas"]:
            for _, row in df.iterrows():
                if pd.notna(row.get('aluno_alvo')):
                    aluno = str(row['aluno_alvo']).strip().lower()
                    dados_linha = row.to_dict()
                    dados_linha.pop('aluno_alvo', None)
                    dados_linha = {k: (None if pd.isna(v) else v) for k, v in dados_linha.items()}
                    resultado[aluno] = dados_linha
            return resultado
            
    except Exception as e:
        st.error(f"Erro ao ler planilha {aba}: {e}")
        return dados_padrao

# ==============================================================================
# CONFIGURAÇÃO DE ESTADO
# ==============================================================================
USUARIOS_PADRAO = {
   "sn1084433": {"nome": "Benedito Ricardo dos Santos", "senha": "Celina2610**", "perfil": "Gestor/Diretor"},
   "aluno_ricardo": {"nome": "Ricardo (Aluno)", "senha": "123", "perfil": "Aluno"}
}

if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None
    st.session_state.perfil_logado = None
    st.session_state.nome_exibicao = None

# ==============================================================================
# INTERFACE
# ==============================================================================
st.set_page_config(page_title="SUATS | SENAI-122", layout="wide")

if st.session_state.usuario_logado is None:
    st.title("🔐 SUATS | Portal de Acesso")
    u_in = st.text_input("Login:")
    s_in = st.text_input("Senha:", type="password")
    
    if st.button("Entrar"):
        dados_usuarios = ler_dados_sheets("usuarios", USUARIOS_PADRAO)
        user_data = dados_usuarios.get(u_in.strip().lower())
        
        if user_data and user_data["senha"] == s_in:
            st.session_state.usuario_logado = u_in
            st.session_state.perfil_logado = user_data["perfil"]
            st.session_state.nome_exibicao = user_data.get("nome", u_in)
            st.rerun()
        else:
            st.error("Login ou senha incorretos.")
else:
    st.sidebar.title(f"Olá, {st.session_state.nome_exibicao}")
    if st.sidebar.button("Sair"):
        st.session_state.usuario_logado = None
        st.rerun()
        
    st.title("Sistema Unificado de Avaliações Técnicas (SUATS)")
    st.write(f"Perfil logado: {st.session_state.perfil_logado}")
