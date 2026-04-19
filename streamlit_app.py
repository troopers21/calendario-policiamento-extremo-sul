import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES E CONEXÃO ---
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

# --- 3. LÓGICA DE AUTENTICAÇÃO (LOGIN E CADASTRO) ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

# Tenta recuperar sessão ativa de forma robusta
try:
    session_res = supabase.auth.get_session()
    if session_res and session_res.session:
        st.session_state.user_session = session_res.user
    else:
        st.session_state.user_session = None
except:
    st.session_state.user_session = None

# TELA DE ACESSO (Só aparece se não estiver logado)
if not st.session_state.user_session:
    aba_auth = st.tabs(["🔐 Entrar", "📝 Cadastrar-se"])
    
    with aba_auth[0]:
        with st.form("login_form"):
            email_input = st.text_input("E-mail") 
            senha_input = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_input, "password": senha_input})
                    if res.user:
                        st.session_state.user_session = res.user
                        st.success("Acesso autorizado! Carregando...")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro no login: {e}")

    with aba_auth[1]:
        st.info("Preencha seus dados funcionais para criar o perfil.")
        with st.form("register_form"):
            posto_grad = st.selectbox("Posto/Graduação", ["Cel", "Ten Cel", "Maj", "Cap", "1º Ten", "Subten", "1º Sgt", "2º Sgt", "3º Sgt", "Cb", "Sd"])
            nome_completo = st.text_input("Nome Completo")
            matricula_input = st.text_input("Matrícula (ex: 12.345-6)")
            st.divider()
            new_email = st.text_input("E-mail para Cadastro")
            new_senha = st.text_input("Crie uma Senha (mín. 6 caracteres)", type="password")
            confirm = st.text_input("Confirme a Senha", type="password")
            
            if st.form_submit_button("Finalizar Cadastro", use_container_width=True):
                if not nome_completo or not matricula_input:
                    st.error("Preencha Nome e Matrícula.")
                elif new_senha != confirm:
                    st.error("As senhas não coincidem.")
                elif len(new_senha) < 6:
                    st.warning("Senha muito curta.")
                else:
                    try:
                        supabase.auth.sign_up({
                            "email": new_email, 
                            "password": new_senha,
                            "options": {"data": {"posto_grad": posto_grad, "nome_completo": nome_completo, "matricula": matricula_input}}
                        })
                        st.success("Cadastro realizado! Mude para a aba 'Entrar' para acessar.")
                    except Exception as e:
                        st.error(f"Erro ao cadastrar: {e}")
    st.stop()

# --- 4. VARIÁVEIS DE SESSÃO E FUNÇÕES (SÓ RODA SE LOGADO) ---
user_email = st.session_state.user_session.email
user_meta = st.session_state.user_session.user_metadata
p_g = user_meta.get("posto_grad", "")
nome_user = user_meta.get("nome_completo", "Usuário")
mat_user = user_meta.get("matricula", "")

def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        return pd.DataFrame(response.data)
    except: return pd.DataFrame()

def formatar_data_br(data_iso):
    return datetime.datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")

lista_horas = [f"{h:02d}:00" for h in range(24)]

# --- 5. INTERFACE (SIDEBAR E ABAS) ---
with st.sidebar:
    st.markdown(f"### 👮 {p_g} {nome_user}")
    st.caption(f"Matrícula: {mat_user}")
    st.write(f"📧 {user_email}")
    if st.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"])

# --- ABA 0: CONSULTA ---
with menu[0]:
    data_con = st.date_input("Data de Consulta:", datetime.date.today())
    df_tot = carregar_dados_db()
    if not df_tot.empty:
        df_dia = df_tot[df_tot['data'] == data_con.strftime("%Y-%m-%d")]
        if not df_dia.empty:
            df_dia['Estado'] = df_dia['cumprido'].map({True: "✅ Cumprida", False: "⚠️ Em Aberto"})
            st.dataframe(df_dia[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)
        else: st.info("Sem missões para esta data.")

# --- ABA 1: CUMPRIMENTO (AUTO-PREENCHIMENTO INTELIGENTE) ---
with menu[1]:
    df_c = carregar_dados_db()
    if not df_c.empty:
        df_c['sel'] = df_c['data'].apply(formatar_data_br) + " | " + df_c['municipio']
        escolha = st.selectbox("Selecione a Missão:", df_c['sel'].tolist())
        d = df_c[df_c['sel'] == escolha].iloc[0]
        
        with st.form("f_cump"):
            c1, c2, c3 = st.columns(3)
            # Preenchimento automático baseado no perfil logado
            n = c1.text_input("Comandante", d.get('comandante_nome') or f"{p_g} {nome_user}")
            m = c2.text_input("Matrícula", d.get('comandante_matricula') or mat_user)
            v = c3.text_input("Vtr", d.get('viatura', ''))
            
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
                st.success("Registro atualizado com sucesso!"); st.rerun()

# --- ABA 2: ESTATÍSTICAS ---
with menu[2]:
    df_e = carregar_dados_db()
    if not df_e.empty:
        df_e['data_dt'] = pd.to_datetime(df_e['data'])
        df_e['Mês'] = df_e['data_dt'].dt.strftime('%m/%Y')
        col_bar1, col_bar2 = st.columns(2)
        with col_bar1: st.markdown("### 📅 Mensal"); st.bar_chart(df_e['Mês'].value_counts())
        with col_bar2: st.markdown("### 🏙️ Por Cidade"); st.bar_chart(df_e['municipio'].value_counts(), horizontal=True)

# --- ABA 3: GESTÃO ---
with menu[3]:
    if not st.session_state.get("gestao_liberada", False):
        with st.form("f_lock"):
            ch = st.text_input("Chave de Comando:", type="password")
            if st.form_submit_button("Desbloquear"):
                if ch == CHAVE_GESTAO: 
                    st.session_state.gestao_liberada = True
                    st.rerun()
                else: st.error("Chave incorreta.")
    else:
        st.button("🔒 Bloquear Painel", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        with st.expander("➕ Agendar Nova Missão"):
            with st.form("f_nova"):
                dt = st.date_input("Data")
                mu = st.selectbox("Cidade", ["Porto Seguro", "Eunápolis", "Teixeira de Freitas", "Itamaraju", "Prado", "Mucuri", "Santa Cruz Cabrália"])
                un = st.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
                he_ag = st.selectbox("Entrada", lista_horas)
                hs_ag = st.selectbox("Saída", lista_horas)
                ob = st.text_area("Objetivo")
                if st.form_submit_button("Agendar"):
                    supabase.table("escala_operacional").insert({
                        "data": str(dt), "municipio": mu, "unidade": un, "missao": ob,
                        "hora_entrada": he_ag, "hora_saida": hs_ag, "criado_por": user_email
                    }).execute()
                    st.success("Agendado!"); st.rerun()
        
        st.subheader("🕵️ Auditoria e Controle")
        df_audit = carregar_dados_db()
        if not df_audit.empty:
            st.dataframe(df_audit[['data', 'municipio', 'criado_por', 'editado_por', 'ultima_edicao']], use_container_width=True, hide_index=True)
