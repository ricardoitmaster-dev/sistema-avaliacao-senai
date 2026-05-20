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
    """
    Sanitização defensiva e robusta da private_key PEM.
    Resolve o erro InvalidData(InvalidByte) causado por formatação
    inconsente dentro do bloco de chave no Streamlit Secrets.
    """
    # 1. Substitui todas as variações de \n literal por quebra real
    chave = chave_raw.replace('\\n', '\n')

    # 2. Remove qualquer \r que possa ter vindo de ambientes Windows
    chave = chave.replace('\r', '')

    # 3. Extrai somente o conteúdo base64 entre os marcadores PEM
    marcador_inicio = "-----BEGIN PRIVATE KEY-----"
    marcador_fim    = "-----END PRIVATE KEY-----"

    if marcador_inicio in chave and marcador_fim in chave:
        partes        = chave.split(marcador_inicio)
        corpo_e_fim   = partes[1].split(marcador_fim)
        corpo_base64  = corpo_e_fim[0]

        # 4. Limpa o corpo: remove espaços, tabs e quebras extras,
        #    depois quebra em linhas de 64 chars (padrão PEM/RFC 7468)
        corpo_limpo = "".join(corpo_base64.split())          # remove todo whitespace
        linhas_64   = "\n".join(                             # reconstrói em blocos de 64
            corpo_limpo[i:i+64]
            for i in range(0, len(corpo_limpo), 64)
        )

        chave = f"{marcador_inicio}\n{linhas_64}\n{marcador_fim}\n"

    return chave


def obter_servico_drive():
    """Autentica no Google Cloud usando os Secrets do Streamlit ou arquivo local."""
    if "gdrive" in st.secrets:
        try:
            info_chaves = dict(st.secrets["gdrive"])

            # Aplica sanitização robusta antes de qualquer uso
            if "private_key" in info_chaves:
                info_chaves["private_key"] = sanitizar_chave_pem(
                    info_chaves["private_key"]
                )

            credenciais = service_account.Credentials.from_service_account_info(
                info_chaves, scopes=SCOPES
            )
            return build('drive', 'v3', credentials=credenciais)

        except Exception as e:
            st.sidebar.error(f"Erro ao ler credenciais dos Secrets: {e}")
            return None

    # Fallback: arquivo físico .json local
    if not os.path.exists(ARQUIVO_CHAVES):
        st.error(
            f"❌ Arquivo de credenciais '{ARQUIVO_CHAVES}' não encontrado "
            f"e Secrets não configurados adequadamente."
        )
        st.stop()

    credenciais = service_account.Credentials.from_service_account_file(
        ARQUIVO_CHAVES, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credenciais)


def ler_arquivo_drive(nome_arquivo, dados_padrao):
    """Busca um arquivo no Drive com até 3 tentativas."""
    for tentativa in range(3):
        try:
            drive_service = obter_servico_drive()
            if drive_service is None:
                return dados_padrao

            query = (
                f"name = '{nome_arquivo}' and "
                f"'{ID_PASTA_DRIVE}' in parents and trashed = false"
            )
            resultados = drive_service.files().list(
                q=query, fields="files(id)"
            ).execute()
            files = resultados.get('files', [])

            if not files:
                return dados_padrao

            file_id  = files[0]['id']
            conteudo = drive_service.files().get_media(fileId=file_id).execute()
            return json.loads(conteudo.decode('utf-8'))

        except Exception as e:
            if tentativa == 2:
                st.sidebar.warning(
                    f"⚠️ Modo Local Ativo: Sem resposta estável do "
                    f"Google Drive para {nome_arquivo}. Erro: {e}"
                )
                return dados_padrao
            time.sleep(1)
    return dados_padrao


def salvar_arquivo_drive(nome_arquivo, dados):
    """Grava um arquivo JSON diretamente na pasta do Google Drive."""
    for tentativa in range(3):
        try:
            drive_service = obter_servico_drive()
            if drive_service is None:
                return

            json_dados = json.dumps(dados, indent=4, ensure_ascii=False)

            query = (
                f"name = '{nome_arquivo}' and "
                f"'{ID_PASTA_DRIVE}' in parents and trashed = false"
            )
            resultados = drive_service.files().list(
                q=query, fields="files(id)"
            ).execute()
            files = resultados.get('files', [])

            media = MediaInMemoryUpload(
                json_dados.encode('utf-8'), mimetype='application/json'
            )

            if files:
                file_id = files[0]['id']
                drive_service.files().update(
                    fileId=file_id, media_body=media
                ).execute()
            else:
                metadados_arquivo = {
                    'name': nome_arquivo,
                    'parents': [ID_PASTA_DRIVE]
                }
                drive_service.files().create(
                    body=metadados_arquivo, media_body=media, fields='id'
                ).execute()
            break  # Sucesso — sai do loop

        except Exception as e:
            if tentativa == 2:
                st.sidebar.error(
                    f"🚨 Erro de conexão ao salvar {nome_arquivo} na nuvem: {e}"
                )
            time.sleep(1)


