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
# 2. CONFIGURAÇÃO DE ACESSO AO GOOGLE DRIVE EM NUVEM (SOLUÇÃO DEFINITIVA P0)
# ==============================================================================
ID_PASTA_DRIVE = "1-bHDGxbJDWTzT30zL9S-oj0ktM-c60_R"
SCOPES = ['https://www.googleapis.com/auth/drive']

def sanitizar_chave_pem(chave_raw: str) -> str:
    """
    Função Blindada: Reconstrói o bloco PEM independentemente de como foi colado no Secrets.
    Elimina espaços em branco, quebras falsas e garante o padrão RFC 1421 (64 caracteres por linha).
    """
    chave = str(chave_raw).strip()
    chave = chave.replace('\\n', '\n').replace('\r', '')
    
    marcador_inicio = "-----BEGIN PRIVATE KEY-----"
    marcador_fim = "-----END PRIVATE KEY-----"
    
    if marcador_inicio in chave and marcador_fim in chave:
        # Isola o corpo criptográfico descartando os marcadores velhos
        corpo = chave.split(marcador_inicio)[1].split(marcador_fim)[0]
        # Remove ABSOLUTAMENTE qualquer espaço, quebra de linha ou tabulação existente
        corpo_puro = "".join(corpo.split())
        # Divide o bloco limpo em linhas exatas de 64 caracteres
        linhas_64 = [corpo_puro[i:i+64] for i in range(0, len(corpo_puro), 64)]
        # Remonta a estrutura PEM com quebras de linha limpas e válidas
        return f"{marcador_inicio}\n" + "\n".join(linhas_64) + f"\n{marcador_fim}\n"
    return chave

def obter_servico_drive():
    """Conecta com segurança e estabilidade à API do Google Drive."""
    if "gdrive" in st.secrets:
        try:
            info_chaves = dict(st.secrets["gdrive"])
            if "private_key" in info_chaves:
                info_chaves["private_key"] = sanitizar_chave_pem(info_chaves["private_key"])
            
            credenciais = service_account.Credentials.from_service_account_info(info_chaves, scopes=SCOPES)
            return build('drive', 'v3', credentials=credenciais, cache_discovery=False)
        except Exception as e:
            st.error(f"Erro ao inicializar o motor criptográfico do Drive: {e}")
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
    except Exception as e:
        st.sidebar.error(f"🚨 Erro ao salvar {nome_arquivo}: {e}")

# ==============================================================================
# 3. DADOS INICIAIS E SESSION STATE (Isolamento Concorrente)
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

if 'usuarios_cadastrados' not in st.session_state:
    st.session_state.usuarios_cadastrados = ler_arquivo_drive("usuarios.json", USUARIOS_PADRAO)

if "sn1084433" not in st.session_state.usuarios_cadastrados:
    st.session_state.usuarios_cadastrados.update(USUARIOS_PADRAO)
    salvar_arquivo_drive("usuarios.json", st.session_state.usuarios_cadastrados)

if 'provas_geradas' not in st.session_state:
    st.session_state.provas_geradas = ler_arquivo_drive("provas.json", {})

if 'entregas_sistema' not in st.session_state:
    st.session_state.entregas_sistema = ler_arquivo_drive("entregas.json", {})

# ==============================================================================
# 4. INTERFACE VISUAL (BMW Portinari Blue, Dourado e Dark Mode)
# ==============================================================================
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
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 5. GERENCIAMENTO DE TELAS E MENUS (Roteamento conforme Blueprint)
# ==============================================================================

