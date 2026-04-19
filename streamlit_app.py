import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES E BANCO ---
CHAVE_GESTAO = "comando2026"

# Conexão com Supabase via Secrets
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="SISPOSIÇÃO - PMBA - CPR-ES", layout="wide", page_icon="🛡️")

# --- 2. CABEÇALHO INSTITUCIONAL ---
col_logo1, col_logo2, col_logo3 = st.columns([0.5, 2.0, 0.5])
with col_logo2:
    try:
        st.image("logo_unidade.jpeg", use_container_width=True) 
    except:
        pass

st.markdown("""
    <div style='text-align: center;'>
        <h1 style='margin-bottom: 0;'>🛡️ SISPOSIÇÃO</h1>
        <p style='font-size: 1.2em; color: gray;'>Sistema de Policiamento Sem Sobreposição — CPR-ES</p>
        <hr style='margin-top: 0;'>
    </div>
""", unsafe_allow_html=True)

# --- 3. LÓGICA DE AUTENTICAÇÃO (E-MAIL E SENHA) ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

# Recuperar sessão
try:
    session = supabase.auth.get_session()
    st.session_state.user_session = session.user if session else None
except:
    st.session_state.user_session = None

if not st.session_state.user_session:
    aba_auth = st.tabs(["🔐 Entrar", "📝 Cadastrar-se"])
    
    with aba_auth[0]:
        with st.form("login_form"):
            email = st.text_input("E-mail") 
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user_session = res.user
                    st.rerun()
                except Exception as e:
                    # DICA DE ERRO ATIVADA: Mostra o motivo real do erro
                    st.error(f"Erro no login: {e}")

    with aba_auth[1]:
        st.info("O cadastro permite o acesso às escalas e registro de cumprimento.")
        with st.form("register_form"):
            new_email = st.text_input("E-mail para Cadastro")
            new_senha = st.text_input("Senha (mín. 6 caracteres)", type="password")
            confirm = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro", use_container_width=True):
                if new_senha != confirm: st.error("Senhas não coincidem.")
                elif len(new_senha) < 6: st.warning("Senha muito curta (mínimo 6 caracteres).")
                else:
                    try:
                        supabase.auth.sign_up({"email": new_email, "password": new_senha})
                        st.success("Cadastro realizado! Se o 'Confirm Email' estiver OFF no Supabase, já pode logar.")
                    except Exception as e: st.error(f"Erro ao cadastrar: {e}")
    st.stop()

# --- 4. FUNÇÕES DE DADOS COM AUDITORIA ---
user_email = st.session_state.user_session.email

def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        df = pd.DataFrame(response.data)
        return df
    except: return pd.DataFrame()

def formatar_data_br(data_iso):
    return datetime.datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")

lista_horas = [f"{h:02d}:00" for h in range(24)]

# --- 5. INTERFACE PRINCIPAL ---
with st.sidebar:
    st.write(f"👤 **Usuário:**\n{user_email}")
    if st.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"])

# ABA 0: CONSULTA
with menu[0]:
    data_con = st.date_input("Data:", datetime.date.today())
    df = carregar_dados_db()
    if not df.empty:
        df_dia = df[df['data'] == data_con.strftime("%Y-%m-%d")]
        if not df_dia.empty:
            df_dia['Estado'] = df_dia['cumprido'].map({True: "✅ Cumprida", False: "⚠️ Em Aberto"})
            st.dataframe(df_dia[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)
        else: st.info("Sem missões para esta data.")

# ABA 1: CUMPRIMENTO (REGISTRA QUEM EDITOU)
with menu[1]:
    df_c = carregar_dados_db()
    if not df_c.empty:
        df_c['sel'] = df_c['data'].apply(formatar_data_br) + " | " + df_c['municipio']
        escolha = st.selectbox("Selecione a Missão:", df_c['sel'].tolist())
        d = df_c[df_c['sel'] == escolha].iloc[0]
        with st.form("f_c"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Cmt Nome", d.get('comandante_nome', ''))
            m = c2.text_input("Matrícula", d.get('comandante_matricula', ''))
            v = c3.text_input("Vtr", d.get('viatura', ''))
            h_e = st.selectbox("Entrada", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
            h_s = st.selectbox("Saída", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
            rel = st.text_area("Relatório", d.get('relatorio_resumido', ''))
            conf = st.checkbox("Confirmar Cumprimento", value=bool(d.get('cumprido', False)))
            if st.form_submit_button("Salvar Alterações"):
                supabase.table("escala_operacional").update({
                    "comandante_nome": n, "comandante_matricula": m, "viatura": v,
                    "hora_entrada": h_e, "hora_saida": h_s, "relatorio_resumido": rel, "cumprido": conf,
                    "editado_por": user_email, 
                    "ultima_edicao": datetime.datetime.now().isoformat()
                }).eq("id", d['id']).execute()
                st.success("Atualizado com sucesso!"); st.rerun()

# ABA 2: ESTATÍSTICAS
with menu[2]:
    df_e = carregar_dados_db()
    if not df_e.empty:
        df_e['data_dt'] = pd.to_datetime(df_e['data'])
        df_e['Mês'] = df_e['data_dt'].dt.strftime('%m/%Y')
        col_e1, col_e2 = st.columns(2)
        with col_e1: st.markdown("### 📅 Por Mês"); st.bar_chart(df_e['Mês'].value_counts())
        with col_e2: st.markdown("### 🏙️ Por Cidade"); st.bar_chart(df_e['municipio'].value_counts(), horizontal=True)

# ABA 3: GESTÃO (REGISTRA QUEM CRIOU)
with menu[3]:
    if not st.session_state.get("gestao_liberada", False):
        with st.form("f_g"):
            ch = st.text_input("Chave de Comando:", type="password")
            if st.form_submit_button("Desbloquear"):
                if ch == CHAVE_GESTAO: st.session_state.gestao_liberada = True; st.rerun()
                else: st.error("Chave incorreta.")
    else:
        st.button("🔒 Bloquear", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        with st.expander("➕ Nova Missão"):
            with st.form("f_n"):
                dt = st.date_input("Data")
                mu = st.selectbox("Cidade", ["Porto Seguro", "Eunápolis", "Teixeira de Freitas", "Itamaraju", "Prado", "Mucuri", "Eunápolis"])
                un = st.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
                ob = st.text_area("Objetivo da Missão")
                if st.form_submit_button("Agendar"):
                    supabase.table("escala_operacional").insert({
                        "data": str(dt), "municipio": mu, "unidade": un, "missao": ob,
                        "criado_por": user_email
                    }).execute()
                    st.success("Agendado!"); st.rerun()
        
        st.subheader("🕵️ Auditoria de Sistema")
        df_audit = carregar_dados_db()
        if not df_audit.empty:
            st.dataframe(df_audit[['data', 'municipio', 'criado_por', 'editado_por', 'ultima_edicao']], use_container_width=True, hide_index=True)
