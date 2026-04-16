import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES E BANCO ---
USUARIO_CORRETO = "admin"
SENHA_CORRETA = "pmba2026"
CHAVE_GESTAO = "comando2026"

url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Sistema de Policiamento - PMBA", layout="wide")

# --- 2. LOGO NO TOPO ---
col_logo1, col_logo2, col_logo3 = st.columns([2, 1, 2])
with col_logo2:
    try:
        st.image("logo_unidade.jpeg", width=900) 
    except:
        pass

st.markdown("<h1 style='text-align: center;'>📅 Sistema Operacional - Extremo Sul</h1>", unsafe_allow_html=True)

# --- 3. FUNÇÕES DE SUPORTE ---
def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        df = pd.DataFrame(response.data)
        colunas = ['id', 'data', 'municipio', 'unidade', 'missao', 'cumprido', 'hora_entrada', 'hora_saida', 'relatorio_resumido', 'comandante_nome', 'comandante_matricula']
        for col in colunas:
            if col not in df.columns: df[col] = None
        return df
    except:
        return pd.DataFrame(columns=['id', 'data', 'municipio', 'unidade', 'missao'])

def atualizar_cumprimento(id_registro, entrada, saida, relatorio, status_bool, nome, matricula):
    try:
        supabase.table("escala_operacional").update({
            "hora_entrada": entrada,
            "hora_saida": saida,
            "relatorio_resumido": relatorio,
            "cumprido": status_bool,
            "comandante_nome": nome,
            "comandante_matricula": matricula
        }).eq("id", id_registro).execute()
        return True
    except: return False

def salvar_no_db(data, municipio, unidade, missao):
    supabase.table("escala_operacional").insert({
        "data": data.strftime("%Y-%m-%d"), 
        "municipio": municipio, 
        "unidade": unidade, 
        "missao": missao, 
        "cumprido": False
    }).execute()

def apagar_no_db(id_registro):
    try:
        supabase.table("escala_operacional").delete().eq("id", id_registro).execute()
        return True
    except: return False

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

# --- 4. LÓGICA DE AUTENTICAÇÃO (CORRIGIDA) ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "gestao_liberada" not in st.session_state:
    st.session_state.gestao_liberada = False

if not st.session_state.autenticado:
    # Centralização usando colunas em vez de st.center()
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        with st.form("login"):
            st.subheader("🔐 Login de Acesso")
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if u == USUARIO_CORRETO and p == SENHA_CORRETA:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
    st.stop()

# --- 5. INTERFACE PRINCIPAL ---
if st.sidebar.button("Logoff"):
    st.session_state.autenticado = False
    st.session_state.gestao_liberada = False
    st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "⚙️ Gestão"])

# ABA CONSULTA
with menu[0]:
    data_con = st.date_input("Filtrar por Dia", datetime.date.today())
    df_total = carregar_dados_db()
    
    regioes = {
        "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
        "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
    }

    for regiao, cidades in regioes.items():
        st.markdown(f"#### 📍 {regiao}")
        rows = []
        for cid in cidades:
            rows.append({"Município": cid, "Ocupação": "Livre", "Status": "Pendente"})
        df_reg = pd.DataFrame(rows)
        if not df_total.empty:
            df_dia = df_total[df_total['data'] == data_con.strftime("%Y-%m-%d")]
            for _, r in df_dia.iterrows():
                if r['municipio'] in cidades:
                    txt = "✅ Cumprido" if r.get('cumprido') is True else "⚠️ Escalado"
                    df_reg.loc[df_reg['Município'] == r['municipio'], ['Ocupação', 'Status']] = [r['unidade'], txt]
        st.dataframe(df_reg.style.map(color_status, subset=['Ocupação']), use_container_width=True, hide_index=True)

# ABA CUMPRIMENTO (REGISTRO ÚNICO E CHECKBOX SIM)
with menu[1]:
    st.subheader("Registrar Cumprimento")
    df_raw = carregar_dados_db()
    
    if not df_raw.empty:
        hoje = datetime.date.today().strftime("%Y-%m-%d")
        df_cump = df_raw[df_raw['data'] <= hoje].copy()
        
        if not df_cump.empty:
            df_cump['selecao'] = df_cump['data'] + " | " + df_cump['municipio']
            sel = st.selectbox("Selecione a Missão:", df_cump['selecao'].tolist())
            d = df_cump[df_cump['selecao'] == sel].iloc[0]
            
            ja_cumprido = d.get('cumprido') is True

            with st.form("f_cump_novo"):
                col1, col2 = st.columns(2)
                n = col1.text_input("Comandante da Guarnição", value=str(d.get('comandante_nome') or ""))
                m = col2.text_input("Matrícula", value=str(d.get('comandante_matricula') or ""))
                e = col1.text_input("Hora de Entrada na Cidade", value=str(d.get('hora_entrada') or ""))
                s = col2.text_input("Hora de Saída na Cidade", value=str(d.get('hora_saida') or ""))
                
                confirmar = st.checkbox("Sim", value=ja_cumprido, help="Marque para confirmar o cumprimento da missão")
                
                rel = st.text_area("Resumo da Missão", value=str(d.get('relatorio_resumido') or ""))
                
                if st.form_submit_button("Salvar Registro"):
                    if ja_cumprido:
                        st.warning("Esta missão já possui um registro salvo. Alterações serão sobrescritas.")
                    
                    if not confirmar:
                        st.error("Marque a caixa 'Sim' para validar o cumprimento.")
                    else:
                        if atualizar_cumprimento(d['id'], e, s, rel, confirmar, n, m):
                            st.success("Missão registrada!")
                            st.rerun()
        else:
            st.info("Nenhuma missão pendente para hoje ou datas passadas.")

# ABA GESTÃO
with menu[2]:
    if not st.session_state.gestao_liberada:
        ch = st.text_input("Chave de Comando:", type="password")
        if st.button("Liberar Acesso"):
            if ch == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True
                st.rerun()
    else:
        st.button("🔒 Bloquear", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        t1, t2 = st.tabs(["📝 Agendar", "🗑️ Apagar"])
        with t1:
            todas_cidades = ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela", "Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
            c1, c2 = st.columns(2)
            dt = c1.date_input("Data", datetime.date.today())
            un = c1.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
            mu = c2.selectbox("Município", sorted(todas_cidades))
            ms = c2.text_area("Missão")
            if st.button("Salvar Registro"):
                salvar_no_db(dt, mu, un, ms)
                st.rerun()
        with t2:
            df_del = carregar_dados_db().sort_values(by='data', ascending=False)
            if not df_del.empty:
                v = st.selectbox("Apagar:", (df_del['data'] + " | " + df_del['municipio']).tolist())
                id_a = df_del[(df_del['data'] + " | " + df_del['municipio']) == v]['id'].values[0]
                if st.button("Confirmar Exclusão"):
                    apagar_no_db(id_a)
                    st.rerun()

# --- 8. HISTÓRICO ---
with st.expander("📊 Histórico Completo"):
    df_h = carregar_dados_db()
    if not df_h.empty:
        df_h = df_h.sort_values(by='data', ascending=False)
        df_h['Dia da Semana'] = df_h['data'].apply(obter_dia_semana)
        df_h['Cumprida?'] = df_h['cumprido'].map({True: "Sim", False: "Não"}).fillna("-")
        st.dataframe(df_h[['data', 'Dia da Semana', 'municipio', 'unidade', 'comandante_nome', 'Cumprida?', 'hora_entrada', 'hora_saida', 'relatorio_resumido']], use_container_width=True, hide_index=True)
