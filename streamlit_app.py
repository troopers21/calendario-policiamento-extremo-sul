import streamlit as st
import pandas as pd
import os

# Configuração da página
st.set_page_config(page_title="Controle de Policiamento - PMBA", layout="wide")

st.title("🛡️ Sistema de Prevenção de Sobreposição - PMBA")

# --- ORGANIZAÇÃO DOS MUNICÍPIOS ---
prioritarios = ["Teixeira de Freitas", "Porto Seguro", "Eunápolis"]

todos_municipios = [
    "Teixeira de Freitas", "Itanhém", "Medeiros Neto", "Vereda", "Lajedão", 
    "Ibirapuã", "Caravelas", "Posto da Mata", "Nova Viçosa", "Mucuri", 
    "Prado", "Alcobaça", "Itamaraju", "Jucuruçu", "Guaratinga", 
    "Itabela", "Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itagimirim"
]

restante_alfabetico = sorted([m for m in todos_municipios if m not in prioritarios])
municipios = prioritarios + restante_alfabetico

# --- LÓGICA DE PERSISTÊNCIA ---
DB_FILE = "status_policiamento.csv"

def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE, index_col=0)['Ocupação'].to_dict()
        except:
            return {m: "Livre" for m in municipios}
    return {m: "Livre" for m in municipios}

def salvar_dados(dados):
    df_save = pd.DataFrame(list(dados.items()), columns=['Município', 'Ocupação'])
    df_save.to_csv(DB_FILE)

if 'status_policiamento' not in st.session_state:
    st.session_state.status_policiamento = carregar_dados()

# --- INTERFACE ---
st.sidebar.header("Registrar Movimentação")
unidade = st.sidebar.selectbox("Sua Unidade:", ["Selecione", "CIPE-MA", "CIPT-ES"])
cidade_alvo = st.sidebar.selectbox("Município de Destino:", municipios)

if st.sidebar.button("Confirmar Entrada"):
    st.session_state.status_policiamento = carregar_dados()
    status_atual = st.session_state.status_policiamento.get(cidade_alvo, "Livre")
    
    if status_atual == "Livre":
        st.session_state.status_policiamento[cidade_alvo] = unidade
        salvar_dados(st.session_state.status_policiamento)
        st.sidebar.success(f"Entrada confirmada em {cidade_alvo}")
        st.rerun()
    elif status_atual == unidade:
        st.sidebar.warning(f"Você já está registrado em {cidade_alvo}.")
    else:
        st.sidebar.error(f"BLOQUEIO: A {status_atual} já está em {cidade_alvo}!")

if st.sidebar.button("Registrar Saída/Liberação"):
    st.session_state.status_policiamento[cidade_alvo] = "Livre"
    salvar_dados(st.session_state.status_policiamento)
    st.sidebar.info(f"{cidade_alvo} liberada.")
    st.rerun()

# Exibição
status_dict = st.session_state.status_policiamento
df = pd.DataFrame([{"Município": m, "Ocupação": status_dict.get(m, "Livre")} for m in municipios])

def color_status(val):
    color = '#ffffff'
    if val == 'CIPE-MA': color = '#add8e6' # Azul claro
    if val == 'CIPT-ES': color = '#90ee90' # Verde claro
    return f'background-color: {color}'

st.write("### Mapa de Ocupação Atualizado")
st.dataframe(df.style.map(color_status, subset=['Ocupação']), height=750, use_container_width=True)

if st.button("🔄 Atualizar Mapa"):
    st.session_state.status_policiamento = carregar_dados()
    st.rerun()
