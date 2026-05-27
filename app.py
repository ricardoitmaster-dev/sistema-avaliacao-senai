import os
import sys
import json
import random
from datetime import datetime
import streamlit as st
import pandas as pd
import requests
import google.generativeai as genai


def gerar_questoes_ia(
    tema,
    contexto,
    nivel,
    tipo,
    qtd,
    alternativas
):
    """
    Geração inteligente de avaliações SENAI
    com Gemini IA.
    """

    try:

        # ======================================================
        # PROMPT DINÂMICO POR TIPO
        # ======================================================

        if tipo == "Múltipla Escolha":

            prompt = f"""
Você é um professor especialista do SENAI.

Crie {qtd} questões PROFISSIONAIS
de múltipla escolha.

TEMA:
{tema}

CONTEXTO:
{contexto}

NÍVEL:
{nivel}

Quantidade de alternativas:
{alternativas}

REGRAS:

1. Questões reais e técnicas.
2. Nada genérico.
3. Se for Excel Avançado:
- usar PROCV
- PROCX
- SOMASES
- Tabela Dinâmica
- VBA
- cenários empresariais

RETORNE APENAS JSON.

Formato obrigatório:

[
    {{
        "tipo": "multipla_escolha",
        "enunciado": "texto",
        "alternativas": {{
            "A": "texto",
            "B": "texto",
            "C": "texto",
            "D": "texto"
        }},
        "resposta_correta": "A"
    }}
]
"""

        elif tipo == "Dissertativa":

            prompt = f"""
Você é um professor especialista SENAI.

Crie {qtd} questões DISSERTATIVAS.

Tema:
{tema}

Contexto:
{contexto}

Nível:
{nivel}

REGRAS:

1. Questões abertas.
2. Respostas argumentativas.
3. Nível técnico SENAI.
4. Nada genérico.

RETORNE APENAS JSON.

Formato:

[
    {{
        "tipo": "dissertativa",
        "enunciado": "texto da questão",
        "criterios_avaliacao": [
            "critério 1",
            "critério 2"
        ]
    }}
]
"""

        elif tipo == "Estudo de Caso":

            prompt = f"""
Você é um especialista SENAI.

Crie UM estudo de caso aplicado REAL.

Tema:
{tema}

Contexto:
{contexto}

Nível:
{nivel}

REGRAS IMPORTANTES:

1. Criar cenário empresarial real.
2. Problema técnico real.
3. O aluno deve EXECUTAR algo.
4. Pode envolver:
- Excel
- VBA
- SQL
- Redes
- Programação
- Dados

5. Incluir instruções claras.
6. Criar entregáveis.
7. Estilo SENAI profissional.

RETORNE APENAS JSON.

Formato:

[
    {{
        "tipo": "estudo_caso",
        "empresa": "Nome fictício",
        "cenario": "Situação do problema",
        "desafio": "O que deve ser feito",
        "instrucoes": [
            "Passo 1",
            "Passo 2"
        ],
        "entregaveis": [
            "Arquivo Excel",
            "PDF"
        ],
        "criterios_avaliacao": [
            "Precisão",
            "Lógica"
        ]
    }}
]
"""

        elif tipo == "Híbrida":

            prompt = f"""
Você é um professor especialista SENAI.

Crie uma avaliação híbrida.

Tema:
{tema}

Contexto:
{contexto}

Nível:
{nivel}

A prova deve conter:

- questões objetivas
- questões dissertativas
- estudo de caso aplicado

RETORNE APENAS JSON.

Formato:

[
    {{
        "tipo": "multipla_escolha",
        "enunciado": "texto",
        "alternativas": {{
            "A": "texto",
            "B": "texto",
            "C": "texto",
            "D": "texto"
        }},
        "resposta_correta": "A"
    }},
    {{
        "tipo": "dissertativa",
        "enunciado": "texto",
        "criterios_avaliacao": [
            "critério 1"
        ]
    }},
    {{
        "tipo": "estudo_caso",
        "empresa": "empresa fictícia",
        "cenario": "problema",
        "desafio": "atividade"
    }}
]
"""

        else:
            raise Exception(
                f"Tipo de prova inválido: {tipo}"
            )

        # ======================================================
        # GEMINI
        # ======================================================

        resposta = cliente_ia.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        texto = (
            resposta.text.strip()
            if hasattr(resposta, "text")
            else ""
        )

        # limpeza markdown
        texto = (
            texto
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        questoes = json.loads(texto)

        return questoes

    except Exception as e:

        st.error(
            f"Erro ao gerar questões com IA: {e}"
        )

        return [
            {
                "tipo": "erro",
                "enunciado": (
                    "Erro ao gerar avaliação."
                )
            }
        ]

# ==============================================================================
# 1. CONFIGURAÇÃO E CONEXÃO SEGURA AO SUPABASE (SQL NA NUVEM)
# ==============================================================================
SUPABASE_URL = "https://hjtqqshmxpeleywwzgca.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqdHFxc2hteHBlbGV5d3d6Z2NhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0OTY1NDgsImV4cCI6MjA5NTA3MjU0OH0.4v_EyCfUyE2ZEgqOYdnFNZlHVhG8_Quc9otQ7o8Di_s"

# Cabeçalhos padrão para comunicação com a API REST do Supabase
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# ==============================================================================
# 2. CONFIGURAÇÃO GEMINI IA
# ==============================================================================

try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")

    if GEMINI_API_KEY:

        genai.configure(api_key=GEMINI_API_KEY)

        modelo_ia = genai.GenerativeModel(
            "gemini-2.5-flash"
        )

    else:
        modelo_ia = None
        st.warning("Chave Gemini não encontrada.")

except Exception as e:
    modelo_ia = None
    st.warning(f"Erro ao carregar Gemini: {e}")

# Massa de dados padrão master para consistência do sistema (Backup Local Seguro)
USUARIOS_PADRAO = {
    "sn1084433": {
        "nome": "Benedito Ricardo dos Santos",
        "senha": "Celina2610**",
        "perfil": "Gestor/Diretor",
    },
    "sn1220001": {
        "nome": "Professor de Testes SENAI",
        "senha": "122",
        "perfil": "Professor",
    },
    "aluno_ricardo": {"nome": "Ricardo (Aluno)", "senha": "123", "perfil": "Aluno"},
    "aluno_elizandra": {"nome": "Elizandra (Aluna)", "senha": "123", "perfil": "Aluno"},
    "coord_teste": {
        "nome": "Coordenador Técnico",
        "senha": "122",
        "perfil": "Coordenador",
    },
    "sn1220002": {
        "nome": "Elizandra pascoalino",
        "senha": "123",
        "perfil": "Professor",
    },
}


def ler_dados_supabase(tabela):
    """
    Busca os dados do Supabase de forma protegida. Se houver falha de credenciais,
    retorna um dicionário vazio sem travar a renderização das telas do Streamlit.
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/{tabela}?select=*"
        resposta = requests.get(url, headers=HEADERS, timeout=5)

        if resposta.status_code == 200:
            dados_lista = resposta.json()
            if not dados_lista:
                return {}

            resultado = {}
            if tabela == "usuarios":
                for item in dados_lista:
                    u_id = str(item.get("id", "")).strip().lower()
                    if not u_id:
                        continue
                    resultado[u_id] = {
                        "nome": item.get("nome", u_id),
                        "senha": item.get("senha", ""),
                        "perfil": item.get("perfil", "Aluno"),
                    }
                return resultado

            elif tabela in ["provas", "entregas"]:
                for item in dados_lista:
                    aluno_alvo = str(item.get("id_alvo", "")).strip().lower()
                    if not aluno_alvo:
                        continue
                    resultado[aluno_alvo] = {
                        k: v for k, v in item.items() if k != "id_alvo"
                    }
                return resultado
        return {}
    except Exception:
        return {}


def salvar_dados_supabase(tabela, dados):
    """
    Salva dados no Supabase com UPSERT estável
    e exibe erro real caso exista.
    """
    try:
        linhas = []

        if tabela == "usuarios":
            for k, v in dados.items():
                linhas.append(
                    {
                        "id": k,
                        "nome": v["nome"],
                        "senha": v["senha"],
                        "perfil": v["perfil"],
                    }
                )

            chave_conflito = "id"

        elif tabela in ["provas", "entregas"]:
            for k, v in dados.items():
                linha = {"id_alvo": k}
                linha.update(v)
                linhas.append(linha)

            chave_conflito = "id_alvo"

        else:
            return False

        if not linhas:
            return True

        url = f"{SUPABASE_URL}/rest/v1/{tabela}" f"?on_conflict={chave_conflito}"

        headers_upsert = HEADERS.copy()
        headers_upsert["Prefer"] = (
            "resolution=merge-duplicates," "return=representation"
        )

        resposta = requests.post(url, headers=headers_upsert, json=linhas, timeout=15)

        # MOSTRAR O ERRO REAL
        if resposta.status_code not in [200, 201]:
            st.error(f"Erro Supabase ({resposta.status_code}): " f"{resposta.text}")
            return False

        return True

    except Exception as e:
        st.error(f"Erro Python: {str(e)}")
        return False


# ==============================================================================
# 2. CONTROLE DE ESTADO DA SESSÃO E INICIALIZAÇÃO DE VARIÁVEIS
# ==============================================================================
# --- INICIALIZAÇÃO SEGURA DO ESTADO ---
# Garante que as variáveis existam imediatamente
if "loading" not in st.session_state:
    st.session_state.loading = False
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state:
    st.session_state.perfil_logado = None
if "nome_exibicao" not in st.session_state:
    st.session_state.nome_exibicao = None
# --------------------------------------

# Sincronização Dinâmica estável pós-autenticação
if st.session_state.usuario_logado is not None:
    if (
        "usuarios_cadastrados" not in st.session_state
        or not st.session_state.usuarios_cadastrados
    ):
        dados_usuarios = ler_dados_supabase("usuarios")
        st.session_state.usuarios_cadastrados = (
            dados_usuarios if dados_usuarios else USUARIOS_PADRAO
        )
    if "provas_geradas" not in st.session_state:
        st.session_state.provas_geradas = ler_dados_supabase("provas")
    if "entregas_sistema" not in st.session_state:
        st.session_state.entregas_sistema = ler_dados_supabase("entregas")
else:
    st.session_state.usuarios_cadastrados = USUARIOS_PADRAO
    st.session_state.provas_geradas = {}
    st.session_state.entregas_sistema = {}

# ==============================================================================
# 3. INTERFACE VISUAL CORPORATIVA (BMW Portinari Blue, Dourado e Brilhante)
# ==============================================================================
st.set_page_config(page_title="SUATS | SENAI-122", page_icon="🏆", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0F111A;
        color: #F4F4F6;
    }
    [data-testid="stSidebar"] {
        background-color: #161925;
        border-right: 2px solid #D4AF37;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #D4AF37 !important;
    }
    .stButton > button {
        background-color: #D4AF37 !important;
        color: #0F111A !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        border: 1px solid #D4AF37 !important;
    }
    .stTextInput > div > div > input, .stSelectbox > div > div, .stTextArea textarea {
        background-color: #1E2233 !important;
        color: #F4F4F6 !important;
        border: 1px solid #D4AF37 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #D4AF37 !important;
        font-weight: bold;
    }
    div[data-testid="stMetricLabel"] {
        color: #F4F4F6 !important;

Parte 2:

    }
    .css-19v6m80 {
        background-color: #161925 !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 4. PORTAL DE LOGIN / CONTROLE DE ACESSO
# ==============================================================================
if st.session_state.usuario_logado is None:
    st.markdown(
        "<h2 style='text-align:center;'>🔐 SUATS | Portal de Acesso</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;'>Insira suas credenciais corporativas SENAI para acessar a plataforma.</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u_in = st.text_input("Login Corporativo (Ex: snXXXXXXX):").strip().lower()
        s_in = st.text_input("Senha de Acesso:", type="password").strip()

        if st.button("🔓 Autenticar no Sistema"):
            dados_drive = ler_dados_supabase("usuarios")

            # Mecanismo de contingência local estruturado
            user_data = dados_drive.get(u_in) if dados_drive else None
            if not user_data and u_in in USUARIOS_PADRAO:
                user_data = USUARIOS_PADRAO[u_in]

            # Comparação de senha corrigida com .strip()
            if user_data and str(user_data.get("senha", "")).strip() == s_in:
                st.session_state.usuario_logado = u_in
                st.session_state.perfil_logado = user_data["perfil"]
                st.session_state.nome_exibicao = user_data.get("nome", u_in)

                if dados_drive:
                    st.session_state.usuarios_cadastrados = dados_drive
                else:
                    st.session_state.usuarios_cadastrados = USUARIOS_PADRAO
                    salvar_dados_supabase("usuarios", USUARIOS_PADRAO)

                st.session_state.provas_geradas = ler_dados_supabase("provas")
                st.session_state.entregas_sistema = ler_dados_supabase("entregas")
                st.rerun()
            else:
                st.error(
                    "Login ou senha incorretos. Por favor verifique suas credenciais corporativas."
                )
else:
    # DEFINIÇÃO DOS MENUS DE ACESSO CONFORME PERFIL DOCENTE / DISCENTE / GESTOR
    opcao_menu = None

    with st.sidebar:
        st.markdown(
            f"<h3 style='text-align:center;'>🏆 SENAI-122</h3>", unsafe_allow_html=True
        )
        st.write(f"Conectado: **{st.session_state.nome_exibicao}**")
        st.write(f"Perfil: *{st.session_state.perfil_logado}*")
        st.write("---")

        if st.session_state.perfil_logado == "Gestor/Diretor":
            opcao_menu = st.radio(
                "Menu de Navegação",
                [
                    "🏠 Dashboard Geral",
                    "👥 Usuários",
                    "🏫 Turmas",
                    "👨‍🏫 Professores",
                    "📝 Avaliações",
                    "📊 Analytics",
                    "📁 Relatórios",
                    "🛡 Auditoria",
                    "⚙ Configurações",
                ],
            )
        elif st.session_state.perfil_logado == "Professor":
            opcao_menu = st.radio(
                "Menu de Navegação",
                [
                    "🏠 Dashboard",
                    "➕ Criar Avaliação",
                    "📚 Banco de Questões",
                    "📝 Avaliações Ativas",
                    "📤 Entregas",
                    "📊 Relatórios",
                    "⚙ Configurações",
                ],
            )
        elif st.session_state.perfil_logado == "Aluno":
            opcao_menu = st.radio(
                "Menu de Navegação",
                [
                    "🏠 Início",
                    "📝 Minhas Avaliações",
                    "📥 Downloads",
                    "📤 Upload",
                    "📈 Histórico",
                    "💬 Feedbacks",
                ],
            )
        elif st.session_state.perfil_logado == "Coordenador":
            opcao_menu = st.radio(
                "Menu de Navegação",
                ["🏠 Dashboard", "🏫 Turmas", "📊 Analytics", "📁 Relatórios"],
            )

        st.write("---")
        if st.button("🚪 Encerrar Sessão"):
            st.session_state.usuario_logado = None
            st.session_state.perfil_logado = None
            st.session_state.nome_exibicao = None
            st.rerun()

    st.title(f"Sistema Unificado de Avaliações Técnicas (SUATS)")
    st.markdown(f"**Navegação Ativa:** {opcao_menu}")
    st.markdown("---")

    # segurança contra perfil inválido
    if opcao_menu is None:
        opcao_menu = "🏠 Início"

    # ==============================================================================
    # 5. MÓDULO EXECUTIVO - GESTOR / DIRETOR
    # ==============================================================================
    if st.session_state.perfil_logado == "Gestor/Diretor":

        if "🏠 Dashboard Geral" in opcao_menu:
            df_users = pd.DataFrame(
                [
                    {"id": k, **v}
                    for k, v in st.session_state.usuarios_cadastrados.items()
                ]
            )
            total_alunos = (
                len(df_users[df_users["perfil"] == "Aluno"])
                if not df_users.empty
                else 0
            )
            total_profs = (
                len(df_users[df_users["perfil"] == "Professor"])
                if not df_users.empty
                else 0
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Alunos Cadastrados", f"{total_alunos}")
            c2.metric("Corpo Docente", f"{total_profs}")
            c3.metric("Provas em Aberto", f"{len(st.session_state.provas_geradas)}")
            c4.metric(
                "Entregas Realizadas", f"{len(st.session_state.entregas_sistema)}"
            )

            st.write("---")
            st.subheader("👁️ Monitoramento de Exames Real-Time")

            if len(st.session_state.entregas_sistema) > 0:
                dados_entregas = []
                for aluno, info in st.session_state.entregas_sistema.items():
                    nome_completo = st.session_state.usuarios_cadastrados.get(
                        aluno, {}
                    ).get("nome", aluno)
                    dados_entregas.append(
                        {
                            "Matrícula Aluno": aluno,
                            "Nome Completo": nome_completo,
                            "Exame/Disciplina": info.get("materia", "Não informada"),
                            "Data/Hora de Envio": info.get("data_entrega", "-"),
                            "Status do Envio": info.get("status", "Enviado"),
                        }
                    )
                st.dataframe(
                    pd.DataFrame(dados_entregas),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(
                    "Nenhuma atividade de entrega registrada em nuvem até o momento."
                )

        elif "👥 Usuários" in opcao_menu:
            st.subheader("👤 Gerenciamento de Usuários")
            col_form, col_lista = st.columns([1, 2])

            with col_form:
                st.markdown("### Vincular Novo Usuário")
                # Utilizando st.form para limpar campos automaticamente após envio
                with st.form("form_novo_usuario", clear_on_submit=True):
                    novo_id = st.text_input("Login Corporativo:").strip().lower()
                    novo_nome = st.text_input("Nome Completo:")
                    nova_senha = st.text_input(
                        "Senha Corporativa:", type="password"
                    ).strip()
                    novo_perfil = st.selectbox(
                        "Perfil de Acesso:",
                        ["Aluno", "Professor", "Coordenador", "Gestor/Diretor"],
                    )

                    submit_button = st.form_submit_button("Salvar Usuário")

                    if submit_button:
                        if novo_id and novo_nome and nova_senha:
                            # Prepara dicionário temporário apenas com este usuário
                            novo_usuario_dict = {
                                novo_id: {
                                    "nome": novo_nome,
                                    "senha": nova_senha,
                                    "perfil": novo_perfil,
                                }
                            }

                            # Tenta salvar no Supabase
                            if salvar_dados_supabase("usuarios", novo_usuario_dict):
                                # Atualiza estado local apenas se salvou com sucesso
                                st.session_state.usuarios_cadastrados[novo_id] = (
                                    novo_usuario_dict[novo_id]
                                )
                                st.success(
                                    f"Usuário '{novo_id}' cadastrado com sucesso!"
                                )
                                st.rerun()  # Atualiza a tabela
                            else:
                                st.error(
                                    "Erro ao salvar no banco de dados. Verifique a conexão."
                                )
                        else:
                            st.error("Preencha todos os campos.")

            with col_lista:
                st.markdown("### Base Registrada")
                df_exibicao = pd.DataFrame(
                    [
                        {"ID": k, "Nome": v["nome"], "Perfil": v["perfil"]}
                        for k, v in st.session_state.usuarios_cadastrados.items()
                    ]
                )
                st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

        elif "🏫 Turmas" in opcao_menu:
            st.subheader("🏫 Painel Coletivo de Turmas")
            if len(st.session_state.provas_geradas) > 0:
                df_provas = pd.DataFrame(st.session_state.provas_geradas.values())
                if "turma" in df_provas.columns:
                    turmas_detectadas = df_provas["turma"].unique()
                    st.write(
                        f"Turmas Ativas no Ciclo Corrente: **{', '.join(turmas_detectadas)}**"
                    )
                    st.dataframe(
                        df_provas[["turma", "materia", "curso"]].drop_duplicates(),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Nenhuma turma ativa vinculada no momento.")
            else:
                st.info("Aguardando criação de exames pelos docentes.")

        elif "👨‍🏫 Professores" in opcao_menu:
            st.subheader("👨‍🏫 Alocação e Atividades Docentes")
            df_users = pd.DataFrame(
                [
                    {"id": k, **v}
                    for k, v in st.session_state.usuarios_cadastrados.items()
                ]
            )
            if not df_users.empty:
                df_profs = df_users[df_users["perfil"] == "Professor"]
                st.dataframe(
                    df_profs[["id", "nome"]], use_container_width=True, hide_index=True
                )

        elif "📝 Avaliações" in opcao_menu:
            st.subheader("📝 Repositório Geral de Exames")
            if len(st.session_state.provas_geradas) > 0:
                df_provas_gerais = pd.DataFrame(
                    [
                        {"Vínculo": k, **v}
                        for k, v in st.session_state.provas_geradas.items()
                    ]
                )
                st.dataframe(
                    df_provas_gerais, use_container_width=True, hide_index=True
                )
            else:
                st.info("Nenhum exame cadastrado no sistema.")

        elif "📊 Analytics" in opcao_menu:
            st.subheader("📊 Relatórios e Indicadores Críticos")
            st.markdown(
                f"- **Volume de Cadastros Totais:** {len(st.session_state.usuarios_cadastrados)}"
            )
            st.markdown(
                f"- **Provas Disponibilizadas:** {len(st.session_state.provas_geradas)}"
            )
            st.markdown(
                f"- **Taxa de Conclusão Global:** {len(st.session_state.entregas_sistema)} entregas efetuadas."
            )

        elif "📁 Relatórios" in opcao_menu:
            st.subheader("📁 Exportação de Dados")
            df_export = pd.DataFrame(
                [
                    {"ID": k, "Nome": v["nome"], "Perfil": v["perfil"]}
                    for k, v in st.session_state.usuarios_cadastrados.items()
                ]
            )
            csv = df_export.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Exportar Lista de Usuários (CSV)",
                csv,
                "usuarios_suats.csv",
                "text/csv",
            )

        elif "🛡 Auditoria" in opcao_menu:
            st.subheader("🛡 Logs de Segurança e Auditoria")
            st.code(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Usuário {st.session_state.usuario_logado} carregou o painel administrativo master."
            )

        elif "⚙ Configurações" in opcao_menu:
            st.subheader("⚙ Configurações Gerais do Sistema")
            st.write(
                f"Banco de Dados Ativo: **Supabase Cloud Relational (PostgreSQL)**"
            )
            st.write(f"Endpoint Conexão: {SUPABASE_URL}")

    # ==============================================================================
    # 6. MÓDULO PEDAGÓGICO - PROFESSOR
    # ==============================================================================
    elif st.session_state.perfil_logado == "Professor":
        if "🏠 Dashboard" in opcao_menu:
            st.subheader("📊 Painel de Controle Geral do Docente")
            st.write(
                "Acompanhe o status das avaliações e entregas feitas pelos alunos na nuvem."
            )
            c1, c2 = st.columns(2)
            c1.metric("Provas Criadas por Você", len(st.session_state.provas_geradas))
            c2.metric(
                "Entregas Prontas para Correção", len(st.session_state.entregas_sistema)
            )

        elif "➕ Criar Avaliação" in opcao_menu:

            st.subheader("⚙️ Wizard Profissional de Criação de Exames")

            # ==========================================================
            # ETAPA 1 — IDENTIFICAÇÃO
            # ==========================================================
            st.markdown("##### **Etapa 1: Informações de Identificação da Disciplina**")

            col1, col2 = st.columns(2)

            with col1:
                area = (
                    st.text_input(
                        "Área Técnica:",
                        "METALMECÂNICA / TI"
                    ).strip().upper()
                )

                curso = (
                    st.text_input(
                        "Nome do Curso:",
                        "TÉCNICO EM INFORMÁTICA"
                    ).strip().upper()
                )

                materia = (
                    st.text_input(
                        "Componente Curricular (Disciplina):"
                    ).strip().upper()
                )

            with col2:
                turma = (
                    st.text_input(
                        "Identificador da Turma (Ex: 1TIND):"
                    ).strip().upper()
                )

                unidade = (
                    st.text_input(
                        "Unidade Escolar SENAI:",
                        "SENAI-122 GUARULHOS"
                    ).strip().upper()
                )

            st.markdown("---")

            # ==========================================================
            # ETAPA 2 — MODELO DE AVALIAÇÃO
            # ==========================================================
            st.markdown("##### **Etapa 2: Modelo Pedagógico da Avaliação**")

            tipo_prova = st.selectbox(
                "Selecione o modelo:",
                [
                    "Múltiplas Escolhas Estruturadas",
                    "Dissertativa Completa",
                    "Estudo de Caso Aplicado",
                    "Avaliação Híbrida",
                ],
            )

            st.markdown("---")

            # ==========================================================
            # ETAPA 3 — CONFIGURAÇÕES GERAIS
            # ==========================================================
            st.markdown("##### **Etapa 3: Configuração Geral**")

            origem_questoes = st.selectbox(
                "Origem das questões:",
                [
                    "Sistema Automático",
                    "Banco de Questões",
                    "IA (Gemini Contextualizada)",
                ],
            )

            nivel_dificuldade = st.selectbox(
                "Nível de dificuldade:",
                ["Básico", "Intermediário", "Avançado"]
            )

            usar_ia = st.radio(
                "Modo de criação:",
                [
                    "IA (Automático)",
                    "Manual (Professor criará depois)"
                ]
            )

            st.markdown("---")

            # ==========================================================
            # ETAPA 4 — CONFIGURAÇÃO DINÂMICA
            # ==========================================================
            st.markdown("##### **Etapa 4: Configuração Técnica da Avaliação**")

            tipo_questao = ""
            num_alternativas = 0

            # ----------------------------------------------------------
            # MÚLTIPLA ESCOLHA
            # ----------------------------------------------------------
            if tipo_prova == "Múltiplas Escolhas Estruturadas":

                tipo_questao = "Múltipla Escolha"

                num_questoes = st.number_input(
                    "Número de questões:",
                    min_value=1,
                    max_value=30,
                    value=10
                )

                num_alternativas = st.selectbox(
                    "Número de alternativas:",
                    [2, 3, 4, 5],
                    index=2
                )

                params_formulas = st.text_area(
                    "Funções/Conteúdos obrigatórios:"
                )

                st.info(
                    "A IA irá gerar questões objetivas "
                    "com alternativas e gabarito."
                )

            # ----------------------------------------------------------
            # DISSERTATIVA
            # ----------------------------------------------------------
            elif tipo_prova == "Dissertativa Completa":

                tipo_questao = "Dissertativa"

                num_questoes = st.number_input(
                    "Número de questões dissertativas:",
                    min_value=1,
                    max_value=20,
                    value=5
                )

                params_formulas = st.text_area(
                    "Competências e conteúdos obrigatórios:"
                )

                st.info(
                    "A IA irá gerar perguntas abertas "
                    "com resposta discursiva."
                )

            # ----------------------------------------------------------
            # ESTUDO DE CASO
            # ----------------------------------------------------------
            elif tipo_prova == "Estudo de Caso Aplicado":

                tipo_questao = "Estudo de Caso"

                num_questoes = 1

                contexto_empresa = st.text_input(
                    "Empresa/Cenário (Opcional):"
                )

                params_formulas = st.text_area(
                    "Tecnologias obrigatórias "
                    "(Excel, PROCX, VBA, SQL, Redes etc.):"
                )

                entregavel = st.multiselect(
                    "Entregáveis do aluno:",
                    [
                        "Arquivo Excel",
                        "PDF",
                        "Documento Word",
                        "Código Fonte",
                        "Relatório Técnico",
                    ],
                    default=["Arquivo Excel"]
                )

                st.success(
                    "A IA irá gerar um estudo de caso "
                    "profissional baseado em cenário real."
                )

            # ----------------------------------------------------------
            # HÍBRIDA
            # ----------------------------------------------------------
            elif tipo_prova == "Avaliação Híbrida":

                tipo_questao = "Híbrida"

                qtd_objetivas = st.number_input(
                    "Quantidade de objetivas:",
                    min_value=1,
                    max_value=20,
                    value=5
                )

                qtd_dissertativas = st.number_input(
                    "Quantidade de dissertativas:",
                    min_value=1,
                    max_value=20,
                    value=3
                )

                incluir_estudo = st.checkbox(
                    "Incluir Estudo de Caso Aplicado",
                    value=True
                )

                num_alternativas = st.selectbox(
                    "Alternativas das objetivas:",
                    [2, 3, 4, 5],
                    index=2
                )

                params_formulas = st.text_area(
                    "Conteúdos obrigatórios:"
                )

                num_questoes = (
                    qtd_objetivas +
                    qtd_dissertativas
                )

                if incluir_estudo:
                    num_questoes += 1

                st.success(
                    "A IA irá gerar uma prova completa "
                    "com múltipla escolha + dissertativa "
                    "+ estudo de caso."
                )

            st.markdown("---")

            # ==========================================================
            # ETAPA 5 — ALUNO ALVO
            # ==========================================================
            st.markdown("##### **Etapa 5: Vinculação do Discente**")

            lista_alunos = [
                k
                for k, v in st.session_state.usuarios_cadastrados.items()
                if v["perfil"] == "Aluno"
            ]

            aluno_alvo = st.selectbox(
                "Liberar acesso exclusivo para:",
                lista_alunos
                if lista_alunos
                else ["Nenhum aluno cadastrado"]
            )

            st.markdown("---")

            # ==========================================================
            # ETAPA 6 — IA
            # ==========================================================
            st.markdown("##### 🤖 Geração com Inteligência Artificial")

            tema_prova = None
            contexto_prova = None

            if usar_ia == "IA (Automático)":

                tema_prova = st.text_input(
                    "Tema central da avaliação:"
                )

                contexto_prova = st.text_area(
                    "Contexto pedagógico adicional:"
                )

            st.info(
                "A avaliação será criada "
                "automaticamente pela IA."
            )

            # ==========================================================
            # BOTÃO GERAR
            # ==========================================================
            if st.button(
                "🚀 Finalizar, Gerar e Liberar Prova",
                disabled=st.session_state.loading
            ):

                if not materia:
                    st.warning(
                        "Por favor, informe a disciplina."
                    )

                elif aluno_alvo == "Nenhum aluno cadastrado":
                    st.warning(
                        "Nenhum aluno disponível."
                    )

                else:

                    st.session_state.loading = True

                    questoes_geradas = gerar_questoes_ia(
                        tema_prova,
                        contexto_prova,
                        nivel_dificuldade,
                        tipo_questao,
                        num_questoes,
                        num_alternativas,
                    )

                    prova_nova = {
                        "questoes": questoes_geradas,
                        "area": area,
                        "curso": curso,
                        "materia": materia,
                        "turma": turma,
                        "unidade": unidade,
                        "tipo_prova": tipo_prova,
                        "tipo_questao": tipo_questao,
                        "origem_questoes": origem_questoes,
                        "nivel_dificuldade": nivel_dificuldade,
                        "num_questoes": num_questoes,
                        "num_alternativas": num_alternativas,
                        "parametros": params_formulas,
                        "status": "Liberada",
                        "data_criacao": datetime.now().strftime("%d/%m/%Y"),
                    }

                    st.session_state.provas_geradas[
                        aluno_alvo
                    ] = prova_nova

                    prova_individual = {
                        aluno_alvo: prova_nova
                    }

                    with st.spinner(
                        "Salvando avaliação..."
                    ):
                        resultado = salvar_dados_supabase(
                            "provas",
                            prova_individual
                        )

                    st.session_state.loading = False

                    if resultado:

                        st.success(
                            f"✅ Avaliação liberada "
                            f"com sucesso para "
                            f"{aluno_alvo}"
                        )

                        st.session_state.provas_geradas = (
                            ler_dados_supabase("provas")
                        )

                    else:
                        st.error(
                            "❌ Erro ao salvar "
                            "no Supabase."
                        )
        elif "📚 Banco de Questões" in opcao_menu:
            st.subheader("📚 Banco de Questões Integrado")
            st.info(
                "Módulo em sincronia contínua. Permite resgatar itens avaliativos pré-configurados da matriz SENAI."
            )

        elif "📝 Avaliações Ativas" in opcao_menu:
            st.subheader("📝 Monitoramento de Avaliações Ativas")
            if len(st.session_state.provas_geradas) > 0:
                df_ativas = pd.DataFrame(
                    [
                        {"Matrícula": k, **v}
                        for k, v in st.session_state.provas_geradas.items()
                    ]
                )
                st.dataframe(df_ativas, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma avaliação ativa encontrada no banco de dados.")

        elif "📤 Entregas" in opcao_menu:
            st.subheader("📥 Arquivo de Entregas Realizadas pelos Alunos")
            if len(st.session_state.entregas_sistema) > 0:
                dados_completos = []
                for aluno, info in st.session_state.entregas_sistema.items():
                    dados_completos.append(
                        {
                            "Aluno ID": aluno,
                            "Disciplina": info.get("materia", "Não informada"),
                            "Data do Envio": info.get("data_entrega", "-"),
                            "Status": info.get("status", "Enviado"),
                            "Nota Atribuída": info.get("nota", 0.0),
                        }
                    )
                st.dataframe(
                    pd.DataFrame(dados_completos), use_container_width=True, hide_index=True
                )
            else:
                st.info("Nenhuma entrega feita pelos alunos até o momento.")

        elif "📊 Relatórios" in opcao_menu or "⚙ Configurações" in opcao_menu:
            st.info(
                "Utilize as opções principais do menu para interagir com a base operacional."
            )

    # ==============================================================================
    # 7. MÓDULO DISCENTE - ALUNO
    # ==============================================================================
    elif st.session_state.perfil_logado == "Aluno":
        aluno_atual = st.session_state.usuario_logado

        if "🏠 Início" in opcao_menu:
            st.subheader("🚀 Central do Aluno")
            st.write(
                f"Bem-vindo, **{st.session_state.nome_exibicao}**! Use o menu lateral para acessar suas avaliações."
            )

        elif "📝 Minhas Avaliações" in opcao_menu:
            if aluno_atual in st.session_state.entregas_sistema:
                st.success(
                    "✅ Avaliação realizada e entregue com sucesso para processamento docente!"
                )
                st.write("Dados da sua entrega:")
                st.json(st.session_state.entregas_sistema[aluno_atual])
            elif aluno_atual not in st.session_state.provas_geradas:
                st.warning(
                    "⚠️ Nenhuma avaliação disponível para o seu usuário neste momento. Aguarde liberação."
                )
            else:
                prova = st.session_state.provas_geradas[aluno_atual]
                respostas_aluno = st.session_state.get("respostas_aluno", [])
                st.info(
                    f"📋 Avaliação: {prova['materia']} | Tipo: {prova['tipo_prova']}"
                )

                st.markdown("## 🧪 Prova Online")

                respostas_aluno = []

                for i, q in enumerate(prova["questoes"]):
                    st.markdown(f"### Questão {i+1}")
                    st.write(q["enunciado"])

                    alternativas = list(q["alternativas"].keys())

                    resposta = st.radio(
                        f"Escolha sua resposta - Q{i+1}",
                        alternativas,
                        index=None,
                        key=f"q_{i}",
                    )

                    respostas_aluno.append(resposta)

                st.markdown("---")
                st.markdown("#### 📤 Finalização da Prova")
                arquivo_submetido = st.file_uploader(
                    "Arraste e solte o arquivo da sua prova resolvida aqui (Excel, PDF ou TXT):",
                    type=["txt", "xlsx", "pdf"],
                )

                if arquivo_submetido is not None:
                    if st.button("Finalizar e Enviar Avaliação Definitiva"):

                        # 1. Salva entrega do aluno
                        st.session_state.entregas_sistema[aluno_atual] = {
                            "materia": prova["materia"],
                            "status": "Enviado",
                            "data_entrega": datetime.now().strftime(
                                "%d/%m/%Y %H:%M:%S"
                            ),
                            "arquivo_nome": arquivo_submetido.name,
                        }

                        # 2. CORREÇÃO AUTOMÁTICA
                        st.markdown("### 🤖 Corrigindo prova...")

                        prova = st.session_state.provas_geradas[aluno_atual]

                        acertos = 0
                        feedback = []

                        for i, q in enumerate(prova["questoes"]):
                            resposta_aluno = respostas_aluno[i]
                            resposta_correta = q.get("resposta_correta")

                            if resposta_aluno == resposta_correta:
                                acertos += 1
                                feedback.append(f"✔ Questão {i+1}: Correta")
                            else:
                                feedback.append(f"❌ Questão {i+1}: Errada")

                        nota_final = round((acertos / len(prova["questoes"])) * 10, 2)

                        # 3. salva nota
                        st.session_state.entregas_sistema[aluno_atual][
                            "nota"
                        ] = nota_final
                        st.session_state.entregas_sistema[aluno_atual][
                            "feedback"
                        ] = feedback

                        # 4. salva no banco
                        if salvar_dados_supabase(
                            "entregas", st.session_state.entregas_sistema
                        ):
                            st.success(f"Nota final: {nota_final}")
                            st.rerun()

        elif opcao_menu in [
            "📥 Downloads",
            "📤 Upload",
            "📈 Histórico",
            "💬 Feedbacks",
        ]:
            st.info(
                "Acesse a aba 'Minhas Avaliações' para interagir com os arquivos de exames liberados."
            )

    # ======================================================================
    # 8. MÓDULO COMPLEMENTAR - COORDENADOR
    # ======================================================================
    elif st.session_state.perfil_logado == "Coordenador":
        if "🏠 Dashboard" in opcao_menu:
            st.subheader("📊 Painel de Acompanhamento Pedagógico (Coordenação)")
            if len(st.session_state.provas_geradas) > 0:
                df_coord = pd.DataFrame(
                    [
                        {"Aluno ID": k, **v}
                        for k, v in st.session_state.provas_geradas.items()
                    ]
                )
                st.dataframe(df_coord, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum dado de avaliação disponível para monitoramento.")
        else:
            st.info("Navegue utilizando os menus ativos da coordenação técnica.")

    st.markdown("---")
    st.write("Backup estável - SUATS funcional com Supabase")
