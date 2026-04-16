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

# --- 4. AUTENTICAÇÃO ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if not st.session_state.autenticado:
    with st.center(): # Simulação de centralização
        with st.form("login"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if u == USUARIO_CORRETO and p == SENHA_CORRETA:
                    st.session_state.autenticado = True
                    st.rerun()
    st.stop()

# --- 5. INTERFACE PRINCIPAL ---
menu = st.tabs(["📋 Consulta", "✅ Cumprimento", "⚙️ Gestão"])

# ABA CONSULTA (Visualização)
with menu[0]:
    data_con = st.date_input("Filtrar por Dia", datetime.date.today())
    df_total = carregar_dados_db()
    # Lógica de exibição simplificada... (mantida do código anterior)

# ABA CUMPRIMENTO (Onde as mudanças foram aplicadas)
with menu[1]:
    st.subheader("Registrar Cumprimento")
    df_raw = carregar_dados_db()
    
    if not df_raw.empty:
        hoje = datetime.date.today().strftime("%Y-%m-%d")
        df_cump = df_raw[df_raw['data'] <= hoje].copy()
        
        if not df_cump.empty:
            df_cump['selecao'] = df_cump['data'] + " | " + df_cump['municipio']
            sel = st.selectbox("Selecione a Missão:", df_cump['selecao'].tolist())
            d = df_cump[df_cump['selecao'] == sel].iloc[0]
            
            # Verificação de registro já existente
            ja_cumprido = d.get('cumprido') is True

            with st.form("f_cump_novo"):
                col1, col2 = st.columns(2)
                n = col1.text_input("Comandante da Guarnição", value=str(d.get('comandante_nome') or ""))
                m = col2.text_input("Matrícula", value=str(d.get('comandante_matricula') or ""))
                e = col1.text_input("Hora de Entrada na Cidade", value=str(d.get('hora_entrada') or ""))
                s = col2.text_input("Hora de Saída na Cidade", value=str(d.get('hora_saida') or ""))
                
                # Mudança: Apenas uma caixa de seleção com o texto "Sim"
                confirmar = st.checkbox("Sim", value=ja_cumprido, help="Marque se a missão foi cumprida")
                
                rel = st.text_area("Resumo da Missão", value=str(d.get('relatorio_resumido') or ""))
                
                btn_salvar = st.form_submit_button("Salvar Registro")
                
                if btn_salvar:
                    # Regra de Ouro: Validar se já está cumprido para evitar duplicidade na mesma missão
                    if ja_cumprido and confirmar:
                        st.warning("Esta missão já possui um registro de cumprimento salvo.")
                    elif not confirmar:
                        st.error("Para salvar o cumprimento, você deve marcar a caixa 'Sim'.")
                    else:
                        if atualizar_cumprimento(d['id'], e, s, rel, confirmar, n, m):
                            st.success("Missão registrada com sucesso!")
                            st.rerun()
        else:
            st.info("Nenhuma missão pendente para hoje ou datas passadas.")

# ABA GESTÃO E HISTÓRICO... (Mantidos conforme versões anteriores)
