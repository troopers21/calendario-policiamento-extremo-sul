import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# Configuração da página
st.set_page_config(page_title="Calendário Operacional - PMBA", layout="wide")

st.title("📅 Calendário de Policiamento - Extremo Sul")
st.info("Planejamento Antecipado e Prevenção de Sobreposição")

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

# --- LÓGICA DE PERSISTÊNCIA (BANCO DE DADOS EM CALENDÁRIO) ---
DB_FILE = "escala_policiamento.csv"

def carregar_escala():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Município', 'Unidade'])

def salvar_escala(df):
    df.to_csv(DB_FILE, index=False)

# --- INTERFACE LATERAL (CADASTRO PELO CHEFE) ---
st.sidebar.header("⚙️ Gestão da Escala")
senha = st.sidebar.text_input("Senha do Gestor", type="password")

# Apenas quem tem a senha (ex: "pmba123") pode cadastrar
if senha == "123": # Altere sua senha aqui
    st.sidebar.subheader("Agendar Policiamento")
    data_agendada = st.sidebar.date_input("Data do Policiamento", date.today())
    unidade_agendada = st.sidebar.selectbox("Unidade:", ["CIPE-MA", "CIPT-ES"])
    cidades_agendadas = st.sidebar.multiselect("Selecionar Municípios:", municipios)

    if st.sidebar.button("Salvar Escala"):
        df_escala = carregar_escala()
        data_str = data_agendada.strftime("%Y-%m-%d")
        
        novos_registros = []
        conflitos = []

        for cidade in cidades_agendadas:
            # Verifica se já existe ALGUÉM nessa cidade nessa data
            conflito = df_escala[(df_escala['Data'] == data_str) & (df_escala['Município'] == cidade)]
            
            if not conflito.empty:
                unid_ocupante = conflito.iloc[0]['Unidade']
                conflitos.append(f"{cidade} ({unid_ocupante})")
            else:
                novos_registros.append({'Data': data_str, 'Município': cidade, 'Unidade': unidade_agendada})
        
        if conflitos:
            st.sidebar.error(f"Erro! Sobreposição em: {', '.join(conflitos)}")
        
        if novos_registros:
            df_escala = pd.concat([df_escala, pd.DataFrame(novos_registros)], ignore_index=True)
            salvar_escala(df_escala)
            st.sidebar.success("Escala atualizada com sucesso!")
            st.rerun()

    if st.sidebar.button("Limpar Escala do Dia"):
        df_escala = carregar_escala()
        data_str = data_agendada.strftime("%Y-%m-%d")
        df_escala = df_escala[df_escala['Data'] != data_str]
        salvar_escala(df_escala)
        st.sidebar.warning(f"Escala de {data_str} removida.")
        st.rerun()
else:
    st.sidebar.warning("Insira a senha para cadastrar escalas.")

# --- VISUALIZAÇÃO (PARA TODOS AS UNIDADES) ---
st.write("### 🔍 Consultar Planejamento")
data_consulta = st.date_input("Selecione o dia para verificar o policiamento:", date.today())
data_consulta_str = data_consulta.strftime("%Y-%m-%d")

df_total = carregar_escala()
df_dia = df_total[df_total['Data'] == data_consulta_str]

# Criar a tabela de visualização para o dia selecionado
tabela_visual = pd.DataFrame([{"Município": m, "Ocupação": "Livre"} for m in municipios])

for index, row in df_dia.iterrows():
    tabela_visual.loc[tabela_visual['Município'] == row['Município'], 'Ocupação'] = row['Unidade']

def color_status(val):
    if val == 'CIPE-MA': return 'background-color: #add8e6; color: black'
    if val == 'CIPT-ES': return 'background-color: #90ee90; color: black'
    return 'background-color: white; color: black'

st.write(f"**Escala para o dia: {data_consulta.strftime('%d/%m/%Y')}**")
st.dataframe(tabela_visual.style.map(color_status, subset=['Ocupação']), height=700, use_container_width=True)

# --- HISTÓRICO / RELATÓRIO ---
with st.expander("📊 Ver Relatório Completo (Todos os Dias)"):
    if not df_total.empty:
        st.dataframe(df_total.sort_values(by='Data', ascending=False), use_container_width=True)
    else:
        st.write("Nenhum dado agendado ainda.")
