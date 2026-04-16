import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES DE ACESSO ---
USUARIO_CORRETO = "admin"
SENHA_CORRETA = "pmba2026"

# --- 2. CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE) ---
# Lembre-se de cadastrar SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit Cloud
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Sistema de Policiamento - PMBA", layout="wide")

# --- 3. DEFINIÇÃO DAS REGIÕES E CIDADES (LISTAS OFICIAIS) ---
regioes = {
    "Costa do Descobrimento": [
        "Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", 
        "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"
    ],
    "Costa das Baleias": [
        "Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", 
        "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", 
        "Prado", "Caravelas", "Mucuri", "Nova Viçosa"
    ]
}

todas_cidades = sorted([c for lista in regioes.values() for c in lista])

# --- 4. FUNÇÕES DE SUPORTE ---
def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame(columns=['data', 'municipio', 'unidade', 'missao'])

def salvar_no_db(data, municipio, unidade, missao):
    data_data = {
        "data": data.strftime("%Y-%m-%d"),
        "municipio": municipio,
        "unidade": unidade,
        "missao": missao
    }
    supabase.table("escala_operacional").insert(data_data).execute()

def color_status(val):
    if val == 'CIPE-MA': return 'background-color: #add8e6; color: black'
    if val == 'CIPT-ES': return 'background-color: #90ee90; color: black'
    return 'background-color: white; color: black'

# --- 5. LÓGICA DE AUTENTICAÇÃO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acesso Restrito - Extremo Sul")
    with st.form("login_form"):
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar no Sistema")
        
        if entrar:
            if user == USUARIO_CORRETO and password == SENHA_CORRETA:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
    st.stop()

# --- 6. INTERFACE PRINCIPAL (APÓS LOGIN) ---

if st.sidebar.button("Sair / Logoff"):
    st.session_state.autenticado = False
    st.rerun()

st.title("📅 Calendário de Policiamento - Extremo Sul")

# Abas de navegação
menu = st.tabs(["📋 Consulta de Escala", "⚙️ Gestão/Agendamento"])

with menu[1]: # Aba de Gestão
    st.subheader("Agendar Nova Missão")
    col1, col2 = st.columns(2)
    
    with col1:
        data_ag = st.date_input("Data da Missão", datetime.date.today())
        
        # Exibição do Dia da Semana em Português
        dias_semana = {
            0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
            3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
        }
        dia_nome = dias_semana[data_ag.weekday()]
        st.write(f"📅 **Dia selecionado:** {dia_nome}")
        
        unid_ag = st.selectbox("Unidade Responsável", ["CIPE-MA", "CIPT-ES"])
    
    with col2:
