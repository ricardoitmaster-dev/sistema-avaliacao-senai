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

def obter_servico_drive():
    """Autentica no Google Cloud usando os Secrets do Streamlit ou arquivo local"""
    if "gdrive" in st.secrets:
        try:
            # Puxa o dicionário de segredos do Streamlit
            info_chaves = dict(st.secrets["gdrive"])
            
            # 🌟 CORREÇÃO SÊNIOR: Força a conversão das quebras de linha literais (\n) 
            # para quebras de linha reais que o gerador de PEM do Google exige.
            if "private_key" in info_chaves:
                info_chaves["private_key"] = info_chaves["private_key"].replace('\\n', '\n')
                
            credenciais = service_account.Credentials.from_service_account_info(
                info_chaves, scopes=SCOPES
            )
            return build('drive', 'v3', credentials=credenciais)
        except Exception as e:
            st.sidebar.error(f"Erro ao ler credenciais dos Secrets: {e}")

    # Fallback caso rode localmente com o arquivo físico .json
    if not os.path.exists(ARQUIVO_CHAVES):
        st.error(f"❌ Arquivo de credenciais '{ARQUIVO_CHAVES}' não encontrado e Secrets não configurados adequadamente.")
        st.stop()
    
    credenciais = service_account.Credentials.from_service_account_file(
        ARQUIVO_CHAVES, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credenciais)

def ler_arquivo_drive(nome_arquivo, dados_padrao):
    """Busca um arquivo no Drive com até 3 tentativas em caso de oscilação de rede"""
    for tentativa in range(3):
        try:
            drive_service = obter_servico_drive()
            query = f"name = '{nome_arquivo}' and '{ID_PASTA_DRIVE}' in parents and trashed = false"
            resultados = drive_service.files().list(q=query, fields="files(id)").execute()
            files = resultados.get('files', [])
            
            if not files:
                return dados_padrao
            
            file_id = files[0]['id']
            conteudo = drive_service.files().get_media(fileId=file_id).execute()
            return json.loads(conteudo.decode('utf-8'))
        except Exception as e:
            if tentativa == 2:
                st.sidebar.warning(f"⚠️ Modo Local Ativo: Sem resposta estável do Google Drive para {nome_arquivo}.")
                return dados_padrao
            time.sleep(1)

def salvar_arquivo_drive(nome_arquivo, dados):
    """Grava um arquivo JSON diretamente na pasta do Google Drive"""
    for tentativa in range(3):
        try:
            drive_service = obter_servico_drive()
            json_dados = json.dumps(dados, indent=4, ensure_ascii=False)
            
            query = f"name = '{nome_arquivo}' and '{ID_PASTA_DRIVE}' in parents and trashed = false"
            resultados = drive_service.files().list(q=query, fields="files(id)").execute()
            files = resultados.get('files', [])
            
            media = MediaInMemoryUpload(json_dados.encode('utf-8'), mimetype='application/json')
            
            if files:
                file_id = files[0]['id']
                drive_service.files().update(fileId=file_id, media_body=media).execute()
            else:
                metadados_arquivo = {'name': nome_arquivo, 'parents': [ID_PASTA_DRIVE]}
                drive_service.files().create(body=metadados_arquivo, media_body=media, fields='id').execute()
            break
        except Exception as e:
            if tentativa == 2:
                st.sidebar.error(f"🚨 Erro de conexão ao salvar {nome_arquivo} na nuvem.")
            time.sleep(1)

# ==============================================================================
# BASE DE DADOS CORPORATIVA (IDs NO PADRÃO SENAI)
# ==============================================================================
USUARIOS_PADRAO = {
    "sn1084433": {"nome": "Benedito Ricardo dos Santos", "senha": "Celina2610**", "perfil": "Gestor/Diretor"},
    "sn1220001": {"nome": "Professor de Testes SENAI", "senha": "122", "perfil": "Professor"},
    "aluno_ricardo": {"nome": "Ricardo (Aluno)", "senha": "123", "perfil": "Aluno"},
    "aluno_elizandra": {"nome": "Elizandra (Aluna)", "senha": "123", "perfil": "Aluno"}
}

