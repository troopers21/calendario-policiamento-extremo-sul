import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# Configuração da página
st.set_page_config(page_title="Calendário Operacional - PMBA", layout="wide")

st.title("📅 Calendário de Policiamento - Extremo Sul")
st.info("Planejamento Antecipado com Descrição de Missão")

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
DB_FILE = "escala_policiamento.csv"

def carregar_escala():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Município', 'Unidade', 'Missão'])

def salvar_escala(df):
    df.to_csv(DB_FILE, index=False)

# --- INTERFACE LATERAL (GESTOR) ---
st.sidebar.header("⚙️ Gestão da Escala")
senha = st.sidebar.text_input("Senha do Gestor", type="password")

if senha == "123":
    st.sidebar.subheader("Agendar Policiamento")
    data_agendada = st.sidebar.date_input("Data do Policiamento", date.today())
    unidade_agendada = st.sidebar.selectbox("Unidade:", ["CIPE-MA", "CIPT-ES"])
    cidades_agendadas = st.sidebar.multiselect("Selecionar Municípios:", municipios)
    
    # NOVO CAMPO: Descrição da Missão
    missao_texto = st.sidebar.text_area("Descrição da Missão:", placeholder="Ex: Patrulhamento Rural, Apoio à Delegacia, Operação Intensificação...")

    if st.sidebar.button("Salvar Escala"):
        if not cidades_agendadas:
            st.sidebar.error("Selecione pelo menos um município.")
        elif not missao_texto:
            st.sidebar.error("Descreva a missão antes de salvar.")
        else:
            df_escala = carregar_escala()
            data_str = data_agendada.strftime("%Y-%m-%d")
            
            novos_registros = []
            conflitos = []

            for cidade in cidades_agendadas:
                conflito = df_escala[(df_escala['Data'] == data_str) & (df_escala['Município'] == cidade)]
                
                if not conflito.empty:
                    unid_ocupante = conflito.iloc[0]['Unidade']
                    conflitos.append(f"{cidade} ({unid_ocupante})")
                else:
                    novos_registros.append({
                        'Data': data_str, 
                        'Município': cidade, 
                        'Unidade': unidade_agendada,
                        'Missão': missao_texto # Salva o texto da missão
                    })
            
            if conflitos:
                st.sidebar.error(f"Erro! Sobreposição em: {', '.join(conflitos)}")
            
            if novos_registros:
                df_escala = pd.concat([df_escala, pd.DataFrame(novos_registros)], ignore_index=True)
                salvar_escala(df_escala)
                st.sidebar.success("Escala e Missão salvas!")
                st.rerun()

    if st.sidebar.button("Limpar Escala do Dia"):
        df_escala = carregar_escala()
        data_str = data_agendada.strftime("%Y-%m-%d")
        df_escala = df_escala[df_escala['Data'] != data_str]
        salvar_escala(df_escala)
        st.sidebar.warning(f"Escala de {data_str} removida.")
        st.rerun()
else:
    st.sidebar.warning("Insira a senha para gerenciar.")

# --- VISUALIZAÇÃO ---
st.write("### 🔍 Consultar Planejamento")
data_consulta = st.date_input("Selecione o dia:", date.today())
data_consulta_str = data_consulta.strftime("%Y-%m-%d")

df_total = carregar_escala()
df_dia = df_total[df_total['Data'] == data_consulta_str]

# Tabela de exibição com a coluna de Missão
tabela_visual = pd.DataFrame([{"Município": m, "Ocupação": "Livre", "Missão": "-"} for m in municipios])

for index, row in df_dia.iterrows():
    tabela_visual.loc[tabela_visual['Município'] == row['Município'], 'Ocupação'] = row['Unidade']
    tabela_visual.loc[tabela_visual['Município'] == row['Município'], 'Missão'] = row['Missão']

def color_status(val):
    if val == 'CIPE-MA': return 'background-color: #add8e6; color: black'
    if val == 'CIPT-ES': return 'background-color: #90ee90; color: black'
    return 'background-color: white; color: black'

st.write(f"**Escala de {data_consulta.strftime('%d/%m/%Y')}**")
# Exibindo a tabela completa com a Missão
st.dataframe(
    tabela_visual.style.map(color_status, subset=['Ocupação']), 
    height=700, 
    use_container_width=True,
    hide_index=True
)

# Relatório detalhado
with st.expander("📊 Histórico e Detalhes das Missões"):
    if not df_total.empty:
        # Ordena por data mais recente
        st.dataframe(df_total.sort_values(by='Data', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.write("Nenhum registro encontrado.")
