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

st.set_page_config(page_title="CPR-ES - Sistema Controle Antisobreposição do Policiamento", layout="wide")

# --- 2. LOGO NO TOPO ---
col_logo1, col_logo2, col_logo3 = st.columns([2, 1, 2])
with col_logo2:
    try:
        st.image("logo_unidade.jpeg", width=800) 
    except:
        pass

st.markdown("<h1 style='text-align: center;'>📅 CPR-ES - Sistema Controle Antisobreposição do Policiamento</h1>", unsafe_allow_html=True)

# --- 3. FUNÇÕES DE SUPORTE ---
def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        df = pd.DataFrame(response.data)
        colunas_nec = ['id', 'data', 'municipio', 'unidade', 'missao', 'cumprido', 'hora_entrada', 'hora_saida', 'relatorio_resumido', 'comandante_nome', 'comandante_matricula']
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

def atualizar_cumprimento(id_registro, entrada, saida, relatorio, status_bool, nome, matricula):
    try:
        supabase.table("escala_operacional").update({
            "hora_entrada": entrada, "hora_saida": saida, "relatorio_resumido": relatorio,
            "cumprido": status_bool, "comandante_nome": nome, "comandante_matricula": matricula
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
            st.subheader("🔐 Login de Acesso")
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if u == USUARIO_CORRETO and p == SENHA_CORRETA:
                    st.session_state.autenticado = True
                    st.rerun()
                else: st.error("Incorreto.")
    st.stop()

# --- 5. INTERFACE PRINCIPAL ---
if st.sidebar.button("Sair / Logoff"):
    st.session_state.autenticado = False
    st.session_state.gestao_liberada = False
    st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "⚙️ Gestão"])

# --- ABA 0: CONSULTA (Ajuste da Altura feito aqui) ---
with menu[0]:
    data_con = st.date_input("Selecione a Data", datetime.date.today())
    df_total = carregar_dados_db()
    
    regioes = {
        "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
        "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
    }

    for regiao, cidades in regioes.items():
        st.markdown(f"#### 📍 {regiao}")
        rows = []
        for cid in cidades:
            rows.append({"Município": cid, "Unidade": "Livre", "Status": "Pendente"})
        df_reg = pd.DataFrame(rows)
        
        if not df_total.empty:
            df_dia = df_total[df_total['data'] == data_con.strftime("%Y-%m-%d")]
            for _, r in df_dia.iterrows():
                if r['municipio'] in cidades:
                    txt = "✅ Cumprido" if r.get('cumprido') is True else "⚠️ Escalado"
                    df_reg.loc[df_reg['Município'] == r['municipio'], ['Unidade', 'Status']] = [r['unidade'], txt]
        
        # AJUSTE: O cálculo da altura impede a barra de rolagem (40px por linha aprox + cabeçalho)
        altura_dinamica = (len(cidades) + 1) * 35 + 3
        
        st.dataframe(
            df_reg, 
            use_container_width=True, 
            hide_index=True, 
            height=altura_dinamica
        )

# --- ABA 1: CUMPRIMENTO ---
with menu[1]:
    st.subheader("Registrar Cumprimento")
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
                c1, c2 = st.columns(2)
                n = c1.text_input("Comandante", value=str(d.get('comandante_nome') or ""))
                m = c2.text_input("Matrícula", value=str(d.get('comandante_matricula') or ""))
                h_e = c1.selectbox("Hora Entrada", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
                h_s = c2.selectbox("Hora Saída", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
                confirmar = st.checkbox("Sim", value=bool(d.get('cumprido')))
                rel = st.text_area("Resumo", value=str(d.get('relatorio_resumido') or ""))
                if st.form_submit_button("Salvar Registro"):
                    if atualizar_cumprimento(d['id'], h_e, h_s, rel, confirmar, n, m): st.rerun()

# --- ABA 2: GESTÃO ---
with menu[2]:
    if not st.session_state.gestao_liberada:
        ch = st.text_input("Insira a Chave:", type="password")
        if st.button("Liberar Acesso"):
            if ch == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True
                st.rerun()
    else:
        st.button("🔒 Bloquear", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        t1, t2 = st.tabs(["📝 Agendar", "🗑️ Apagar"])
        with t1:
            c1, c2 = st.columns(2)
            dt = c1.date_input("Data da Missão", datetime.date.today())
            un = c1.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
            mu = c2.selectbox("Município", sorted([cid for reg in regioes.values() for cid in reg]))
            h_ent_ag = c1.selectbox("Entrada Prevista", lista_horas)
            h_sai_ag = c2.selectbox("Saída Prevista", lista_horas)
            ms = c2.text_area("Missão")
            if st.button("Salvar Agendamento"):
                df_ex = carregar_dados_db()
                conflito = False
                if not df_ex.empty:
                    mesma_cidade = df_ex[(df_ex['data'] == dt.strftime("%Y-%m-%d")) & (df_ex['municipio'] == mu)]
                    for _, row in mesma_cidade.iterrows():
                        ex_in = int(row['hora_entrada'].split(':')[0]); ex_fi = int(row['hora_saida'].split(':')[0])
                        no_in = int(h_ent_ag.split(':')[0]); no_fi = int(h_sai_ag.split(':')[0])
                        if (no_in < ex_fi) and (no_fi > ex_in):
                            conflito = True
                            st.error(f"❌ Conflito em {mu}."); break
                if not conflito:
                    salvar_no_db(dt, mu, un, ms, h_ent_ag, h_sai_ag); st.rerun()
        with t2:
            df_del = carregar_dados_db().sort_values(by='data', ascending=False)
            if not df_del.empty:
                df_del['data_br'] = df_del['data'].apply(formatar_data_br)
                v = st.selectbox("Escolha para apagar:", (df_del['data_br'] + " | " + df_del['municipio']).tolist())
                id_a = df_del[(df_del['data_br'] + " | " + df_del['municipio']) == v]['id'].values[0]
                if st.button("Confirmar Exclusão"): apagar_no_db(id_a); st.rerun()

# --- 8. HISTÓRICO ---
st.markdown("---")
with st.expander("📊 Histórico"):
    df_h = carregar_dados_db()
    if not df_h.empty:
        df_h = df_h.sort_values(by='data', ascending=False)
        df_h['Data'] = df_h['data'].apply(formatar_data_br)
        df_h['Dia da Semana'] = df_h['data'].apply(obter_dia_semana)
        df_h['Cumprida?'] = df_h['cumprido'].map({True: "Sim", False: "Não"}).fillna("-")
        st.dataframe(df_h[['Data', 'Dia da Semana', 'municipio', 'unidade', 'comandante_nome', 'Cumprida?', 'hora_entrada', 'hora_saida', 'relatorio_resumido']], use_container_width=True, hide_index=True)
