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
                        if res.user.email_confirmed_at is None:
                            st.warning("⚠️ E-mail não confirmado. Verifique sua caixa de entrada.")
                        else:
                            st.session_state.user_session = res.user
                            st.rerun()
                except Exception as e:
                    st.error(f"Erro no login: {e}")

    with aba_auth[1]:
        st.info("⚠️ Um link de ativação será enviado ao e-mail informado.")
        with st.form("register_form"):
            # LISTA DE POSTOS/GRADUAÇÕES ATUALIZADA
            lista_postos = [
                "Cel PM", "Ten Cel PM", "Maj PM", "Cap PM", 
                "Ten PM", "Asp PM", "Subten PM", "Sgt PM", 
                "Cb PM", "Sd PM"
            ]
            posto_grad = st.selectbox("Posto/Graduação", lista_postos)
            nome_reg = st.text_input("Nome Completo")
            mat_reg = st.text_input("Matrícula")
            st.divider()
            email_reg = st.text_input("E-mail")
            pass_reg = st.text_input("Senha (mín. 6 caracteres)", type="password")
            confirm = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro", use_container_width=True):
                if pass_reg != confirm: st.error("Senhas não coincidem.")
                elif not nome_reg or not mat_reg: st.error("Preencha Nome e Matrícula.")
                else:
                    try:
                        supabase.auth.sign_up({"email": email_reg, "password": pass_reg,
                            "options": {"data": {"posto_grad": posto_grad, "nome_completo": nome_reg, "matricula": mat_reg}}})
                        st.success("✅ Cadastro solicitado! Verifique seu e-mail.")
                    except Exception as e: st.error(f"Erro: {e}")
    st.stop()

# --- 4. VARIÁVEIS E FUNÇÕES GERAIS ---
user_email = st.session_state.user_session.email
user_meta = st.session_state.user_session.user_metadata
p_g_user = user_meta.get("posto_grad", "")
nome_user = user_meta.get("nome_completo", "Usuário")
mat_user = user_meta.get("matricula", "")

def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        return pd.DataFrame(response.data)
    except: return pd.DataFrame()

def formatar_data_br(data_iso):
    try: return datetime.datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except: return data_iso

lista_horas = [f"{h:02d}:00" for h in range(24)]

territorios = {
    "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
    "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
}

# --- 5. INTERFACE SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👮 {p_g_user} {nome_user}")
    st.caption(f"Matrícula: {mat_user}")
    if st.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()

