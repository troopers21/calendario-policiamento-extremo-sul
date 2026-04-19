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
            # CAMPOS DE PERFIL ATUALIZADOS
            lista_postos = ["Cel PM", "Ten Cel PM", "Maj PM", "Cap PM", "Ten PM", "Asp PM", "Subten PM", "Sgt PM", "Cb PM", "Sd PM"]
            lista_unidades_cadastro = ["CPR-ES", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"]
            
            col_reg1, col_reg2 = st.columns(2)
            with col_reg1:
                posto_grad = st.selectbox("Posto/Graduação", lista_postos)
                nome_reg = st.text_input("Nome Completo")
            with col_reg2:
                unidade_reg = st.selectbox("Unidade", lista_unidades_cadastro)
                mat_reg = st.text_input("Matrícula")
            
            st.divider()
            email_reg = st.text_input("E-mail")
            pass_reg = st.text_input("Senha (mín. 6 caracteres)", type="password")
            confirm = st.text_input("Confirme a Senha", type="password")
            
            if st.form_submit_button("Finalizar Cadastro", use_container_width=True):
                if pass_reg != confirm: 
                    st.error("Senhas não coincidem.")
                elif not nome_reg or not mat_reg: 
                    st.error("Preencha todos os campos obrigatórios.")
                else:
                    try:
                        supabase.auth.sign_up({
                            "email": email_reg, 
                            "password": pass_reg,
                            "options": {
                                "data": {
                                    "posto_grad": posto_grad, 
                                    "nome_completo": nome_reg, 
                                    "matricula": mat_reg,
                                    "unidade": unidade_reg
                                }
                            }
                        })
                        st.success("✅ Cadastro solicitado! Verifique seu e-mail para ativar a conta.")
                    except Exception as e: 
                        st.error(f"Erro: {e}")
    st.stop()

# --- 4. VARIÁVEIS DO USUÁRIO LOGADO ---
user_email = st.session_state.user_session.email
user_meta = st.session_state.user_session.user_metadata
p_g_user = user_meta.get("posto_grad", "")
nome_user = user_meta.get("nome_completo", "Usuário")
mat_user = user_meta.get("matricula", "")
unidade_user = user_meta.get("unidade", "")

# Lógica de Acesso à aba Comandante (Oficiais)
postos_comando = ["Cel PM", "Ten Cel PM", "Maj PM", "Cap PM", "Ten PM"]
eh_comando = p_g_user in postos_comando

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
    st.caption(f"Unidade: {unidade_user} | Matrícula: {mat_user}")
    if st.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()

# Definição das Abas
titulos_abas = ["📋 Consulta de Escala", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"]
if eh_comando:
    titulos_abas.insert(1, "🎖️ Comandante")

abas = st.tabs(titulos_abas)

if eh_comando:
    tab_cons, tab_cmdo, tab_cump, tab_esta, tab_gest = abas
else:
    tab_cons, tab_cump, tab_esta, tab_gest = abas

# --- ABA 0: CONSULTA ---
with tab_cons:
    data_con = st.date_input("Consultar Data:", datetime.date.today())
    df_total = carregar_dados_db()
    if not df_total.empty:
        for regiao, cidades in territorios.items():
            df_dia = df_total[(df_total['data'] == data_con.strftime("%Y-%m-%d")) & (df_total['municipio'].isin(cidades))]
            if not df_dia.empty:
                st.markdown(f"#### 📍 {regiao}")
                df_dia['Estado'] = df_dia['cumprido'].map({True: "✅ Cumprida", False: "⚠️ Em Aberto"})
                st.dataframe(df_dia[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)

# --- ABA 1: COMANDANTE (VISÃO TOTAL) ---
if eh_comando:
    with tab_cmdo:
        st.subheader("🎖️ Painel de Comando - Todos os Registros")
        df_all = carregar_dados_db()
        if not df_all.empty:
            df_all = df_all.sort_values(by="data", ascending=False)
            for regiao, cidades in territorios.items():
                df_reg = df_all[df_all['municipio'].isin(cidades)]
                if not df_reg.empty:
                    with st.expander(f"📍 {regiao}", expanded=True):
                        df_reg['Data'] = df_reg['data'].apply(formatar_data_br)
                        df_reg['Situação'] = df_reg['cumprido'].map({True: "✅ Concluída", False: "📅 Agendada"})
                        df_reg['Relatório/Objetivo'] = df_reg.apply(
                            lambda x: x['relatorio_resumido'] if x['cumprido'] and x['relatorio_resumido'] else x['missao'], 
                            axis=1
                        )
                        st.dataframe(
                            df_reg[['Data', 'municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Situação', 'Relatório/Objetivo']], 
                            use_container_width=True, hide_index=True
                        )
        else: st.info("Sem registros.")

# --- ABA: CUMPRIMENTO ---
with tab_cump:
    df_c = carregar_dados_db()
    if not df_c.empty:
        df_c = df_c.sort_values(by="data", ascending=False)
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
                st.success("Atualizado!"); st.rerun()

# --- ABA: ESTATÍSTICAS ---
with tab_esta:
    df_est = carregar_dados_db()
    if not df_est.empty:
        st.subheader("📊 Estatísticas por Cidade")
        st.bar_chart(df_est['municipio'].value_counts(), horizontal=True)

# --- ABA: GESTÃO ---
with tab_gest:
    if not st.session_state.get("gestao_liberada", False):
        with st.form("f_gest"):
            if st.form_submit_button("Desbloquear") and st.text_input("Chave:", type="password") == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True; st.rerun()
    else:
        st.button("🔒 Bloquear", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📝 Agendar")
            with st.form("f_nova", clear_on_submit=True):
                dt = st.date_input("Data")
                mu = st.selectbox("Cidade", sorted(territorios["Costa do Descobrimento"] + territorios["Costa das Baleias"]))
                un = st.selectbox("Unidade Responsável", ["CPR-ES", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"])
                h_e = st.selectbox("Entrada Prevista", lista_horas)
                h_s = st.selectbox("Saída Prevista", lista_horas)
                ob = st.text_area("Objetivo")
                if st.form_submit_button("Confirmar"):
                    supabase.table("escala_operacional").insert({
                        "data": str(dt), "municipio": mu, "unidade": un, 
                        "hora_entrada": h_e, "hora_saida": h_s, "missao": ob, 
                        "criado_por": user_email
                    }).execute()
                    st.rerun()
        with col2:
            st.subheader("🗑️ Excluir")
            df_del = carregar_dados_db().sort_values(by='data', ascending=False)
            if not df_del.empty:
                df_del['txt'] = df_del['data'] + " | " + df_del['municipio']
                it = st.selectbox("Selecione:", df_del['txt'].tolist())
                if st.button("Remover"):
                    id_del = df_del[df_del['txt'] == it]['id'].values[0]
                    supabase.table("escala_operacional").delete().eq("id", id_del).execute()
                    st.rerun()