if st.session_state.usuario_logado is None:
    st.markdown("<h2 style='text-align:center;'>🔐 SUATS | Portal de Acesso</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Insira suas credenciais corporativas SENAI para acessar a plataforma.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u_in = st.text_input("Login Corporativo:").strip().lower()
        s_in = st.text_input("Senha:", type="password")
        
        if st.button("🔓 Autenticar no Sistema"):
            user_data = st.session_state.usuarios_cadastrados.get(u_in)
            if user_data and user_data["senha"] == s_in:
                st.session_state.usuario_logado = u_in
                st.session_state.perfil_logado = user_data["perfil"]
                st.session_state.nome_exibicao = user_data.get("nome", u_in)
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

    # TELA 2 — DASHBOARD GESTOR
    if st.session_state.perfil_logado == "Gestor/Diretor":
        if "🏠 Dashboard Geral" in opcao_menu:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total de Alunos", "2")
            c2.metric("Total de Professores", "1")
            c3.metric("Avaliações Ativas", len(st.session_state.provas_geradas))
            c4.metric("Avaliações Concluídas", len(st.session_state.entregas_sistema))
            
            st.subheader("👁️ Monitoramento ao Vivo")
            dados_monitoramento = [
                {"Usuário": "Ricardo", "Perfil": "Aluno", "Status": "Em Prova"},
                {"Usuário": "João", "Perfil": "Professor", "Status": "Online"}
            ]
            st.dataframe(pd.DataFrame(dados_monitoramento), use_container_width=True)
            
        elif "👥 Usuários" in opcao_menu:
            st.subheader("👤 Gerenciamento de Usuários")
            novo_id = st.text_input("Novo Login:")
            novo_nome = st.text_input("Nome:")
            nova_senha = st.text_input("Senha:", type="password")
            novo_perfil = st.selectbox("Perfil:", ["Aluno", "Professor", "Coordenador", "Gestor/Diretor"])
            
            if st.button("Salvar Usuário"):
                if novo_id and novo_nome and nova_senha:
                    st.session_state.usuarios_cadastrados[novo_id] = {"nome": novo_nome, "senha": nova_senha, "perfil": novo_perfil}
                    salvar_arquivo_drive("usuarios.json", st.session_state.usuarios_cadastrados)
                    st.success("Usuário cadastrado com sucesso e salvo no Drive!")
                    st.rerun()
            
            st.dataframe(pd.DataFrame([{"ID": k, **v} for k, v in st.session_state.usuarios_cadastrados.items()]), use_container_width=True)

    # TELA 3 — DASHBOARD PROFESSOR
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
                        "area": area,
                        "curso": curso,
                        "materia": materia,
                        "turma": turma,
                        "unidade": unidade,
                        "tipo_prova": tipo_prova,
                        "modo": modo_criacao,
                        "parametros": params_formulas,
                        "status": "Liberada",
                        "data_criacao": datetime.now().strftime("%d/%m/%Y")
                    }
                    salvar_arquivo_drive("provas.json", st.session_state.provas_geradas)
                    st.success(f"Prova liberada e vinculada com sucesso para {aluno_alvo}!")

    # TELA 4 — DASHBOARD ALUNO
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
                st.write(f"Curso: {prova['curso']} | Turma: {prova['turma']}")
                
                st.markdown("#### 📥 1. Downloads")
                conteudo_prova_txt = f"PROVA DE {prova['materia']}\nTurma: {prova['turma']}\nTipo: {prova['tipo_prova']}\nParâmetros obrigatórios: {prova['parametros']}\nInsira seu e-mail e respostas abaixo."
                st.download_button(label="📥 Baixar Arquivo da Prova", data=conteudo_prova_txt, fileName=f"Prova_{prova['materia']}_{aluno_atual}.txt")
                
                st.markdown("#### 📤 2. Entrega (Apenas 1 envio permitido)")
                arquivo_submetido = st.file_uploader("Arraste e solte o arquivo da sua prova resolvida aqui:", type=["txt", "xlsx", "pdf"])
                
                if arquivo_submetido is not None:
                    if st.button("Finalizar e Enviar Avaliação"):
                        st.session_state.entregas_sistema[aluno_atual] = {
                            "materia": prova['materia'],
                            "status": "Enviado",
                            "nota": 10.0,
                            "data_entrega": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "arquivo_nome": arquivo_submetido.name
                        }
                        salvar_arquivo_drive("entregas.json", st.session_state.entregas_sistema)
                        st.success("Prova gravada e salva em nuvem!")
                        st.rerun()

    # TELA 5 — COORDENADOR
    elif st.session_state.perfil_logado == "Coordenador":
        st.write("Painel de acompanhamento pedagógico analítico (Modo Leitura).")
        st.dataframe(pd.DataFrame([{"Aluno/ID": k, **v} for k, v in st.session_state.provas_geradas.items()]), use_container_width=True)
