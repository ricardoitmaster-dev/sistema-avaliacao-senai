# utils.py
import requests
import streamlit as st

SUPABASE_URL = "https://hjtqqshmxpeleywwzgca.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqdHFxc2hteHBlbGV5d3d6Z2NhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0OTY1NDgsImV4cCI6MjA5NTA3MjU0OH0.4v_EyCfUyE2ZEgqOYdnFNZlHVhG8_Quc9otQ7o8Di_s"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def ler_dados_supabase(tabela):
    try:
        url = f"{SUPABASE_URL}/rest/v1/{tabela}?select=*"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            dados = resp.json()
            # Tratamento robusto: se retornar lista, transforma em dicionário
            if tabela == "usuarios":
                return {str(i['id']).strip().lower(): i for i in dados}
            return {str(i.get('id_alvo', '')).strip().lower(): i for i in dados}
        else:
            print(f"ERRO SUPABASE {tabela}: {resp.status_code} - {resp.text}")
            return {}
    except Exception as e:
        print(f"ERRO DE CONEXÃO: {e}")
        return {}

def salvar_dados_supabase(tabela, dados):
    # Lógica de upsert... (inserir sua lógica aqui)
    return True
