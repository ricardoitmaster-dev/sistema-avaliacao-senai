import os
import sys
import subprocess
import time
import streamlit as st
import pandas as pd
import json
import random
from datetime import datetime

# ==============================================================================
# INSTALAÇÃO AUTOMÁTICA DE DEPENDÊNCIAS
# ==============================================================================
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-auth", "google-api-python-client"])
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload

# ==============================================================================
# CONFIGURAÇÃO DE ACESSO AO GOOGLE DRIVE EM NUVEM
# ==============================================================================
ID_PASTA_DRIVE = "1-bHDGxbJDWTzT30zL9S-oj0ktM-c60_R"
ARQUIVO_CHAVES = "chaves_google.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

def sanitizar_chave_pem(chave_raw: str) -> str:
    chave = chave_raw.replace('\\n', '\n').replace('\r', '')
    marcador_inicio = "-----BEGIN PRIVATE KEY-----"
    marcador_fim    = "-----END PRIVATE KEY-----"
    if marcador_inicio in chave and marcador_fim in chave:
        partes       = chave.split(marcador_inicio)
        corpo_e_fim  = partes[1].split(marcador_fim)
        corpo_base64  = corpo_e_fim[0]
        corpo_limpo = "".join(corpo_base64.split())
        linhas_64   = "\n".join([corpo_limpo[i:i+64] for i in range(0, len(corpo_limpo), 64)])
        chave = f"{marcador_inicio}\n{linhas_64}\n{marcador_fim}\n"
    return chave

def obter_servico_drive():
    if "gdrive" in st.secrets:
        try:
            info_chaves = dict(st.secrets["gdrive"])
            if "private_key" in info_chaves:
                info_chaves["private_key"] = sanitizar_chave_pem(info_chaves["private_key"])
            credenciais = service_account.Credentials.from_service_account_info(info_chaves, scopes=SCOPES)
            return build('drive', 'v3', credentials=credenciais)
        except Exception as e:
            st.sidebar.error(f"Erro ao ler Secrets: {e}")
            return None
    if not os.path.exists(ARQUIVO_CHAVES):
        return None
    try:
        credenciais = service_account.Credentials.from_service_account_file(ARQUIVO_CHAVES, scopes=SCOPES)
        return build('drive', 'v3', credentials=credenciais)
    except Exception:
        return None

def ler_arquivo_drive(nome_arquivo, dados_padrao):
    try:
        drive_service = obter_servico_drive()
        if drive_service is None: return None
        query = f"name = '{nome_arquivo}' and '{ID_PASTA_DRIVE}' in parents and trashed = false"
        resultados = drive_service.files().list(q=query, fields="files(id)").execute()
        files = resultados.get('files', [])
        if not files: return dados_padrao
        file_id = files[0]['id']
        conteudo = drive_service.files().get_media(fileId=file_id).execute()
        return json.loads(conteudo.decode('utf-8'))
    except Exception:
        return None

def salvar_arquivo_drive(nome_arquivo, dados):
    try:
        drive_service = obter_servico_drive()
        if drive_service is None: return
        json_dados = json.dumps(dados, indent=4, ensure_ascii=False)
        query = f"name = '{nome_arquivo}' and '{ID_PASTA_DRIVE}' in parents and trashed = false"
        resultados = drive_service.files().list(q=query, fields="files(id)").execute()
        files = resultados.get('files', [])
        media = MediaInMemoryUpload(json_dados.encode('utf-8'), mimetype='application/json')
        if files:
            drive_service.files().update(fileId=files[0]['id'], media_body=media).execute()
        else:
            drive_service.files().create(body={'name': nome_arquivo, 'parents': [ID_PASTA_DRIVE]}, media_body=media).execute()
    except Exception as e:
        st.sidebar.error(f"🚨 Erro ao salvar {nome_arquivo}: {e}")

# ==============================================================================
# DADOS INICIAIS E SESSION STATE
# ==============================================================================
USUARIOS_PADRAO = {
    "sn1084433": {"nome": "Benedito Ricardo dos Santos", "senha": "Celina2610**", "perfil": "Gestor/Diretor"},
    "sn1220001": {"nome": "Professor de Testes SENAI", "senha": "122", "perfil": "Professor"},
    "aluno_ricardo": {"nome": "Ricardo (Aluno)", "senha": "123", "perfil": "Aluno"},
    "aluno_elizandra": {"nome": "Elizandra (Aluna)", "senha": "123", "perfil": "Aluno"}
}

if 'usuarios_cadastrados' not in st.session_state:
    carregado = ler_arquivo_drive("usuarios.json", USUARIOS_PADRAO)
    st.session_state.usuarios_cadastrados = carregado if carregado is not None else USUARIOS_PADRAO
    if "sn1084433" not in st.session_state.usuarios_cadastrados:
        st.session_state.usuarios_cadastrados.update(USUARIOS_PADRAO)
        salvar_arquivo_drive("usuarios.json", st.session_state.usuarios_cadastrados)

if 'provas_geradas' not in st.session_state:
    carregado = ler_arquivo_drive("provas.json", {})
    st.session_state.provas_geradas = carregado if carregado is not None else {}

if 'entregas_sistema' not in st.session_state:
    carregado = ler_arquivo_drive("entregas.json", {})
    st.session_state.entregas_sistema = carregado if carregado is not None else {}

if 'banco_questoes_ia' not in st.session_state:
    st.session_state.banco_questoes_ia = {"EXCEL AVANÇADO": [{"id": 101, "tipo": "Múltipla Escolha", "enunciado": "Qual função combina INDEX e MATCH?", "alternativas": {"A": "PROCV", "B": "INDICE+CORRESP", "C": "DESLOC", "D": "FILTRO"}, "correta": "B"}]}

