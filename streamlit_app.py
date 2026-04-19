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

# --- 3. LÓGICA DE AUTENTICAÇÃO (SUPABASE AUTH) ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

# Tenta recuperar sessão ativa
try:
    session = supabase.auth.get_session()
    st.session_state.user_session = session.user if session else None
except:
    st.session_state.user_session = None

if not st.session_state.user_session:
    aba_auth = st.tabs(["🔐 Entrar", "📝 Cadastrar-se"])
    
    with aba_auth[0]:
        with st.form("login_form"):
            email = st.text_input("E-mail Funcional")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user_session = res.user
                    st.rerun()
                except:
                    st.error("E-mail ou senha incorretos.")

    with aba_auth[1]:
        st.info("O cadastro permite o acesso às escalas e registro de cumprimento.")
        with st.form("register_form"):
            new_email = st.text_input("E-mail para Cadastro")
            new_senha = st.text_input("Senha (mín. 6 caracteres)", type="password")
            confirm = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro", use_container_width=True):
                if new_senha != confirm: st.error("Senhas não coincidem.")
                elif len(new_senha) < 6: st.warning("Senha muito curta.")
                else:
                    try:
                        supabase.auth.sign_up({"email": new_email, "password": new_senha})
                        st.success("Cadastro realizado! Você já pode tentar o login.")
                    except Exception as e: st.error(f"Erro: {e}")
    st.stop()

# --- 4. FUNÇÕES DE DADOS ---
def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        df = pd.DataFrame(response.data)
        colunas = ['id', 'data', 'municipio', 'unidade', 'missao', 'cumprido', 'hora_entrada', 'hora_saida', 'relatorio_resumido', 'comandante_nome', 'comandante_matricula', 'viatura']
        for col in colunas:
            if col not in df.columns: df[col] = None
        return df
    except: return pd.DataFrame()

def atualizar_cumprimento(id_reg, ent, sai, rel, status, nome, mat, vtr):
    supabase.table("escala_operacional").update({
        "hora_entrada": ent, "hora_saida": sai, "relatorio_resumido": rel, 
        "cumprido": status, "comandante_nome": nome, "comandante_matricula": mat, "viatura": vtr
    }).eq("id", id_reg).execute()

def formatar_data_br(data_iso):
    return datetime.datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")

lista_horas = [f"{h:02d}:00" for h in range(24)]

# --- 5. INTERFACE PRINCIPAL ---
with st.sidebar:
    st.write(f"👤 **Usuário:** {st.session_state.user_session.email}")
    if st.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"])

# ABA 0: CONSULTA
with menu[0]:
    data_con = st.date_input("Data:", datetime.date.today())
    df = carregar_dados_db()
    regioes = {
        "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
        "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
    }
    for reg, cidades in regioes.items():
        df_dia = df[(df['data'] == data_con.strftime("%Y-%m-%d")) & (df['municipio'].isin(cidades))] if not df.empty else pd.DataFrame()
        if not df_dia.empty:
            st.markdown(f"#### 📍 {reg}")
            df_dia['Estado'] = df_dia['cumprido'].map({True: "✅ Cumprida", False: "⚠️ Em Aberto"})
            st.dataframe(df_dia[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)

# ABA 1: CUMPRIMENTO
with menu[1]:
    df_c = carregar_dados_db()
    if not df_c.empty:
        df_c['sel'] = df_c['data'].apply(formatar_data_br) + " | " + df_c['municipio']
        escolha = st.selectbox("Selecione a Missão:", df_c['sel'].tolist())
        d = df_c[df_c['sel'] == escolha].iloc[0]
        with st.form("f_c"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Cmt Nome", d['comandante_nome'])
            m = c2.text_input("Matrícula", d['comandante_matricula'])
            v = c3.text_input("Vtr", d['viatura'])
            h_e = st.selectbox("Entrada", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
            h_s = st.selectbox("Saída", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
            rel = st.text_area("Relatório", d['relatorio_resumido'])
            conf = st.checkbox("Confirmar Cumprimento", value=bool(d['cumprido']))
            if st.form_submit_button("Salvar"):
                atualizar_cumprimento(d['id'], h_e, h_s, rel, conf, n, m, v)
                st.success("Salvo!"); st.rerun()

# ABA 2: ESTATÍSTICAS
with menu[2]:
    df_e = carregar_dados_db()
    if not df_e.empty:
        df_e['data_dt'] = pd.to_datetime(df_e['data'])
        df_e['Mês'] = df_e['data_dt'].dt.strftime('%m/%Y')
        st.markdown("### 📅 Mensal"); st.line_chart(df_e['Mês'].value_counts())
        st.markdown("### 🏙️ Por Cidade"); st.bar_chart(df_e['municipio'].value_counts(), horizontal=True)

# ABA 3: GESTÃO
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
                mu = st.selectbox("Cidade", sorted(regioes["Costa do Descobrimento"] + regioes["Costa das Baleias"]))
                un = st.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
                he = st.selectbox("Entrada", lista_horas)
                hs = st.selectbox("Saída", lista_horas)
                ob = st.text_area("Missão")
                if st.form_submit_button("Agendar"):
                    supabase.table("escala_operacional").insert({
                        "data": str(dt), "municipio": mu, "unidade": un, 
                        "missao": ob, "hora_entrada": he, "hora_saida": hs
                    }).execute()
                    st.rerun()
        # Lista para exclusão
        st.subheader("Excluir Registros")
        df_del = carregar_dados_db()
        if not df_del.empty:
            sel_del = st.selectbox("Excluir:", (df_del['data'] + " | " + df_del['municipio']).tolist())
            id_del = df_del[(df_del['data'] + " | " + df_del['municipio']) == sel_del]['id'].values[0]
            if st.button("Confirmar Exclusão"):
                supabase.table("escala_operacional").delete().eq("id", id_del).execute()
                st.rerun()
