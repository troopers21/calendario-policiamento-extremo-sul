import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES DE ACESSO ---
USUARIO_CORRETO = "admin"
SENHA_CORRETA = "pmba2026"
CHAVE_GESTAO = "comando2026"

# --- 2. CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE) ---
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

# --- 4. FUNÇÕES DE SUPORTE (CRUD) ---
def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame(columns=['id', 'data', 'municipio', 'unidade', 'missao'])

def salvar_no_db(data, municipio, unidade, missao):
    data_data = {
        "data": data.strftime("%Y-%m-%d"),
        "municipio": municipio,
        "unidade": unidade,
        "missao": missao
    }
    supabase.table("escala_operacional").insert(data_data).execute()

def apagar_no_db(id_registro):
    try:
        supabase.table("escala_operacional").delete().eq("id", id_registro).execute()
        return True
    except Exception:
        return False

def obter_dia_semana(data_str):
    dias = {
        0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
        3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
    }
    try:
        data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d")
        return dias[data_obj.weekday()]
    except:
        return "-"

def color_status(val):
    if val == 'CIPE-MA': return 'background-color: #add8e6; color: black'
    if val == 'CIPT-ES': return 'background-color: #90ee90; color: black'
    return 'background-color: white; color: black'

# --- 5. LÓGICA DE AUTENTICAÇÃO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "gestao_liberada" not in st.session_state:
    st.session_state.gestao_liberada = False

if not st.session_state.autenticado:
    st.title("🔐 Acesso Restrito - Extremo Sul")
    with st.form("login_form"):
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar no Sistema"):
            if user == USUARIO_CORRETO and password == SENHA_CORRETA:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
    st.stop()

# --- 6. INTERFACE PRINCIPAL ---
if st.sidebar.button("Sair / Logoff"):
    st.session_state.autenticado = False
    st.session_state.gestao_liberada = False
    st.rerun()

st.title("📅 Calendário de Policiamento - Extremo Sul")

menu = st.tabs(["📋 Consulta de Escala", "⚙️ Gestão/Agendamento"])

# --- ABA DE CONSULTA ---
with menu[0]:
    st.subheader("Visualização por Região")
    col_data_con, _ = st.columns([1, 2])
    with col_data_con:
        data_con = st.date_input("Filtrar por Dia", datetime.date.today())
    
    df_total = carregar_dados_db()
    data_con_str = data_con.strftime("%Y-%m-%d")

    for regiao, cidades in regioes.items():
        st.markdown(f"#### 📍 {regiao}")
        rows = []
        for cid in cidades:
            rows.append({"Município": cid, "Ocupação": "Livre", "Missão": "-"})
        df_regiao = pd.DataFrame(rows)

        if not df_total.empty:
            df_dia = df_total[df_total['data'] == data_con_str]
            for _, row in df_dia.iterrows():
                if row['municipio'] in cidades:
                    df_regiao.loc[df_regiao['Município'] == row['municipio'], 'Ocupação'] = row['unidade']
                    df_regiao.loc[df_regiao['Município'] == row['municipio'], 'Missão'] = row['missao']

        st.dataframe(df_regiao.style.map(color_status, subset=['Ocupação']), use_container_width=True, hide_index=True)

# --- ABA DE GESTÃO (AGENDAR E APAGAR) ---
with menu[1]:
    if not st.session_state.gestao_liberada:
        st.warning("🔒 Esta área exige a Chave de Comando.")
        chave_input = st.text_input("Insira a Chave de Gestão:", type="password")
        if st.button("Liberar Acesso"):
            if chave_input == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True
                st.rerun()
            else:
                st.error("Chave incorreta.")
    else:
        st.button("🔒 Bloquear Gestão", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        
        tab_cad, tab_del = st.tabs(["📝 Novo Agendamento", "🗑️ Apagar Registro"])
        
        with tab_cad:
            col1, col2 = st.columns(2)
            with col1:
                data_ag = st.date_input("Data da Missão", datetime.date.today(), key="cad_data")
                st.write(f"📅 **Dia:** {obter_dia_semana(data_ag.strftime('%Y-%m-%d'))}")
                unid_ag = st.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"], key="cad_unid")
            with col2:
                cidade_ag = st.selectbox("Município Alvo", todas_cidades, key="cad_cid")
                missao_ag = st.text_area("Missão", placeholder="Descreva o objetivo...", key="cad_miss")

            if st.button("Salvar no Banco de Dados"):
                if not missao_ag: st.error("A missão é obrigatória.")
                else:
                    salvar_no_db(data_ag, cidade_ag, unid_ag, missao_ag)
                    st.success("Salvo!")
                    st.rerun()

        with tab_del:
            st.subheader("Excluir Missão")
            df_atual = carregar_dados_db()
            if not df_atual.empty:
                df_atual['view'] = df_atual['data'] + " | " + df_atual['municipio'] + " (" + df_atual['unidade'] + ")"
                lista_missões = df_atual.sort_values(by='data', ascending=False)
                selecionado = st.selectbox("Selecione para apagar:", lista_missões['view'].tolist())
                id_alvo = df_atual[df_atual['view'] == selecionado]['id'].values[0]
                
                if st.button("❌ EXCLUIR DEFINITIVAMENTE"):
                    if apagar_no_db(id_alvo):
                        st.success("Excluído com sucesso!")
                        st.rerun()
            else:
                st.info("Nenhum registro para apagar.")

# --- 7. HISTÓRICO COM COLUNA DIA DA SEMANA ---
st.markdown("---")
with st.expander("📊 Histórico de Missões"):
    df_hist = carregar_dados_db()
    if not df_hist.empty:
        # Criar a coluna Dia da Semana
        df_hist['Dia da Semana'] = df_hist['data'].apply(obter_dia_semana)
        
        # Reorganizar colunas para: Data, Dia da Semana, Município, Unidade, Missão
        # Nota: 'id' é mantido mas pode ser escondido se desejar
        df_hist = df_hist[['data', 'Dia da Semana', 'municipio', 'unidade', 'missao']]
        
        # Renomear para exibição amigável
        df_hist.columns = ['Data', 'Dia da Semana', 'Município', 'Unidade', 'Missão']
        
        st.dataframe(df_hist.sort_values(by='Data', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.write("Nenhum dado registrado.")
