import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
import os

# --- 1. CONFIGURAÇÕES DE ACESSO ---
USUARIO_CORRETO = "admin"
SENHA_CORRETA = "pmba2026"
CHAVE_GESTAO = "comando2026"

# --- 2. CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE) ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Configuração da Página
st.set_page_config(page_title="Sistema de Policiamento - PMBA", layout="wide")

# --- 3. POSICIONAMENTO DA IMAGEM NO TOPO ---
# Criamos colunas para centralizar a imagem
col_logo1, col_logo2, col_logo3 = st.columns([2, 1, 2])
with col_logo2:
    # Verifique se o nome do arquivo está correto no seu GitHub
    # Se a imagem estiver na pasta raiz, basta o nome dela:
    try:
        st.image("logo_unidade.jpeg", width=150) 
    except:
        st.warning("Arquivo 'logo_unidade.png' não encontrado no repositório.")

# --- 4. TÍTULOS E DEFINIÇÕES ---
st.markdown("<h1 style='text-align: center;'>📅 Sistema Operacional - Extremo Sul</h1>", unsafe_allow_html=True)

regioes = {
    "Costa do Descobrimento": [
        "Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", 
        "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"
    ],
    "Costa das Baleias": [
        "Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", 
        "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", 
        "Prado", "Caravelas", "Mucuri", "Nova Viçosa"
    ]
}

todas_cidades = sorted([c for lista in regioes.values() for c in lista])

# --- 5. FUNÇÕES DE SUPORTE ---
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

def salvar_no_db(data, municipio, unidade, missao):
    supabase.table("escala_operacional").insert({"data": data.strftime("%Y-%m-%d"), "municipio": municipio, "unidade": unidade, "missao": missao, "cumprido": None}).execute()

def atualizar_cumprimento(id_registro, entrada, saida, relatorio, status_sim_nao, nome, matricula):
    valor_cumprido = True if status_sim_nao == "Sim" else False if status_sim_nao == "Não" else None
    try:
        supabase.table("escala_operacional").update({"hora_entrada": entrada, "hora_saida": saida, "relatorio_resumido": relatorio, "cumprido": valor_cumprido, "comandante_nome": nome, "comandante_matricula": matricula}).eq("id", id_registro).execute()
        return True
    except: return False

def apagar_no_db(id_registro):
    try:
        supabase.table("escala_operacional").delete().eq("id", id_registro).execute()
        return True
    except: return False

def obter_dia_semana(data_str):
    dias = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
    try:
        data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d")
        return dias[data_obj.weekday()]
    except: return "-"

def color_status(val):
    if val == 'CIPE-MA': return 'background-color: #add8e6; color: black'
    if val == 'CIPT-ES': return 'background-color: #90ee90; color: black'
    return 'background-color: white; color: black'

# --- 6. AUTENTICAÇÃO ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "gestao_liberada" not in st.session_state: st.session_state.gestao_liberada = False

if not st.session_state.autenticado:
    with st.form("login"):
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if u == USUARIO_CORRETO and p == SENHA_CORRETA:
                st.session_state.autenticado = True
                st.rerun()
            else: st.error("Erro")
    st.stop()

# --- 7. INTERFACE PRINCIPAL ---
if st.sidebar.button("Logoff"):
    st.session_state.autenticado = False
    st.rerun()

menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "⚙️ Gestão"])

with menu[0]:
    data_con = st.date_input("Filtrar por Dia", datetime.date.today())
    df_total = carregar_dados_db()
    for regiao, cidades in regioes.items():
        st.markdown(f"#### 📍 {regiao}")
        rows = []
        for cid in cidades:
            rows.append({"Município": cid, "Ocupação": "Livre", "Status": "Pendente"})
        df_reg = pd.DataFrame(rows)
        if not df_total.empty:
            df_dia = df_total[df_total['data'] == data_con.strftime("%Y-%m-%d")]
            for _, r in df_dia.iterrows():
                if r['municipio'] in cidades:
                    txt = "✅ Cumprido" if r.get('cumprido') is True else "❌ Não" if r.get('cumprido') is False else "⚠️ Escalado"
                    df_reg.loc[df_reg['Município'] == r['municipio'], ['Ocupação', 'Status']] = [r['unidade'], txt]
        st.dataframe(df_reg.style.map(color_status, subset=['Ocupação']), use_container_width=True, hide_index=True)

