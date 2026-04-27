import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
import time
import extra_streamlit_components as stx

# --- 1. CONFIGURAÇÕES E CONEXÃO ---
CHAVE_GESTAO = "comando2026"
MATRICULA_ADMIN = "30455232"
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="SISPOSIÇÃO - PMBA - CPR-ES", layout="wide", page_icon="🛡️")

# Inicia o gerenciador de Cookies
cookie_manager = stx.CookieManager(key="gerenciador_cookies")

if "esperou_cookies" not in st.session_state:
    time.sleep(0.3)
    st.session_state.esperou_cookies = True
    st.rerun()

cookies_gerais = cookie_manager.get_all()
if cookies_gerais is None:
    st.markdown("🔄 Sincronizando sessão segura... Aguarde.", unsafe_allow_html=True)
    st.stop()

# --- LÓGICA DE SESSÃO ---
if "temp_access_token" in st.session_state:
    validade = datetime.datetime.now() + datetime.timedelta(days=30)
    cookie_manager.set("sb_access_token", st.session_state.temp_access_token, expires_at=validade, key="set_acc")
    cookie_manager.set("sb_refresh_token", st.session_state.temp_refresh_token, expires_at=validade, key="set_ref")
    del st.session_state["temp_access_token"]
    del st.session_state["temp_refresh_token"]

if "temp_logout" in st.session_state:
    try: cookie_manager.delete("sb_access_token", key="del_acc")
    except: pass
    try: cookie_manager.delete("sb_refresh_token", key="del_ref")
    except: pass
    supabase.auth.sign_out()
    del st.session_state["temp_logout"]

# --- 2. CABEÇALHO ---
col_logo1, col_logo2, col_logo3 = st.columns([0.5, 2.0, 0.5])
with col_logo2:
    try: st.image("logo_unidade.jpeg", use_container_width=True)
    except: pass
    st.markdown("🛡️ SISPOSIÇÃO - Sistema de Policiamento Sem Sobreposição", unsafe_allow_html=True)

# --- 3. AUTENTICAÇÃO ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

try:
    session_res = supabase.auth.get_session()
    if session_res and session_res.session:
        st.session_state.user_session = session_res.user
except: pass

if st.session_state.user_session is None:
    access_token = cookie_manager.get(cookie="sb_access_token")
    refresh_token = cookie_manager.get(cookie="sb_refresh_token")
    if access_token and refresh_token:
        try:
            res_cookie = supabase.auth.set_session(access_token, refresh_token)
            if res_cookie.user: st.session_state.user_session = res_cookie.user
        except: pass

if st.session_state.user_session is None:
    aba_auth = st.tabs(["🔐 Entrar", "📝 Cadastrar-se"])
    with aba_auth[0]:
        with st.form("login_form"):
            email_in = st.text_input("Email")
            senha_in = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_in, "password": senha_in})
                    if res.user:
                        if res.user.email_confirmed_at is None:
                            st.warning("⚠️ Confirme seu e-mail para acessar.")
                        else:
                            st.session_state.user_session = res.user
                            st.session_state.temp_access_token = res.session.access_token
                            st.session_state.temp_refresh_token = res.session.refresh_token
                            st.rerun()
                except Exception as e: st.error(f"Erro no login: {e}")
    
    with aba_auth[1]:
        with st.form("register_form"):
            lista_p = ["Cel PM", "Ten Cel PM", "Maj PM", "Cap PM", "Ten PM", "Asp PM", "Subten PM", "Sgt PM", "Cb PM", "Sd PM"]
            lista_u = ["Operação Pegasus", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"]
            c_r1, c_r2 = st.columns(2)
            posto_grad = c_r1.selectbox("Posto/Graduação", lista_p)
            nome_reg = c_r1.text_input("Nome Completo")
            unidade_reg = c_r2.selectbox("Unidade", lista_u)
            mat_reg = c_r2.text_input("Matrícula")
            st.divider()
            e_reg = st.text_input("Email")
            p_reg = st.text_input("Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro"):
                try:
                    perms = ["✅ Cumprimento"] if posto_grad in ["Subten PM", "Sgt PM", "Cb PM", "Sd PM"] else ["📋 Consulta de Escala", "🎖️ Comandante", "✅ Cumprimento", "📊 Estatísticas"]
                    supabase.auth.sign_up({"email": e_reg, "password": p_reg, "options": {"data": {"posto_grad": posto_grad, "nome_completo": nome_reg, "matricula": mat_reg, "unidade": unidade_reg}}})
                    supabase.table("permissoes_usuarios").upsert({"matricula": mat_reg, "abas_permitidas": perms}).execute()
                    st.success("✅ Cadastro solicitado! Verifique seu e-mail.")
                except Exception as e: st.error(f"Erro: {e}")
    st.stop()

# --- 4. VARIÁVEIS E FUNÇÕES ---
user_email = st.session_state.user_session.email
user_meta = st.session_state.user_session.user_metadata
p_g_user = user_meta.get("posto_grad", "")
nome_user = user_meta.get("nome_completo", "Usuário")
mat_user = user_meta.get("matricula", "")
unidade_user = user_meta.get("unidade", "")

def buscar_permissoes(matricula):
    try:
        res = supabase.table("permissoes_usuarios").select("abas_permitidas").eq("matricula", matricula).execute()
        if res.data: return res.data[0]["abas_permitidas"]
    except: pass
    return ["✅ Cumprimento"]

def carregar_dados_db():
    try:
        res = supabase.table("escala_operacional").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=["id", "data", "municipio", "unidade", "hora_entrada", "hora_saida", "missao", "comandante_nome", "viatura", "cumprido"])
    except: return pd.DataFrame()

