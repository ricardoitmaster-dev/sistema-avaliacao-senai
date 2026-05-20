import os
import sys
import subprocess
import time

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

import streamlit as st
import pandas as pd
import json
import random
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÃO DE ACESSO AO GOOGLE DRIVE EM NUVEM
# ==============================================================================
ID_PASTA_DRIVE = "1-bHDGxbJDWTzT30zL9S-oj0ktM-c60_R"
ARQUIVO_CHAVES = "chaves_google.json"
SCOPES = ['https://www.googleapis.com/auth/drive']


def sanitizar_chave_pem(chave_raw: str) -> str:
    """Sanitização robusta da private_key."""
    chave = chave_raw.replace('\\n', '\n').replace('\r', '')
    marcador_inicio = "-----BEGIN PRIVATE KEY-----"
    marcador_fim    = "-----END PRIVATE KEY-----"
    if marcador_inicio in chave and marcador_fim in chave:
        partes        = chave.split(marcador_inicio)
        corpo_e_fim   = partes[1].split(marcador_fim)
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
    return None


def ler_arquivo_drive(nome_arquivo, dados_padrao):
    for tentativa in range(3):
        try:
            drive_service = obter_servico_drive()
            if drive_service is None: return dados_padrao
            query = f"name = '{nome_arquivo}' and '{ID_PASTA_DRIVE}' in parents and trashed = false"
            resultados = drive_service.files().list(q=query, fields="files(id)").execute()
            files = resultados.get('files', [])
            if not files: return dados_padrao
            file_id  = files[0]['id']
            conteudo = drive_service.files().get_media(fileId=file_id).execute()
            return json.loads(conteudo.decode('utf-8'))
        except Exception:
            time.sleep(1)
    return dados_padrao


def salvar_arquivo_drive(nome_arquivo, dados):
    for tentativa in range(3):
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
            break
        except Exception:
            time.sleep(1)

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================
USUARIOS_PADRAO = {"sn1084433": {"nome": "Benedito Ricardo dos Santos", "senha": "Celina2610**", "perfil": "Gestor/Diretor"}}

if 'usuarios_cadastrados' not in st.session_state:
    st.session_state.usuarios_cadastrados = ler_arquivo_drive("usuarios.json", USUARIOS_PADRAO)
if 'provas_geradas' not in st.session_state: st.session_state.provas_geradas = ler_arquivo_drive("provas.json", {})
if 'entregas_sistema' not in st.session_state: st.session_state.entregas_sistema = ler_arquivo_drive("entregas.json", {})
if 'banco_questoes_ia' not in st.session_state: st.session_state.banco_questoes_ia = {"EXCEL AVANÇADO": []}
if 'usuario_logado' not in st.session_state: st.session_state.usuario_logado = None
if 'perfil_logado' not in st.session_state: st.session_state.perfil_logado = None
if 'nome_exibicao' not in st.session_state: st.session_state.nome_exibicao = None

st.set_page_config(page_title="Sistema SENAI", page_icon="🏆", layout="wide")

# (Estilos CSS omitidos aqui por brevidade, pode manter os seus originais)
st.markdown("""<style>.stButton > button { background-color: #D4AF37 !important; }</style>""", unsafe_allow_html=True)

# ==============================================================================
# PAINEL GESTOR - CADASTRO COM CORREÇÃO
# ==============================================================================
if st.session_state.perfil_logado == "Gestor/Diretor":
    aba_dados, aba_cadastros, aba_provas = st.tabs(["📈 Relatório", "👤 Cadastro", "📋 Provas"])
    
    with aba_cadastros:
        st.subheader("➕ Registrar Novo Usuário")
        col_a, col_b = st.columns(2)
        with col_a:
            novo_id = st.text_input("Login/Chapa:", key="key_id").strip().lower()
            novo_nome = st.text_input("Nome Completo:", key="key_nome")
        with col_b:
            nova_senha = st.text_input("Senha de Acesso:", type="password", key="key_senha")
            novo_perfil = st.selectbox("Perfil:", ["Aluno", "Professor", "Gestor/Diretor"], key="key_perfil")

        if st.button("💾 Salvar Novo Usuário"):
            if novo_id and novo_nome and nova_senha:
                if novo_id in st.session_state.usuarios_cadastrados:
                    st.warning("⚠️ ID já existe.")
                else:
                    st.session_state.usuarios_cadastrados[novo_id] = {"nome": novo_nome, "senha": nova_senha, "perfil": novo_perfil}
                    salvar_arquivo_drive("usuarios.json", st.session_state.usuarios_cadastrados)
                    st.success("✅ Usuário salvo!")
                    
                    # Lógica de Limpeza da Opção 2
                    st.session_state.key_id = ""
                    st.session_state.key_nome = ""
                    st.session_state.key_senha = ""
                    st.rerun() # Recarrega a tela para limpar visualmente os campos
            else:
                st.error("Preencha todos os campos.")
# ... restante do seu código segue igual ...
