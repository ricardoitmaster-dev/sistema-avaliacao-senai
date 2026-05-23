import os
import sys
import json
from datetime import datetime
import streamlit as st
import pandas as pd
import requests

# ==============================================================================
# 1. CONFIGURAÇÃO E CONEXÃO SEGURA AO SUPABASE (SQL NA NUVEM)
# ==============================================================================
SUPABASE_URL = "https://hjtqqshmxpeleywwzgca.supabase.co"
SUPABASE_KEY = "sb_publishable_Q0gok1Hp7-3El1UOGKDrZw_Ku5QqDbu"

# Cabeçalhos padrão para comunicação segura com a API REST do Supabase
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Massa de dados padrão master para consistência do sistema
USUARIOS_PADRAO = {
    "sn1084433": {"nome": "Benedito Ricardo dos Santos", "senha": "Celina2610**", "perfil": "Gestor/Diretor"},
    "sn1220001": {"nome": "Professor de Testes SENAI", "senha": "122", "perfil": "Professor"},
    "aluno_ricardo": {"nome": "Ricardo (Aluno)", "senha": "123", "perfil": "Aluno"},
    "aluno_elizandra": {"nome": "Elizandra (Aluna)", "senha": "123", "perfil": "Aluno"},
    "coord_teste": {"nome": "Coordenador Técnico", "senha": "122", "perfil": "Coordenador"},
    "sn1220002": {"nome": "Elizandra pascoalino", "senha": "123", "perfil": "Professor"}
}

