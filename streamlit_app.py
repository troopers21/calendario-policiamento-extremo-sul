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

# --- LÓGICA DE PERSISTÊNCIA ROBUSTA ---
DB_FILE = "status_policiamento.csv"

def carregar_dados_do_arquivo():
    """Lê o arquivo CSV e retorna um dicionário com o status de cada cidade."""
    dados_atuais = {m: "Livre" for m in municipios}
    if os.path.exists(DB_FILE):
        try:
            df_lido = pd.read_csv(DB_FILE, index_col=0)
            # Converte o CSV de volta para dicionário atualizando o padrão
            for m, ocup in df_lido.set_index('Município')['Ocupação'].to_dict().items():
                if m in dados_atuais:
                    dados_atuais[m] = ocup
        except:
            pass
    return dados_atuais

def salvar_dados_no_arquivo(dados):
    """Salva o dicionário completo no arquivo CSV."""
    df_save = pd.DataFrame(list(dados.items()), columns=['Município', 'Ocupação'])
    df_save.to_csv(DB_FILE)

# Inicialização da sessão
if 'status_policiamento' not in st.session_state:
    st.session_state.status_policiamento = carregar_dados_do_arquivo()

# --- INTERFACE LATERAL ---
st.sidebar.header("Registrar Movimentação")
unidade = st.sidebar.selectbox("Sua Unidade:", ["Selecione", "CIPE-MA", "CIPT-ES"])
cidade_alvo = st.sidebar.selectbox("Município de Destino:", municipios)

# BOTÃO ENTRADA
if st.sidebar.button("Confirmar Entrada"):
    if unidade == "Selecione":
        st.sidebar.error("Selecione sua unidade primeiro!")
    else:
        # 1. Busca o que está gravado no arquivo AGORA (sincronização)
        dados_do_disco = carregar_dados_do_arquivo()
        status_atual = dados_do_disco.get(cidade_alvo, "Livre")
        
        if status_atual == "Livre":
            # 2. Atualiza apenas a cidade selecionada mantendo as outras
            dados_do_disco[cidade_alvo] = unidade
            salvar_dados_no_arquivo(dados_do_disco)
            st.session_state.status_policiamento = dados_do_disco
            st.sidebar.success(f"Entrada confirmada em {cidade_alvo}")
            st.rerun()
        elif status_atual == unidade:
            st.sidebar.warning(f"Você já está registrado em {cidade_alvo}.")
        else:
            st.sidebar.error(f"BLOQUEIO: A {status_atual} já está em {cidade_alvo}!")

# BOTÃO SAÍDA
if st.sidebar.button("Registrar Saída/Liberação"):
    dados_do_disco = carregar_dados_do_arquivo()
    dados_do_disco[cidade_alvo] = "Livre"
    salvar_dados_no_arquivo(dados_do_disco)
    st.session_state.status_policiamento = dados_do_disco
    st.sidebar.info(f"{cidade_alvo} liberada.")
    st.rerun()

# --- EXIBIÇÃO DO DASHBOARD ---
# Sempre lê do estado da sessão que foi sincronizado com o disco
df_view = pd.DataFrame([{"Município": m, "Ocupação": st.session_state.status_policiamento.get(m, "Livre")} for m in municipios])

def color_status(val):
    if val == 'CIPE-MA': return 'background-color: #add8e6; color: black'
    if val == 'CIPT-ES': return 'background-color: #90ee90; color: black'
    return 'background-color: white; color: black'

st.write("### Painel de Ocupação em Tempo Real")
st.dataframe(df_view.style.map(color_status, subset=['Ocupação']), height=750, use_container_width=True)

if st.button("🔄 Sincronizar/Atualizar"):
    st.session_state.status_policiamento = carregar_dados_do_arquivo()
    st.rerun()