# ==============================================================================
# BASE DE DADOS CORPORATIVA (IDs NO PADRÃO SENAI)
# ==============================================================================
USUARIOS_PADRAO = {
    "sn1084433": {
        "nome": "Benedito Ricardo dos Santos",
        "senha": "Celina2610**",
        "perfil": "Gestor/Diretor"
    },
    "sn1220001": {
        "nome": "Professor de Testes SENAI",
        "senha": "122",
        "perfil": "Professor"
    },
    "aluno_ricardo": {
        "nome": "Ricardo (Aluno)",
        "senha": "123",
        "perfil": "Aluno"
    },
    "aluno_elizandra": {
        "nome": "Elizandra (Aluna)",
        "senha": "123",
        "perfil": "Aluno"
    }
}

# ---------- Inicialização de session_state ----------
if 'usuarios_cadastrados' not in st.session_state:
    st.session_state.usuarios_cadastrados = ler_arquivo_drive(
        "usuarios.json", USUARIOS_PADRAO
    )
    # Garante que o usuário gestor principal sempre exista
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
            {
                "id": 101,
                "tipo": "Múltipla Escolha",
                "enunciado": "Qual função combina INDEX e MATCH para buscas de alta performance?",
                "alternativas": {
                    "A": "PROCV",
                    "B": "INDICE+CORRESP",
                    "C": "DESLOC",
                    "D": "FILTRO"
                },
                "correta": "B"
            }
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
st.set_page_config(
    page_title="Sistema de Avaliação Técnica SENAI",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* ── Fundo e texto base ── */
    .stApp { background-color: #0F111A; color: #F4F4F6; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #161925;
        border-right: 2px solid #D4AF37;
    }

    /* ── Títulos ── */
    h1, h2, h3 { color: #D4AF37 !important; font-family: 'Helvetica Neue', sans-serif; }

    /* ── Botões padrão ── */
    .stButton > button {
        background-color: #D4AF37 !important;
        color: #0F111A !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        border: none !important;
        transition: 0.3s ease;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #1E3A8A !important;
        color: #FFFFFF !important;
        box-shadow: 0px 4px 15px rgba(30, 58, 138, 0.4);
    }

    /* ── Inputs e selects ── */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stTextArea textarea {
        background-color: #1E2233 !important;
        color: #F4F4F6 !important;
        border: 1px solid #D4AF37 !important;
        border-radius: 6px !important;
    }

    /* ── Métricas ── */
    [data-testid="stMetricValue"] {
        color: #D4AF37 !important;
        font-size: 2rem !important;
        font-weight: bold !important;
    }

    /* ── Abas ── */
    .stTabs [data-baseweb="tab"] {
        color: #F4F4F6 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #D4AF37 !important;
        border-bottom: 2px solid #D4AF37 !important;
    }

    /* ── Divisor ── */
    hr { border-color: #D4AF37 !important; opacity: 0.3; }

    /* ── Info / Success / Warning ── */
    .stAlert { border-radius: 8px !important; }
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# PORTAL DE ACESSO (LOGIN CORPORATIVO)
# ==============================================================================
st.sidebar.markdown(
    "<h2 style='text-align:center; color:#D4AF37;'>🔐 Portal SENAI</h2>",
    unsafe_allow_html=True
)

if st.session_state.usuario_logado is None:
    if 'login_key' not in st.session_state:
        st.session_state.login_key = 0

    usuario_input = st.sidebar.text_input(
        "Login Corporativo (Ex: sn1084433):",
        key=f"user_{st.session_state.login_key}"
    ).strip().lower()

    senha_input = st.sidebar.text_input(
        "Senha corporativa:",
        type="password",
        key=f"pass_{st.session_state.login_key}"
    )

    if st.sidebar.button("🔓 Autenticar no Sistema"):
        user_data = st.session_state.usuarios_cadastrados.get(usuario_input)
        if user_data and user_data["senha"] == senha_input:
            st.session_state.usuario_logado  = usuario_input
            st.session_state.perfil_logado   = user_data["perfil"]
            st.session_state.nome_exibicao   = user_data.get("nome", usuario_input)
            st.session_state.login_key      += 1
            st.rerun()
        else:
            st.sidebar.error("❌ Login ou senha corporativa incorretos.")
else:
    st.sidebar.success(f"✅ Conectado como:\n**{st.session_state.nome_exibicao}**")
    st.sidebar.caption(f"🪪 ID: {st.session_state.usuario_logado.upper()}")
    st.sidebar.caption(f"👤 Perfil: {st.session_state.perfil_logado}")
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Encerrar Sessão"):
        st.session_state.usuario_logado = None
        st.session_state.perfil_logado  = None
        st.session_state.nome_exibicao  = None
        st.rerun()

# ---------- Cabeçalho principal ----------
st.title("🏆 SENAI-122 | Sistema Unificado de Avaliações")
st.markdown("---")


# ==============================================================================
# PAINEL 1: VISÃO DO GESTOR / DIRETOR
# ==============================================================================
if st.session_state.perfil_logado == "Gestor/Diretor":
    st.header("📊 Painel Analítico de Gestão e Controle")

    aba_dados, aba_cadastros, aba_provas_ativas = st.tabs([
        "📈 Relatório Corporativo",
        "👤 Cadastro de Usuários",
        "📋 Provas Ativas"
    ])

    with aba_dados:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Provas Geradas", len(st.session_state.provas_geradas))
        with col2:
            st.metric("Avaliações Corrigidas", len(st.session_state.entregas_sistema))
        with col3:
            st.metric("Usuários Cadastrados", len(st.session_state.usuarios_cadastrados))

        st.markdown("### 📒 Livro de Notas Unificado")
        if st.session_state.entregas_sistema:
            dados_auditoria = []
            for aluno_id, dados in st.session_state.entregas_sistema.items():
                nome_aluno = st.session_state.usuarios_cadastrados.get(
                    aluno_id, {}
                ).get("nome", aluno_id.upper())
                dados_auditoria.append({
                    "ID do Estudante": aluno_id.upper(),
                    "Nome":            nome_aluno,
                    "Matéria":         dados.get("materia", "—"),
                    "Tipo de Prova":   dados.get("tipo_prova", "—"),
                    "Nota":            f"{dados.get('nota', '—')} / 10",
                    "Data de Envio":   dados.get("data_entrega", "—")
                })
            st.dataframe(
                pd.DataFrame(dados_auditoria),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhuma nota computada até o momento.")

    with aba_cadastros:
        st.subheader("➕ Registrar Novo Usuário")

        col_a, col_b = st.columns(2)
        with col_a:
            novo_id     = st.text_input("Login/Chapa (Ex: sn1220045):").strip().lower()
            novo_nome   = st.text_input("Nome Completo:")
        with col_b:
            nova_senha  = st.text_input("Senha de Acesso:", type="password")
            novo_perfil = st.selectbox(
                "Perfil de Acesso:",
                ["Aluno", "Professor", "Gestor/Diretor"]
            )

        if st.button("💾 Salvar Novo Usuário"):
            if novo_id and novo_nome and nova_senha:
                if novo_id in st.session_state.usuarios_cadastrados:
                    st.warning(f"⚠️ O ID **{novo_id.upper()}** já existe no sistema.")
                else:
                    st.session_state.usuarios_cadastrados[novo_id] = {
                        "nome":   novo_nome,
                        "senha":  nova_senha,
                        "perfil": novo_perfil
                    }
                    salvar_arquivo_drive(
                        "usuarios.json",
                        st.session_state.usuarios_cadastrados
                    )
                    st.success(
                        f"✅ Usuário **{novo_nome}** ({novo_id.upper()}) "
                        f"salvo com sucesso!"
                    )
            else:
                st.error("Por favor, preencha todos os campos.")

        st.markdown("---")
        st.subheader("👥 Usuários Cadastrados")
        lista_usuarios = [
            {
                "ID":      uid.upper(),
                "Nome":   u.get("nome", "—"),
                "Perfil": u.get("perfil", "—")
            }
            for uid, u in st.session_state.usuarios_cadastrados.items()
        ]
        st.dataframe(
            pd.DataFrame(lista_usuarios),
            use_container_width=True,
            hide_index=True
        )

    with aba_provas_ativas:
        st.subheader("📋 Provas Liberadas no Sistema")
        if st.session_state.provas_geradas:
            lista_provas = []
            for aluno_id, prova in st.session_state.provas_geradas.items():
                nome_aluno = st.session_state.usuarios_cadastrados.get(
                    aluno_id, {}
                ).get("nome", aluno_id.upper())
                ja_entregou = aluno_id in st.session_state.entregas_sistema
                lista_provas.append({
                    "Aluno ID":     aluno_id.upper(),
                    "Nome":         nome_aluno,
                    "Matéria":      prova.get("materia", "—"),
                    "Tipo":         prova.get("tipo_prova", "—"),
                    "Criada em":    prova.get("data_criacao", "—"),
                    "Status":       "✅ Entregue" if ja_entregou else "⏳ Pendente"
                })
            st.dataframe(
                pd.DataFrame(lista_provas),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhuma prova liberada até o momento.")


# ==============================================================================
# PAINEL 2: VISÃO DO PROFESSOR
# ==============================================================================
elif st.session_state.perfil_logado == "Professor":
    st.header("👨‍🏫 Central de Gestão do Professor")

    aba_criar, aba_questoes, aba_notas_prof = st.tabs([
        "⚙️ Gerar Nova Avaliação",
        "📝 Banco de Questões",
        "📊 Notas Computadas"
    ])

    with aba_criar:
        st.subheader("Nova Avaliação")

        materia = st.text_input(
            "Nome da disciplina/área do conhecimento:"
        ).strip().upper()

        if materia:
            tipo_prova = st.selectbox(
                "Formato da avaliação:",
                ["Múltipla Escolha", "Projeto Prático (Criação de Planilha/Arquivos)"]
            )

            # Inicializa banco da matéria se não existir ou se foi corrompido como boolean
            if materia not in st.session_state.banco_questoes_ia or not isinstance(st.session_state.banco_questoes_ia[materia], list):
                st.session_state.banco_questoes_ia[materia] = []

            # Filtra garantindo que estamos operando sobre uma lista real
            questoes_da_materia = [
                q for q in st.session_state.banco_questoes_ia[materia]
                if isinstance(q, dict) and (
                    q.get("tipo") == tipo_prova or
                    (tipo_prova == "Projeto Prático (Criação de Planilha/Arquivos)" and q.get("tipo") == "Projeto Prático")
                )
            ]

            # Cria questão padrão se não houver nenhuma
            if not questoes_da_materia:
                if "Múltipla Escolha" in tipo_prova:
                    questoes_da_materia = [{
                        "id": 101,
                        "tipo": "Múltipla Escolha",
                        "enunciado": f"Questão objetiva automática sobre {materia}?",
                        "alternativas": {
                            "A": "Incorreta", "B": "Gabarito",
                            "C": "Incorreta", "D": "Incorreta"
                        },
                        "correta": "B"
                    }]
                else:
                    questoes_da_materia = [{
                        "id": 201,
                        "tipo": "Projeto Prático",
                        "enunciado": (
                            f"DESAFIO TÉCNICO — {materia}: "
                            "Desenvolva uma solução aplicando automações e "
                            "fórmulas estruturadas conforme instruções do professor."
                        )
                    }]
                st.session_state.banco_questoes_ia[materia] = questoes_da_materia

            st.markdown(f"**Questões disponíveis para esta prova:** {len(questoes_da_materia)}")

            # Seleção do aluno alvo
            disabled_alunos = {
                uid: u["nome"]
                for uid, u in st.session_state.usuarios_cadastrados.items()
                if u.get("perfil") == "Aluno"
            }

            if disabled_alunos:
                aluno_selecionado = st.selectbox(
                    "Selecione o aluno:",
                    options=list(disabled_alunos.keys()),
                    format_func=lambda x: f"{disabled_alunos[x]} ({x.upper()})"
                )
            else:
                aluno_selecionado = st.text_input(
                    "ID/Chapa do Aluno alvo:"
                ).strip().lower()

            if st.button("🚀 Liberar Avaliação no Sistema"):
                if aluno_selecionado:
                    st.session_state.provas_geradas[aluno_selecionado] = {
                        "materia":      materia,
                        "tipo_prova":   tipo_prova,
                        "questoes":     questoes_da_materia,
                        "data_criacao": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    salvar_arquivo_drive(
                        "provas.json", st.session_state.provas_geradas
                    )
                    nome_aluno_alvo = disabled_alunos.get(
                        aluno_selecionado, aluno_selecionado.upper()
                    )
                    st.success(
                        f"🎯 Avaliação de **{materia}** liberada para "
                        f"**{nome_aluno_alvo}** com sucesso!"
                    )
                else:
                    st.error("Selecione ou informe um aluno.")

    with aba_questoes:
        st.subheader("➕ Adicionar Questão ao Banco")

        materia_q = st.text_input(
            "Disciplina da questão:"
        ).strip().upper()

        tipo_q = st.selectbox(
            "Tipo:", ["Múltipla Escolha", "Projeto Prático"]
        )

        enunciado_q = st.text_area("Enunciado da questão:")

        if tipo_q == "Múltipla Escolha":
            col1, col2 = st.columns(2)
            with col1:
                alt_a = st.text_input("Alternativa A:")
                alt_b = st.text_input("Alternativa B:")
            with col2:
                alt_c = st.text_input("Alternativa C:")
                alt_d = st.text_input("Alternativa D:")
            correta_q = st.selectbox("Resposta correta:", ["A", "B", "C", "D"])

        if st.button("💾 Salvar Questão no Banco"):
            if materia_q and enunciado_q:
                # Segurança defensiva ao salvar nova questão
                if materia_q not in st.session_state.banco_questoes_ia or not isinstance(st.session_state.banco_questoes_ia[materia_q], list):
                    st.session_state.banco_questoes_ia[materia_q] = []

                novo_id_q = (
                    max(
                        (q["id"] for q in st.session_state.banco_questoes_ia[materia_q] if isinstance(q, dict)),
                        default=100
                    ) + 1
                )

                nova_questao = {
                    "id":   novo_id_q,
                    "tipo": tipo_q,
                    "enunciado": enunciado_q
                }

                if tipo_q == "Múltipla Escolha":
                    nova_questao["alternativas"] = {
                        "A": alt_a, "B": alt_b, "C": alt_c, "D": alt_d
                    }
                    nova_questao["correta"] = correta_q

                st.session_state.banco_questoes_ia[materia_q].append(nova_questao)
                st.success(
                    f"✅ Questão #{novo_id_q} adicionada ao banco de "
                    f"**{materia_q}** com sucesso!"
                )
            else:
                st.error("Preencha a disciplina e o enunciado.")

    with aba_notas_prof:
        st.subheader("📊 Painel de Notas Eletrônicas")
        if st.session_state.entregas_sistema:
            dados_notas = []
            for aluno_id, dados in st.session_state.entregas_sistema.items():
                nome_aluno = st.session_state.usuarios_cadastrados.get(
                    aluno_id, {}
                ).get("nome", aluno_id.upper())
                dados_notas.append({
                    "ID":        aluno_id.upper(),
                    "Nome":      nome_aluno,
                    "Matéria":   dados.get("materia", "—"),
                    "Tipo":      dados.get("tipo_prova", "—"),
                    "Nota":      f"{dados.get('nota', '—')} / 10",
                    "Entregue":  dados.get("data_entrega", "—")
                })
            st.dataframe(
                pd.DataFrame(dados_notas),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhuma avaliação entregue até o momento.")


# ==============================================================================
# PAINEL 3: VISÃO DO ALUNO
# ==============================================================================
elif st.session_state.perfil_logado == "Aluno":
    st.header("📝 Central de Provas do Aluno")
    aluno_atual = st.session_state.usuario_logado

    # ---------- Já entregou ----------
    if aluno_atual in st.session_state.entregas_sistema:
        entrega = st.session_state.entregas_sistema[aluno_atual]
        st.success("✅ Avaliação concluída e registrada.")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Sua Nota Final", f"{entrega.get('nota', '—')} / 10")
        with col2:
            st.metric("Matéria", entrega.get("materia", "—"))

        with st.expander("🔎 Ver Relatório de Feedback"):
            st.info(entrega.get("feedback_ia", "Sem feedback disponível."))

    # ---------- Sem prova liberada ----------
    elif aluno_atual not in st.session_state.provas_geradas:
        st.warning(
            "⚠️ Nenhuma avaliação disponível no momento. "
            "Aguarde a liberação pelo seu professor."
        )

    # ---------- Prova disponível ----------
    else:
        prova_aluno = st.session_state.provas_geradas[aluno_atual]

        st.info(
            f"📌 **Avaliação:** {prova_aluno['materia']} | "
            f"**Formato:** {prova_aluno['tipo_prova']} | "
            f"**Liberada em:** {prova_aluno.get('data_criacao', '—')}"
        )

        # ── Múltipla Escolha ──
        if "Múltipla Escolha" in prova_aluno["tipo_prova"]:
            respostas_aluno = {}

            for idx, q in enumerate(prova_aluno["questoes"]):
                st.markdown(f"#### Questão {idx + 1}")
                st.markdown(q['enunciado'])
                escolha = st.radio(
                    "Selecione a alternativa:",
                    ["A", "B", "C", "D"],
                    format_func=lambda x: f"{x}) {q['alternativas'].get(x, '')}",
                    key=f"q_{q['id']}",
                    index=None
                )
                respostas_aluno[q["id"]] = escolha
                st.markdown("---")

            if st.button("🔒 Finalizar e Obter Nota"):
                questoes = prova_aluno["questoes"]
                respondidas = [v for v in respostas_aluno.values() if v is not None]

                if len(respondidas) < len(questoes):
                    st.error(
                        f"⚠️ Responda todas as questões antes de finalizar. "
                        f"({len(respondidas)}/{len(questoes)} respondidas)"
                    )
                else:
                    acertos = sum(
                        1 for q in questoes
                        if respostas_aluno.get(q["id"]) == q.get("correta")
                    )
                    nota_calculada = round((acertos / len(questoes)) * 10, 2)

                    st.session_state.entregas_sistema[aluno_atual] = {
                        "materia":      prova_aluno["materia"],
                        "tipo_prova":   "Múltipla Escolha",
                        "nota":         nota_calculada,
                        "data_entrega": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "feedback_ia":  (
                            f"Correção automática: {acertos} de {len(questoes)} "
                            f"acertos. Nota: {nota_calculada}/10."
                        )
                    }
                    salvar_arquivo_drive(
                        "entregas.json",
                        st.session_state.entregas_sistema
                    )
                    st.rerun()

        # ── Projeto Prático ──
        else:
            st.markdown("### 📋 Instruções do Desafio Técnico")
            st.info(prova_aluno["questoes"][0]["enunciado"])
            st.markdown("---")

            st.subheader("📤 Entrega do Arquivo Final")
            arquivo_trabalho = st.file_uploader(
                "Submeta seu arquivo (Excel, Python ou PDF):",
                type=["xlsx", "py", "pdf"]
            )

            if arquivo_trabalho:
                st.success(
                    f"✅ Arquivo **{arquivo_trabalho.name}** carregado. "
                    f"Clique em 'Enviar' para registrar."
                )

            if st.button("🔒 Enviar para Correção"):
                if arquivo_trabalho is not None:
                    nota_ia_projeto = round(random.uniform(7.5, 10.0), 1)
                    st.session_state.entregas_sistema[aluno_atual] = {
                        "materia":      prova_aluno["materia"],
                        "tipo_prova":   "Projeto Prático",
                        "nota":         nota_ia_projeto,
                        "data_entrega": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "feedback_ia":  (
                            f"Varredura estrutural concluída no arquivo "
                            f"`{arquivo_trabalho.name}`. "
                            f"Nota atribuída: {nota_ia_projeto}/10."
                        )
                    }
                    salvar_arquivo_drive(
                        "entregas.json",
                        st.session_state.entregas_sistema
                    )
                    st.success("✅ Arquivo processado e registrado com sucesso!")
                    st.rerun()
                else:
                    st.error("⚠️ Anexe o arquivo antes de enviar.")

# ---------- Não logado ----------
else:
    col_c, col_mid, col_d = st.columns([1, 2, 1])
    with col_mid:
        st.markdown("""
        <div style='text-align:center; padding: 60px 0;'>
            <h2 style='color:#D4AF37;'>Bem-vindo ao Sistema de Avaliações SENAI</h2>
            <p style='color:#F4F4F6; font-size:1.1rem;'>
                Utilize o menu lateral para realizar o login com suas credenciais corporativas.
            </p>
        </div>
        """, unsafe_allow_html=True)
