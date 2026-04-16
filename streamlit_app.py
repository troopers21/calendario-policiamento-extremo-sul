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
col_logo1, col_logo2, col_logo3 = st.columns([2, 1, 2])
with col_logo2:
    try:
        st.image("logo_unidade.jpeg", width=700) 
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
        colunas_nec = [
            'id', 'data', 'municipio', 'unidade', 'missao', 'cumprido', 
            'hora_entrada', 'hora_saida', 'relatorio_resumido', 
            'comandante_nome', 'comandante_matricula', 'viatura'
        ]
        for col in colunas_nec:
            if col not in df.columns: df[col] = None
        return df
    except:
        return pd.DataFrame(columns=['id', 'data', 'municipio', 'unidade', 'missao'])

def salvar_no_db(data, municipio, unidade, missao, h_ent, h_sai):
    supabase.table("escala_operacional").insert({
        "data": data.strftime("%Y-%m-%d"), 
        "municipio": municipio, 
        "unidade": unidade, 
        "missao": missao, 
        "cumprido": False,
        "hora_entrada": h_ent,
        "hora_saida": h_sai
    }).execute()

def atualizar_cumprimento(id_registro, entrada, saida, relatorio, status_bool, nome, matricula, vtr):
    try:
        supabase.table("escala_operacional").update({
            "hora_entrada": entrada, "hora_saida": saida, "relatorio_resumido": relatorio,
            "cumprido": status_bool, "comandante_nome": nome, "comandante_matricula": matricula,
            "viatura": vtr
        }).eq("id", id_registro).execute()
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

menu = st.tabs(["📋 Consulta de Escala", "✅ Cumprimento de Missão", "⚙️ Gestão SISPOSIÇÃO"])

# --- ABA 0: CONSULTA ---
with menu[0]:
    data_con = st.date_input("Consultar Data:", datetime.date.today())
    df_total = carregar_dados_db()
    
    regioes = {
        "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
        "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
    }

    existem_missoes = False
    for regiao, cidades in regioes.items():
        rows = []
        if not df_total.empty:
            df_dia = df_total[(df_total['data'] == data_con.strftime("%Y-%m-%d")) & (df_total['municipio'].isin(cidades))]
            if not df_dia.empty:
                existem_missoes = True
                st.markdown(f"#### 📍 {regiao}")
                for _, r in df_dia.iterrows():
                    status_txt = "✅ Missão Cumprida" if r.get('cumprido') is True else "⚠️ Em Aberto"
                    rows.append({"Município": r['municipio'], "Unidade": r['unidade'], "Entrada": r['hora_entrada'], "Saída": r['hora_saida'], "Estado": status_txt})
                df_reg_view = pd.DataFrame(rows)
                st.dataframe(df_reg_view, use_container_width=True, hide_index=True)
    if not existem_missoes:
        st.info(f"Não existem missões registadas no SISPOSIÇÃO para o dia {data_con.strftime('%d/%m/%Y')}.")

