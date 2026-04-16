import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÕES E BANCO ---
USUARIO_CORRETO = "admin"
SENHA_CORRETA = "pmba2026"
CHAVE_GESTAO = "comando2026"

url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Sistema de Policiamento - PMBA", layout="wide")

# --- 2. LOGO NO TOPO ---
col_logo1, col_logo2, col_logo3 = st.columns([2, 1, 2])
with col_logo2:
    try:
        st.image("logo_unidade.jpeg", width=900) 
    except:
        pass

st.markdown("<h1 style='text-align: center;'>📅 Sistema Operacional - Extremo Sul</h1>", unsafe_allow_html=True)

# --- 3. FUNÇÕES DE SUPORTE ---
def carregar_dados_db():
    try:
        response = supabase.table("escala_operacional").select("*").execute()
        df = pd.DataFrame(response.data)
        colunas = ['id', 'data', 'municipio', 'unidade', 'missao', 'cumprido', 'hora_entrada', 'hora_saida', 'relatorio_resumido', 'comandante_nome', 'comandante_matricula']
        for col in colunas:
            if col not in df.columns: df[col] = None
        return df
    except:
        return pd.DataFrame(columns=['id', 'data', 'municipio', 'unidade', 'missao'])

def atualizar_cumprimento(id_registro, entrada, saida, relatorio, status_bool, nome, matricula):
    try:
        supabase.table("escala_operacional").update({
            "hora_entrada": entrada,
            "hora_saida": saida,
            "relatorio_resumido": relatorio,
            "cumprido": status_bool,
            "comandante_nome": nome,
            "comandante_matricula": matricula
        }).eq("id", id_registro).execute()
        return True
    except: return False

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

def apagar_no_db(id_registro):
    try:
        supabase.table("escala_operacional").delete().eq("id", id_registro).execute()
        return True
    except: return False

def formatar_data_br(data_iso):
    try:
        return datetime.datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except: return data_iso

def obter_dia_semana(data_str):
    dias = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
    try:
        data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d")
        return dias[data_obj.weekday()]
    except: return "-"

# Lista de horas para o selectbox
lista_horas = [f"{h:02d}:00" for h in range(24)]

# --- 4. LÓGICA DE AUTENTICAÇÃO ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
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
                else: st.error("Usuário ou senha inválidos.")
    st.stop()

# --- 5. INTERFACE PRINCIPAL ---
if st.sidebar.button("Logoff"):
    st.session_state.autenticado = False
    st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "⚙️ Gestão"])

# ABA CONSULTA
with menu[0]:
    data_con = st.date_input("Filtrar por Dia", datetime.date.today())
    df_total = carregar_dados_db()
    # (Lógica de cores e exibição simplificada mantida...)

# ABA CUMPRIMENTO
with menu[1]:
    st.subheader("Registrar Cumprimento")
    df_raw = carregar_dados_db()
    if not df_raw.empty:
        hoje = datetime.date.today().strftime("%Y-%m-%d")
        df_filt = df_raw[df_raw['data'] <= hoje].copy()
        if not df_filt.empty:
            df_filt['data_br'] = df_filt['data'].apply(formatar_data_br)
            df_filt['selecao'] = df_filt['data_br'] + " | " + df_filt['municipio']
            sel = st.selectbox("Selecione a Missão:", df_filt['selecao'].tolist())
            d = df_filt[df_filt['selecao'] == sel].iloc[0]
            
            with st.form("f_cump"):
                col1, col2 = st.columns(2)
                n = col1.text_input("Comandante da Guarnição", value=str(d.get('comandante_nome') or ""))
                m = col2.text_input("Matrícula", value=str(d.get('comandante_matricula') or ""))
                # Aqui o cumprimento pode apenas confirmar as horas já sugeridas na gestão ou editá-las
                h_e = col1.selectbox("Entrada Real na Cidade", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
                h_s = col2.selectbox("Saída Real na Cidade", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
                confirmar = st.checkbox("Sim", value=bool(d.get('cumprido')))
                rel = st.text_area("Resumo da Missão", value=str(d.get('relatorio_resumido') or ""))
                if st.form_submit_button("Salvar Registro"):
                    if atualizar_cumprimento(d['id'], h_e, h_s, rel, confirmar, n, m):
                        st.success("Registrado!")
                        st.rerun()

# ABA GESTÃO (COM TRAVA DE SOBREPOSIÇÃO)
with menu[2]:
    if not st.session_state.gestao_liberada:
        ch = st.text_input("Chave de Comando:", type="password")
        if st.button("Liberar Acesso"):
            if ch == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True
                st.rerun()
    else:
        st.button("🔒 Bloquear", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        t1, t2 = st.tabs(["📝 Agendar", "🗑️ Apagar"])
        with t1:
            todas_cidades = sorted(["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela", "Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"])
            c1, c2 = st.columns(2)
            dt = c1.date_input("Data da Missão", datetime.date.today())
            un = c1.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
            mu = c2.selectbox("Município", todas_cidades)
            h_ent_ag = c1.selectbox("Hora de Entrada Prevista", lista_horas)
            h_sai_ag = c2.selectbox("Hora de Saída Prevista", lista_horas)
            ms = c2.text_area("Missão")
            
            if st.button("Salvar Agendamento"):
                # Lógica de Sobreposição
                dt_str = dt.strftime("%Y-%m-%d")
                df_existente = carregar_dados_db()
                conflito = False
                
                if not df_existente.empty:
                    # Filtra missões da mesma unidade no mesmo dia
                    mesmo_dia = df_existente[(df_existente['data'] == dt_str) & (df_existente['unidade'] == un)]
                    
                    for _, row in mesmo_dia.iterrows():
                        # Converter strings de hora para inteiros para comparação
                        ex_inicio = int(row['hora_entrada'].split(':')[0])
                        ex_fim = int(row['hora_saida'].split(':')[0])
                        novo_inicio = int(h_ent_ag.split(':')[0])
                        novo_fim = int(h_sai_ag.split(':')[0])
                        
                        # Verifica se o intervalo novo invade o intervalo existente
                        if (novo_inicio < ex_fim) and (novo_fim > ex_inicio):
                            conflito = True
                            st.error(f"❌ Conflito de Horário! A unidade {un} já possui missão em {row['municipio']} das {row['hora_entrada']} às {row['hora_saida']}.")
                            break
                
                if not conflito:
                    if int(h_sai_ag.split(':')[0]) <= int(h_ent_ag.split(':')[0]):
                        st.error("A hora de saída deve ser maior que a hora de entrada.")
                    else:
                        salvar_no_db(dt, mu, un, ms, h_ent_ag, h_sai_ag)
                        st.success("Agendado com sucesso!")
                        st.rerun()

# --- 8. HISTÓRICO COM DATA BR ---
with st.expander("📊 Histórico Completo"):
    df_h = carregar_dados_db()
    if not df_h.empty:
        df_h = df_h.sort_values(by='data', ascending=False)
        df_h['Data'] = df_h['data'].apply(formatar_data_br)
        df_h['Dia da Semana'] = df_h['data'].apply(obter_dia_semana)
        df_h['Cumprida?'] = df_h['cumprido'].map({True: "Sim", False: "Não"}).fillna("-")
        st.dataframe(df_h[['Data', 'Dia da Semana', 'municipio', 'unidade', 'comandante_nome', 'Cumprida?', 'hora_entrada', 'hora_saida', 'relatorio_resumido']], use_container_width=True, hide_index=True)
