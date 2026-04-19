import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES E CONEXÃO ---
CHAVE_GESTAO = "comando2026"
MATRICULA_ADMIN = "30455232"

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
except: pass

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
                            st.warning("⚠️ Confirme seu e-mail.")
                        else:
                            st.session_state.user_session = res.user
                            st.rerun()
                except Exception as e: st.error(f"Erro no login: {e}")

    with aba_auth[1]:
        with st.form("register_form"):
            lista_p = ["Cel PM", "Ten Cel PM", "Maj PM", "Cap PM", "Ten PM", "Asp PM", "Subten PM", "Sgt PM", "Cb PM", "Sd PM"]
            lista_u = ["CPR-ES", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"]
            c_r1, c_r2 = st.columns(2)
            posto_grad = c_r1.selectbox("Posto/Graduação", lista_p)
            nome_reg = c_r1.text_input("Nome Completo")
            unidade_reg = c_r2.selectbox("Unidade", lista_u)
            mat_reg = c_r2.text_input("Matrícula")
            st.divider()
            e_reg, p_reg = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro"):
                try:
                    supabase.auth.sign_up({"email": e_reg, "password": p_reg, "options": {"data": {"posto_grad": posto_grad, "nome_completo": nome_reg, "matricula": mat_reg, "unidade": unidade_reg}}})
                    # Cria entrada básica de permissão
                    supabase.table("permissoes_usuarios").insert({"matricula": mat_reg, "abas_permitidas": ["📋 Consulta de Escala"]}).execute()
                    st.success("✅ Verifique seu e-mail!")
                except Exception as e: st.error(f"Erro: {e}")
    st.stop()

# --- 4. VARIÁVEIS DO USUÁRIO ---
user_meta = st.session_state.user_session.user_metadata
p_g_user = user_meta.get("posto_grad", "")
nome_user = user_meta.get("nome_completo", "Usuário")
mat_user = user_meta.get("matricula", "")
unidade_user = user_meta.get("unidade", "")

# Busca permissões no banco de dados
def buscar_permissoes(matricula):
    try:
        res = supabase.table("permissoes_usuarios").select("abas_permitidas").eq("matricula", matricula).execute()
        if res.data:
            return res.data[0]["abas_permitidas"]
    except: pass
    return ["📋 Consulta de Escala"] # Padrão

abas_liberadas = buscar_permissoes(mat_user)
eh_admin = mat_user == MATRICULA_ADMIN

def carregar_dados_db():
    res = supabase.table("escala_operacional").select("*").execute()
    return pd.DataFrame(res.data)

territorios = {
    "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
    "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
}

# --- 5. INTERFACE ---
with st.sidebar:
    st.markdown(f"### 👮 {p_g_user} {nome_user}\n{unidade_user} | {mat_user}")
    if st.button("Sair"):
        supabase.auth.sign_out(); st.session_state.user_session = None; st.rerun()

# Filtragem dinâmica de abas
abas_possiveis = ["📋 Consulta de Escala", "🎖️ Comandante", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"]
if eh_admin: abas_possiveis.append("🔑 Admin")

# Só mostra o que está no banco de dados para aquele usuário
titulos_finais = [a for a in abas_possiveis if a in abas_liberadas]
if not titulos_finais: titulos_finais = ["📋 Consulta de Escala"]

tabs = st.tabs(titulos_finais)

# Mapeamento de conteúdo
for i, titulo in enumerate(titulos_finais):
    with tabs[i]:
        if titulo == "📋 Consulta de Escala":
            dt_c = st.date_input("Data:", datetime.date.today())
            df = carregar_dados_db()
            if not df.empty:
                for r, cidades in territorios.items():
                    df_r = df[(df['data'] == str(dt_c)) & (df['municipio'].isin(cidades))]
                    if not df_r.empty:
                        st.markdown(f"#### 📍 {r}")
                        df_r['Estado'] = df_r['cumprido'].map({True: "✅ OK", False: "⚠️ Aberto"})
                        st.dataframe(df_r[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)

        elif titulo == "🎖️ Comandante":
            df_all = carregar_dados_db().sort_values(by="data", ascending=False)
            for r, cidades in territorios.items():
                df_r = df_all[df_all['municipio'].isin(cidades)]
                if not df_r.empty:
                    with st.expander(f"📍 {r}"):
                        st.dataframe(df_r, use_container_width=True, hide_index=True)

        elif titulo == "✅ Cumprimento":
            df_c = carregar_dados_db().sort_values(by="data", ascending=False)
            if not df_c.empty:
                df_c['sel'] = df_c['data'] + " | " + df_c['municipio']
                it = st.selectbox("Missão:", df_c['sel'].tolist())
                d = df_c[df_c['sel'] == it].iloc[0]
                with st.form("f_c"):
                    rel = st.text_area("Relatório", d.get('relatorio_resumido', ''))
                    conf = st.checkbox("Cumprido", value=bool(d.get('cumprido')))
                    if st.form_submit_button("Salvar"):
                        supabase.table("escala_operacional").update({"relatorio_resumido": rel, "cumprido": conf}).eq("id", d['id']).execute()
                        st.rerun()

        elif titulo == "📊 Estatísticas":
            df_e = carregar_dados_db()
            if not df_e.empty: st.bar_chart(df_e['municipio'].value_counts())

        elif titulo == "⚙️ Gestão":
            if st.text_input("Chave:", type="password") == CHAVE_GESTAO:
                with st.form("f_n"):
                    dt = st.date_input("Data")
                    mu = st.selectbox("Cidade", sorted(territorios["Costa do Descobrimento"] + territorios["Costa das Baleias"]))
                    un = st.selectbox("Unidade", ["CPR-ES", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"])
                    if st.form_submit_button("Agendar"):
                        supabase.table("escala_operacional").insert({"data": str(dt), "municipio": mu, "unidade": un}).execute()
                        st.rerun()

        elif titulo == "🔑 Admin" and eh_admin:
            st.subheader("Controle de Acesso por Usuário")
            try:
                # Lista usuários da View
                res_u = supabase.table("lista_usuarios_admin").select("*").execute()
                if res_u.data:
                    df_u = pd.DataFrame(res_u.data)
                    for _, row in df_u.iterrows():
                        with st.expander(f"👤 {row['nome_completo']} ({row['matricula']})"):
                            # Busca permissões atuais deste usuário específico
                            perm_atual = buscar_permissoes(row['matricula'])
                            novas_perms = st.multiselect(
                                f"Abas para {row['matricula']}:",
                                ["📋 Consulta de Escala", "🎖️ Comandante", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão", "🔑 Admin"],
                                default=perm_atual,
                                key=f"perm_{row['matricula']}"
                            )
                            if st.button("Atualizar Permissões", key=f"btn_{row['matricula']}"):
                                supabase.table("permissoes_usuarios").upsert({
                                    "matricula": row['matricula'],
                                    "abas_permitidas": novas_perms
                                }).execute()
                                st.success("Atualizado!")
            except Exception as e: st.error(f"Erro: {e}")
