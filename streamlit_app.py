import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES E CONEXÃO ---
CHAVE_GESTAO = "comando2026"
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="SISPOSIÇÃO - PMBA - CPR-ES", layout="wide", page_icon="🛡️")

# --- 2. CABEÇALHO ---
col_logo1, col_logo2, col_logo3 = st.columns([0.5, 2.0, 0.5])
with col_logo2:
    try: st.image("logo_unidade.jpeg", use_container_width=True) 
    except: pass

st.markdown("<div style='text-align: center;'><h1>🛡️ SISPOSIÇÃO</h1><p>Sistema de Policiamento Sem Sobreposição — CPR-ES</p><hr></div>", unsafe_allow_html=True)

# --- 3. LÓGICA DE AUTENTICAÇÃO ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

try:
    session_res = supabase.auth.get_session()
    if session_res and session_res.session:
        st.session_state.user_session = session_res.user
except:
    pass

if st.session_state.user_session is None:
    aba_auth = st.tabs(["🔐 Entrar", "📝 Cadastrar-se"])
    
    with aba_auth[0]:
        with st.form("login_form"):
            email_in = st.text_input("E-mail") 
            senha_in = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_in, "password": senha_in})
                    if res.user:
                        # VERIFICAÇÃO DE E-MAIL CONFIRMADO
                        if res.user.email_confirmed_at is None:
                            st.warning("⚠️ Seu e-mail ainda não foi confirmado. Verifique sua caixa de entrada (ou spam) e clique no link de ativação.")
                        else:
                            st.session_state.user_session = res.user
                            st.toast("Acesso autorizado!", icon="✅")
                            st.rerun()
                except Exception as e:
                    st.error(f"Erro no login: {e}")

    with aba_auth[1]:
        st.info("⚠️ Um e-mail de confirmação será enviado após o cadastro.")
        with st.form("register_form"):
            p_g_reg = st.selectbox("Posto/Graduação", ["Cel", "Ten Cel", "Maj", "Cap", "1º Ten", "Subten", "1º Sgt", "2º Sgt", "3º Sgt", "Cb", "Sd"])
            nome_reg = st.text_input("Nome Completo")
            mat_reg = st.text_input("Matrícula")
            st.divider()
            email_reg = st.text_input("E-mail")
            pass_reg = st.text_input("Senha (mín. 6 caracteres)", type="password")
            confirm = st.text_input("Confirme a Senha", type="password")
            
            if st.form_submit_button("Finalizar Cadastro", use_container_width=True):
                if pass_reg != confirm: st.error("Senhas não coincidem.")
                else:
                    try:
                        supabase.auth.sign_up({
                            "email": email_reg, "password": pass_reg,
                            "options": {"data": {"posto_grad": p_g_reg, "nome_completo": nome_reg, "matricula": mat_reg}}
                        })
                        st.success("✅ Cadastro solicitado!")
                        st.info(f"Enviamos um link de confirmação para **{email_reg}**. O acesso só será liberado após a confirmação.")
                    except Exception as e: st.error(f"Erro: {e}")
    st.stop()

# --- 4. ÁREA LOGADA ---
user_email = st.session_state.user_session.email
user_meta = st.session_state.user_session.user_metadata

def carregar_dados_db():
    try:
        res = supabase.table("escala_operacional").select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

with st.sidebar:
    st.markdown(f"### 👮 {user_meta.get('posto_grad', '')} {user_meta.get('nome_completo', 'Usuário')}")
    st.caption(f"Matrícula: {user_meta.get('matricula', '')}")
    if st.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"])

# --- ABA CONSULTA ---
with menu[0]:
    dt_con = st.date_input("Data:", datetime.date.today())
    df = carregar_dados_db()
    if not df.empty:
        df_d = df[df['data'] == dt_con.strftime("%Y-%m-%d")]
        if not df_d.empty:
            df_d['Estado'] = df_d['cumprido'].map({True: "✅ Cumprida", False: "⚠️ Em Aberto"})
            st.dataframe(df_d[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)

# --- ABA CUMPRIMENTO ---
with menu[1]:
    df_c = carregar_dados_db()
    if not df_c.empty:
        df_c['sel'] = df_c['data'] + " | " + df_c['municipio']
        sel_missao = st.selectbox("Missão:", df_c['sel'].tolist())
        d = df_c[df_c['sel'] == sel_missao].iloc[0]
        with st.form("f_c"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Comandante", d.get('comandante_nome') or f"{user_meta.get('posto_grad')} {user_meta.get('nome_completo')}")
            m = c2.text_input("Matrícula", d.get('comandante_matricula') or user_meta.get('matricula'))
            rel = st.text_area("Relatório", d.get('relatorio_resumido', ''))
            conf = st.checkbox("Confirmar", value=bool(d.get('cumprido')))
            if st.form_submit_button("Salvar"):
                supabase.table("escala_operacional").update({
                    "comandante_nome": n, "comandante_matricula": m, 
                    "relatorio_resumido": rel, "cumprido": conf,
                    "editado_por": user_email, "ultima_edicao": datetime.datetime.now().isoformat()
                }).eq("id", d['id']).execute()
                st.success("Salvo!"); st.rerun()

# --- ABA GESTÃO ---
with menu[3]:
    if not st.session_state.get("gestao_liberada", False):
        with st.form("f_lock"):
            if st.form_submit_button("Desbloquear") and st.text_input("Chave:", type="password") == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True; st.rerun()
    else:
        with st.form("f_new"):
            dt = st.date_input("Data")
            mu = st.selectbox("Cidade", ["Porto Seguro", "Eunápolis", "Teixeira de Freitas", "Itamaraju", "Prado"])
            un = st.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
            ob = st.text_area("Objetivo")
            if st.form_submit_button("Agendar"):
                supabase.table("escala_operacional").insert({
                    "data": str(dt), "municipio": mu, "unidade": un, "missao": ob, "criado_por": user_email
                }).execute()
                st.rerun()
