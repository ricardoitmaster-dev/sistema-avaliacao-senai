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
    """Busca um arquivo no Drive. Retorna dados_padrao se arquivo não existir, ou None se houver erro de conexão."""
    try:
        drive_service = obter_servico_drive()
        if drive_service is None:
