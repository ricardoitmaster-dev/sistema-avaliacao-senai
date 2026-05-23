import streamlit as st
from utils import ler_dados_supabase # Importa do outro arquivo

# ... (seu restante de imports)

# No seu bloco de Login:
if st.session_state.usuario_logado is None:
    # ... inputs ...
    if st.button("🔓 Autenticar"):
        # Força a leitura do banco na hora do clique
        base_usuarios = ler_dados_supabase("usuarios")
        
        # Merge com o padrão caso o banco esteja vazio
        usuario_digitado = u_in.strip().lower()
        senha_digitada = s_in.strip()
        
        # Verifica no banco, se não achar, verifica no fixo
        dados_do_usuario = base_usuarios.get(usuario_digitado)
        
        # Debug visual (remova depois que funcionar)
        st.write(f"DEBUG: Usuário encontrado? {dados_do_usuario is not None}")
        
        if dados_do_usuario and str(dados_do_usuario.get("senha")).strip() == senha_digitada:
            st.session_state.usuario_logado = usuario_digitado
            st.session_state.perfil_logado = dados_do_usuario.get("perfil")
            st.rerun()
        else:
            st.error("Credenciais inválidas. Verifique usuário ou senha.")
