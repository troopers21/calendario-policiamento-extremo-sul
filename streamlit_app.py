import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
import time
import extra_streamlit_components as stx

# --- 1. CONFIGURAÇÕES E CONEXÃO ---

CHAVE_GESTAO = "comando2026"
MATRICULA_ADMIN = "30455232"
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="SISPOSIÇÃO - PMBA - CPR-ES", layout="wide", page_icon="🛡️")

# Inicia o gerenciador de Cookies
cookie_manager = stx.CookieManager(key="gerenciador_cookies")

# --- CORREÇÃO DEFINITIVA DO F5 ---
if "esperou_cookies" not in st.session_state:
    time.sleep(0.3)
    st.session_state.esperou_cookies = True
    st.rerun()

# --- LÓGICA DE SINCRONIZAÇÃO SEGURA DO NAVEGADOR ---
cookies_gerais = cookie_manager.get_all()
if cookies_gerais is None:
    st.markdown("🔄 Sincronizando sessão segura... Aguarde.", unsafe_allow_html=True)
    st.stop()

if "temp_access_token" in st.session_state:
    validade = datetime.datetime.now() + datetime.timedelta(days=30)
    cookie_manager.set("sb_access_token", st.session_state.temp_access_token, expires_at=validade, key="set_acc")
    cookie_manager.set("sb_refresh_token", st.session_state.temp_refresh_token, expires_at=validade, key="set_ref")
    del st.session_state["temp_access_token"]
    del st.session_state["temp_refresh_token"]

if "temp_logout" in st.session_state:
    try: cookie_manager.delete("sb_access_token", key="del_acc")
    except: pass
    try: cookie_manager.delete("sb_refresh_token", key="del_ref")
    except: pass
    supabase.auth.sign_out()
    del st.session_state["temp_logout"]

# --- 2. CABEÇALHO ---