with menu[1]:
    df_raw = carregar_dados_db()
    if not df_raw.empty:
        hoje = datetime.date.today().strftime("%Y-%m-%d")
        df_cump = df_raw[df_raw['data'] <= hoje].copy()
        if not df_cump.empty:
            df_cump['selecao'] = df_cump['data'] + " | " + df_cump['municipio']
            sel = st.selectbox("Escolha a Missão:", df_cump['selecao'].tolist())
            d = df_cump[df_cump['selecao'] == sel].iloc[0]
            with st.form("f_cump"):
                c1, c2 = st.columns(2)
                n = c1.text_input("Comandante", value=str(d.get('comandante_nome') or ""))
                m = c2.text_input("Matrícula", value=str(d.get('comandante_matricula') or ""))
                e = c1.text_input("Entrada na Cidade", value=str(d.get('hora_entrada') or ""))
                s = c2.text_input("Saída na Cidade", value=str(d.get('hora_saida') or ""))
                st_sel = st.selectbox("Missão Cumprida?", ["", "Sim", "Não"], index=(1 if d.get('cumprido') is True else 2 if d.get('cumprido') is False else 0))
                rel = st.text_area("Resumo", value=str(d.get('relatorio_resumido') or ""))
                if st.form_submit_button("Salvar"):
                    if atualizar_cumprimento(d['id'], e, s, rel, st_sel, n, m): st.rerun()

with menu[2]:
    if not st.session_state.gestao_liberada:
        ch = st.text_input("Chave:", type="password")
        if st.button("Liberar"):
            if ch == CHAVE_GESTAO:
                st.session_state.gestao_liberada = True
                st.rerun()
    else:
        st.button("🔒 Bloquear", on_click=lambda: st.session_state.update({"gestao_liberada": False}))
        t1, t2 = st.tabs(["📝 Agendar", "🗑️ Apagar"])
        with t1:
            c1, c2 = st.columns(2)
            dt = c1.date_input("Data", datetime.date.today())
            un = c1.selectbox("Unidade", ["CIPE-MA", "CIPT-ES"])
            mu = c2.selectbox("Município", todas_cidades)
            ms = c2.text_area("Missão")
            if st.button("Salvar Registro"):
                salvar_no_db(dt, mu, un, ms)
                st.rerun()
        with t2:
            df_del = carregar_dados_db().sort_values(by='data', ascending=False)
            if not df_del.empty:
                v = st.selectbox("Apagar:", (df_del['data'] + " | " + df_del['municipio']).tolist())
                id_a = df_del[(df_del['data'] + " | " + df_del['municipio']) == v]['id'].values[0]
                if st.button("Confirmar Exclusão"):
                    apagar_no_db(id_a)
                    st.rerun()

# --- 8. HISTÓRICO ---
with st.expander("📊 Histórico"):
    df_h = carregar_dados_db()
    if not df_h.empty:
        df_h = df_h.sort_values(by='data', ascending=False)
        df_h['Dia da Semana'] = df_h['data'].apply(obter_dia_semana)
        df_h['Cumprida?'] = df_h['cumprido'].map({True: "Sim", False: "Não"}).fillna("-")
        st.dataframe(df_h[['data', 'Dia da Semana', 'municipio', 'unidade', 'comandante_nome', 'Cumprida?', 'hora_entrada', 'hora_saida', 'relatorio_resumido']], use_container_width=True, hide_index=True)