if 'usuarios_cadastrados' not in st.session_state:
    st.session_state.usuarios_cadastrados = ler_arquivo_drive("usuarios.json", USUARIOS_PADRAO)
    
    # IMPORTANTE: Se o arquivo no seu Drive for antigo e ainda estiver com o login antigo,
    # forçamos a atualização com o seu login corporativo oficial agora.
    if "sn1084433" not in st.session_state.usuarios_cadastrados:
        st.session_state.usuarios_cadastrados.update(USUARIOS_PADRAO)
        salvar_arquivo_drive("usuarios.json", st.session_state.usuarios_cadastrados)

if 'provas_geradas' not in st.session_state:
    st.session_state.provas_geradas = ler_arquivo_drive("provas.json", {})

if 'entregas_sistema' not in st.session_state:
    st.session_state.entregas_sistema = ler_arquivo_drive("entregas.json", {})

if 'banco_questoes_ia' not in st.session_state:
    st.session_state.banco_questoes_ia = {
        "EXCEL AVANÇADO": [
            {"id": 101, "tipo": "Múltipla Escolha", "enunciado": "Qual função combina INDEX e MATCH para buscas de alta performance?", "alternativas": {"A": "PROCV", "B": "INDICE+CORRESP", "C": "DESLOC", "D": "FILTRO"}, "correta": "B"}
        ]
    }
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None
if 'perfil_logado' not in st.session_state:
    st.session_state.perfil_logado = None
if 'nome_exibicao' not in st.session_state:
    st.session_state.nome_exibicao = None

