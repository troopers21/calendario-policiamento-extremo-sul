import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Controle de Policiamento - Extremo Sul", layout="wide")

st.title("🛡️ Sistema de Prevenção de Sobreposição - PMBA")
st.subheader("Coordenação de Policiamento em 21 Municípios")

# Lista dos 21 municípios (Exemplo do Extremo Sul)
municipios = [
    "Teixeira de Freitas", "Itanhém", "Medeiros Neto", "Vereda", "Lajedão", 
    "Ibirapuã", "Caravelas", "Posto da Mata", "Nova Viçosa", "Mucuri", 
    "Prado", "Alcobaça", "Itamaraju", "Jucuruçu", "Guaratinga", 
    "Itabela", "Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itagimirim"
]

# Simulação de Banco de Dados (Em produção, usar st.session_state ou DB real)
if 'status_policiamento' not in st.session_state:
    st.session_state.status_policiamento = {m: "Livre" for m in municipios}

# Sidebar para Registro de Entrada
st.sidebar.header("Registrar Movimentação")
unidade = st.sidebar.selectbox("Sua Unidade:", ["Selecione", "Unidade 1", "Unidade 2"])
cidade_alvo = st.sidebar.selectbox("Município de Destino:", municipios)

if st.sidebar.button("Confirmar Entrada"):
    status_atual = st.session_state.status_policiamento[cidade_alvo]
    
    if status_atual == "Livre":
        st.session_state.status_policiamento[cidade_alvo] = unidade
        st.sidebar.success(f"Entrada confirmada em {cidade_alvo}")
    elif status_atual == unidade:
        st.sidebar.warning(f"Você já está registrado em {cidade_alvo}.")
    else:
        st.sidebar.error(f"BLOQUEIO: A {status_atual} já está operando em {cidade_alvo}!")

if st.sidebar.button("Registrar Saída/Liberação"):
    st.session_state.status_policiamento[cidade_alvo] = "Livre"
    st.sidebar.info(f"{cidade_alvo} agora está livre.")

# Exibição do Dashboard
col1, col2 = st.columns([2, 1])

with col1:
    st.write("### Mapa de Ocupação em Tempo Real")
    # Criando uma tabela visual para simular o mapa
    df = pd.DataFrame(list(st.session_state.status_policiamento.items()), columns=['Município', 'Ocupação'])
    
    def color_status(val):
        color = '#ffffff' # Branco para Livre
        if val == 'Unidade 1': color = '#add8e6' # Azul claro
        if val == 'Unidade 2': color = '#90ee90' # Verde claro
        return f'background-color: {color}'

    st.dataframe(df.style.map(color_status, subset=['Ocupação']), height=750, use_container_width=True)

with col2:
    st.write("### Resumo Operacional")
    u1_count = list(st.session_state.status_policiamento.values()).count("Unidade 1")
    u2_count = list(st.session_state.status_policiamento.values()).count("Unidade 2")
    livres = list(st.session_state.status_policiamento.values()).count("Livre")
    
    st.metric("Cidades com Unidade 1", u1_count)
    st.metric("Cidades com Unidade 2", u2_count)
    st.metric("Cidades Disponíveis", livres)
