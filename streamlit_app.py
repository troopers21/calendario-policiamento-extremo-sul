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
        df = pd.DataFrame(response.data)
        
        colunas_necessarias = ['id', 'data', 'municipio', 'unidade', 'missao', 'cumprido', 'hora_entrada', 'hora_saida', 'relatorio_resumido']
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = None if col != 'cumprido' else False
        return df
    except Exception:
        return pd.DataFrame(columns=['id', 'data', 'municipio', 'unidade', 'missao', 'cumprido', 'hora_entrada', 'hora_saida', 'relatorio_resumido'])

def salvar_no_db(data, municipio, unidade, missao):
    data_data = {
        "data": data.strftime("%Y-%m-%d"),
        "municipio": municipio,
        "unidade": unidade,
        "missao": missao,
        "cumprido": False
    }
    supabase.table("escala_operacional").insert(data_data).execute()

def atualizar_cumprimento(id_registro, entrada, saida, relatorio, status):
    try:
        supabase.table("escala_operacional").update({
            "hora_entrada": entrada,
            "hora_saida": saida,
            "relatorio_resumido": relatorio,
            "cumprido": status
        }).eq("id", id_registro).execute()
        return True
    except:
        return False

def apagar_no_db(id_registro):
    try:
        supabase.table("escala_operacional").delete().eq("id", id_registro).execute()
        return True
    except Exception:
        return False

def obter_dia_semana(data_str):
    dias = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
    try:
        data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d")
        return dias[data_obj.weekday()]
    except: return "-"

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
            else: st.error("Usuário ou senha inválidos.")
    st.stop()

# --- 6. INTERFACE PRINCIPAL ---
if st.sidebar.button("Sair / Logoff"):
    st.session_state.autenticado = False
    st.session_state.gestao_liberada = False
    st.rerun()

st.title("📅 Sistema Operacional - Extremo Sul")

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "⚙️ Gestão"])

# --- ABA 0: CONSULTA ---
with menu[0]:
    st.subheader("Consulta de Escala")
    data_con = st.date_input("Filtrar por Dia", datetime.date.today())
    df_total = carregar_dados_db()
    data_con_str = data_con.strftime("%Y-%m-%d")

    for regiao, cidades in regioes.items():
        st.markdown(f"#### 📍 {regiao}")
        rows = []
        for cid in cidades:
            rows.append({"Município": cid, "Ocupação": "Livre", "Status": "Pendente"})
        df_regiao = pd.DataFrame(rows)

        if not df_total.empty:
            df_dia = df_total[df_total['data'] == data_con_str]
            for _, row in df_dia.iterrows():
                if row['municipio'] in cidades:
                    status_txt = "✅ Cumprido" if row.get('cumprido') == True else "⚠️ Escalado"
                    df_regiao.loc[df_regiao['Município'] == row['municipio'], 'Ocupação'] = row['unidade']
                    df_regiao.loc[df_regiao['Município'] == row['municipio'], 'Status'] = status_txt

        st.dataframe(df_regiao.style.map(color_status, subset=['Ocupação']), use_container_width=True, hide_index=True)

# --- ABA 1: CUMPRIMENTO DA ESCALA (FILTRADO POR DATA) ---
with menu[1]:
    st.subheader("Registrar Cumprimento de Missão")
    df_raw = carregar_dados_db()
    
    if not df_raw.empty:
        # Lógica de Filtro: Converter coluna data para objeto date e comparar com HOJE
        hoje = datetime.date.today().strftime("%Y-%m-%d")
        df_cump = df_raw[df_raw['data'] <= hoje].copy()
        
        if not df_cump.empty:
            df_cump = df_cump.sort_values(by='data', ascending=False)
            df_cump['selecao'] = df_cump['data'] + " | " + df_cump['municipio'] + " (" + df_cump['unidade'] + ")"
            
            missao_sel = st.selectbox("Selecione a Missão (Apenas datas de hoje ou passadas):", df_cump['selecao'].tolist())
            dados_missao = df_cump[df_cump['selecao'] == missao_sel].iloc[0]
            
            with st.form("form_cumprimento"):
                col1, col2 = st.columns(2)
                with col1:
                    h_entrada = st.text_input("Hora de Entrada", value=str(dados_missao.get('hora_entrada') or ""))
                    h_saida = st.text_input("Hora de Saída", value=str(dados_missao.get('hora_saida') or ""))
                with col2:
                    status_final = st.checkbox("Missão cumprida?", value=bool(dados_missao.get('cumprido')))
                
                relatorio = st.text_area("Resumo da Missão", value=str(dados_missao.get('relatorio_resumido') or ""))
                
                if st.form_submit_button("Salvar Registro"):
                    if atualizar_cumprimento(dados_missao['id'], h_entrada, h_saida, relatorio, status_final):
                        st.success("Atualizado!")
                        st.rerun()
        else:
            st.warning("Não existem missões agendadas para hoje ou para datas passadas.")
    else:
        st.write("Nenhuma missão encontrada no sistema.")

# --- ABA 2: GESTÃO ---
with menu[2]:
    if not st.session_state.gestao_liberada:
        st.warning("🔒 Área Restrita.")
        chave_input = st.text_input("Chave de Comando:", type="password")
        if st.button("Liberar"):
            if chave_input == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True
                st.rerun()
    else:
        st.button("🔒 Bloquear", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        tab_cad, tab_del = st.tabs(["📝 Agendar", "🗑️ Apagar"])
        with tab_cad:
            col1, col2 = st.columns(2)
            with col1:
                data_ag = st.date_input("Data", datetime.date.today())
                unid_ag = st.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
            with col2:
                cidade_ag = st.selectbox("Município", todas_cidades)
                missao_ag = st.text_area("Missão")
            if st.button("Salvar"):
                salvar_no_db(data_ag, cidade_ag, unid_ag, missao_ag)
                st.success("Agendado!")
                st.rerun()
        with tab_del:
            df_del = carregar_dados_db().sort_values(by='data', ascending=False)
            if not df_del.empty:
                df_del['view'] = df_del['data'] + " | " + df_del['municipio']
                sel = st.selectbox("Apagar:", df_del['view'].tolist())
                id_alvo = df_del[df_del['view'] == sel]['id'].values[0]
                if st.button("Excluir"):
                    apagar_no_db(id_alvo)
                    st.rerun()

# --- 7. HISTÓRICO ---
st.markdown("---")
with st.expander("📊 Histórico de Cumprimento"):
    df_hist = carregar_dados_db()
    if not df_hist.empty:
        df_hist = df_hist.sort_values(by='data', ascending=False)
        df_hist['Dia da Semana'] = df_hist['data'].apply(obter_dia_semana)
        colunas_final = ['data', 'Dia da Semana', 'municipio', 'unidade', 'cumprido', 'hora_entrada', 'hora_saida', 'relatorio_resumido']
        df_exibir = df_hist[colunas_final].copy()
        df_exibir.columns = ['Data', 'Dia da Semana', 'Município', 'Unidade', 'Cumprido', 'Entrada', 'Saída', 'Relatório']
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)