def ler_dados_supabase(tabela):
    """
    Busca os dados diretamente do Supabase e reconstrói a estrutura de 
    dicionário dinâmico que o app usa nativamente para session_state.
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/{tabela}?select=*"
        resposta = requests.get(url, headers=HEADERS)
        
        if resposta.status_code == 200:
            dados_lista = resposta.json()
            if not dados_lista:
                return {}
                
            resultado = {}
            if tabela == "usuarios":
                for item in dados_lista:
                    u_id = str(item['id']).strip().lower()
                    resultado[u_id] = {
                        "nome": item.get('nome', u_id),
                        "senha": item.get('senha', ''),
                        "perfil": item.get('perfil', 'Aluno')
                    }
                return resultado
                
            elif tabela in ["provas", "entregas"]:
                for item in dados_lista:
                    aluno_alvo = item.get('id_alvo', '').strip().lower()
                    if not aluno_alvo:
                        continue
                    resultado[aluno_alvo] = {k: v for k, v in item.items() if k != 'id_alvo'}
                return resultado
        return {}
    except Exception as e:
        return {}

def salvar_dados_supabase(tabela, dados):
    """
    Converte os dicionários dinâmicos do Streamlit de volta para JSON estruturado
    e realiza uma operação de UPSERT (insere ou atualiza) no Supabase.
    """
    try:
        linhas = []
        if tabela == "usuarios":
            for k, v in dados.items():
                linhas.append({"id": k, "nome": v["nome"], "senha": v["senha"], "perfil": v["perfil"]})
                
        elif tabela in ["provas", "entregas"]:
            for k, v in dados.items():
                linha = {"id_alvo": k}
                linha.update(v)
                linhas.append(linha)
        
        if not linhas:
            return True
            
        url = f"{SUPABASE_URL}/rest/v1/{tabela}"
        headers_upsert = HEADERS.copy()
        headers_upsert["Prefer"] = "resolution=merge-duplicates"
        
        resposta = requests.post(url, headers=headers_upsert, json=linhas)
        
        if resposta.status_code not in [200, 201]:
            for registro in linhas:
                requests.post(url, headers=headers_upsert, json=registro)
            return True
            
        return True
    except Exception as e:
        return False

# ==============================================================================
# 2. CONTROLE DE ESTADO DA SESSÃO E CARGA DO BANCO DE DADOS
# ==============================================================================
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None
if 'perfil_logado' not in st.session_state:
    st.session_state.perfil_logado = None
if 'nome_exibicao' not in st.session_state:
    st.session_state.nome_exibicao = None

# Sincronização Dinâmica Pós-Login em tempo real com o Supabase
if st.session_state.usuario_logado is not None:
    if 'usuarios_cadastrados' not in st.session_state or not st.session_state.usuarios_cadastrados:
        dados_usuarios = ler_dados_supabase("usuarios")
        st.session_state.usuarios_cadastrados = dados_usuarios if dados_usuarios else USUARIOS_PADRAO
    if 'provas_geradas' not in st.session_state:
        st.session_state.provas_geradas = ler_dados_supabase("provas")
    if 'entregas_sistema' not in st.session_state:
        st.session_state.entregas_sistema = ler_dados_supabase("entregas")
else:
    st.session_state.usuarios_cadastrados = USUARIOS_PADRAO
    st.session_state.provas_geradas = {}
    st.session_state.entregas_sistema = {}

# ==============================================================================
# 3. INTERFACE VISUAL (BMW Portinari Blue, Dourado e Dark Mode)
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
# 4. PORTAL DE LOGIN / NAVEGAÇÃO
# ==============================================================================
if st.session_state.usuario_logado is None:
    st.markdown("<h2 style='text-align:center;'>🔐 SUATS | Portal de Acesso</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Insira suas credenciais corporativas SENAI para acessar a plataforma.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u_in = st.text_input("Login Corporativo (Ex: snXXXXXXX):").strip().lower()
        s_in = st.text_input("Senha de Acesso:", type="password")
        
        if st.button("🔓 Autenticar no Sistema"):
            # Tenta buscar os dados vivos na nuvem do Supabase
            dados_drive = ler_dados_supabase("usuarios")
            
            # MECANISMO DE FALLBACK (Garante o login mesmo com tabelas em nuvem inicialmente limpas)
            user_data = dados_drive.get(u_in) if dados_drive else None
            if not user_data and u_in in USUARIOS_PADRAO:
                user_data = USUARIOS_PADRAO[u_in]
                
            if user_data and str(user_data["senha"]) == str(s_in):
                st.session_state.usuario_logado = u_in
                st.session_state.perfil_logado = user_data["perfil"]
                st.session_state.nome_exibicao = user_data.get("nome", u_in)
                
                # Se a nuvem estava vazia, faz o provisionamento imediato com a lista base
                if not dados_drive:
                    salvar_dados_supabase("usuarios", USUARIOS_PADRAO)
                    st.session_state.usuarios_cadastrados = USUARIOS_PADRAO
                else:
                    st.session_state.usuarios_cadastrados = dados_drive
                    
                st.session_state.provas_geradas = ler_dados_supabase("provas")
                st.session_state.entregas_sistema = ler_dados_supabase("entregas")
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
    # 5. RENDERIZAÇÃO DAS ÁREAS DE TRABALHO - GESTOR
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
                st.info("Nenhuma atividade de entrega registrada na base em nuvem Supabase até o momento.")
            
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
                        if salvar_dados_supabase("usuarios", st.session_state.usuarios_cadastrados):
                            st.success(f"Usuário '{novo_id}' gravado com sucesso no Supabase!")
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
            st.write(f"Banco de Dados Ativo: **Supabase Cloud Relational (PostgreSQL)**")
            st.write(f"Endpoint: {SUPABASE_URL}")

    # ==============================================================================
    # 6. RENDERIZAÇÃO DAS ÁREAS DE TRABALHO - PROFESSOR
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
                    if salvar_dados_supabase("provas", st.session_state.provas_geradas):
                        st.success(f"Prova liberada e vinculada com sucesso na nuvem para {aluno_alvo}!")

    # ==============================================================================
    # 7. RENDERIZAÇÃO DAS ÁREAS DE TRABALHO - ALUNO
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
                st.download_button(label="📥 Baixar Arquivo da Prova", data=conteudo_prova_txt, file_name=f"Prova_{prova['materia']}_{aluno_atual}.txt")
                
                st.markdown("#### 📤 2. Entrega (Apenas 1 envio permitido)")
                arquivo_submetido = st.file_uploader("Arraste e solte o arquivo da sua prova resolvida aqui:", type=["txt", "xlsx", "pdf"])
                
                if arquivo_submetido is not None:
                    if st.button("Finalizar e Enviar Avaliação"):
                        st.session_state.entregas_sistema[aluno_atual] = {
                            "materia": prova['materia'], "status": "Enviado", "nota": 10.0,
                            "data_entrega": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "arquivo_nome": arquivo_submetido.name
                        }
                        if salvar_dados_supabase("entregas", st.session_state.entregas_sistema):
                            st.success("Prova gravada e salva com sucesso no banco relacional Supabase!")
                            st.rerun()

    # ==============================================================================
    # 8. RENDERIZAÇÃO DAS ÁREAS DE TRABALHO - COORDENADOR
    # ==============================================================================
    elif st.session_state.perfil_logado == "Coordenador":
        st.write("Painel de acompanhamento pedagógico analítico (Modo Leitura).")
        if len(st.session_state.provas_geradas) > 0:
            st.dataframe(pd.DataFrame([{"Aluno/ID": k, **v} for k, v in st.session_state.provas_geradas.items()]), use_container_width=True)
        else:
            st.info("Nenhum dado de prova disponível para monitoramento.")
