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

st.markdown("""
    <div style='text-align: center;'>
        <h1>🛡️ SISPOSIÇÃO</h1>
        <p>Sistema de Policiamento Sem Sobreposição — CPR-ES</p>
        <hr>
    </div>
""", unsafe_allow_html=True)

# --- 3. AUTENTICAÇÃO ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

try:
    session_res = supabase.auth.get_session()
    st.session_state.user_session = session_res.user if session_res and session_res.session else None
except:
    st.session_state.user_session = None

if not st.session_state.user_session:
    aba_auth = st.tabs(["🔐 Entrar", "📝 Cadastrar-se"])
    
    with aba_auth[0]:
        with st.form("login_form"):
            email_in = st.text_input("E-mail") 
            senha_in = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_in, "password": senha_in})
                    if res.user:
                        st.session_state.user_session = res.user
                        st.rerun()
                except Exception as e: st.error(f"Erro no login: {e}")

    with aba_auth[1]:
        with st.form("register_form"):
            p_g_reg = st.selectbox("Posto/Graduação", ["Cel", "Ten Cel", "Maj", "Cap", "1º Ten", "Subten", "1º Sgt", "2º Sgt", "3º Sgt", "Cb", "Sd"])
            nome_reg = st.text_input("Nome Completo")
            mat_reg = st.text_input("Matrícula (ex: 12.345-6)")
            st.divider()
            email_reg = st.text_input("E-mail para Cadastro")
            pass_reg = st.text_input("Senha (mín. 6 caracteres)", type="password")
            confirm = st.text_input("Confirme a Senha", type="password")
            
            if st.form_submit_button("Finalizar Cadastro", use_container_width=True):
                if not nome_reg or not mat_reg: st.error("Preencha Nome e Matrícula.")
                elif pass_reg != confirm: st.error("As senhas não coincidem.")
                else:
                    try:
                        supabase.auth.sign_up({
                            "email": email_reg, "password": pass_reg,
                            "options": {"data": {"posto_grad": p_g_reg, "nome_completo": nome_reg, "matricula": mat_reg}}
                        })
                        st.success("Cadastro realizado! Tente logar na aba 'Entrar'.")
                    except Exception as e:
                        if "rate limit" in str(e).lower():
                            st.error("Muitas tentativas seguidas. Aguarde alguns minutos e tente novamente.")
                        else:
                            st.error(f"Erro ao cadastrar: {e}")
    st.stop()

# --- 4. VARIÁVEIS DE SESSÃO ---
user_email = st.session_state.user_session.email
meta = st.session_state.user_session.user_metadata
p_g_user = meta.get("posto_grad", "")
nome_user = meta.get("nome_completo", "Usuário")
mat_user = meta.get("matricula", "")

def carregar_dados_db():
    try:
        res = supabase.table("escala_operacional").select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

lista_horas = [f"{h:02d}:00" for h in range(24)]

# --- 5. INTERFACE SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👮 {p_g_user} {nome_user}")
    st.caption(f"Matrícula: {mat_user}")
    if st.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"])

# ABA CONSULTA
with menu[0]:
    dt_con = st.date_input("Data:", datetime.date.today())
    df = carregar_dados_db()
    if not df.empty:
        df_d = df[df['data'] == dt_con.strftime("%Y-%m-%d")]
        if not df_d.empty:
            df_d['Estado'] = df_d['cumprido'].map({True: "✅ Cumprida", False: "⚠️ Em Aberto"})
            st.dataframe(df_d[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)

# ABA CUMPRIMENTO
with menu[1]:
    df_c = carregar_dados_db()
    if not df_c.empty:
        df_c['sel'] = df_c['data'] + " | " + df_c['municipio']
        sel = st.selectbox("Missão:", df_c['sel'].tolist())
        d = df_c[df_c['sel'] == sel].iloc[0]
        with st.form("f_c"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Cmt", d.get('comandante_nome') or f"{p_g_user} {nome_user}")
            m = c2.text_input("Matrícula", d.get('comandante_matricula') or mat_user)
            v = c3.text_input("Vtr", d.get('viatura', ''))
            h_e = st.selectbox("Entrada", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
            h_s = st.selectbox("Saída", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
            rel = st.text_area("Relatório", d.get('relatorio_resumido', ''))
            conf = st.checkbox("Confirmar", value=bool(d.get('cumprido')))
            if st.form_submit_button("Salvar"):
                supabase.table("escala_operacional").update({
                    "comandante_nome": n, "comandante_matricula": m, "viatura": v,
                    "hora_entrada": h_e, "hora_saida": h_s, "relatorio_resumido": rel, "cumprido": conf,
                    "editado_por": user_email, "ultima_edicao": datetime.datetime.now().isoformat()
                }).eq("id", d['id']).execute()
                st.success("Atualizado!"); st.rerun()

# ABA ESTATÍSTICA
with menu[2]:
    df_e = carregar_dados_db()
    if not df_e.empty:
        st.markdown("### 🏙️ Por Cidade"); st.bar_chart(df_e['municipio'].value_counts(), horizontal=True)

# ABA GESTÃO
with menu[3]:
    if not st.session_state.get("gestao_liberada", False):
        with st.form("f_lock"):
            if st.form_submit_button("Desbloquear") and st.text_input("Chave:", type="password") == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True; st.rerun()
    else:
        st.button("🔒 Bloquear", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        with st.expander("➕ Agendar"):
            with st.form("f_new"):
                dt_n = st.date_input("Data")
                mu_n = st.selectbox("Cidade", ["Porto Seguro", "Eunápolis", "Teixeira de Freitas", "Itamaraju"])
                un_n = st.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
                ob_n = st.text_area("Missão")
                if st.form_submit_button("Salvar"):
                    supabase.table("escala_operacional").insert({
                        "data": str(dt_n), "municipio": mu_n, "unidade": un_n, "missao": ob_n, "criado_por": user_email
                    }).execute()
                    st.rerun()
        st.subheader("Auditoria")
        df_a = carregar_dados_db()
        if not df_a.empty:
            st.dataframe(df_a[['data', 'municipio', 'criado_por', 'editado_por']], use_container_width=True)