for key in ['usuario_logado', 'perfil_logado', 'nome_exibicao']:
    if key not in st.session_state: st.session_state[key] = None

# ==============================================================================
# INTERFACE VISUAL
# ==============================================================================
st.set_page_config(page_title="Sistema de Avaliação Técnica SENAI", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0F111A; color: #F4F4F6; }
    [data-testid="stSidebar"] { background-color: #161925; border-right: 2px solid #D4AF37; }
    h1, h2, h3 { color: #D4AF37 !important; }
    .stButton > button { background-color: #D4AF37 !important; color: #0F111A !important; font-weight: bold !important; border-radius: 6px !important; }
    .stTextInput > div > div > input, .stSelectbox > div > div, .stTextArea textarea { background-color: #1E2233 !important; color: #F4F4F6 !important; border: 1px solid #D4AF37 !important; }
    </style>
""", unsafe_allow_html=True)

# PORTAL DE ACESSO
st.sidebar.markdown("<h2 style='text-align:center; color:#D4AF37;'>🔐 Portal SENAI</h2>", unsafe_allow_html=True)
if st.session_state.usuario_logado is None:
    if 'login_key' not in st.session_state: st.session_state.login_key = 0
    u_in = st.sidebar.text_input("Login Corporativo:", key=f"user_{st.session_state.login_key}").strip().lower()
    s_in = st.sidebar.text_input("Senha:", type="password", key=f"pass_{st.session_state.login_key}")
    if st.sidebar.button("🔓 Autenticar"):
        user_data = st.session_state.usuarios_cadastrados.get(u_in)
        if user_data and user_data["senha"] == s_in:
            st.session_state.usuario_logado = u_in
            st.session_state.perfil_logado = user_data["perfil"]
            st.session_state.nome_exibicao = user_data.get("nome", u_in)
            st.session_state.login_key += 1
            st.rerun()
        else: st.sidebar.error("Login ou senha incorretos.")
else:
    st.sidebar.success(f"Conectado: **{st.session_state.nome_exibicao}**")
    if st.sidebar.button("🚪 Encerrar Sessão"):
        for key in ['usuario_logado', 'perfil_logado', 'nome_exibicao']: st.session_state[key] = None
        st.rerun()

st.title("🏆 SENAI-122 | Sistema Unificado de Avaliações")
st.markdown("---")

# ==============================================================================
# PAINEL GESTOR
# ==============================================================================
if st.session_state.perfil_logado == "Gestor/Diretor":
    st.header("📊 Painel Analítico")
    aba1, aba2, aba3 = st.tabs(["📈 Relatório", "👤 Usuários", "📋 Provas"])
    with aba1:
        st.metric("Total de Provas", len(st.session_state.provas_geradas))
        if st.session_state.entregas_sistema:
            st.dataframe(pd.DataFrame([{"ID": uid, **d} for uid, d in st.session_state.entregas_sistema.items()]))
    with aba2:
        novo_id = st.text_input("Novo Login:")
        novo_nome = st.text_input("Nome:")
        nova_senha = st.text_input("Senha:", type="password")
        if st.button("Salvar Usuário"):
            if novo_id and novo_nome and nova_senha:
                st.session_state.usuarios_cadastrados[novo_id] = {"nome": novo_nome, "senha": nova_senha, "perfil": "Aluno"}
                salvar_arquivo_drive("usuarios.json", st.session_state.usuarios_cadastrados)
                st.success("Salvo!")
        st.dataframe(pd.DataFrame([{"ID": k, **v} for k, v in st.session_state.usuarios_cadastrados.items()]))
    with aba3:
        st.write(st.session_state.provas_geradas)

# ==============================================================================
# PAINEL PROFESSOR
# ==============================================================================
elif st.session_state.perfil_logado == "Professor":
    st.header("👨‍🏫 Central do Professor")
    aba1, aba2 = st.tabs(["⚙️ Criar Prova", "📝 Banco de Questões"])
    with aba1:
        materia = st.text_input("Matéria:").strip().upper()
        if materia:
            aluno = st.selectbox("Aluno:", list(st.session_state.usuarios_cadastrados.keys()))
            if st.button("Liberar Prova"):
                st.session_state.provas_geradas[aluno] = {"materia": materia, "tipo_prova": "Múltipla Escolha", "questoes": st.session_state.banco_questoes_ia.get(materia, [])}
                salvar_arquivo_drive("provas.json", st.session_state.provas_geradas)
                st.success("Prova liberada!")

# ==============================================================================
# PAINEL ALUNO
# ==============================================================================
elif st.session_state.perfil_logado == "Aluno":
    st.header("📝 Central de Provas")
    aluno_atual = st.session_state.usuario_logado
    if aluno_atual in st.session_state.entregas_sistema:
        st.success("✅ Prova já realizada!")
    elif aluno_atual not in st.session_state.provas_geradas:
        st.warning("⚠️ Aguarde a liberação do professor.")
    else:
        prova = st.session_state.provas_geradas[aluno_atual]
        st.info(f"Prova de {prova['materia']}")
        # Lógica de respostas
        if st.button("Finalizar"):
            st.session_state.entregas_sistema[aluno_atual] = {"materia": prova['materia'], "nota": 10.0, "data_entrega": datetime.now().strftime("%d/%m/%Y")}
            salvar_arquivo_drive("entregas.json", st.session_state.entregas_sistema)
            st.rerun()
else:
    st.markdown("### Bem-vindo. Faça o login no menu lateral.")
