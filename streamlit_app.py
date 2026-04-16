import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES E BANCO ---
USUARIO_CORRETO = "admin"
SENHA_CORRETA = "pmba2026"
CHAVE_GESTAO = "comando2026"

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "gestao_liberada" not in st.session_state:
    st.session_state.gestao_liberada = False

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

def salvar_no_db(data, municipio, unidade, missao, h_ent, h_sai):
    supabase.table("escala_operacional").insert({"data": data.strftime("%Y-%m-%d"), "municipio": municipio, "unidade": unidade, "missao": missao, "cumprido": False, "hora_entrada": h_ent, "hora_saida": h_sai}).execute()

def atualizar_cumprimento(id_registro, entrada, saida, relatorio, status_bool, nome, matricula, vtr):
    try:
        supabase.table("escala_operacional").update({"hora_entrada": entrada, "hora_saida": saida, "relatorio_resumido": relatorio, "cumprido": status_bool, "comandante_nome": nome, "comandante_matricula": matricula, "viatura": vtr}).eq("id", id_registro).execute()
        return True
    except: return False

def apagar_no_db(id_registro):
    try:
        supabase.table("escala_operacional").delete().eq("id", id_registro).execute()
        return True
    except: return False

def formatar_data_br(data_iso):
    try: return datetime.datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except: return data_iso

def obter_dia_semana(data_str):
    dias = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
    try:
        data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d")
        return dias[data_obj.weekday()]
    except: return "-"

lista_horas = [f"{h:02d}:00" for h in range(24)]

# --- 4. LÓGICA DE AUTENTICAÇÃO ---
if not st.session_state.autenticado:
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        with st.form("login"):
            st.subheader("🔐 Acesso Restrito")
            u = st.text_input("Utilizador")
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema"):
                if u == USUARIO_CORRETO and p == SENHA_CORRETA:
                    st.session_state.autenticado = True
                    st.rerun()
                else: st.error("Credenciais Inválidas.")
    st.stop()

# --- 5. INTERFACE PRINCIPAL ---
if st.sidebar.button("Terminar Sessão"):
    st.session_state.autenticado = False
    st.session_state.gestao_liberada = False
    st.rerun()

