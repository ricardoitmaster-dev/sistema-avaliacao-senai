import os
import sys
import json
import subprocess
from datetime import datetime
import streamlit as st
import pandas as pd

# ==============================================================================
# 1. GERENCIAMENTO DE DEPENDÊNCIAS CRÍTICAS (P0)
# ==============================================================================
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "google-auth", "google-api-python-client"])
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload

# ==============================================================================
# 2. CONFIGURAÇÕES GLOBAIS E IDENTIDADE VISUAL (BMW Portinari Blue & Gold)
# ==============================================================================
st.set_page_config(
    page_title="SUATS | SENAI-122",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

def injetar_css_corporativo():
    st.markdown("""
        <style>
        /* Paleta Executiva: Dark Mode Base, BMW Portinari Blue, Gold e Black */
        .stApp {
            background-color: #0F111A;
            color: #F4F4F6;
        }
        [data-testid="stSidebar"] {
            background-color: #000000;
            border-right: 3px solid #D4AF37;
        }
        /* Títulos e Elementos de Destaque */
        h1, h2, h3 {
            color: #D4AF37 !important;
            font-family: 'Arial Black', sans-serif;
        }
        .sub-header-azul {
            color: #002868 !important;
            font-weight: bold;
        }
        /* Customização de Botões Master */
        .stButton > button {
            background-color: #D4AF37 !important;
            color: #000000 !important;
            font-weight: bold !important;
            border-radius: 4px !important;
            border: 1px solid #D4AF37 !important;
            transition: all 0.3s ease;
            width: 100%;
        }
        .stButton > button:hover {
            background-color: #002868 !important;
            color: #ffffff !important;
            border: 1px solid #002868 !important;
        }
        /* Customização de Inputs */
        .stTextInput > div > div > input, .stSelectbox > div > div, .stTextArea textarea {
            background-color: #161925 !important;
            color: #F4F4F6 !important;
            border: 1px solid #002868 !important;
            border-radius: 4px !important;
        }
        .stTextInput > div > div > input:focus {
            border: 1px solid #D4AF37 !important;
        }
        /* Cards Informativos (Dashboards) */
        .metric-card {
            background-color: #161925;
            border-left: 5px solid #D4AF37;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

injetar_css_corporativo()

# ==============================================================================
# 3. SEGURANÇA: SANITIZAÇÃO DA CHAVE PEM E CONEXÃO DRIVE (P0)
# ==============================================================================
ID_PASTA_DRIVE = "1-bHDGxbJDWTzT30zL9S-oj0ktM-c60_R"
SCOPES = ['https://www.googleapis.com/auth/drive']

def sanitizar_chave_pem(chave_raw: str) -> str:
    """Corrige quebras de linha e formatação do bloco de chave privada Google Cloud."""
    chave = chave_raw.replace('\\n', '\n').replace('\r', '')
    marcador_inicio = "-----BEGIN PRIVATE KEY-----"
    marcador_fim = "-----END PRIVATE KEY-----"
    
    if marcador_inicio in chave and marcador_fim in chave:
        corpo = chave.split(marcador_inicio)[1].split(marcador_fim)[0]
        corpo_limpo = "".join(corpo.split())
        linhas_64 = "\n".join([corpo_limpo[i:i+64] for i in range(0, len(corpo_limpo), 64)])
        return f"{marcador_inicio}\n{linhas_64}\n{marcador_fim}\n"
    return chave

@st.cache_resource(show_spinner=False)
def obter_servico_drive():
    """Instancia o cliente da API do Google Drive utilizando cache táctico."""
    if "gdrive" in st.secrets:
        try:
            info_chaves = dict(st.secrets["gdrive"])
            if "private_key" in info_chaves:
                info_chaves["private_key"] = sanitizar_chave_pem(info_chaves["private_key"])
            credenciais = service_account.Credentials.from_service_account_info(info_chaves, scopes=SCOPES)
            return build('drive', 'v3', credentials=credenciais, cache_discovery=False)
        except Exception as e:
            st.error(f"Erro crítico nas credenciais de nuvem: {e}")
    return None

def ler_arquivo_json_drive(nome_arquivo, dados_padrao):
    """Lê dados estruturados diretamente da árvore de diretórios do Drive."""
    try:
        service = obter_servico_drive()
        if not service:
            return dados_padrao
        query = f"name = '{nome_arquivo}' and '{ID_PASTA_DRIVE}' in parents and trashed = false"
        resultados = service.files().list(q=query, fields="files(id)").execute()
        arquivos = resultados.get('files', [])
        
        if not arquivos:
            return dados_padrao
            
        file_id = arquivos[0]['id']
        conteudo = service.files().get_media(fileId=file_id).execute()
        return json.loads(conteudo.decode('utf-8'))
    except Exception:
        return dados_padrao

def salvar_arquivo_json_drive(nome_arquivo, dados):
    """Persiste payloads de forma síncrona na nuvem."""
    try:
        service = obter_servico_drive()
        if not service:
            return
        json_dados = json.dumps(dados, indent=4, ensure_ascii=False)
        query = f"name = '{nome_arquivo}' and '{ID_PASTA_DRIVE}' in parents and trashed = false"
        resultados = service.files().list(q=query, fields="files(id)").execute()
        arquivos = resultados.get('files', [])
        
        media = MediaInMemoryUpload(json_dados.encode('utf-8'), mimetype='application/json')
        if arquivos:
            service.files().update(fileId=arquivos[0]['id'], media_body=media).execute()
        else:
            service.files().create(body={'name': nome_arquivo, 'parents': [ID_PASTA_DRIVE]}, media_body=media).execute()
    except Exception as e:
        st.sidebar.error(f"Erro de persistência em nuvem ({nome_arquivo}): {e}")

# ==============================================================================
# 4. ORQUESTRAÇÃO DE ESTADO E CONCORRÊNCIA (P0)
# ==============================================================================
USUARIOS_HARDCODED = {
    "sn1084433": {"nome": "Benedito Ricardo dos Santos", "senha": "Celina2610**", "perfil": "Gestor/Diretor"},
    "sn1220001": {"nome": "Professor de Testes SENAI", "senha": "122", "perfil": "Professor"},
    "aluno_ricardo": {"nome": "Ricardo (Aluno)", "senha": "123", "perfil": "Aluno"},
    "aluno_elizandra": {"nome": "Elizandra (Aluna)", "senha": "123", "perfil": "Aluno"},
    "coord_teste": {"nome": "Coordenador Técnico", "senha": "122", "perfil": "Coordenador"}
}

# Inicialização limpa e centralizada de estados locais
if 'suats_state' not in st.session_state:
    st.session_state.suats_state = {
        "usuario_logado": None,
        "perfil_logado": None,
        "nome_exibicao": None,
        "usuarios_cache": ler_arquivo_json_drive("usuarios.json", USUARIOS_HARDCODED),
        "provas_cache": ler_arquivo_json_drive("provas.json", {}),
        "entregas_cache": ler_arquivo_json_drive("entregas.json", {})
    }

state = st.session_state.suats_state

# Força sincronia se a conta mestre administrativa sumir do cache
if "sn1084433" not in state["usuarios_cache"]:
    state["usuarios_cache"].update(USUARIOS_HARDCODED)
    salvar_arquivo_json_drive("usuarios.json", state["usuarios_cache"])

# ==============================================================================
# 5. ROTAS E INTERFACES EXCLUSIVAS (BLUEPRINT FASE 1)
# ==============================================================================

def view_login():
    """Portal de Acesso Corporativo com proteção contra multiplos cliques."""
    st.markdown("<h2 style='text-align: center;'>🔐 SUATS | Portal de Acesso</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #cbd5e1;'>Insira suas credenciais corporativas SENAI para acessar a plataforma.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form(key="form_login"):
            input_user = st.text_input("Login Corporativo (Ex: snXXXXXXX):").strip().lower()
            input_pass = st.text_input("Senha de Acesso:", type="password")
            btn_submit = st.form_submit_button("🔓 Autenticar no Sistema")
            
            if btn_submit:
                user_info = state["usuarios_cache"].get(input_user)
                if user_info and user_info["senha"] == input_pass:
                    state["usuario_logado"] = input_user
                    state["perfil_logado"] = user_info["perfil"]
                    state["nome_exibicao"] = user_info["nome"]
                    st.success("Autenticação bem-sucedida! Redirecionando...")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas ou usuário inativo.")
        
        st.markdown("<p style='text-align:center; font-size:12px; color:#64748b;'>Suporte Técnico? Acione o Helpdesk da Unidade Senai-122.</p>", unsafe_allow_html=True)

def view_gestor():
    st.markdown(f"<h2>📊 Painel Executivo | Direção & Gestão</h2>", unsafe_allow_html=True)
    st.info(f"Contexto operacional: {state['nome_exibicao']}")
    # Conteúdo analítico e tabelas corporativas (Adicionado na próxima Sprint)

def view_professor():
    st.markdown("<h2>👨‍🏫 Central de Engenharia de Avaliações</h2>", unsafe_allow_html=True)
    st.info(f"Instrutor conectado: {state['nome_exibicao']}")
    # Assistente Wizard de criação de provas (Adicionado na próxima Sprint)

def view_aluno():
    st.markdown("<h2>📝 Terminal de Provas e Exames Técnicos</h2>", unsafe_allow_html=True)
    st.info(f"Estudante: {state['nome_exibicao']}")
    # Interface restrita de download e upload único (Adicionado na próxima Sprint)

def view_coordenador():
    st.markdown("<h2>🏫 Portal de Monitoramento da Coordenação</h2>", unsafe_allow_html=True)
    st.info(f"Visualização Analítica: {state['nome_exibicao']}")
    # Painel Read-only de turmas e desempenho (Adicionado na próxima Sprint)

# ==============================================================================
# 6. ORQUESTRAÇÃO DE ROTAS NO MENU LATERAL (SIDEBAR)
# ==============================================================================
if state["usuario_logado"] is None:
    view_login()
else:
    # Construção da Sidebar customizada baseada em Papéis
    with st.sidebar:
        st.markdown(f"<h3 style='color:#D4AF37; text-align:center;'>🏆 SENAI-122</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; font-size:12px;'>Usuário: {state['nome_exibicao']}<br><b>Perfil: {state['perfil_logado']}</b></p>", unsafe_allow_html=True)
        st.write("---")
        
        # Roteamento de Menus Dinâmicos conforme Blueprint Técnico
        if state["perfil_logado"] == "Gestor/Diretor":
            opcao = st.radio("Navegação Master", [
                "🏠 Dashboard Geral", "👥 Usuários", "🏫 Turmas", "👨‍🏫 Professores", 
                "📝 Avaliações", "📊 Analytics", "📁 Relatórios", "🛡 Auditoria", "⚙ Configurações"
            ])
        elif state["perfil_logado"] == "Professor":
            opcao = st.radio("Navegação Docente", [
                "🏠 Dashboard", "➕ Criar Avaliação", "📚 Banco de Questões", 
                "📝 Avaliações Ativas", "📤 Entregas", "📊 Relatórios", "⚙ Configurações"
            ])
        elif state["perfil_logado"] == "Aluno":
            opcao = st.radio("Navegação Discente", [
                "🏠 Início", "📝 Minhas Avaliações", "📥 Downloads", "📤 Upload", "📈 Histórico", "💬 Feedbacks"
            ])
        elif state["perfil_logado"] == "Coordenador":
            opcao = st.radio("Navegação Coordenação", [
                "🏠 Dashboard", "🏫 Turmas", "📊 Analytics", "📁 Relatórios"
            ])
            
        st.write("---")
        if st.button("🚪 Encerrar Sessão Corporativa"):
            state["usuario_logado"] = None
            state["perfil_logado"] = None
            state["nome_exibicao"] = None
            st.rerun()

    # Renderização da área de trabalho ativa baseada no perfil de segurança
    if state["perfil_logado"] == "Gestor/Diretor":
        view_gestor()
    elif state["perfil_logado"] == "Professor":
        view_professor()
    elif state["perfil_logado"] == "Aluno":
        view_aluno()
    elif state["perfil_logado"] == "Coordenador":
        view_coordenador()
