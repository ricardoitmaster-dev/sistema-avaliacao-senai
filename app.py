import os
import sys
import json
import subprocess
from datetime import datetime
import streamlit as st
import pandas as pd

# ==============================================================================
# 1. INSTALAÇÃO AUTOMÁTICA DE DEPENDÊNCIAS
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
# 2. CONFIGURAÇÃO DE ACESSO AO GOOGLE DRIVE EM NUVEM
# ==============================================================================
ID_PASTA_DRIVE = "1-bHDGxbJDWTzT30zL9S-oj0ktM-c60_R"
SCOPES = ['https://www.googleapis.com/auth/drive']

def sanitizar_chave_pem(chave_raw: str) -> str:
    """Reconstrói rigorosamente o bloco PEM removendo ruídos de colagem."""
    chave = str(chave_raw).strip()
    chave = chave.replace('\\n', '\n').replace('\r', '')
    marcador_inicio = "-----BEGIN PRIVATE KEY-----"
    marcador_fim = "-----END PRIVATE KEY-----"
    if marcador_inicio in chave and marcador_fim in chave:
        corpo = chave.split(marcador_inicio)[1].split(marcador_fim)[0]
        corpo_puro = "".join(corpo.split())
        linhas_64 = [corpo_puro[i:i+64] for i in range(0, len(corpo_puro), 64)]
        return f"{marcador_inicio}\n" + "\n".join(linhas_64) + f"\n{marcador_fim}\n"
    return chave

def obter_servico_drive():
    """Conecta de forma segura garantindo que os Secrets existam."""
    if "gdrive" in st.secrets:
        try:
            info_chaves = dict(st.secrets["gdrive"])
            if "private_key" in info_chaves:
                info_chaves["private_key"] = sanitizar_chave_pem(info_chaves["private_key"])
            credenciais = service_account.Credentials.from_service_account_info(info_chaves, scopes=SCOPES)
            return build('drive', 'v3', credentials=credenciais, cache_discovery=False)
        except Exception:
            # Silencia o erro visual na inicialização para não quebrar a tela de login
            return None
    return None

def ler_arquivo_drive(nome_arquivo, dados_padrao):
    try:
        drive_service = obter_servico_drive()
        if drive_service is None:
            return dados_padrao
        query = f"name = '{nome_arquivo}' and '{ID_PASTA_DRIVE}' in parents and trashed = false"
        resultados = drive_service.files().list(q=query, fields="files(id)").execute()
        files = resultados.get('files', [])
        if not files:
            return dados_padrao
        file_id = files[0]['id']
        conteudo = drive_service.files().get_media(fileId=file_id).execute()
        return json.loads(conteudo.decode('utf-8'))
    except Exception:
        return dados_padrao

def salvar_arquivo_drive(nome_arquivo, dados):
    try:
        drive_service = obter_servico_drive()
        if drive_service is None:
            return
        json_dados = json.dumps(dados, indent=4, ensure_ascii=False)
        query = f"name = '{nome_arquivo}' and '{ID_PASTA_DRIVE}' in parents and trashed = false"
        resultados = drive_service.files().list(q=query, fields="files(id)").execute()
        files = resultados.get('files', [])
        media = MediaInMemoryUpload(json_dados.encode('utf-8'), mimetype='application/json')
        if files:
            drive_service.files().update(fileId=files[0]['id'], media_body=media).execute()
        else:
            drive_service.files().create(body={'name': nome_arquivo, 'parents': [ID_PASTA_DRIVE]}, media_body=media).execute()
    except Exception:
        pass

# ==============================================================================
# 3. CONTROLE DE ESTADO DA SESSÃO (Garantia Pós-F5)
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
if 'perfil_logado' not in st.session_state:
    st.session_state.perfil_logado = None
if 'nome_exibicao' not in st.session_state:
    st.session_state.nome_exibicao = None

