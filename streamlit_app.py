import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES E BANCO ---
# Chave de Gestão continua manual para segurança dupla
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

# --- 3. FUNÇÕES DE SUPORTE ---
def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        df = pd.DataFrame(response.data)
        colunas_nec = ['id', 'data', 'municipio', 'unidade', 'missao', 'cumprido', 'hora_entrada', 'hora_saida', 'relatorio_resumido', 'comandante_nome', 'comandante_matricula', 'viatura']
        for col in colunas_nec:
            if col not in df.columns: df[col] = None
        return df
    except:
        return pd.DataFrame(columns=['id', 'data', 'municipio', 'unidade', 'missao'])

def login_google():
    # Esta função gera a URL de login do Supabase para o Google
    res = supabase.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {
            "redirect_to": st.secrets.get("REDIRECT_URL", "http://localhost:8501")
        }
    })
    return res.url

# --- 4. LÓGICA DE AUTENTICAÇÃO SUPABASE / GOOGLE ---
# Verificamos se há um usuário na sessão do Supabase
user = supabase.auth.get_user()

if not user:
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
        st.subheader("🔐 Acesso Institucional")
        st.info("Utilize seu e-mail funcional ou conta Google autorizada.")
        
        # Botão estilizado para o Google
        auth_url = login_google()
        st.markdown(f'''
            <a href="{auth_url}" target="_self">
                <button style="width:100%; height:50px; border-radius:5px; border:none; background-color:#4285F4; color:white; font-weight:bold; cursor:pointer;">
                    Entrar com Google
                </button>
            </a>
        ''', unsafe_allow_html=True)
    st.stop()

# Se chegou aqui, está autenticado
email_logado = user.user.email

# --- 5. INTERFACE PRINCIPAL ---
if st.sidebar.button("Terminar Sessão"):
    supabase.auth.sign_out()
    st.rerun()

st.sidebar.write(f"👤 **Usuário:** {email_logado}")

menu = st.tabs(["📋 Consulta de Escala", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão SISPOSIÇÃO"])

# --- ABA 0, 1 e 2 (Consulta, Cumprimento, Estatísticas) ---
# (O código dessas abas permanece o mesmo das versões anteriores)
with menu[0]:
    data_con = st.date_input("Consultar Data:", datetime.date.today())
    df_total = carregar_dados_db()
    regioes = {"Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"], "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]}
    existem_missoes = False
    for regiao, cidades in regioes.items():
        if not df_total.empty:
            df_dia = df_total[(df_total['data'] == data_con.strftime("%Y-%m-%d")) & (df_total['municipio'].isin(cidades))]
            if not df_dia.empty:
                existem_missoes = True
                st.markdown(f"#### 📍 {regiao}")
                view_cols = [{"Município": r['municipio'], "Unidade": r['unidade'], "Entrada": r['hora_entrada'], "Saída": r['hora_saida'], "Estado": "✅ Cumprida" if r['cumprido'] else "⚠️ Em Aberto"} for _, r in df_dia.iterrows()]
                st.dataframe(pd.DataFrame(view_cols), use_container_width=True, hide_index=True)
    if not existem_missoes: st.info("Sem missões.")

# --- ABA 3: GESTÃO ---
with menu[3]:
    if not st.session_state.get("gestao_liberada", False):
        st.warning("🔒 Área Restrita à Chave de Comando CPR-ES.")
        with st.form("form_desbloqueio", clear_on_submit=True):
            ch = st.text_input("Chave de Segurança:", type="password")
            if st.form_submit_button("Desbloquear Painel"):
                if ch == CHAVE_GESTAO:
                    st.session_state.gestao_liberada = True
                    st.rerun()
                else: st.error("Chave Incorreta.")
    else:
        st.button("🔒 Bloquear Painel", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        # ... (Restante do código de Agendamento, Exclusão e Painel Executivo)