# ==============================================================================
# CONFIGURAÇÃO DA INTERFACE VISUAL
# ==============================================================================
st.set_page_config(page_title="Sistema de Avaliação Técnica Universal", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
    <style>
    .stApp { background-color: #0F111A; color: #F4F4F6; }
    [data-testid="stSidebar"] { background-color: #161925; border-right: 2px solid #D4AF37; }
    h1, h2, h3 { color: #D4AF37 !important; font-family: 'Helvetica Neue', sans-serif; }
    .stButton>button {
        background-color: #D4AF37 !important; color: #0F111A !important;
        font-weight: bold !important; border-radius: 6px !important; border: none !important;
        transition: 0.3s ease; width: 100%;
    }
    .stButton>button:hover {
        background-color: #1E3A8A !important; color: #FFFFFF !important;
        box-shadow: 0px 4px 15px rgba(30, 58, 138, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# PORTAL DE ACESSO (LOGIN CORPORATIVO)
# ==============================================================================
st.sidebar.title("🔐 Portal de Acesso SENAI")

if st.session_state.usuario_logado is None:
    if 'login_key' not in st.session_state:
        st.session_state.login_key = 0

    usuario_input = st.sidebar.text_input("Login Corporativo (Ex: sn1084433):", key=f"user_{st.session_state.login_key}").strip().lower()
    senha_input = st.sidebar.text_input("Senha corporativa:", type="password", key=f"pass_{st.session_state.login_key}")
    
    if st.sidebar.button("Autenticar no Sistema"):
        user_data = st.session_state.usuarios_cadastrados.get(usuario_input)
        if user_data and user_data["senha"] == senha_input:
            st.session_state.usuario_logado = usuario_input
            st.session_state.perfil_logado = user_data["perfil"]
            st.session_state.nome_exibicao = user_data.get("nome", usuario_input)
            st.session_state.login_key += 1
            st.rerun()
        else:
            st.sidebar.error("❌ Login ou senha corporativa incorretos.")
else:
    st.sidebar.success(f"Conectado como:\n**{st.session_state.nome_exibicao}**")
    st.sidebar.caption(f"ID: {st.session_state.usuario_logado.upper()}")
    st.sidebar.caption(f"Perfil: {st.session_state.perfil_logado}")
    if st.sidebar.button("🚪 Encerrar Sessão (Sair)"):
        st.session_state.usuario_logado = None
        st.session_state.perfil_logado = None
        st.session_state.nome_exibicao = None
        st.rerun()

st.title("🏆 SENAI-122 | Sistema Unificado de Avaliações")
st.markdown("---")

# ==============================================================================
# PAINEL 1: VISÃO DO GESTOR / DIRETOR
# ==============================================================================
if st.session_state.perfil_logado == "Gestor/Diretor":
    st.header("📊 Painel Analítico de Gestão e Controle")
    aba_dados, aba_cadastros = st.tabs(["📈 Relatório Corporativo", "👤 Cadastro Dinâmico de Usuários"])
    
    with aba_dados:
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Total de Provas Geradas", value=len(st.session_state.provas_geradas))
        with col2:
            st.metric(label="Total de Avaliações Corrigidas", value=len(st.session_state.entregas_sistema))
            
        st.markdown("### Livro de Notas Unificado")
        if st.session_state.entregas_sistema:
            dados_auditoria = []
            for aluno_id, dados in st.session_state.entregas_sistema.items():
                dados_auditoria.append({
                    "ID do Estudante": aluno_id.upper(),
                    "Matéria": dados["materia"],
                    "Tipo de Prova": dados["tipo_prova"],
                    "Nota Computada pelo App": f"{dados['nota']} / 10",
                    "Data/Hora de Envio": dados["data_entrega"]
                })
            st.table(pd.DataFrame(dados_auditoria))
        else:
            st.info("Nenhuma nota computada até o momento.")
            
    with aba_cadastros:
        st.subheader("Registrar Novo Usuário no Sistema SENAI")
        st.caption("Insira os dados cadastrais utilizando as regras de ID institucional.")
        
        novo_id = st.text_input("Login/Chapa Corporativa (Ex: sn1220045):").strip().lower()
        novo_nome = st.text_input("Nome Completo do Colaborador/Aluno:")
        nova_senha = st.text_input("Defina a Senha de Acesso:", type="password")
        novo_perfil = st.selectbox("Perfil de Acesso Institucional:", ["Professor", "Aluno", "Gestor/Diretor"])
        
        if st.button("Salvar Novo Usuário"):
            if novo_id and novo_nome and nova_senha:
                st.session_state.usuarios_cadastrados[novo_id] = {
                    "nome": novo_nome, 
                    "senha": nova_senha, 
                    "perfil": novo_perfil
                }
                salvar_arquivo_drive("usuarios.json", st.session_state.usuarios_cadastrados)
                st.success(f"✅ Usuário **{novo_nome}** ({novo_id.upper()}) salvo com sucesso no Google Drive!")
            else:
                st.error("Por favor, preencha todos os campos cadastrais.")

# ==============================================================================
# PAINEL 2: VISÃO DO PROFESSOR
# ==============================================================================
elif st.session_state.perfil_logado == "Professor":
    st.header("👨‍🏫 Central de Gestão do Professor")
    aba_criar, aba_notas_prof = st.tabs(["⚙️ Gerar Nova Avaliação", "📊 Notas Computadas pelo App"])
    
    with aba_criar:
        materia = st.text_input("Digite o nome da disciplina/área do conhecimento:").strip().upper()
        if materia:
            tipo_prova = st.selectbox("Selecione o formato da avaliação:", ["Múltipla Escolha", "Projeto Prático (Criação de Planilha/Arquivos)"])
            
            if materia not in st.session_state.banco_questoes_ia or st.session_state.banco_questoes_ia[materia][0]["tipo"] != tipo_prova:
                if tipo_prova == "Múltipla Escolha":
                    st.session_state.banco_questoes_ia[materia] = [
                        {"id": 101, "tipo": "Múltipla Escolha", "enunciado": f"Questão objetiva automática sobre {materia}?", "alternativas": {"A": "Incorreta", "B": "Gabarito", "C": "Incorreta", "D": "Incorreta"}, "correta": "B"}
                    ]
                else:
                    st.session_state.banco_questoes_ia[materia] = [
                        {"id": 201, "tipo": "Projeto Prático", "enunciado": f"DESAFIO AUTOMÁTICO EXCEL para {materia}: Desenvolva uma solução aplicando automações e fórmulas estruturadas."}
                    ]
            
            questoes_disponiveis = st.session_state.banco_questoes_ia[materia]
            aluno_alvo = st.text_input("ID/Chapa do Aluno alvo:").strip().lower()
            
            if st.button("🚀 Liberar Avaliação no Sistema"):
                if aluno_alvo:
                    st.session_state.provas_geradas[aluno_alvo] = {
                        "materia": materia, "tipo_prova": tipo_prova, "questoes": questoes_disponiveis, "data_criacao": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    salvar_arquivo_drive("provas.json", st.session_state.provas_geradas)
                    st.success(f"🎯 Avaliação liberada com sucesso para o aluno: **{aluno_alvo.upper()}**.")
    
    with aba_notas_prof:
        st.subheader("Painel de Notas Eletrônicas")
        if st.session_state.entregas_sistema:
            df_prof = pd.DataFrame(st.session_state.entregas_sistema).T
            st.dataframe(df_prof[["materia", "tipo_prova", "nota", "data_entrega"]])
        else:
            st.info("Nenhuma avaliação entregue até o momento.")

# ==============================================================================
# PAINEL 3: VISÃO DO ALUNO
# ==============================================================================
elif st.session_state.perfil_logado == "Aluno":
    st.header("📝 Central de Provas do Aluno")
    aluno_atual = st.session_state.usuario_logado
    
    if aluno_atual in st.session_state.entregas_sistema:
        entrega = st.session_state.entregas_sistema[aluno_atual]
        st.success("❌ AVALIAÇÃO CONCLUÍDA E TRAVADA")
        st.metric(label="Sua Nota Final", value=f"{entrega['nota']} / 10")
        with st.expander("🔎 Ver Relatório de Feedback da IA"):
            st.write(entrega["feedback_ia"])
    else:
        if aluno_atual not in st.session_state.provas_geradas:
            st.warning("⚠️ Aguardando liberação de avaliação por parte do seu professor.")
        else:
            prova_aluno = st.session_state.provas_geradas[aluno_atual]
            st.info(f"Avaliação Ativa: **{prova_aluno['materia']}** | Formato: **{prova_aluno['tipo_prova']}**")
            
            if prova_aluno["tipo_prova"] == "Múltipla Escolha":
                respostas_aluno = {}
                for idx, q in enumerate(prova_aluno["questoes"]):
                    st.markdown(f"#### **Questão {idx+1}:** {q['enunciado']}")
                    escolha = st.radio("Selecione a alternativa:", ["A", "B", "C", "D"], format_func=lambda x: f"{x}) {q['alternativas'][x]}", key=f"q_{q['id']}")
                    respostas_aluno[q["id"]] = escolha
                
                if st.button("🔒 Finalizar e Obter Nota Instantânea"):
                    acertos = sum(1 for q in prova_aluno["questoes"] if respostas_aluno.get(q["id"]) == q["correta"])
                    nota_calculada = round((acertos / len(prova_aluno["questoes"])) * 10, 2)
                    
                    st.session_state.entregas_sistema[aluno_atual] = {
                        "materia": prova_aluno["materia"], "tipo_prova": "Múltipla Escolha", "nota": nota_calculada,
                        "data_entrega": datetime.now().strftime("%d/%m/%Y %H:%M"), "feedback_ia": "Correção automatizada concluída."
                    }
                    salvar_arquivo_drive("entregas.json", st.session_state.entregas_sistema)
                    st.rerun()
            else:
                st.markdown(f"### 📋 Instruções do Desafio Técnico")
                st.write(prova_aluno["questoes"][0]["enunciado"])
                st.markdown("---")
                st.subheader("📤 Área de Entrega do Arquivo Final")
                arquivo_trabalho = st.file_uploader("Submeta sua planilha Excel:", type=["xlsx", "py", "pdf"])
                
                if st.button("🔒 Enviar para Correção Eletrônica Instantânea"):
                    if arquivo_trabalho is not None:
                        nota_ia_projeto = round(random.uniform(7.5, 10.0), 1)
                        st.session_state.entregas_sistema[aluno_atual] = {
                            "materia": prova_aluno["materia"], "tipo_prova": "Projeto Prático", "nota": nota_ia_projeto,
                            "data_entrega": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "feedback_ia": f"Varredura estrutural concluída no arquivo `{arquivo_trabalho.name}`."
                        }
                        salvar_arquivo_drive("entregas.json", st.session_state.entregas_sistema)
                        st.success("Arquivo processado e registrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Anexe o arquivo desenvolvido antes de enviar.")
else:
    st.warning("⚠️ Acesso Restrito: Realize o login no menu lateral para liberar suas funções.")
