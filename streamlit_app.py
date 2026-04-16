import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- CONFIGURAÇÃO DE SEGURANÇA ---
USUARIO_CORRETO = "admin"  # Altere para o usuário desejado
SENHA_CORRETA = "pmba2026" # Altere para a senha desejada

# --- CONFIGURAÇÃO SUPABASE ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Sistema de Policiamento - PMBA", layout="wide")

# --- FUNÇÃO DE LOGIN ---
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔐 Acesso Restrito - Extremo Sul")
        with st.form("login_form"):
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar")
            
            if entrar:
                if user == USUARIO_CORRETO and password == SENHA_CORRETA:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        return False
    return True

# --- INÍCIO DO PROGRAMA ---
if verificar_login():
    # Botão de Logout na lateral
    if st.sidebar.button("Sair do Sistema"):
        st.session_state.autenticado = False
        st.rerun()

    st.title("📅 Calendário de Policiamento - Extremo Sul")

    # [TODO O RESTANTE DO CÓDIGO DE REGIÕES E BANCO DE DADOS ENTRA AQUI]
    # ... (Copie o código das regiões, funções do DB e visualização aqui dentro)

st.title("📅 Calendário de Policiamento - Extremo Sul")

# --- DEFINIÇÃO DAS REGIÕES (LISTAS OFICIAIS) ---
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

# Lista para o menu de cadastro (Ordem Alfabética Geral para busca rápida)
todas_cidades = sorted([c for lista in regioes.values() for c in lista])

# --- FUNÇÕES DE BANCO DE DADOS ---
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

# --- INTERFACE LATERAL (GESTOR) ---
st.sidebar.header("⚙️ Gestão da Escala")
senha = st.sidebar.text_input("Senha do Gestor", type="password")

if senha == "123":
    st.sidebar.subheader("Agendar Policiamento")
    data_ag = st.sidebar.date_input("Data", datetime.date.today())
    unid_ag = st.sidebar.selectbox("Unidade:", ["CIPE-MA", "CIPT-ES"])
    cidade_ag = st.sidebar.selectbox("Município:", todas_cidades)
    missao_ag = st.sidebar.text_area("Missão:")

    if st.sidebar.button("Salvar no Banco de Dados"):
        if not missao_ag:
            st.sidebar.error("Por favor, descreva a missão.")
        else:
            salvar_no_db(data_ag, cidade_ag, unid_ag, missao_ag)
            st.sidebar.success(f"Escala salva: {cidade_ag}")
            st.rerun()
else:
    st.sidebar.warning("Insira a senha para gerenciar a escala.")

# --- VISUALIZAÇÃO PRINCIPAL ---
st.write("### 🔍 Consulta de Policiamento por Região")
data_con = st.date_input("Selecione o dia para visualizar:", datetime.date.today())
df_total = carregar_dados_db()

def color_status(val):
    if val == 'CIPE-MA': return 'background-color: #add8e6; color: black'
    if val == 'CIPT-ES': return 'background-color: #90ee90; color: black'
    return 'background-color: white; color: black'

# --- RENDERIZAÇÃO DAS TABELAS AGRUPADAS ---
for regiao, cidades in regioes.items():
    st.markdown(f"#### 📍 {regiao}") 
    
    # Monta a tabela base para a região
    rows = []
    for cid in cidades:
        rows.append({"Município": cid, "Ocupação": "Livre", "Missão": "-"})
    df_regiao = pd.DataFrame(rows)

    # Preenche com os dados salvos no Supabase para a data selecionada
    if not df_total.empty:
        df_dia = df_total[df_total['data'] == data_con.strftime("%Y-%m-%d")]
        for _, row in df_dia.iterrows():
            if row['municipio'] in cidades:
                df_regiao.loc[df_regiao['Município'] == row['municipio'], 'Ocupação'] = row['unidade']
                df_regiao.loc[df_regiao['Município'] == row['municipio'], 'Missão'] = row['missao']

    st.dataframe(
        df_regiao.style.map(color_status, subset=['Ocupação']), 
        use_container_width=True, 
        hide_index=True
    )
    st.write("") 

# --- HISTÓRICO ---
with st.expander("📊 Ver Histórico Geral de Missões"):
    if not df_total.empty:
        st.dataframe(
            df_total.sort_values(by='data', ascending=False), 
            use_container_width=True, 
            hide_index=True
        )
