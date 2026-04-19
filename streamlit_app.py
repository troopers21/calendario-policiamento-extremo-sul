import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES ---
CHAVE_GESTAO = "comando2026"
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="SISPOSIÇÃO - PMBA - CPR-ES", layout="wide", page_icon="🛡️")

# --- 2. CABEÇALHO ---
col_logo1, col_logo2, col_logo3 = st.columns([0.5, 2.0, 0.5])
with col_logo2:
    try:
        st.image("logo_unidade.jpeg", use_container_width=True) 
    except: pass

st.markdown("<div style='text-align: center;'><h1>🛡️ SISPOSIÇÃO</h1><p>Sistema de Policiamento Sem Sobreposição — CPR-ES</p><hr></div>", unsafe_allow_html=True)

# --- 3. AUTENTICAÇÃO ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

try:
    session = supabase.auth.get_session()
    st.session_state.user_session = session.user if session else None
except:
    st.session_state.user_session = None

if not st.session_state.user_session:
    aba_auth = st.tabs(["🔐 Entrar", "📝 Cadastrar-se"])
    with aba_auth[0]:
        with st.form("login"):
            e = st.text_input("E-mail") # Texto alterado conforme solicitado
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": e, "password": s})
                    st.session_state.user_session = res.user
                    st.rerun()
                except: st.error("Erro no login.")
    with aba_auth[1]:
        with st.form("reg"):
            ne = st.text_input("E-mail para Cadastro")
            ns = st.text_input("Senha (mín. 6 chars)", type="password")
            if st.form_submit_button("Cadastrar"):
                try:
                    supabase.auth.sign_up({"email": ne, "password": ns})
                    st.success("Cadastro pronto! Pode logar.")
                except Exception as ex: st.error(f"Erro: {ex}")
    st.stop()

# --- 4. FUNÇÕES COM AUDITORIA ---
user_email = st.session_state.user_session.email

def carregar_dados():
    res = supabase.table("escala_operacional").select("*").execute()
    return pd.DataFrame(res.data)

def formatar_data_br(d_iso):
    return datetime.datetime.strptime(d_iso, "%Y-%m-%d").strftime("%d/%m/%Y")

lista_horas = [f"{h:02d}:00" for h in range(24)]

# --- 5. INTERFACE ---
with st.sidebar:
    st.write(f"👤 **Logado:**\n{user_email}")
    if st.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"])

with menu[1]: # CUMPRIMENTO COM LOG
    df = carregar_dados()
    if not df.empty:
        df['sel'] = df['data'].apply(formatar_data_br) + " | " + df['municipio']
        item = st.selectbox("Missão:", df['sel'].tolist())
        d = df[df['sel'] == item].iloc[0]
        with st.form("f_cump"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Comandante", d.get('comandante_nome', ''))
            m = c2.text_input("Matrícula", d.get('comandante_matricula', ''))
            v = c3.text_input("Vtr", d.get('viatura', ''))
            rel = st.text_area("Relatório", d.get('relatorio_resumido', ''))
            conf = st.checkbox("Confirmar", value=bool(d.get('cumprido')))
            if st.form_submit_button("Salvar"):
                supabase.table("escala_operacional").update({
                    "comandante_nome": n, "comandante_matricula": m, "viatura": v,
                    "relatorio_resumido": rel, "cumprido": conf,
                    "editado_por": user_email, "ultima_edicao": datetime.datetime.now().isoformat()
                }).eq("id", d['id']).execute()
                st.success("Atualizado!"); st.rerun()

with menu[3]: # GESTÃO COM LOG
    if not st.session_state.get("gestao_liberada", False):
        with st.form("f_gest"):
            if st.form_submit_button("Desbloquear") and st.text_input("Chave:", type="password") == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True; st.rerun()
    else:
        with st.form("nova_m"):
            dt = st.date_input("Data")
            mu = st.selectbox("Cidade", ["Porto Seguro", "Eunápolis", "Teixeira de Freitas", "Itamaraju", "Prado", "Mucuri"])
            un = st.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
            ms = st.text_area("Missão")
            if st.form_submit_button("Agendar"):
                supabase.table("escala_operacional").insert({
                    "data": str(dt), "municipio": mu, "unidade": un, "missao": ms,
                    "criado_por": user_email # Log de criação
                }).execute()
                st.rerun()
        
        st.subheader("Auditoria de Alterações")
        st.dataframe(carregar_dados()[['data', 'municipio', 'criado_por', 'editado_por', 'ultima_edicao']], use_container_width=True)