# Carga sob demanda: Só busca do Drive se o usuário já estiver autenticado
if st.session_state.usuario_logado is not None:
    if 'usuarios_cadastrados' not in st.session_state:
        st.session_state.usuarios_cadastrados = ler_arquivo_drive("usuarios.json", USUARIOS_PADRAO)
    if 'provas_geradas' not in st.session_state:
        st.session_state.provas_geradas = ler_arquivo_drive("provas.json", {})
    if 'entregas_sistema' not in st.session_state:
        st.session_state.entregas_sistema = ler_arquivo_drive("entregas.json", {})
else:
    # Se deslogado, mantém apenas a memória padrão local para o ecossistema de login operar limpo
    st.session_state.usuarios_cadastrados = USUARIOS_PADRAO
    st.session_state.provas_geradas = {}
    st.session_state.entregas_sistema = {}

# ==============================================================================
# 4. INTERFACE VISUAL (BMW Portinari Blue, Dourado e Dark Mode)
# ==============================================================================
st.set_page_config(page_title="SUATS | SENAI-122", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #0F111A;
        color: #F4F4F6;
    }
    [data-testid="stSidebar"] {
        background-color: #161925;
        border-right: 2px solid #D4AF37;
    }
    h1, h2, h3 {
        color: #D4AF37 !important;
    }
    .stButton > button {
        background-color: #D4AF37 !important;
        color: #0F111A !important;
        font-weight: bold !important;
        border-radius: 6px !important;
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
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 5. PORTAL DE LOGIN / NAVEGAÇÃO
# ==============================================================================
if st.session_state.usuario_logado is None:
    st.markdown("<h2 style='text-align:center;'>🔐 SUATS | Portal de Acesso</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Insira suas credenciais corporativas SENAI para acessar a plataforma.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u_in = st.text_input("Login Corporativo:").strip().lower()
        s_in = st.text_input("Senha:", type="password")
        
        if st.button("🔓 Autenticar no Sistema"):
            # Primeiro, tenta puxar do Drive para verificar se há novos cadastros salvos lá antes de validar
            dados_drive = ler_arquivo_drive("usuarios.json", USUARIOS_PADRAO)
            user_data = dados_drive.get(u_in)
            
            if user_data and user_data["senha"] == s_in:
                st.session_state.usuario_logado = u_in
                st.session_state.perfil_logado = user_data["perfil"]
                st.session_state.nome_exibicao = user_data.get("nome", u_in)
                # Força a carga completa dos dados pós-autenticação bem-sucedida
                st.session_state.usuarios_cadastrados = dados_drive
                st.session_state.provas_geradas = ler_arquivo_drive("provas.json", {})
                st.session_state.entregas_sistema = ler_arquivo_drive("entregas.json", {})
                st.rerun()
            else:
                st.error("Login ou senha incorretos.")
else:
    with st.sidebar:
        st.markdown(f"<h3 style='text-align:center;'>🏆 SENAI-122</h3>", unsafe_allow_html=True)
        st.write(f"Conectado: **{st.session_state.nome_exibicao}**")
        st.write(f"Perfil: *{st.session_state.perfil_logado}*")
        st.write("---")
        
        if st.session_state.perfil_logado == "Gestor/Diretor":
            opcao_menu = st.radio("Menu", [
                "🏠 Dashboard Geral", "👥 Usuários", "🏫 Turmas", "👨‍🏫 Professores", 
                "📝 Avaliações", "📊 Analytics", "📁 Relatórios", "🛡 Auditoria", "⚙ Configurações"
            ])
        elif st.session_state.perfil_logado == "Professor":
            opcao_menu = st.radio("Menu", [
                "🏠 Dashboard", "➕ Criar Avaliação", "📚 Banco de Questões", 
                "📝 Avaliações Ativas", "📤 Entregas", "📊 Relatórios", "⚙ Configurações"
            ])
        elif st.session_state.perfil_logado == "Aluno":
            opcao_menu = st.radio("Menu", [
                "🏠 Início", "📝 Minhas Avaliações", "📥 Downloads", "📤 Upload", "📈 Histórico", "💬 Feedbacks"
            ])
        elif st.session_state.perfil_logado == "Coordenador":
            opcao_menu = st.radio("Menu", [
                "🏠 Dashboard", "🏫 Turmas", "📊 Analytics", "📁 Relatórios"
            ])
            
        st.write("---")
        if st.button("🚪 Encerrar Sessão"):
            st.session_state.usuario_logado = None
            st.session_state.perfil_logado = None
            st.session_state.nome_exibicao = None
            st.rerun()

    st.title(f"Sistema Unificado de Avaliações Técnicas (SUATS)")
    st.markdown(f"**Navegação Ativa:** {opcao_menu}")
    st.markdown("---")

    # ==============================================================================
    # RENDERIZAÇÃO DAS ÁREAS DE TRABALHO - GESTOR
    # ==============================================================================
    if st.session_state.perfil_logado == "Gestor/Diretor":
        
        if "🏠 Dashboard Geral" in opcao_menu:
            df_users = pd.DataFrame([{"id": k, **v} for k, v in st.session_state.usuarios_cadastrados.items()])
            total_alunos = len(df_users[df_users['perfil'] == 'Aluno']) if not df_users.empty else 0
            total_profs = len(df_users[df_users['perfil'] == 'Professor']) if not df_users.empty else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Alunos Cadastrados", f"{total_alunos}")
            c2.metric("Corpo Docente", f"{total_profs}")
            c3.metric("Provas em Aberto", f"{len(st.session_state.provas_geradas)}")
            c4.metric("Entregas Realizadas", f"{len(st.session_state.entregas_sistema)}")
            
            st.write("---")
            st.subheader("👁️ Monitoramento de Exames Real-Time")
            
            if len(st.session_state.entregas_sistema) > 0:
                dados_entregas = []
                for aluno, info in st.session_state.entregas_sistema.items():
                    nome_completo = st.session_state.usuarios_cadastrados.get(aluno, {}).get("nome", aluno)
                    dados_entregas.append({
                        "Matrícula Aluno": aluno,
                        "Nome Completo": nome_completo,
                        "Exame/Disciplina": info.get("materia", "Não informada"),
                        "Data/Hora de Envio": info.get("data_entrega", "-"),
                        "Status do Envio": info.get("status", "Enviado")
                    })
                st.dataframe(pd.DataFrame(dados_entregas), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma atividade de entrega registrada no banco de dados em nuvem até o momento.")
            
        elif "👥 Usuários" in opcao_menu:
            st.subheader("👤 Gerenciamento de Usuários")
            col_form, col_lista = st.columns([1, 2])
            
            with col_form:
                st.markdown("### Vincular Usuário")
                novo_id = st.text_input("Login Corporativo:").strip().lower()
                novo_nome = st.text_input("Nome Completo:")
                nova_senha = st.text_input("Senha Corporativa:", type="password")
                novo_perfil = st.selectbox("Perfil de Acesso:", ["Aluno", "Professor", "Coordenador", "Gestor/Diretor"])
                
                if st.button("Salvar Usuário"):
                    if novo_id and novo_nome and nova_senha:
                        st.session_state.usuarios_cadastrados[novo_id] = {
                            "nome": novo_nome, 
                            "senha": nova_senha, 
                            "perfil": novo_perfil
                        }
                        salvar_arquivo_drive("usuarios.json", st.session_state.usuarios_cadastrados)
                        st.success(f"Usuário '{novo_id}' persistido em nuvem!")
                        st.rerun()
                    else:
                        st.error("Preencha todos os campos obrigatórios.")
            
            with col_lista:
                st.markdown("### Base Registrada")
                df_exibicao = pd.DataFrame([
                    {"ID": k, "Nome": v["nome"], "Perfil": v["perfil"]} 
                    for k, v in st.session_state.usuarios_cadastrados.items()
                ])
                st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

        elif "🏫 Turmas" in opcao_menu:
            st.subheader("🏫 Painel Coletivo de Turmas")
            if len(st.session_state.provas_geradas) > 0:
                df_provas = pd.DataFrame(st.session_state.provas_geradas.values())
                if 'turma' in df_provas.columns:
                    turmas_detectadas = df_provas['turma'].unique()
                    st.write(f"Turmas Ativas no Ciclo Corrente: **{', '.join(turmas_detectadas)}**")
                    st.dataframe(df_provas[['turma', 'materia', 'curso']].drop_duplicates(), use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma turma com vínculo ativo de avaliação.")
            else:
                st.info("Aguardando criação de avaliações pelos professores para mapeamento de turmas.")

        elif "👨‍🏫 Professores" in opcao_menu:
            st.subheader("👨‍🏫 Alocação e Atividades Docentes")
            df_users = pd.DataFrame([{"id": k, **v} for k, v in st.session_state.usuarios_cadastrados.items()])
            if not df_users.empty:
                df_profs = df_users[df_users['perfil'] == 'Professor']
                st.dataframe(df_profs[['id', 'nome']], use_container_width=True, hide_index=True)

        elif "📝 Avaliações" in opcao_menu:
            st.subheader("📝 Repositório Geral de Exames")
            if len(st.session_state.provas_geradas) > 0:
                df_provas_gerais = pd.DataFrame([{"Vínculo": k, **v} for k, v in st.session_state.provas_geradas.items()])
                st.dataframe(df_provas_gerais, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum exame cadastrado no sistema.")

        elif "📊 Analytics" in opcao_menu:
            st.subheader("📊 Relatórios e Indicadores Críticos")
            st.markdown(f"- **Volume de Cadastros Totais:** {len(st.session_state.usuarios_cadastrados)}")
            st.markdown(f"- **Provas Disponibilizadas:** {len(st.session_state.provas_geradas)}")
            st.markdown(f"- **Taxa de Conclusão Global:** {len(st.session_state.entregas_sistema)} entregas.")

        elif "📁 Relatórios" in opcao_menu:
            st.subheader("📁 Exportação de Dados")
            df_export = pd.DataFrame([{"ID": k, "Nome": v["nome"], "Perfil": v["perfil"]} for k, v in st.session_state.usuarios_cadastrados.items()])
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Lista de Usuários (CSV)", csv, "usuarios_suats.csv", "text/csv")

        elif "🛡 Auditoria" in opcao_menu:
            st.subheader("🛡 Logs de Segurança e Auditoria")
            st.code(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Usuário {st.session_state.usuario_logado} carregou o painel administrativo.")

        elif "⚙ Configurações" in opcao_menu:
            st.subheader("⚙ Configurações Gerais")
            st.code(ID_PASTA_DRIVE)

    # ==============================================================================
    # RENDERIZAÇÃO DAS ÁREAS DE TRABALHO - PROFESSOR
    # ==============================================================================
    elif st.session_state.perfil_logado == "Professor":
        if "🏠 Dashboard" in opcao_menu:
            st.write("Bem-vindo à Central do Docente. Escolha uma ação no menu à esquerda.")
            
        elif "➕ Criar Avaliação" in opcao_menu:
            st.subheader("⚙️ Wizard Profissional de Criação")
            
            st.markdown("##### **Etapa 1: Informações da Disciplina**")
            area = st.text_input("Área:").strip().upper()
            curso = st.text_input("Curso:").strip().upper()
            materia = st.text_input("Disciplina:").strip().upper()
            turma = st.text_input("Turma:").strip().upper()
            unidade = st.text_input("Unidade:").strip().upper()
            
            st.markdown("##### **Etapa 2: Tipo de Prova**")
            tipo_prova = st.selectbox("Selecione o modelo:", ["Dissertativa", "Múltiplas Escolhas", "Problema", "Prática", "Híbrida"])
            
            st.markdown("##### **Etapa 3: Modo de Criação**")
            modo_criacao = st.radio("Escolha o método:", ["Automática (Padrão Exposto)", "Manual (Passar Questões/Respostas)"])
            
            st.markdown("##### **Etapa 4: Configuração de Parâmetros Técnicos**")
            params_formulas = st.text_area("Insira as funções/fórmulas obrigatórias para esta prova (Ex: PROCV, SE, SOMA):")
            aluno_alvo = st.selectbox("Liberar para o Aluno:", list(st.session_state.usuarios_cadastrados.keys()))
            
            if st.button("🚀 Gerar e Liberar Prova"):
                if materia and aluno_alvo:
                    st.session_state.provas_geradas[aluno_alvo] = {
                        "area": area, "curso": curso, "materia": materia, "turma": turma,
                        "unidade": unidade, "tipo_prova": tipo_prova, "modo": modo_criacao,
                        "parametros": params_formulas, "status": "Liberada",
                        "data_criacao": datetime.now().strftime("%d/%m/%Y")
                    }
                    salvar_arquivo_drive("provas.json", st.session_state.provas_geradas)
                    st.success(f"Prova liberada e vinculada com sucesso para {aluno_alvo}!")

    # ==============================================================================
    # RENDERIZAÇÃO DAS ÁREAS DE TRABALHO - ALUNO
    # ==============================================================================
    elif st.session_state.perfil_logado == "Aluno":
        aluno_atual = st.session_state.usuario_logado
        
        if "🏠 Início" in opcao_menu:
            st.write(f"Olá {st.session_state.nome_exibicao}, bem-vindo ao seu painel de exames.")
            
        elif "📝 Minhas Avaliações" in opcao_menu:
            if aluno_atual in st.session_state.entregas_sistema:
                st.success("✅ Avaliação realizada e entregue com sucesso!")
                st.write(st.session_state.entregas_sistema[aluno_atual])
            elif aluno_atual not in st.session_state.provas_geradas:
                st.warning("⚠️ Nenhuma avaliação disponível no momento. Aguarde liberação do professor.")
            else:
                prova = st.session_state.provas_geradas[aluno_atual]
                st.info(f"📋 **Avaliação Disponível:** {prova['materia']} | **Tipo:** {prova['tipo_prova']}")
                
                st.markdown("#### 📥 1. Downloads")
                conteudo_prova_txt = f"PROVA DE {prova['materia']}\nTurma: {prova['turma']}\nTipo: {prova['tipo_prova']}\nParâmetros obrigatórios: {prova['parametros']}\nInsira seu e-mail e respostas abaixo."
                st.download_button(label="📥 Baixar Arquivo da Prova", data=conteudo_prova_txt, fileName=f"Prova_{prova['materia']}_{aluno_atual}.txt")
                
                st.markdown("#### 📤 2. Entrega (Apenas 1 envio permitido)")
                arquivo_submetido = st.file_uploader("Arraste e solte o arquivo da sua prova resolvida aqui:", type=["txt", "xlsx", "pdf"])
                
                if arquivo_submetido is not None:
                    if st.button("Finalizar e Enviar Avaliação"):
                        st.session_state.entregas_sistema[aluno_atual] = {
                            "materia": prova['materia'], "status": "Enviado", "nota": 10.0,
                            "data_entrega": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "arquivo_nome": arquivo_submetido.name
                        }
                        salvar_arquivo_drive("entregas.json", st.session_state.entregas_sistema)
                        st.success("Prova gravada e salva em nuvem!")
                        st.rerun()

    # ==============================================================================
    # RENDERIZAÇÃO DAS ÁREAS DE TRABALHO - COORDENADOR
    # ==============================================================================
    elif st.session_state.perfil_logado == "Coordenador":
        st.write("Painel de acompanhamento pedagógico analítico (Modo Leitura).")
        st.dataframe(pd.DataFrame([{"Aluno/ID": k, **v} for k, v in st.session_state.provas_geradas.items()]), use_container_width=True)
