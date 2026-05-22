import os
import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==============================================================================
# CONFIGURAÇÃO GERAL E CONEXÃO
# ==============================================================================
# URL da planilha deve estar no Secrets ou definida aqui.
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19xe6ySfOGbylZOtW4tULojW3AFLC6KR1TankzLx3cYQ/edit"

def ler_dados_sheets(aba, dados_padrao):
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
        st.error(f"Erro ao salvar: {e}")
        return False

# ==============================================================================
# ESTADO DA SESSÃO
# ==============================================================================
USUARIOS_PADRAO = {
   "sn1084433": {"nome": "Benedito Ricardo dos Santos", "senha": "Celina2610**", "perfil": "Gestor/Diretor"},
   "sn1220001": {"nome": "Professor de Testes SENAI", "senha": "122", "perfil": "Professor"},
   "aluno_ricardo": {"nome": "Ricardo (Aluno)", "senha": "123", "perfil": "Aluno"},
   "aluno_elizandra": {"nome": "Elizandra (Aluna)", "senha": "123", "perfil": "Aluno"},
   "coord_teste": {"nome": "Coordenador Técnico", "senha": "122", "perfil": "Coordenador"}
}

if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None
    st.session_state.perfil_logado = None
    st.session_state.nome_exibicao = None

# Sincronização
if st.session_state.usuario_logado:
    if 'usuarios_cadastrados' not in st.session_state:
        st.session_state.usuarios_cadastrados = ler_dados_sheets("usuarios", USUARIOS_PADRAO)
    if 'provas_geradas' not in st.session_state:
        st.session_state.provas_geradas = ler_dados_sheets("provas", {})
    if 'entregas_sistema' not in st.session_state:
        st.session_state.entregas_sistema = ler_dados_sheets("entregas", {})
else:
    st.session_state.usuarios_cadastrados = USUARIOS_PADRAO
    st.session_state.provas_geradas = {}
    st.session_state.entregas_sistema = {}