menu = st.tabs(["📋 Consulta de Escala", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão SISPOSIÇÃO"])

# ABA 0: CONSULTA
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
                view_cols = []
                for _, r in df_dia.iterrows():
                    status_txt = "✅ Missão Cumprida" if r.get('cumprido') is True else "⚠️ Em Aberto"
                    view_cols.append({"Município": r['municipio'], "Unidade": r['unidade'], "Entrada": r['hora_entrada'], "Saída": r['hora_saida'], "Estado": status_txt})
                st.dataframe(pd.DataFrame(view_cols), use_container_width=True, hide_index=True)
    if not existem_missoes: st.info(f"Sem missões para {data_con.strftime('%d/%m/%Y')}.")

# ABA 1: CUMPRIMENTO
with menu[1]:
    st.subheader("Registo de Desfecho Operacional")
    df_raw = carregar_dados_db()
    if not df_raw.empty:
        hoje = datetime.date.today().strftime("%Y-%m-%d")
        df_filt = df_raw[df_raw['data'] <= hoje].copy()
        if not df_filt.empty:
            df_filt['data_br'] = df_filt['data'].apply(formatar_data_br)
            df_filt['selecao'] = df_filt['data_br'] + " | " + df_filt['municipio']
            sel_missao = st.selectbox("Selecione a Missão:", df_filt['selecao'].tolist())
            d = df_filt[df_filt['selecao'] == sel_missao].iloc[0]
            with st.form("f_cump"):
                c1, c2, c3 = st.columns([2, 1, 1]); n = c1.text_input("Comandante", value=str(d.get('comandante_nome') or "")); m = c2.text_input("Matrícula", value=str(d.get('comandante_matricula') or "")); vtr = c3.text_input("Vtr", value=str(d.get('viatura') or ""))
                h_c1, h_c2, h_c3 = st.columns([1, 1, 2]); h_e = h_c1.selectbox("Entrada", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0); h_s = h_c2.selectbox("Saída", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0); confirmar = h_c3.checkbox("Confirmar cumprimento", value=bool(d.get('cumprido')))
                rel = st.text_area("Relatório Resumido", value=str(d.get('relatorio_resumido') or ""))
                if st.form_submit_button("Submeter"):
                    if atualizar_cumprimento(d['id'], h_e, h_s, rel, confirmar, n, m, vtr): st.success("Atualizado!"); st.rerun()

# --- ABA 2: ESTATÍSTICAS (RECOLOCADO TERRITÓRIO E MÊS) ---
with menu[2]:
    st.subheader("📊 Análise de Dados Estratégicos")
    df_est = carregar_dados_db()
    if not df_est.empty:
        # Preparação
        df_est['data_dt'] = pd.to_datetime(df_est['data'])
        df_est['Mês/Ano'] = df_est['data_dt'].dt.strftime('%m/%Y')
        total_geral = len(df_est)
        
        territorios = {
            "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
            "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
        }
        mapeamento = {cidade: terr for terr, cidades in territorios.items() for cidade in cidades}
        df_est['Território'] = df_est['municipio'].map(mapeamento)

        # 1. Por Mês
        st.markdown("### 📅 Missões por Mês")
        df_mensal = df_est['Mês/Ano'].value_counts().reset_index()
        df_mensal.columns = ['Mês/Ano', 'Qtd']; df_mensal['%'] = (df_mensal['Qtd'] / total_geral * 100).map("{:.1f}%".format)
        col_m1, col_m2 = st.columns([1, 2])
        col_m1.dataframe(df_mensal, use_container_width=True, hide_index=True)
        col_m2.line_chart(df_est['Mês/Ano'].value_counts())

        st.markdown("---")

        # 2. Por Território de Identidade (RECOLOCADO)
        st.markdown("### 🌎 Por Território de Identidade")
        df_terr = df_est['Território'].value_counts().reset_index()
        df_terr.columns = ['Território', 'Qtd']; df_terr['%'] = (df_terr['Qtd'] / total_geral * 100).map("{:.1f}%".format)
        col_t1, col_t2 = st.columns([1, 1])
        col_t1.dataframe(df_terr, use_container_width=True, hide_index=True)
        col_t2.bar_chart(df_est['Território'].value_counts())

        st.markdown("---")

        # 3. Por Cidade
        st.markdown("### 🏙️ Ranking por Cidade")
        df_cid = df_est['municipio'].value_counts().reset_index()
        df_cid.columns = ['Cidade', 'Qtd']; df_cid['%'] = (df_cid['Qtd'] / total_geral * 100).map("{:.1f}%".format)
        st.dataframe(df_cid, use_container_width=True, hide_index=True)
        st.bar_chart(df_est['municipio'].value_counts(), horizontal=True)
    else:
        st.info("Aguardando registros para gerar estatísticas.")

# --- ABA 3: GESTÃO ---
with menu[3]:
    if not st.session_state.gestao_liberada:
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
        t_acoes, t_cpr = st.tabs(["📝 Escalonamento", "👮 Comandante CPR-ES"])
        
        with t_acoes:
            col_cad, col_del = st.columns(2)
            with col_cad:
                st.subheader("Agendar Missão")
                dt = st.date_input("Data:", datetime.date.today(), key="gest_dt")
                un = st.selectbox("Unidade:", ["CIPE-MA", "CIPT-ES"], key="gest_un")
                mu = st.selectbox("Município:", sorted(["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela", "Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]), key="gest_mu")
                h_e_ag = st.selectbox("Entrada:", lista_horas, key="gest_he")
                h_s_ag = st.selectbox("Saída:", lista_horas, key="gest_hs")
                ms = st.text_area("Objetivo:", key="gest_ms")
                if st.button("Confirmar Agendamento"):
                    salvar_no_db(dt, mu, un, ms, h_e_ag, h_s_ag); st.rerun()

            with col_del:
                st.subheader("Eliminar Registo")
                df_del = carregar_dados_db().sort_values(by='data', ascending=False)
                if not df_del.empty:
                    df_del['data_br'] = df_del['data'].apply(formatar_data_br)
                    v = st.selectbox("Registo:", (df_del['data_br'] + " | " + df_del['municipio']).tolist(), key="gest_del")
                    id_a = df_del[(df_del['data_br'] + " | " + df_del['municipio']) == v]['id'].values[0]
                    if st.button("Eliminar"): apagar_no_db(id_a); st.rerun()
            
            st.markdown("---")
            st.subheader("📊 Histórico Completo")
            df_h = carregar_dados_db()
            if not df_h.empty:
                df_h = df_h.sort_values(by='data', ascending=False)
                df_h['Data'] = df_h['data'].apply(formatar_data_br)
                df_h['Cumprida?'] = df_h['cumprido'].map({True: "Sim", False: "Não"})
                st.dataframe(df_h[['Data', 'municipio', 'unidade', 'viatura', 'comandante_nome', 'Cumprida?', 'relatorio_resumido']], use_container_width=True, hide_index=True)

        with t_cpr:
            st.subheader("Painel Executivo de Comando")
            df_cpr = carregar_dados_db()
            if not df_cpr.empty:
                df_cpr = df_cpr.sort_values(by='data', ascending=False)
                df_cpr['Situação'] = df_cpr['cumprido'].map({True: "✅ CUMPRIDA", False: "⚠️ AGENDADA"})
                st.dataframe(df_cpr[['data', 'municipio', 'unidade', 'Situação', 'comandante_nome', 'relatorio_resumido']], use_container_width=True, hide_index=True)