# 1. Injeta CSS para remover o espaço vazio do topo da página
st.markdown("""
    <style>
        .block-container {
            padding-top: 2.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Renderiza a Logo Centralizada e Menor
col_logo1, col_logo2, col_logo3 = st.columns([1.5, 1.0, 1.5])
with col_logo2:
    try: 
        st.image("brasoes_cpr_especializadas.png", use_container_width=True)
    except: 
        pass

# 3. Títulos Centralizados com Espaçamento Reduzido
st.markdown("""
    <div style="text-align: center; font-weight: bold; font-size: 120%; line-height: 1.1; margin-top: 10px; margin-bottom: 30px;">
        CPR-ES<br>
        🛡️ SISPOSIÇÃO<br>
        <span style="font-size: 85%; font-weight: normal;">Sistema de Policiamento Sem Sobreposição</span>
    </div>
""", unsafe_allow_html=True)

# --- 3. LÓGICA DE AUTENTICAÇÃO ---

if "user_session" not in st.session_state:
    st.session_state.user_session = None

# Tenta carregar a sessão ativa da memória primeiro
try:
    session_res = supabase.auth.get_session()
    if session_res and session_res.session:
        st.session_state.user_session = session_res.user
except: pass

# Se a memória estiver vazia (F5), puxamos dos cookies já sincronizados
if st.session_state.user_session is None:
    access_token = cookie_manager.get(cookie="sb_access_token")
    refresh_token = cookie_manager.get(cookie="sb_refresh_token")
    if access_token and refresh_token:
        try:
            res_cookie = supabase.auth.set_session(access_token, refresh_token)
            if res_cookie.user:
                st.session_state.user_session = res_cookie.user
        except: pass

# TELA DE LOGIN / CADASTRO
if st.session_state.user_session is None:
    aba_auth = st.tabs(["🔐 Entrar", "📝 Cadastrar-se"])
    
    with aba_auth[0]:
        with st.form("login_form"):
            email_in = st.text_input("Email")
            senha_in = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_in, "password": senha_in})
                    if res.user:
                        if res.user.email_confirmed_at is None:
                            st.warning("⚠️ Confirme seu e-mail para acessar.")
                        else:
                            st.session_state.user_session = res.user
                            st.session_state.temp_access_token = res.session.access_token
                            st.session_state.temp_refresh_token = res.session.refresh_token
                            st.rerun()
                except Exception as e: st.error(f"Erro no login: {e}")

    with aba_auth[1]:
        with st.form("register_form"):
            lista_p = ["Cel PM", "Ten Cel PM", "Maj PM", "Cap PM", "Ten PM", "Asp PM", "Subten PM", "Sgt PM", "Cb PM", "Sd PM"]
            # Lista incluindo o CPR-ES para cadastro de usuários
            lista_u = ["CPR-ES", "Operação Pegasus", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"]
            c_r1, c_r2 = st.columns(2)
            posto_grad = c_r1.selectbox("Posto/Graduação", lista_p)
            nome_reg = c_r1.text_input("Nome Completo")
            unidade_reg = c_r2.selectbox("Unidade", lista_u)
            mat_reg = c_r2.text_input("Matrícula")
            st.divider()
            e_reg, p_reg = st.text_input("E-mail"), st.text_input("Senha", type="password")
            
            if st.form_submit_button("Finalizar Cadastro"):
                try:
                    if posto_grad in ["Subten PM", "Sgt PM", "Cb PM", "Sd PM"]:
                        perms_iniciais = ["✅ Cumprimento"]
                    else:
                        perms_iniciais = ["📋 Consulta de Escala", "🎖️ Comandante", "✅ Cumprimento", "📊 Estatísticas"]
                    
                    supabase.auth.sign_up({"email": e_reg, "password": p_reg, "options": {"data": {"posto_grad": posto_grad, "nome_completo": nome_reg, "matricula": mat_reg, "unidade": unidade_reg}}})
                    supabase.table("permissoes_usuarios").upsert({"matricula": mat_reg, "abas_permitidas": perms_iniciais}).execute()
                    st.success("✅ Cadastro solicitado! Verifique seu e-mail.")
                except Exception as e: st.error(f"Erro: {e}")
    st.stop()


# --- 4. VARIÁVEIS DO USUÁRIO ---

user_email = st.session_state.user_session.email
user_meta = st.session_state.user_session.user_metadata
p_g_user = user_meta.get("posto_grad", "")
nome_user = user_meta.get("nome_completo", "Usuário")
mat_user = user_meta.get("matricula", "")
unidade_user = user_meta.get("unidade", "")

def buscar_permissoes(matricula):
    try:
        res = supabase.table("permissoes_usuarios").select("abas_permitidas").eq("matricula", matricula).execute()
        if res.data: return res.data[0]["abas_permitidas"]
    except: pass
    return ["✅ Cumprimento"]

abas_liberadas = buscar_permissoes(mat_user)
eh_admin = mat_user == MATRICULA_ADMIN

def carregar_dados_db():
    try:
        res = supabase.table("escala_operacional").select("*").execute()
        if res.data: return pd.DataFrame(res.data)
    except: pass
    return pd.DataFrame(columns=["id", "data", "municipio", "unidade", "hora_entrada", "hora_saida", "missao", "comandante_nome", "comandante_matricula", "viatura", "relatorio_resumido", "cumprido", "criado_por", "editado_por", "ultima_edicao"])

def carregar_dados_bases():
    try:
        res = supabase.table("bases_integradas").select("*").execute()
        if res.data: return pd.DataFrame(res.data)
    except: pass
    return pd.DataFrame(columns=["id", "base_nome", "unidade", "data_inicio", "data_fim", "criado_por"])

lista_horas = [f"{h:02d}:00" for h in range(24)]
territorios = {
    "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
    "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
}


# --- 5. INTERFACE SIDEBAR ---

with st.sidebar:
    st.markdown(f"### 👮 {p_g_user} {nome_user}\n{unidade_user} | {mat_user}")
    if st.button("Sair"):
        st.session_state.temp_logout = True
        st.session_state.user_session = None
        st.rerun()


# --- 6. ABAS ---

abas_possiveis = ["📋 Consulta de Escala", "🎖️ Comandante", "✅ Cumprimento", "📊 Estatísticas", "⚙️ Gestão", "🏠 Gestão Base Integrada"]
if eh_admin: abas_possiveis.append("🔑 Admin")

titulos_finais = [a for a in abas_possiveis if a in abas_liberadas]
if not titulos_finais: titulos_finais = ["✅ Cumprimento"]

tabs = st.tabs(titulos_finais)

for i, titulo in enumerate(titulos_finais):
    
    with tabs[i]:
        
        if titulo == "📋 Consulta de Escala":
            dt_c = st.date_input("Data da Escala:", datetime.date.today(), key="dt_cons")
            df = carregar_dados_db()
            if not df.empty:
                for r, cidades in territorios.items():
                    df_r = df[(df['data'] == str(dt_c)) & (df['municipio'].isin(cidades))]
                    if not df_r.empty:
                        st.markdown(f"#### 📍 {r}")
                        df_r['Estado'] = df_r['cumprido'].map({True: "✅ OK", False: "⚠️ Aberto"})
                        st.dataframe(df_r[['municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Estado']], use_container_width=True, hide_index=True)
                        
        elif titulo == "🎖️ Comandante":
            df_all = carregar_dados_db().sort_values(by="data", ascending=False)
            if not df_all.empty:
                for r, cidades in territorios.items():
                    df_r = df_all[df_all['municipio'].isin(cidades)]
                    if not df_r.empty:
                        with st.expander(f"📍 {r}"):
                            df_r['Situação'] = df_r['cumprido'].map({True: "✅ OK", False: "⚠️ Aberto"})
                            # Assegura que a coluna viatura exista e seja mostrada
                            colunas_para_exibir = ['data', 'municipio', 'unidade', 'viatura', 'hora_entrada', 'hora_saida', 'Situação', 'missao']
                            colunas_finais = [col for col in colunas_para_exibir if col in df_r.columns]
                            st.dataframe(df_r[colunas_finais], use_container_width=True, hide_index=True)
                            
        elif titulo == "✅ Cumprimento":
            df_c = carregar_dados_db().sort_values(by="data", ascending=False)
            if not df_c.empty:
                df_c['sel'] = df_c['data'] + " | " + df_c['municipio'] + " | " + df_c['unidade']
                
                # 1. Cria a lista com uma opção em branco no topo
                opcoes_missao = [""] + df_c['sel'].tolist()
                
                # 2. Renderiza a caixa de seleção padrão no índice 0 (em branco)
                it = st.selectbox("Selecione a Missão:", opcoes_missao, index=0, key="sel_cump")
                
                # 3. Só carrega os dados e o formulário se uma missão foi escolhida
                if it != "":
                    d = df_c[df_c['sel'] == it].iloc[0]
                    with st.form("f_cump_completo"):
                        col_c1, col_c2 = st.columns(2)
                        n_cmt = col_c1.text_input("Comandante da Guarnição", d.get('comandante_nome') or f"{p_g_user} {nome_user}")
                        m_cmt = col_c2.text_input("Matrícula do Cmt Gu", d.get('comandante_matricula') or mat_user)
                        v_pref = col_c1.text_input("Viatura (Prefixo)", d.get('viatura', ''))
                        
                        c_h1, c_h2 = st.columns(2)
                        h_e_real = c_h1.selectbox("Horário de Início Real", lista_horas, index=lista_horas.index(d['hora_entrada']) if d['hora_entrada'] in lista_horas else 0)
                        h_s_real = c_h2.selectbox("Horário de Término Real", lista_horas, index=lista_horas.index(d['hora_saida']) if d['hora_saida'] in lista_horas else 0)
                        
                        rel_det = st.text_area("Relatório Resumido da Missão", d.get('relatorio_resumido', ''))
                        conf_c = st.checkbox("Missão Cumprida Totalmente", value=bool(d.get('cumprido')))
                        
                        if st.form_submit_button("Salvar Dados"):
                            try:
                                supabase.table("escala_operacional").update({
                                    "comandante_nome": n_cmt, "comandante_matricula": m_cmt, "viatura": v_pref,
                                    "hora_entrada": h_e_real, "hora_saida": h_s_real, "relatorio_resumido": rel_det,
                                    "cumprido": conf_c, "ultima_edicao": datetime.datetime.now().isoformat(),
                                    "editado_por": f"{p_g_user} {nome_user}"
                                }).eq("id", d['id']).execute()
                                st.success("Salvo com sucesso!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao salvar: {e}")

        elif titulo == "📊 Estatísticas":
            df_e = carregar_dados_db()
            if not df_e.empty: st.bar_chart(df_e['municipio'].value_counts())

        elif titulo == "⚙️ Gestão":
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("📝 Agendar Missão")
                
                # A data inicia em branco (value=None)
                dt_g = st.date_input("Data da Missão", value=None)
                
                df_atual = carregar_dados_db()
                # Só busca e mostra as missões já agendadas se uma data for escolhida
                if dt_g is not None and not df_atual.empty:
                    df_dia = df_atual[df_atual['data'] == str(dt_g)]
                    if not df_dia.empty:
                        st.info("📌 Missões já agendadas para esta data:")
                        colunas_prev = ['data', 'unidade', 'municipio', 'hora_entrada', 'hora_saida']
                        st.dataframe(df_dia[[c for c in colunas_prev if c in df_dia.columns]], use_container_width=True, hide_index=True)

                with st.form("f_gest_nova", clear_on_submit=True):
                    # Adiciona opções em branco no topo das listas (sem CPR-ES)
                    lista_mun = [""] + sorted(territorios["Costa do Descobrimento"] + territorios["Costa das Baleias"])
                    lista_un = ["", "Operação Pegasus", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"]
                    
                    mu_g = st.selectbox("Município", lista_mun, index=0)
                    un_g = st.selectbox("Unidade Responsável", lista_un, index=0)
                    
                    c_f1, c_f2 = st.columns(2)
                    cmt_g = c_f1.text_input("Comandante da Guarnição")
                    vtr_g = c_f2.text_input("Prefixo da Viatura")
                    
                    h_e_prev = st.selectbox("Início Previsto", lista_horas)
                    h_s_prev = st.selectbox("Fim Previsto", lista_horas)
                    
                    # NOVAS CAIXAS DE SELEÇÃO: Revista e Escolta
                    c_chk1, c_chk2 = st.columns(2)
                    chk_revista = c_chk1.checkbox("1 - Revista em Presídio")
                    chk_escolta = c_chk2.checkbox("2 - Escolta")
                    
                    miss_obj = st.text_area("Objetivo da Missão")
                    
                    if st.form_submit_button("Agendar Missão"):
                        # Trava de segurança: impede agendamento se faltarem dados essenciais
                        if dt_g is None or mu_g == "" or un_g == "":
                            st.warning("⚠️ Atenção: Preencha a Data, o Município e a Unidade para agendar.")
                        else:
                            sobreposicao_detectada = False
                            
                            # Define as unidades que entram na regra restrita de sobreposição
                            unidades_com_sobreposicao = ["CIPE-MA", "CIPT-ES"]
                            
                            # A sobreposição será permitida se Revista ou Escolta estiverem marcadas
                            permite_sobreposicao = chk_revista or chk_escolta
                            
                            if not df_atual.empty and (un_g in unidades_com_sobreposicao) and not permite_sobreposicao:
                                # Filtra apenas se for no mesmo município
                                df_conflito = df_atual[(df_atual['data'] == str(dt_g)) & (df_atual['municipio'] == mu_g)]
                                if not df_conflito.empty:
                                    inicio_novo = int(h_e_prev.split(":")[0])
                                    fim_novo = int(h_s_prev.split(":")[0])
                                    if fim_novo <= inicio_novo: fim_novo += 24 
                                    
                                    for _, row in df_conflito.iterrows():
                                        try:
                                            inicio_existente = int(str(row['hora_entrada']).split(":")[0])
                                            fim_existente = int(str(row['hora_saida']).split(":")[0])
                                            if fim_existente <= inicio_existente: fim_existente += 24
                                            
                                            if (inicio_novo < fim_existente) and (fim_novo > inicio_existente):
                                                sobreposicao_detectada = True
                                                break
                                        except: pass
                                        
                            if sobreposicao_detectada:
                                st.error("⚠️ REGRA DE SOBREPOSIÇÃO: Já existe uma missão cadastrada que conflita com este mesmo município e horário.")
                            else:
                                try:
                                    supabase.table("escala_operacional").insert({
                                        "data": str(dt_g), "municipio": mu_g, "unidade": un_g,
                                        "comandante_nome": cmt_g, "viatura": vtr_g,
                                        "hora_entrada": h_e_prev, "hora_saida": h_s_prev, "missao": miss_obj,
                                        "criado_por": f"{p_g_user} {nome_user}" # Alterado para gravar o GH + Nome
                                    }).execute()
                                    st.success("Missão agendada com sucesso!")
                                    st.rerun()
                                except Exception as e: st.error(f"Falha no agendamento: {e}")

            with col_g2:
                st.subheader("🗑️ Excluir Registro")
                df_del = carregar_dados_db().sort_values(by='data', ascending=False)
                if not df_del.empty:
                    # Inclui a unidade na formatação
                    df_del['txt'] = df_del['data'] + " | " + df_del['municipio'] + " | " + df_del['unidade']
                    # Adiciona a string em branco na posição 0
                    opcoes_exclusao = [""] + df_del['txt'].tolist()
                    
                    it_del = st.selectbox("Selecione para excluir:", opcoes_exclusao, index=0, key="del_escala")
                    
                    if it_del != "":
                        reg_selecionado = df_del[df_del['txt'] == it_del].iloc[0]
                        st.info(f"""
**Detalhes da Missão:**
* **Horário:** {reg_selecionado['hora_entrada']} às {reg_selecionado['hora_saida']}
* **Objetivo:** {reg_selecionado.get('missao', 'Não preenchido')}
* **Status:** {'✅ Cumprida' if reg_selecionado.get('cumprido') else '⚠️ Aberta'}
* **Cadastrado Por:** {reg_selecionado.get('criado_por', 'Não identificado')}
                        """)
                        
                        if st.button("Remover Permanentemente"):
                            try:
                                id_d = reg_selecionado['id']
                                supabase.table("escala_operacional").delete().eq("id", id_d).execute()
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao excluir: {e}")

        elif titulo == "🏠 Gestão Base Integrada":
            st.header("🏠 Gestão Base Integrada")
            
            col_b1, col_b2 = st.columns([1, 2])
            
            with col_b1:
                st.subheader("📝 Agendar Base")
                
                # Elemento interativo fora do form
                dt_base = st.date_input("Selecione um dia da semana desejada")
                segunda_f = dt_base - datetime.timedelta(days=dt_base.weekday())
                domingo_f = segunda_f + datetime.timedelta(days=6)
                
                st.info(f"📆 Período: {segunda_f.strftime('%d/%m/%Y')} a {domingo_f.strftime('%d/%m/%Y')}")
                
                with st.form("form_base", clear_on_submit=True):
                    base_escolhida = st.selectbox("Selecione a Base", ["Base 1", "Base 2", "Base 3", "Base 4"])
                    unidade_base = st.selectbox("Unidade", ["Operação Pegasus", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"])
                    
                    if st.form_submit_button("Confirmar Ocupação"):
                        df_bases = carregar_dados_bases()
                        ocupado = False
                        
                        if not df_bases.empty:
                            conflito = df_bases[(df_bases['base_nome'] == base_escolhida) & (df_bases['data_inicio'] == str(segunda_f))]
                            if not conflito.empty:
                                ocupado = True
                                
                        if ocupado:
                            st.error(f"⚠️ A {base_escolhida} já está ocupada nesta semana! Escolha outra base ou semana.")
                        else:
                            try:
                                supabase.table("bases_integradas").insert({
                                    "base_nome": base_escolhida,
                                    "unidade": unidade_base,
                                    "data_inicio": str(segunda_f),
                                    "data_fim": str(domingo_f),
                                    "criado_por": f"{p_g_user} {nome_user}"
                                }).execute()
                                st.success("Base agendada com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao agendar: {e}")

                # Histórico Geral logo abaixo
                df_bases = carregar_dados_bases()
                if not df_bases.empty:
                    st.write("---")
                    st.markdown("**📌 Histórico de Bases Cadastradas**")
                    df_historico = df_bases[['base_nome', 'unidade', 'data_inicio', 'data_fim']].copy()
                    df_historico.columns = ['Base', 'Unidade Ocupante', 'Início', 'Fim']
                    df_historico = df_historico.sort_values(by="Início", ascending=False)
                    st.dataframe(df_historico, use_container_width=True, hide_index=True)

            with col_b2:
                st.subheader("📅 Previsão de Ocupação")
                dt_filtro = st.date_input("Ver a ocupação da semana referente ao dia:", datetime.date.today(), key="filtro_base")
                segunda_filtro = dt_filtro - datetime.timedelta(days=dt_filtro.weekday())
                domingo_filtro = segunda_filtro + datetime.timedelta(days=6)
                
                st.write(f"📆 Semana de: **{segunda_filtro.strftime('%d/%m/%Y')}** até **{domingo_filtro.strftime('%d/%m/%Y')}**")
                
                df_bases = carregar_dados_bases()
                if not df_bases.empty:
                    df_semana = df_bases[df_bases['data_inicio'] == str(segunda_filtro)]
                    
                    if not df_semana.empty:
                        df_semana = df_semana[['base_nome', 'unidade', 'data_inicio', 'data_fim']]
                        df_semana.columns = ['Base', 'Unidade Ocupante', 'Início', 'Fim']
                        df_semana = df_semana.sort_values(by="Base")
                        st.dataframe(df_semana, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhuma base está ocupada para esta semana.")
                else:
                    st.warning("Nenhuma base está ocupada para esta semana.")
                    
                # --- NOVO BLOCO: EXCLUSÃO DE BASE INTEGRADA ---
                st.write("---")
                st.subheader("🗑️ Excluir Registro de Base")
                df_del_base = carregar_dados_bases()
                
                if not df_del_base.empty:
                    df_del_base = df_del_base.sort_values(by='data_inicio', ascending=False)
                    
                    # Formata a string para a caixa de seleção para facilitar a identificação
                    df_del_base['txt'] = df_del_base['data_inicio'] + " a " + df_del_base['data_fim'] + " | " + df_del_base['base_nome'] + " | " + df_del_base['unidade']
                    opcoes_exclusao_base = [""] + df_del_base['txt'].tolist()
                    
                    it_del_base = st.selectbox("Selecione o agendamento para excluir:", opcoes_exclusao_base, index=0, key="del_base_sel")
                    
                    if it_del_base != "":
                        reg_selecionado_base = df_del_base[df_del_base['txt'] == it_del_base].iloc[0]
                        st.warning(f"""
**Confirma a exclusão deste agendamento?**
* **Base:** {reg_selecionado_base['base_nome']}
* **Unidade:** {reg_selecionado_base['unidade']}
* **Período:** {reg_selecionado_base['data_inicio']} até {reg_selecionado_base['data_fim']}
* **Cadastrado Por:** {reg_selecionado_base.get('criado_por', 'Não identificado')}
                        """)
                        
                        if st.button("Remover Agendamento Permanentemente", type="primary", key="btn_remover_base"):
                            try:
                                id_b = reg_selecionado_base['id']
                                supabase.table("bases_integradas").delete().eq("id", int(id_b)).execute()
                                st.success("Registro de base excluído com sucesso!")
                                st.rerun()
                            except Exception as e: 
                                st.error(f"Erro ao excluir o registro da base: {e}")

        elif titulo == "🔑 Admin" and eh_admin:
            st.subheader("Gestão de Acessos")
            try:
                res_u = supabase.table("lista_usuarios_admin").select("*").execute()
                if res_u.data:
                    for user in res_u.data:
                        with st.expander(f"👤 {user['nome_completo']} ({user['matricula']})"):
                            p_atual = buscar_permissoes(user['matricula'])
                            novas_p = st.multiselect("Abas Permitidas:", abas_possiveis, default=p_atual, key=f"p_{user['matricula']}")
                            
                            c_adm1, c_adm2 = st.columns(2)
                            
                            if c_adm1.button("Atualizar", key=f"b_{user['matricula']}"):
                                supabase.table("permissoes_usuarios").upsert({"matricula": user['matricula'], "abas_permitidas": novas_p}).execute()
                                st.success("Atualizado!")
                                
                            # NOVO BOTÃO DE EXCLUIR USUÁRIO
                            if c_adm2.button("🗑️ Excluir Usuário", key=f"del_{user['matricula']}", type="primary"):
                                try:
                                    supabase.table("permissoes_usuarios").delete().eq("matricula", user['matricula']).execute()
                                    st.success("Acesso do usuário excluído com sucesso! Atualize a página.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir usuário: {e}")
            except Exception as e: st.error(f"Erro ao carregar usuários: {e}")