# ==============================================================================
# INTERFACE E ESTILOS
# ==============================================================================
st.set_page_config(page_title="SUATS | SENAI-122", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0F111A; color: #F4F4F6; }
    [data-testid="stSidebar"] { background-color: #161925; border-right: 2px solid #D4AF37; }
    h1, h2, h3 { color: #D4AF37 !important; }
    .stButton > button { background-color: #D4AF37 !important; color: #0F111A !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# LOGIN
# ==============================================================================
if st.session_state.usuario_logado is None:
    st.markdown("<h2 style='text-align:center;'>🔐 SUATS | Portal de Acesso</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u_in = st.text_input("Login Corporativo:").strip().lower()
        s_in = st.text_input("Senha:", type="password")
        if st.button("Autenticar"):
            dados_drive = ler_dados_sheets("usuarios", USUARIOS_PADRAO)
            user_data = dados_drive.get(u_in)
            if user_data and user_data["senha"] == s_in:
                st.session_state.usuario_logado = u_in
                st.session_state.perfil_logado = user_data["perfil"]
                st.session_state.nome_exibicao = user_data.get("nome", u_in)
                st.session_state.usuarios_cadastrados = dados_drive
                st.rerun()
            else:
                st.error("Login ou senha incorretos.")
else:
    with st.sidebar:
        st.markdown(f"### 🏆 SENAI-122")
        st.write(f"**{st.session_state.nome_exibicao}**")
        st.write(f"*{st.session_state.perfil_logado}*")
        st.write("---")
        
        # Definição de Menus por Perfil
        if st.session_state.perfil_logado == "Gestor/Diretor":
            opcao_menu = st.radio("Menu", ["🏠 Dashboard Geral", "👥 Usuários", "🏫 Turmas", "👨‍🏫 Professores", "📝 Avaliações", "📊 Analytics", "📁 Relatórios", "🛡 Auditoria", "⚙ Configurações"])
        elif st.session_state.perfil_logado == "Professor":
            opcao_menu = st.radio("Menu", ["🏠 Dashboard", "➕ Criar Avaliação", "📝 Avaliações Ativas", "📤 Entregas", "⚙ Configurações"])
        elif st.session_state.perfil_logado == "Aluno":
            opcao_menu = st.radio("Menu", ["🏠 Início", "📝 Minhas Avaliações", "📤 Upload"])
        else:
            opcao_menu = st.radio("Menu", ["🏠 Dashboard", "🏫 Turmas", "📊 Analytics"])
            
        if st.button("🚪 Encerrar Sessão"):
            st.session_state.usuario_logado = None
            st.rerun()

    # ==============================================================================
    # RENDERIZAÇÃO DAS PÁGINAS (COMPLETA)
    # ==============================================================================
    st.title(f"Sistema Unificado de Avaliações Técnicas (SUATS)")
    st.subheader(opcao_menu)
    st.markdown("---")

    if st.session_state.perfil_logado == "Gestor/Diretor":
        if "🏠 Dashboard Geral" in opcao_menu:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Alunos", len([u for u in st.session_state.usuarios_cadastrados.values() if u['perfil']=='Aluno']))
            c2.metric("Profs", len([u for u in st.session_state.usuarios_cadastrados.values() if u['perfil']=='Professor']))
            c3.metric("Provas", len(st.session_state.provas_geradas))
            c4.metric("Entregas", len(st.session_state.entregas_sistema))
            
        elif "👥 Usuários" in opcao_menu:
            st.subheader("Gerenciamento")
            col1, col2 = st.columns([1, 2])
            with col1:
                novo_id = st.text_input("ID/Login:")
                novo_nome = st.text_input("Nome:")
                nova_senha = st.text_input("Senha:", type="password")
                novo_perfil = st.selectbox("Perfil:", ["Aluno", "Professor", "Coordenador", "Gestor/Diretor"])
                if st.button("Salvar"):
                    st.session_state.usuarios_cadastrados[novo_id] = {"nome": novo_nome, "senha": nova_senha, "perfil": novo_perfil}
                    salvar_dados_sheets("usuarios", st.session_state.usuarios_cadastrados)
                    st.success("Salvo!")
            with col2:
                st.dataframe(pd.DataFrame([{"ID": k, **v} for k, v in st.session_state.usuarios_cadastrados.items()]))

        elif "📝 Avaliações" in opcao_menu:
            st.dataframe(pd.DataFrame([{"Aluno": k, **v} for k, v in st.session_state.provas_geradas.items()]))

    elif st.session_state.perfil_logado == "Professor":
        if "➕ Criar Avaliação" in opcao_menu:
            materia = st.text_input("Disciplina:")
            aluno_alvo = st.selectbox("Aluno Alvo:", list(st.session_state.usuarios_cadastrados.keys()))
            if st.button("Gerar Prova"):
                st.session_state.provas_geradas[aluno_alvo] = {"materia": materia, "status": "Liberada", "data": datetime.now().strftime("%d/%m/%Y")}
                salvar_dados_sheets("provas", st.session_state.provas_geradas)
                st.success("Prova Gerada!")

    elif st.session_state.perfil_logado == "Aluno":
        if "📝 Minhas Avaliações" in opcao_menu:
            aluno = st.session_state.usuario_logado
            if aluno in st.session_state.provas_geradas:
                prova = st.session_state.provas_geradas[aluno]
                st.info(f"Prova: {prova['materia']}")
                upload = st.file_uploader("Enviar resolução:")
                if upload and st.button("Confirmar Envio"):
                    st.session_state.entregas_sistema[aluno] = {"materia": prova['materia'], "data": datetime.now().strftime("%d/%m/%Y")}
                    salvar_dados_sheets("entregas", st.session_state.entregas_sistema)
                    st.success("Enviado com sucesso!")
            else:
                st.warning("Nenhuma prova pendente.")
