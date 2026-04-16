import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- CONFIGURAÇÃO SUPABASE (Certifique-se que os Secrets estão configurados) ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Calendário Operacional - PMBA", layout="wide")

st.title("📅 Calendário de Policiamento - Extremo Sul")

# --- DIVISÃO REGIONAL DOS MUNICÍPIOS ---
regioes = {
    "Costa das Baleias": [
        "Teixeira de Freitas", "Alcobaça", "Caravelas", "Ibirapuã", 
        "Itanhém", "Lajedão", "Medeiros Neto", "Mucuri", 
        "Nova Viçosa", "Prado", "Vereda", "Posto da Mata"
    ],
    "Costa do Descobrimento": [
        "Porto Seguro", "Eunápolis", "Belmonte", "Guaratinga", 
        "Itabela", "Itagimirim", "Itapebi", "Santa Cruz Cabrália", 
        "Itamaraju", "Jucuruçu"
    ]
}

# Criar uma lista única ordenada para os menus, mantendo a prioridade que você pediu antes
prioritarios = ["Teixeira de Freitas", "Porto Seguro", "Eunápolis"]
todas_cidades = [c for lista in regioes.values() for c in lista]
restante = sorted([c for c in todas_cidades if c not in prioritarios])
lista_ordenada = prioritarios + restante

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
    
    # Seleção por Região para facilitar o cadastro
    regiao_sel = st.sidebar.selectbox("Filtrar por Região:", ["Todas", "Costa das Baleias", "Costa do Descobrimento"])
    
    if regiao_sel == "Todas":
        cidade_ag = st.sidebar.selectbox("Município:", lista_ordenada)
    else:
        cidade_ag = st.sidebar.selectbox("Município:", sorted(regioes[regiao_sel]))
        
    missao_ag = st.sidebar.text_area("Missão:")

    if st.sidebar.button("Salvar no Banco de Dados"):
        if not missao_ag:
            st.sidebar.error("Descreva a missão.")
        else:
            salvar_no_db(data_ag, cidade_ag, unid_ag, missao_ag)
            st.sidebar.success(f"Salvo: {cidade_ag}")
            st.rerun()

# --- VISUALIZAÇÃO PRINCIPAL ---
st.write("### 🔍 Consulta por Região e Data")
data_con = st.date_input("Selecione o dia:", datetime.date.today())
df_total = carregar_dados_db()

# Preparar tabela base com a coluna de Região
rows = []
for reg, cidades in regioes.items():
    for cid in cidades:
        rows.append({"Região": reg, "Município": cid, "Ocupação": "Livre", "Missão": "-"})
tabela_visual = pd.DataFrame(rows)

# Preencher com dados do Banco
if not df_total.empty:
    df_dia = df_total[df_total['data'] == data_con.strftime("%Y-%m-%d")]
    for _, row in df_dia.iterrows():
        tabela_visual.loc[tabela_visual['Município'] == row['municipio'], 'Ocupação'] = row['unidade']
        tabela_visual.loc[tabela_visual['Município'] == row['municipio'], 'Missão'] = row['missao']

# Ordenação final da tabela para exibição
tabela_visual = tabela_visual.sort_values(by=["Região", "Município"])

def color_status(val):
    if val == 'CIPE-MA': return 'background-color: #add8e6; color: black'
    if val == 'CIPT-ES': return 'background-color: #90ee90; color: black'
    return 'background-color: white; color: black'

st.dataframe(
    tabela_visual.style.map(color_status, subset=['Ocupação']), 
    height=750, 
    use_container_width=True, 
    hide_index=True
)

# --- HISTÓRICO ---
with st.expander("📊 Histórico Completo"):
    if not df_total.empty:
        st.dataframe(df_total.sort_values(by='data', ascending=False), use_container_width=True, hide_index=True)
