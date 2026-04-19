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
                        supabase.auth.sign_up({"email": email_reg, "password": pass_reg,
                            "options": {"data": {"posto_grad": p_g_reg, "nome_completo": nome_reg, "matricula": mat_reg}}})
                        st.success("✅ Cadastro solicitado! Verifique seu e-mail para liberar o acesso.")
                    except Exception as e: st.error(f"Erro: {e}")
    st.stop()

# --- 4. VARIÁVEIS E FUNÇÕES GERAIS ---
user_email = st.session_state.user_session.email
user_meta = st.session_state.user_session.user_metadata

def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        df = pd.DataFrame(response.data)
        return df
    except: return pd.DataFrame()

def formatar_data_br(data_iso):
    try: return datetime.datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except: return data_iso

lista_horas = [f"{h:02d}:00" for h in range(24)]

# Definição dos Territórios (Restaurado)
territorios = {
    "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
    "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
}

# --- 5. INTERFACE SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👮 {user_meta.get('posto_grad', '')} {user_meta.get('nome_completo', 'Usuário')}")
    st.caption(f"Matrícula: {user_meta.get('matricula', '')}")
    if st.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()

menu = st.tabs(["📋 Consulta de Escala", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"])

# --- ABA 0: CONSULTA (Restaurado por Território) ---
with menu[0]:
    data_con = st.date_input("Consultar Data:", datetime.date.today())
    df_total = carregar_dados_db()
    existem_missoes = False
    
    if not df_total.empty:
        for regiao, cidades in territorios.items():
            df_dia = df_total[(df_total['data'] == data_con.strftime("%Y-%m-%d")) & (df_total['municipio'].isin(cidades))]
            if not df_dia.empty:
                existem_missoes = True
                st.markdown(f"#### 📍 {regiao}")
                df_dia['Estado'] = df_dia['cumprido'].map({True: "✅ Cumprida", False: "⚠️ Em Aberto"})
                st.dataframe(df_dia[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)
    
    if not existem_missoes:
        st.info(f"Sem missões agendadas para {data_con.strftime('%d/%m/%Y')}.")

# --- ABA 1: CUMPRIMENTO ---
with menu[1]:
    df_c = carregar_dados_db()
    if not df_c.empty:
        df_c['sel'] = df_c['data'].apply(formatar_data_br) + " | " + df_c['municipio']
        escolha = st.selectbox("Selecione a Missão:", df_c['sel'].tolist())
        d = df_c[df_c['sel'] == escolha].iloc[0]
        
        with st.form("f_cump"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Comandante", d.get('comandante_nome') or f"{user_meta.get('posto_grad')} {user_meta.get('nome_completo')}")
            m = c2.text_input("Matrícula", d.get('comandante_matricula') or user_meta.get('matricula'))
            v = c3.text_input("Viatura", d.get('viatura', ''))
            
            h_e = st.selectbox("Entrada", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
            h_s = st.selectbox("Saída", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
            rel = st.text_area("Relatório Resumido", d.get('relatorio_resumido', ''))
            conf = st.checkbox("Confirmar Cumprimento", value=bool(d.get('cumprido', False)))
            
            if st.form_submit_button("Salvar Registro"):
                supabase.table("escala_operacional").update({
                    "comandante_nome": n, "comandante_matricula": m, "viatura": v,
                    "hora_entrada": h_e, "hora_saida": h_s, "relatorio_resumido": rel, "cumprido": conf,
                    "editado_por": user_email, "ultima_edicao": datetime.datetime.now().isoformat()
                }).eq("id", d['id']).execute()
                st.success("Dados atualizados!"); st.rerun()

# --- ABA 2: ESTATÍSTICAS (Restaurado Completo) ---
with menu[2]:
    st.subheader("📊 Análise de Dados Estratégicos")
    df_est = carregar_dados_db()
    if not df_est.empty:
        df_est['data_dt'] = pd.to_datetime(df_est['data'])
        df_est['Mês/Ano'] = df_est['data_dt'].dt.strftime('%m/%Y')
        total_geral = len(df_est)
        
        mapeamento = {cidade: terr for terr, cidades in territorios.items() for cidade in cidades}
        df_est['Território'] = df_est['municipio'].map(mapeamento)
        
        # Estatística Mensal
        st.markdown("### 📅 Missões por Mês")
        df_mensal = df_est['Mês/Ano'].value_counts().reset_index()
        df_mensal.columns = ['Mês', 'Qtd']
        df_mensal['%'] = (df_mensal['Qtd']/total_geral*100).map("{:.1f}%".format)
        col_m1, col_m2 = st.columns([1, 2])
        col_m1.dataframe(df_mensal, hide_index=True)
        col_m2.line_chart(df_est['Mês/Ano'].value_counts())
        
        # Estatística por Território
        st.markdown("---")
        st.markdown("### 🌎 Por Território")
        df_terr = df_est['Território'].value_counts().reset_index()
        df_terr.columns = ['Território', 'Qtd']
        df_terr['%'] = (df_terr['Qtd']/total_geral*100).map("{:.1f}%".format)
        col_t1, col_t2 = st.columns([1, 1])
        col_t1.dataframe(df_terr, hide_index=True)
        col_t2.bar_chart(df_est['Território'].value_counts())
        
        # Estatística por Cidade
        st.markdown("---")
        st.markdown("### 🏙️ Por Cidade")
        st.bar_chart(df_est['municipio'].value_counts(), horizontal=True)
    else:
        st.info("Aguardando registros para gerar gráficos.")

# --- ABA 3: GESTÃO ---
with menu[3]:
    if not st.session_state.get("gestao_liberada", False):
        with st.form("f_gest"):
            ch = st.text_input("Chave de Segurança:", type="password")
            if st.form_submit_button("Desbloquear Painel"):
                if ch == CHAVE_GESTAO: st.session_state.gestao_liberada = True; st.rerun()
                else: st.error("Chave incorreta.")
    else:
        st.button("🔒 Bloquear Painel", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        
        # Cadastro de Missão
        with st.expander("➕ Agendar Nova Missão"):
            with st.form("f_nova"):
                dt = st.date_input("Data")
                todas_cidades = sorted(territorios["Costa do Descobrimento"] + territorios["Costa das Baleias"])
                mu = st.selectbox("Cidade", todas_cidades)
                un = st.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
                h_e_ag = st.selectbox("Entrada", lista_horas)
                h_s_ag = st.selectbox("Saída", lista_horas)
                ob = st.text_area("Objetivo da Missão")
                if st.form_submit_button("Agendar"):
                    supabase.table("escala_operacional").insert({
                        "data": str(dt), "municipio": mu, "unidade": un, "missao": ob,
                        "hora_entrada": h_e_ag, "hora_saida": h_s_ag, "criado_por": user_email
                    }).execute()
                    st.success("Missão agendada!"); st.rerun()
        
        # Auditoria (Restaurado)
        st.subheader("🕵️ Histórico e Auditoria")
        df_audit = carregar_dados_db().sort_values(by='data', ascending=False)
        if not df_audit.empty:
            df_audit['Data'] = df_audit['data'].apply(formatar_data_br)
            st.dataframe(df_audit[['Data', 'municipio', 'unidade', 'criado_por', 'editado_por', 'ultima_edicao']], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            if st.button("🗑️ Excluir registro selecionado"):
                # Lógica de exclusão rápida aqui se necessário
                pass