# --- ABA 1: CUMPRIMENTO ---
with menu[1]:
    st.subheader("Registo de Desfecho Operacional")
    df_raw = carregar_dados_db()
    if not df_raw.empty:
        hoje = datetime.date.today().strftime("%Y-%m-%d")
        df_filt = df_raw[df_raw['data'] <= hoje].copy()
        if not df_filt.empty:
            df_filt['data_br'] = df_filt['data'].apply(formatar_data_br)
            df_filt['selecao'] = df_filt['data_br'] + " | " + df_filt['municipio']
            sel_missao = st.selectbox("Selecione a Missão Cumprida:", df_filt['selecao'].tolist())
            d = df_filt[df_filt['selecao'] == sel_missao].iloc[0]
            with st.form("f_cump"):
                c1, c2, c3 = st.columns([2, 1, 1])
                n = c1.text_input("Comandante da Guarnição", value=str(d.get('comandante_nome') or ""))
                m = c2.text_input("Matrícula", value=str(d.get('comandante_matricula') or ""))
                vtr = c3.text_input("Prefixo Vtr", value=str(d.get('viatura') or ""), placeholder="Ex: 9.0201")
                
                h_c1, h_c2, h_c3 = st.columns([1, 1, 2])
                h_e = h_c1.selectbox("Entrada Real", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
                h_s = h_c2.selectbox("Saída Real", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
                confirmar = h_c3.checkbox("Confirmar cumprimento total da missão", value=bool(d.get('cumprido')))
                
                rel = st.text_area("Resumo da Missão (Ex.: Reintegração de Posse, Revista em Presídio, etc)", value=str(d.get('relatorio_resumido') or ""))
                if st.form_submit_button("Submeter para o SISPOSIÇÃO"):
                    if atualizar_cumprimento(d['id'], h_e, h_s, rel, confirmar, n, m, vtr): 
                        st.success("Registo atualizado com sucesso no sistema!")
                        st.rerun()

# --- ABA 2: GESTÃO ---
with menu[2]:
    if not st.session_state.gestao_liberada:
        st.warning("🔒 Área Restrita à Chave de Comando CPR-ES.")
        ch = st.text_input("Chave de Segurança:", type="password")
        if st.button("Desbloquear Painel"):
            if ch == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True
                st.rerun()
    else:
        st.button("🔒 Bloquear Painel de Gestão", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        t_acoes, t_cpr = st.tabs(["📝 Escalonamento de Missões", "👮 Comandante CPR-ES"])
        
        with t_acoes:
            col_cad, col_del = st.columns(2)
            with col_cad:
                st.subheader("Agendar Nova Missão")
                dt = st.date_input("Data:", datetime.date.today(), key="gest_dt")
                un = st.selectbox("Unidade:", ["CIPE-MA", "CIPT-ES"], key="gest_un")
                todas_cids = sorted(["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela", "Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"])
                mu = st.selectbox("Município:", todas_cids, key="gest_mu")
                h_e_ag = st.selectbox("Entrada Prevista:", lista_horas, key="gest_he")
                h_s_ag = st.selectbox("Saída Prevista:", lista_horas, key="gest_hs")
                ms = st.text_area("Missão / Objetivo:", key="gest_ms")
                
                if st.button("Confirmar Agendamento no SISPOSIÇÃO"):
                    conflito = False 
                    df_ex = carregar_dados_db()
                    
                    if not df_ex.empty:
                        mesma_cidade = df_ex[(df_ex['data'] == dt.strftime("%Y-%m-%d")) & (df_ex['municipio'] == mu)]
                        for _, row in mesma_cidade.iterrows():
                            ex_in = int(row['hora_entrada'].split(':')[0])
                            ex_fi = int(row['hora_saida'].split(':')[0])
                            no_in = int(h_e_ag.split(':')[0])
                            no_fi = int(h_s_ag.split(':')[0])
                            # Lógica de Sobreposição
                            if (no_in < ex_fi) and (no_fi > ex_in):
                                conflito = True
                                st.error(f"❌ BLOQUEIO SISPOSIÇÃO: {mu} já possui missão agendada entre {row['hora_entrada']} e {row['hora_saida']}.")
                                break
                    
                    if not conflito:
                        if int(h_s_ag.split(':')[0]) <= int(h_e_ag.split(':')[0]):
                            st.error("Erro: O horário de saída deve ser posterior ao de entrada.")
                        else:
                            salvar_no_db(dt, mu, un, ms, h_e_ag, h_s_ag)
                            st.rerun()

            with col_del:
                st.subheader("Eliminar Registo")
                df_del = carregar_dados_db().sort_values(by='data', ascending=False)
                if not df_del.empty:
                    df_del['data_br'] = df_del['data'].apply(formatar_data_br)
                    v = st.selectbox("Escolha o registo para eliminar:", (df_del['data_br'] + " | " + df_del['municipio']).tolist(), key="gest_del")
                    id_a = df_del[(df_del['data_br'] + " | " + df_del['municipio']) == v]['id'].values[0]
                    if st.button("Eliminar Permanentemente"): apagar_no_db(id_a); st.rerun()
            
            st.markdown("---")
            st.subheader("📊 Histórico Completo SISPOSIÇÃO")
            df_h = carregar_dados_db()
            if not df_h.empty:
                df_h = df_h.sort_values(by='data', ascending=False)
                df_h['Data'] = df_h['data'].apply(formatar_data_br)
                df_h['Dia'] = df_h['data'].apply(obter_dia_semana)
                df_h['Cumprida?'] = df_h['cumprido'].map({True: "Sim", False: "Não"}).fillna("-")
                st.dataframe(df_h[['Data', 'Dia', 'municipio', 'unidade', 'viatura', 'comandante_nome', 'Cumprida?', 'hora_entrada', 'hora_saida', 'relatorio_resumido']], use_container_width=True, hide_index=True)

        with t_cpr:
            st.subheader("Painel Executivo de Comando")
            df_cpr_data = carregar_dados_db()
            if not df_cpr_data.empty:
                df_cpr_data = df_cpr_data.sort_values(by='data', ascending=False)
                df_cpr_data['Data'] = df_cpr_data['data'].apply(formatar_data_br)
                df_cpr_data['Estado'] = df_cpr_data['cumprido'].map({True: "✅ CUMPRIDA", False: "⚠️ AGENDADA"}).fillna("⚠️ AGENDADA")
                df_cpr_view = df_cpr_data[['Data', 'municipio', 'unidade', 'Estado', 'hora_entrada', 'hora_saida', 'comandante_nome', 'relatorio_resumido']]
                df_cpr_view.columns = ['Data', 'Cidade', 'Unidade', 'Situação Operacional', 'Início', 'Fim', 'Comandante', 'Resumo/Relatório']
                st.dataframe(df_cpr_view, use_container_width=True, hide_index=True)
