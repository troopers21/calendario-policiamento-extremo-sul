import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES DE ACESSO (USUÁRIO E SENHA) ---
USUARIO_CORRETO = "admin"      # Altere como desejar
SENHA_CORRETA = "pmba2026"    # Altere como desejar

# --- 2. CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE) ---
# As chaves devem estar cadastradas no "Settings > Secrets" do Streamlit Cloud
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Sistema de Policiamento - PMBA", layout="wide")

# --- 3. DEFINIÇÃO DAS REGIÕES E CIDADES ---
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
    st.stop() # Interrompe a execução aqui se não estiver logado

# --- 6. INTERFACE PRINCIPAL (APÓS LOGIN) ---

# Botão de Logout na barra lateral
if st.sidebar.button("Sair / Logoff"):
    st.session_state.autenticado = False
    st.rerun()

st.title("📅 Calendário de Policiamento - Extremo Sul")

# Aba de Gestão (Cadastro) e Consulta
menu = st.tabs(["📋 Consulta de Escala", "⚙️ Gestão/Agendamento"])

with menu[1]: # Aba de Gestão
    st.subheader("Agendar Nova Missão")
    col1, col2 = st.columns(2)
    
    with col1:
        data_ag = st.date_input("Data da Missão", datetime.date.today())
        unid_ag = st.selectbox("Unidade Responsável", ["CIPE-MA", "CIPT-ES"])
    
    with col2:
        cidade_ag = st.selectbox("Município Alvo", todas_cidades)
        missao_ag = st.text_area("Descrição Detalhada da Missão")

    if st.button("Confirmar e Salvar no Banco de Dados"):
        if not missao_ag:
            st.error("Erro: A descrição da missão é obrigatória.")
        else:
            salvar_no_db(data_ag, cidade_ag, unid_ag, missao_ag)
            st.success(f"Missão em {cidade_ag} salva com sucesso!")
            st.rerun()

with menu[0]: # Aba de Consulta
    st.subheader("Visualização por Região")
    data_con = st.date_input("Filtrar por Dia", datetime.date.today())
    
    df_total = carregar_dados_db()
    data_con_str = data_con.strftime("%Y-%m-%d")

    for regiao, cidades in regioes.items():
        st.markdown(f"#### 📍 {regiao}")
        
        # Monta a tabela da região
        rows = []
        for cid in cidades:
            rows.append({"Município": cid, "Ocupação": "Livre", "Missão": "-"})
        df_regiao = pd.DataFrame(rows)

        # Filtra dados do banco para o dia e região
        if not df_total.empty:
            df_dia = df_total[df_total['data'] == data_con_str]
            for _, row in df_dia.iterrows():
                if row['municipio'] in cidades:
                    df_regiao.loc[df_regiao['Município'] == row['municipio'], 'Ocupação'] = row['unidade']
                    df_regiao.loc[df_regiao['Município'] == row['municipio'], 'Missão'] = row['missao']

        st.dataframe(
            df_regiao.style.map(color_status, subset=['Ocupação']), 
            use_container_width=True, 
            hide_index=True
        )

# --- 7. HISTÓRICO (EXPANDER NO RODAPÉ) ---
st.markdown("---")
with st.expander("📊 Ver Histórico Completo de Missões (Banco de Dados)"):
    df_hist = carregar_dados_db()
    if not df_hist.empty:
        df_hist = df_hist.rename(columns={
            'data': 'Data', 'municipio': 'Município', 
            'unidade': 'Unidade', 'missao': 'Missão'
        })
        st.dataframe(df_hist.sort_values(by='Data', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.write("Nenhum dado registrado.")
