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
                    # LÓGICA ATUALIZADA: Retirado "📋 Consulta de Escala" para Praças
                    if posto_grad in ["Subten PM", "Sgt PM", "Cb PM", "Sd PM"]:
                        perms_iniciais = ["✅ Cumprimento"]
                    else:
                        perms_iniciais = ["📋 Consulta de Escala", "🎖️ Comandante", "✅ Cumprimento", "📊 Estatísticas"]

                    supabase.auth.sign_up({"email": e_reg, "password": p_reg, "options": {"data": {"posto_grad": posto_grad, "nome_completo": nome_reg, "matricula": mat_reg, "unidade": unidade_reg}}})
                    
                    # Salva as permissões iniciais na tabela
                    supabase.table("permissoes_usuarios").upsert({"matricula": mat_reg, "abas_permitidas": perms_iniciais}).execute()
                    
                    st.success("✅ Cadastro solicitado! Verifique seu e-mail para ativar.")
                except Exception as e: st.error(f"Erro: {e}")
    st.stop()

# --- 4. VARIÁVEIS DO USUÁRIO ---
user_meta = st.session_state.user_session.user_metadata
p_g_user = user_meta.get("posto_grad", "")
nome_user = user_meta.get("nome_completo", "Usuário")
mat_user = user_meta.get("matricula", "")
unidade_user = user_meta.get("unidade", "")

# Função para buscar permissões no banco
def buscar_permissoes(matricula):
    try:
        res = supabase.table("permissoes_usuarios").select("abas_permitidas").eq("matricula", matricula).execute()
        if res.data:
            return res.data[0]["abas_permitidas"]
    except: pass
    return ["✅ Cumprimento"] # Padrão mínimo caso falhe

abas_liberadas = buscar_permissoes(mat_user)
eh_admin = mat_user == MATRICULA_ADMIN

def carregar_dados_db():
    try:
        res = supabase.table("escala_operacional").select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

territorios = {
    "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
    "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
}

# --- 5. INTERFACE ---
with st.sidebar:
    st.markdown(f"### 👮 {p_g_user} {nome_user}\n{unidade_user} | {mat_user}")
    if st.button("Sair"):
        supabase.auth.sign_out(); st.session_state.user_session = None; st.rerun()

# Abas permitidas para o usuário logado
abas_possiveis = ["📋 Consulta de Escala", "🎖️ Comandante", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão"]
if eh_admin: abas_possiveis.append("🔑 Admin")

titulos_finais = [a for a in abas_possiveis if a in abas_liberadas]
if not titulos_finais: titulos_finais = ["✅ Cumprimento"]

tabs = st.tabs(titulos_finais)

for i, titulo in enumerate(titulos_finais):
    with tabs[i]:
        if titulo == "📋 Consulta de Escala":
            dt_c = st.date_input("Data:", datetime.date.today(), key="dt_cons")
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
            if not df_all.empty:
                for r, cidades in territorios.items():
                    df_r = df_all[df_all['municipio'].isin(cidades)]
                    if not df_r.empty:
                        with st.expander(f"📍 {r}"):
                            st.dataframe(df_r, use_container_width=True, hide_index=True)

        elif titulo == "✅ Cumprimento":
            df_c = carregar_dados_db().sort_values(by="data", ascending=False)
            if not df_c.empty:
                df_c['sel'] = df_c['data'] + " | " + df_c['municipio']
                it = st.selectbox("Selecione a Missão:", df_c['sel'].tolist())
                d = df_c[df_c['sel'] == it].iloc[0]
                with st.form("f_cump_real"):
                    n_cmt = st.text_input("Comandante", d.get('comandante_nome') or f"{p_g_user} {nome_user}")
                    rel = st.text_area("Relatório resumido", d.get('relatorio_resumido', ''))
                    conf = st.checkbox("Confirmar Cumprimento", value=bool(d.get('cumprido')))
                    if st.form_submit_button("Salvar Cumprimento"):
                        supabase.table("escala_operacional").update({"comandante_nome": n_cmt, "relatorio_resumido": rel, "cumprido": conf, "ultima_edicao": datetime.datetime.now().isoformat()}).eq("id", d['id']).execute()
                        st.success("Salvo!"); st.rerun()

        elif titulo == "📊 Estatísticas":
            df_e = carregar_dados_db()
            if not df_e.empty: st.bar_chart(df_e['municipio'].value_counts())

        elif titulo == "⚙️ Gestão":
            if st.text_input("Chave de Gestão:", type="password") == CHAVE_GESTAO:
                with st.form("f_gest_nova"):
                    dt_g = st.date_input("Data")
                    mu_g = st.selectbox("Cidade", sorted(territorios["Costa do Descobrimento"] + territorios["Costa das Baleias"]))
                    un_g = st.selectbox("Unidade", ["CPR-ES", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"])
                    miss = st.text_area("Missão")
                    if st.form_submit_button("Agendar"):
                        supabase.table("escala_operacional").insert({"data": str(dt_g), "municipio": mu_g, "unidade": un_g, "missao": miss}).execute()
                        st.rerun()

        elif titulo == "🔑 Admin" and eh_admin:
            st.subheader("Gerenciar Permissões de Acesso")
            try:
                res_u = supabase.table("lista_usuarios_admin").select("*").execute()
                if res_u.data:
                    for user in res_u.data:
                        with st.expander(f"👤 {user['nome_completo']} ({user['matricula']}) - {user['posto_grad']}"):
                            p_atual = buscar_permissoes(user['matricula'])
                            novas_p = st.multiselect(
                                "Abas Permitidas:",
                                ["📋 Consulta de Escala", "🎖️ Comandante", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão", "🔑 Admin"],
                                default=p_atual,
                                key=f"p_{user['matricula']}"
                            )
                            if st.button("Salvar Acessos", key=f"b_{user['matricula']}"):
                                supabase.table("permissoes_usuarios").upsert({"matricula": user['matricula'], "abas_permitidas": novas_p}).execute()
                                st.success(f"Acessos de {user['matricula']} atualizados!")
            except Exception as e: st.error(f"Erro: {e}")