menu = st.tabs(["📋 Consulta de Escala", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"])

# --- ABA 0: CONSULTA ---
with menu[0]:
    data_con = st.date_input("Consultar Data:", datetime.date.today())
    df_total = carregar_dados_db()
    if not df_total.empty:
        for regiao, cidades in territorios.items():
            df_dia = df_total[(df_total['data'] == data_con.strftime("%Y-%m-%d")) & (df_total['municipio'].isin(cidades))]
            if not df_dia.empty:
                st.markdown(f"#### 📍 {regiao}")
                df_dia['Estado'] = df_dia['cumprido'].map({True: "✅ Cumprida", False: "⚠️ Em Aberto"})
                st.dataframe(df_dia[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)

# --- ABA 1: CUMPRIMENTO ---
with menu[1]:
    df_c = carregar_dados_db()
    if not df_c.empty:
        df_c['sel'] = df_c['data'].apply(formatar_data_br) + " | " + df_c['municipio']
        escolha = st.selectbox("Selecione a Missão:", df_c['sel'].tolist())
        d = df_c[df_c['sel'] == escolha].iloc[0]
        with st.form("f_cump"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Comandante", d.get('comandante_nome') or f"{p_g_user} {nome_user}")
            m = c2.text_input("Matrícula", d.get('comandante_matricula') or mat_user)
            v = c3.text_input("Viatura", d.get('viatura', ''))
            h_e = st.selectbox("Entrada Real", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
            h_s = st.selectbox("Saída Real", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
            rel = st.text_area("Relatório Resumido", d.get('relatorio_resumido', ''))
            conf = st.checkbox("Confirmar Cumprimento", value=bool(d.get('cumprido', False)))
            if st.form_submit_button("Salvar Registro"):
                supabase.table("escala_operacional").update({
                    "comandante_nome": n, "comandante_matricula": m, "viatura": v,
                    "hora_entrada": h_e, "hora_saida": h_s, "relatorio_resumido": rel, "cumprido": conf,
                    "editado_por": user_email, "ultima_edicao": datetime.datetime.now().isoformat()
                }).eq("id", d['id']).execute()
                st.success("Dados atualizados!"); st.rerun()

# --- ABA 2: ESTATÍSTICAS ---
with menu[2]:
    st.subheader("📊 Análise Estratégica")
    df_est = carregar_dados_db()
    if not df_est.empty:
        df_est['data_dt'] = pd.to_datetime(df_est['data'])
        df_est['Mês/Ano'] = df_est['data_dt'].dt.strftime('%m/%Y')
        map_cidades = {cidade: terr for terr, cidades in territorios.items() for cidade in cidades}
        df_est['Território'] = df_est['municipio'].map(map_cidades)
        
        st.markdown("### 📅 Mensal")
        st.line_chart(df_est['Mês/Ano'].value_counts())
        st.markdown("### 🌎 Por Território")
        st.bar_chart(df_est['Território'].value_counts())
        st.markdown("### 🏙️ Por Cidade")
        st.bar_chart(df_est['municipio'].value_counts(), horizontal=True)

# --- ABA 3: GESTÃO ---
with menu[3]:
    if not st.session_state.get("gestao_liberada", False):
        with st.form("f_gest"):
            ch = st.text_input("Chave de Comando:", type="password")
            if st.form_submit_button("Desbloquear Painel"):
                if ch == CHAVE_GESTAO: st.session_state.gestao_liberada = True; st.rerun()
                else: st.error("Chave incorreta.")
    else:
        st.button("🔒 Bloquear Painel", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        col_gest1, col_gest2 = st.columns(2)
        with col_gest1:
            st.subheader("📝 Agendar Nova Missão")
            with st.form("f_nova", clear_on_submit=True):
                dt = st.date_input("Data da Missão")
                todas_cidades = sorted(territorios["Costa do Descobrimento"] + territorios["Costa das Baleias"])
                mu = st.selectbox("Município", todas_cidades)
                un = st.selectbox("Unidade Responsável", ["CIPE-MA", "CIPT-ES"])
                h_e_ag = st.selectbox("Horário Previsto Entrada", lista_horas)
                h_s_ag = st.selectbox("Horário Previsto Saída", lista_horas)
                ob = st.text_area("Objetivo / Missão")
                if st.form_submit_button("Confirmar Agendamento"):
                    supabase.table("escala_operacional").insert({
                        "data": str(dt), "municipio": mu, "unidade": un, 
                        "missao": ob, "hora_entrada": h_e_ag, "hora_saida": h_s_ag, 
                        "criado_por": user_email
                    }).execute()
                    st.success("Missão agendada!"); st.rerun()
        with col_gest2:
            st.subheader("🗑️ Excluir Registro")
            df_del = carregar_dados_db().sort_values(by='data', ascending=False)
            if not df_del.empty:
                df_del['txt'] = df_del['data'].apply(formatar_data_br) + " | " + df_del['municipio'] + " (" + df_del['unidade'] + ")"
                it = st.selectbox("Selecione para apagar:", df_del['txt'].tolist())
                if st.button("❌ APAGAR DEFINITIVAMENTE", use_container_width=True):
                    id_del = df_del[df_del['txt'] == it]['id'].values[0]
                    supabase.table("escala_operacional").delete().eq("id", id_del).execute()
                    st.success("Registro removido!"); st.rerun()

        st.markdown("---")
        st.subheader("🕵️ Auditoria")
        df_audit = carregar_dados_db().sort_values(by='data', ascending=False)
        if not df_audit.empty:
            df_audit['Data_Formatada'] = df_audit['data'].apply(formatar_data_br)
            st.dataframe(df_audit[['Data_Formatada', 'municipio', 'unidade', 'criado_por', 'editado_por', 'ultima_edicao']], use_container_width=True, hide_index=True)