def carregar_dados_bases():
    try:
        res = supabase.table("bases_integradas").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=["id", "base_nome", "unidade", "data_inicio", "data_fim"])
    except: return pd.DataFrame()

lista_horas = [f"{h:02d}:00" for h in range(24)]
territorios = {
    "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
    "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
}

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👮 {p_g_user} {nome_user}\n{unidade_user} | {mat_user}")
    if st.button("Sair"):
        st.session_state.temp_logout = True
        st.session_state.user_session = None
        st.rerun()

# --- 6. ABAS ---
abas_possiveis = ["📋 Consulta de Escala", "🎖️ Comandante", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão", "🏠 Gestão Base Integrada"]
if mat_user == MATRICULA_ADMIN: abas_possiveis.append("🔑 Admin")

abas_liberadas = buscar_permissoes(mat_user)
titulos_finais = [a for a in abas_possiveis if a in abas_liberadas]
tabs = st.tabs(titulos_finais)

for i, titulo in enumerate(titulos_finais):
    with tabs[i]:
        if titulo == "📋 Consulta de Escala":
            dt_c = st.date_input("Data da Escala:", datetime.date.today(), key="dt_cons")
            df = carregar_dados_db()
            if not df.empty:
                for r, cidades in territorios.items():
                    df_r = df[(df['data'] == str(dt_c)) & (df['municipio'].isin(cidades))]
                    if not df_r.empty:
                        st.markdown(f"#### 📍 {r}")
                        df_r['Estado'] = df_r['cumprido'].map({True: "✅ OK", False: "⚠️ Aberto"})
                        st.dataframe(df_r[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)

        elif titulo == "🎖️ Comandante":
            df_all = carregar_dados_db()
            if not df_all.empty:
                for r, cidades in territorios.items():
                    df_r = df_all[df_all['municipio'].isin(cidades)]
                    if not df_r.empty:
                        with st.expander(f"📍 {r}", expanded=True):
                            df_r['Situação'] = df_r['cumprido'].map({True: "✅ OK", False: "⚠️ Aberto"})
                            st.dataframe(df_r[['data', 'municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Situação', 'missao']], use_container_width=True, hide_index=True)

        elif titulo == "✅ Cumprimento":
            df_c = carregar_dados_db().sort_values(by="data", ascending=False)
            if not df_c.empty:
                df_c['sel'] = df_c['data'] + " | " + df_c['municipio']
                it = st.selectbox("Selecione a Missão:", df_c['sel'].tolist(), key="sel_cump")
                d = df_c[df_c['sel'] == it].iloc[0]
                with st.form("f_cump_completo"):
                    col_c1, col_c2 = st.columns(2)
                    n_cmt = col_c1.text_input("Comandante da Guarnição", d.get('comandante_nome') or f"{p_g_user} {nome_user}")
                    v_pref = col_c2.text_input("Viatura (Prefixo)", d.get('viatura', ''))
                    h_e_real = st.selectbox("Horário de Início Real", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
                    h_s_real = st.selectbox("Horário de Término Real", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
                    rel_det = st.text_area("Relatório Resumido", d.get('relatorio_resumido', ''))
                    conf_c = st.checkbox("Missão Cumprida", value=bool(d.get('cumprido')))
                    if st.form_submit_button("Salvar"):
                        try:
                            supabase.table("escala_operacional").update({"comandante_nome": n_cmt, "viatura": v_pref, "hora_entrada": h_e_real, "hora_saida": h_s_real, "relatorio_resumido": rel_det, "cumprido": conf_c}).eq("id", d['id']).execute()
                            st.success("Salvo!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        elif titulo == "⚙️ Gestão":
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("📝 Agendar Missão")
                dt_g = st.date_input("Data da Missão", key="dt_gestao")
                df_atual = carregar_dados_db()
                if not df_atual.empty:
                    df_dia = df_atual[df_atual['data'] == str(dt_g)]
                    if not df_dia.empty:
                        st.info("📌 Missões já agendadas para esta data:")
                        st.dataframe(df_dia[['unidade', 'hora_entrada', 'hora_saida']], use_container_width=True, hide_index=True)

                with st.form("f_gest_nova", clear_on_submit=True):
                    mu_g = st.selectbox("Município", sorted(territorios["Costa do Descobrimento"] + territorios["Costa das Baleias"]))
                    un_g = st.selectbox("Unidade Responsável", ["Operação Pegasus", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"])
                    h_e_prev = st.selectbox("Início Previsto", lista_horas)
                    h_s_prev = st.selectbox("Fim Previsto", lista_horas)
                    miss_obj = st.text_area("Objetivo da Missão")
                    
                    if st.form_submit_button("Agendar Missão"):
                        unidades_excecao = ["CIPPA/PS", "CIPRv-Ita", "Operação Pegasus"]
                        permite_sobreposicao = un_g in unidades_excecao
                        sobreposicao = False
                        
                        if not df_atual.empty and not permite_sobreposicao:
                            df_conf = df_atual[df_atual['data'] == str(dt_g)]
                            for _, row in df_conf.iterrows():
                                if (h_e_prev < row['hora_saida']) and (h_s_prev > row['hora_entrada']):
                                    sobreposicao = True
                                    break
                        
                        if sobreposicao:
                            st.error("⚠️ Já existe uma missão neste horário.")
                        else:
                            try:
                                supabase.table("escala_operacional").insert({
                                    "data": str(dt_g), "municipio": mu_g, "unidade": un_g,
                                    "hora_entrada": h_e_prev, "hora_saida": h_s_prev, 
                                    "missao": miss_obj, "criado_por": user_email
                                }).execute()
                                st.success("Agendado!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")

            with col_g2:
                st.subheader("🗑️ Excluir Registro")
                df_del = carregar_dados_db().sort_values(by='data', ascending=False)
                if not df_del.empty:
                    df_del['txt'] = df_del['data'] + " | " + df_del['municipio'] + " | " + df_del['unidade']
                    opcoes = [""] + df_del['txt'].tolist()
                    it_del = st.selectbox("Selecione para excluir:", opcoes, index=0, key="del_escala")
                    
                    if it_del != "":
                        reg = df_del[df_del['txt'] == it_del].iloc[0]
                        st.info(f"Detalhes: {reg['hora_entrada']} às {reg['hora_saida']} | {reg.get('missao', '')}")
                        if st.button("Remover Permanentemente"):
                            try:
                                supabase.table("escala_operacional").delete().eq("id", reg['id']).execute()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")

        elif titulo == "🏠 Gestão Base Integrada":
            st.header("🏠 Gestão Base Integrada")
            col_b1, col_b2 = st.columns([1, 2])
            with col_b1:
                st.subheader("📝 Agendar Base")
                dt_base = st.date_input("Selecione o dia da semana", key="dt_base")
                segunda = dt_base - datetime.timedelta(days=dt_base.weekday())
                domingo = segunda + datetime.timedelta(days=6)
                st.info(f"Período: {segunda.strftime('%d/%m/%Y')} a {domingo.strftime('%d/%m/%Y')}")
                
                with st.form("form_base", clear_on_submit=True):
                    base_sel = st.selectbox("Base", ["Base 1", "Base 2", "Base 3", "Base 4"])
                    un_base = st.selectbox("Unidade", ["Operação Pegasus", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"])
                    if st.form_submit_button("Confirmar Ocupação"):
                        try:
                            supabase.table("bases_integradas").insert({"base_nome": base_sel, "unidade": un_base, "data_inicio": str(segunda), "data_fim": str(domingo), "criado_por": user_email}).execute()
                            st.success("Base ocupada!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                
                st.divider()
                df_b = carregar_dados_bases()
                if not df_b.empty:
                    st.write("📋 Histórico Geral de Ocupações:")
                    st.dataframe(df_b[['base_nome', 'unidade', 'data_inicio', 'data_fim']], use_container_width=True, hide_index=True)

            with col_b2:
                st.subheader("📅 Previsão de Ocupação da Semana")
                dt_f = st.date_input("Filtrar semana pelo dia:", key="filtro_base")
                seg_f = dt_f - datetime.timedelta(days=dt_f.weekday())
                df_f = carregar_dados_bases()
                if not df_f.empty:
                    df_s = df_f[df_f['data_inicio'] == str(seg_f)]
                    if not df_s.empty:
                        st.dataframe(df_s[['base_nome', 'unidade']], use_container_width=True, hide_index=True)
                    else: st.warning("Nenhuma ocupação para esta semana.")

        elif titulo == "📊 Estatísticas":
            df_e = carregar_dados_db()
            if not df_e.empty: st.bar_chart(df_e['municipio'].value_counts())

        elif titulo == "🔑 Admin":
            st.subheader("Gestão de Acessos")
            try:
                res_u = supabase.table("lista_usuarios_admin").select("*").execute()
                if res_u.data:
                    for user in res_u.data:
                        with st.expander(f"👤 {user['nome_completo']} ({user['matricula']})"):
                            p_atual = buscar_permissoes(user['matricula'])
                            novas_p = st.multiselect("Abas Permitidas:", abas_possiveis, default=p_atual, key=f"p_{user['matricula']}")
                            if st.button("Atualizar", key=f"b_{user['matricula']}"):
                                supabase.table("permissoes_usuarios").upsert({"matricula": user['matricula'], "abas_permitidas": novas_p}).execute()
                                st.success("Atualizado!")
            except Exception as e: st.error(f"Erro: {e}")
