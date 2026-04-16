import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE) ---
# No Streamlit Cloud, você cadastrará estas chaves em "Settings > Secrets"
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Calendário Operacional - PMBA", layout="wide")

st.title("📅 Calendário de Policiamento (Banco de Dados Ativo)")

# --- MUNICÍPIOS (ORDEM SOLICITADA) ---
prioritarios = ["Teixeira de Freitas", "Porto Seguro", "Eunápolis"]
todos_municipios = [
    "Teixeira de Freitas", "Itanhém", "Medeiros Neto", "Vereda", "Lajedão", 
    "Ibirapuã", "Caravelas", "Posto da Mata", "Nova Viçosa", "Mucuri", 
    "Prado", "Alcobaça", "Itamaraju", "Jucuruçu", "Guaratinga", 
    "Itabela", "Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itagimirim"
]
restante_alfabetico = sorted([m for m in todos_municipios if m not in prioritarios])
municipios = prioritarios + restante_alfabetico

# --- FUNÇÕES DO BANCO DE DADOS ---
def carregar_dados_db():
    response = supabase.table("escala_operacional").select("*").execute()
    return pd.DataFrame(response.data)

def salvar_no_db(data, municipio, unidade, missao):
    data_data = {
        "data": data.strftime("%Y-%m-%d"),
        "municipio": municipio,
        "unidade": unidade,
        "missao": missao
    }
    supabase.table("escala_operacional").insert(data_data).execute()

# --- INTERFACE LATERAL ---
st.sidebar.header("⚙️ Gestão da Escala")
senha = st.sidebar.text_input("Senha do Gestor", type="password")

if senha == "123":
    st.sidebar.subheader("Agendar Policiamento")
    data_ag = st.sidebar.date_input("Data", datetime.date.today())
    unid_ag = st.sidebar.selectbox("Unidade:", ["CIPE-MA", "CIPT-ES"])
    cidades_ag = st.sidebar.multiselect("Municípios:", municipios)
    missao_ag = st.sidebar.text_area("Missão:")

    if st.sidebar.button("Salvar no Banco de Dados"):
        for cidade in cidades_ag:
            salvar_no_db(data_ag, cidade, unid_ag, missao_ag)
        st.sidebar.success("Dados salvos permanentemente!")
        st.rerun()

# --- VISUALIZAÇÃO ---
st.write("### 🔍 Consulta de Escala")
data_con = st.date_input("Filtrar por dia:", datetime.date.today())
df_total = carregar_dados_db()

if not df_total.empty:
    # Filtro local do dataframe
    df_dia = df_total[df_total['data'] == data_con.strftime("%Y-%m-%d")]
    
    # Monta a tabela visual
    tabela_visual = pd.DataFrame([{"Município": m, "Ocupação": "Livre", "Missão": "-"} for m in municipios])
    for _, row in df_dia.iterrows():
        tabela_visual.loc[tabela_visual['Município'] == row['municipio'], 'Ocupação'] = row['unidade']
        tabela_visual.loc[tabela_visual['Município'] == row['municipio'], 'Missão'] = row['missao']

    def color_status(val):
        if val == 'CIPE-MA': return 'background-color: #add8e6; color: black'
        if val == 'CIPT-ES': return 'background-color: #90ee90; color: black'
        return 'background-color: white; color: black'

    st.dataframe(tabela_visual.style.map(color_status, subset=['Ocupação']), height=600, use_container_width=True, hide_index=True)
else:
    st.write("O banco de dados está vazio.")
