import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
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

# --- LÓGICA DE SINCRONIZAÇÃO SEGURA DO NAVEGADOR (CORREÇÃO DO F5) ---
cookies_gerais = cookie_manager.get_all()
if cookies_gerais is None:
    # Se for None, o componente do frontend ainda não terminou de montar.
    # Paramos o código e exibimos o aviso até que ele se comunique com o Python (leva milissegundos).
    st.markdown("<div style='text-align: center; margin-top: 50px;'><h3>🔄 Sincronizando sessão segura... Aguarde.</h3></div>", unsafe_allow_html=True)
    st.stop()

# --- COMANDOS PENDENTES DE COOKIE ---
# Se o usuário acabou de logar, gravamos o cookie ANTES de processar o resto da página
if "temp_access_token" in st.session_state:
    validade = datetime.datetime.now() + datetime.timedelta(days=30)
    cookie_manager.set("sb_access_token", st.session_state.temp_access_token, expires_at=validade, key="set_acc")
    cookie_manager.set("sb_refresh_token", st.session_state.temp_refresh_token, expires_at=validade, key="set_ref")
    del st.session_state["temp_access_token"]
    del st.session_state["temp_refresh_token"]

# Se o usuário clicou em sair, apagamos o cookie com segurança
if "temp_logout" in st.session_state:
    try: cookie_manager.delete("sb_access_token", key="del_acc")
    except: pass
    try: cookie_manager.delete("sb_refresh_token", key="del_ref")
    except: pass
    supabase.auth.sign_out()
    del st.session_state["temp_logout"]

# --- 2. CABEÇALHO ---
col_logo1, col_logo2, col_logo3 = st.columns([0.5, 2.0, 0.5])
with col_logo2:
    try: st.image("logo_unidade.jpeg", use_container_width=True) 
    except: pass

st.markdown("<div style='text-align: center;'><h1>🛡️ SISPOSIÇÃO</h1><p>Sistema de Policiamento Sem Sobreposição — CPR-ES</p><hr></div>", unsafe_allow_html=True)

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
            email_in = st.text_input("E-mail") 
            senha_in = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_in, "password": senha_in})
                    if res.user:
                        if res.user.email_confirmed_at is None:
                            st.warning("⚠️ Confirme seu e-mail para acessar.")
                        else:
                            # Guarda a sessão e salva os tokens temporariamente para o sistema registrar na próxima passada
                            st.session_state.user_session = res.user
                            st.session_state.temp_access_token = res.session.access_token
                            st.session_state.temp_refresh_token = res.session.refresh_token
                            st.rerun()
                except Exception as e: st.error(f"Erro no login: {e}")

    with aba_auth[1]:
        with st.form("register_form"):
            lista_p = ["Cel PM", "Ten Cel PM", "Maj PM", "Cap PM", "Ten PM", "Asp PM", "Subten PM", "Sgt PM", "Cb PM", "Sd PM"]
            lista_u = ["CPR-ES", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"]
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
        if res.data:
            return pd.DataFrame(res.data)
    except: pass
    return pd.DataFrame(columns=["id", "data", "municipio", "unidade", "hora_entrada", "hora_saida", "missao", "comandante_nome", "comandante_matricula", "viatura", "relatorio_resumido", "cumprido", "criado_por", "editado_por", "ultima_edicao"])

lista_horas = [f"{h:02d}:00" for h in range(24)]
territorios = {
    "Costa do Descobrimento": ["Porto Seguro", "Eunápolis", "Santa Cruz Cabrália", "Belmonte", "Itapebi", "Itagimirim", "Guaratinga", "Itabela"],
    "Costa das Baleias": ["Teixeira de Freitas", "Itamaraju", "Jucuruçu", "Medeiros Neto", "Itanhém", "Lajedão", "Vereda", "Ibirapuã", "Alcobaça", "Prado", "Caravelas", "Mucuri", "Nova Viçosa"]
}

def carregar_dados_bases():
    try:
        res = supabase.table("bases_integradas").select("*").execute()
        if res.data:
            return pd.DataFrame(res.data)
    except: pass
    return pd.DataFrame(columns=["id", "base_nome", "unidade", "data_inicio", "data_fim", "criado_por"])

# --- 5. INTERFACE SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👮 {p_g_user} {nome_user}\n{unidade_user} | {mat_user}")
    if st.button("Sair"):
        # Aciona a flag de logout e desloga da memória. Os cookies serão apagados na próxima reiniciada natural da página.
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
            # --- SEÇÃO CONGELADA ---
            df_all = carregar_dados_db().sort_values(by="data", ascending=False)
            if not df_all.empty:
                for r, cidades in territorios.items():
                    df_r = df_all[df_all['municipio'].isin(cidades)]
                    if not df_r.empty:
                        with st.expander(f"📍 {r}"):
                            df_r['Situação'] = df_r['cumprido'].map({True: "✅ OK", False: "⚠️ Aberto"})
                            st.dataframe(df_r[['data', 'municipio', 'unidade', 'hora_entrada', 'hora_saida', 'Situação', 'missao']], use_container_width=True, hide_index=True)

        elif titulo == "✅ Cumprimento":
            df_c = carregar_dados_db().sort_values(by="data", ascending=False)
            if not df_c.empty:
                df_c['sel'] = df_c['data'] + " | " + df_c['municipio']
                it = st.selectbox("Selecione a Missão:", df_c['sel'].tolist(), key="sel_cump")
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
                                "editado_por": user_email
                            }).eq("id", d['id']).execute()
                            st.success("Salvo com sucesso!"); st.rerun()
                        except Exception as e: st.error(f"Erro ao salvar: {e}")

        elif titulo == "📊 Estatísticas":
            df_e = carregar_dados_db()
            if not df_e.empty: st.bar_chart(df_e['municipio'].value_counts())

        elif titulo == "⚙️ Gestão":
            col_g1, col_g2 = st.columns(2)
            with col_g1:
    st.subheader("📝 Agendar Missão")
    
    # Data fora do formulário para permitir a visualização reativa das missões existentes
    dt_g = st.date_input("Data da Missão", key="data_gestao_nova")
    
    # Busca e exibe missões já agendadas para evitar conflitos visuais
    df_atual = carregar_dados_db()
    if not df_atual.empty:
        df_dia = df_atual[df_atual['data'] == str(dt_g)]
        if not df_dia.empty:
            st.info("📌 Missões já agendadas para esta data:")
            st.dataframe(df_dia[['unidade', 'hora_entrada', 'hora_saida']], use_container_width=True, hide_index=True)

    with st.form("f_gest_nova", clear_on_submit=True):
        mu_g = st.selectbox("Município", sorted(territorios["Costa do Descobrimento"] + territorios["Costa das Baleias"]))
        un_g = st.selectbox("Unidade Responsável", ["Operação Pegasus", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"])
        
        # NOVOS CAMPOS: Nome do Comandante e Viatura lado a lado
        c_campos1, c_campos2 = st.columns(2)
        cmt_g = c_campos1.text_input("Comandante da Guarnição")
        vtr_g = c_campos2.text_input("Prefixo da Viatura")
        
        h_e_prev = st.selectbox("Início Previsto", lista_horas)
        h_s_prev = st.selectbox("Fim Previsto", lista_horas)
        miss_obj = st.text_area("Objetivo da Missão")
        
        if st.form_submit_button("Agendar Missão"):
            unidades_excecao = ["CIPPA/PS", "CIPRv-Ita", "Operação Pegasus"]
            permite_sobreposicao = un_g in unidades_excecao
            sobreposicao_detectada = False
            
            # Lógica de verificação de horários
            if not df_atual.empty and not permite_sobreposicao:
                df_conflito = df_atual[df_atual['data'] == str(dt_g)]
                # ... (sua lógica de cálculo de horas aqui) ...

            if sobreposicao_detectada:
                st.error("⚠️ REGRA DE SOBREPOSIÇÃO: Já existe uma missão neste horário.")
            else:
                try:
                    # INSERT atualizado com os novos campos para o Supabase
                    supabase.table("escala_operacional").insert({
                        "data": str(dt_g), 
                        "municipio": mu_g, 
                        "unidade": un_g,
                        "comandante_nome": cmt_g, # Novo campo
                        "viatura": vtr_g,         # Novo campo
                        "hora_entrada": h_e_prev, 
                        "hora_saida": h_s_prev, 
                        "missao": miss_obj,
                        "criado_por": user_email
                    }).execute()
                    st.success("Missão agendada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Falha no agendamento: {e}")

                # 3. Formulário com os campos restantes
                # --- Trecho para substituir dentro de 'elif titulo == "⚙️ Gestão":' -> 'with col_g1:' ---

with st.form("f_gest_nova", clear_on_submit=True):
    mu_g = st.selectbox("Município", sorted(territorios["Costa do Descobrimento"] + territorios["Costa das Baleias"]))
    un_g = st.selectbox("Unidade Responsável", ["Operação Pegasus", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"])
    
    # NOVOS CAMPOS SOLICITADOS
    col_nova1, col_nova2 = st.columns(2)
    cmt_g = col_nova1.text_input("Comandante da Guarnição")
    vtr_g = col_nova2.text_input("Prefixo da Viatura")
    
    h_e_prev = st.selectbox("Início Previsto", lista_horas)
    h_s_prev = st.selectbox("Fim Previsto", lista_horas)
    miss_obj = st.text_area("Objetivo da Missão")
    
    if st.form_submit_button("Agendar Missão"):
        sobreposicao_detectada = False
        unidades_excecao = ["CIPPA/PS", "CIPRv-Ita", "Operação Pegasus"]
        permite_sobreposicao = un_g in unidades_excecao
        
        # --- LÓGICA DE SOBREPOSIÇÃO ---
        if not df_atual.empty and not permite_sobreposicao:
            df_dia_conflito = df_atual[df_atual['data'] == str(dt_g)]
            if not df_dia_conflito.empty:
                inicio_novo = int(h_e_prev.split(":")[0])
                fim_novo = int(h_s_prev.split(":")[0])
                if fim_novo <= inicio_novo: fim_novo += 24
                
                for _, row in df_dia_conflito.iterrows():
                    try:
                        inicio_existente = int(str(row['hora_entrada']).split(":")[0])
                        fim_existente = int(str(row['hora_saida']).split(":")[0])
                        if fim_existente <= inicio_existente: fim_existente += 24
                        
                        if (inicio_novo < fim_existente) and (fim_novo > inicio_existente):
                            sobreposicao_detectada = True
                            break
                    except:
                        pass

        if sobreposicao_detectada:
            st.error("⚠️ REGRA DE SOBREPOSIÇÃO: Já existe uma missão que conflita com este horário.")
        else:
            try:
                # ADICIONADO cmt_g e vtr_g NO INSERT ABAIXO
                supabase.table("escala_operacional").insert({
                    "data": str(dt_g), 
                    "municipio": mu_g, 
                    "unidade": un_g,
                    "comandante_nome": cmt_g,
                    "viatura": vtr_g,
                    "hora_entrada": h_e_prev, 
                    "hora_saida": h_s_prev, 
                    "missao": miss_obj,
                    "criado_por": user_email
                }).execute()
                st.success("Missão agendada com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Falha no agendamento: {e}")

            with col_g2:
                st.subheader("🗑️ Excluir Registro")
                df_del = carregar_dados_db().sort_values(by='data', ascending=False)
                if not df_del.empty:
                    df_del['txt'] = df_del['data'] + " | " + df_del['municipio'] + " | " + df_del['unidade']
                    
                    # 1. Cria a lista de opções adicionando um item em branco no início
                    opcoes_exclusao = [""] + df_del['txt'].tolist()
                    
                    # 2. Passa a nova lista e define o index=0 (que é o item em branco) como padrão
                    it_del = st.selectbox("Selecione para excluir:", opcoes_exclusao, index=0, key="del_escala")
                    
                    # 3. Só exibe os dados e o botão se o item selecionado não for o espaço em branco
                    if it_del != "":
                        reg_selecionado = df_del[df_del['txt'] == it_del].iloc[0]
                        
                        st.info(f"""
                        **Detalhes da Missão:**
                        * **Horário Previsto:** {reg_selecionado['hora_entrada']} às {reg_selecionado['hora_saida']}
                        * **Objetivo:** {reg_selecionado.get('missao', 'Não preenchido')}
                        * **Status:** {'✅ Cumprida' if reg_selecionado.get('cumprido') else '⚠️ Aberta'}
                        """)

                        if st.button("Remover Permanentemente"):
                            try:
                                id_d = df_del[df_del['txt'] == it_del]['id'].values[0]
                                supabase.table("escala_operacional").delete().eq("id", id_d).execute()
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao excluir: {e}")

        # --- ABA ADMIN ADICIONADA DE VOLTA AQUI ---
        elif titulo == "🔑 Admin" and eh_admin:
            st.subheader("Gestão de Acessos")
            try:
                res_u = supabase.table("lista_usuarios_admin").select("*").execute()
                if res_u.data:
                    for user in res_u.data:
                        with st.expander(f"👤 {user['nome_completo']} ({user['matricula']})"):
                            p_atual = buscar_permissoes(user['matricula'])
                            novas_p = st.multiselect("Abas Permitidas:", abas_possiveis, default=p_atual, key=f"p_{user['matricula']}")
                            if st.button("Atualizar", key=f"b_{user['matricula']}"):
                                supabase.table("permissoes_usuarios").upsert({"matricula": user['matricula'], "abas_permitidas": novas_p}).execute()
                                st.success("Atualizado!")
            except Exception as e: st.error(f"Erro ao carregar usuários: {e}")

        # --- ABA GESTÃO BASES INTEGRADAS ---
        elif titulo == "🏠 Gestão Base Integrada":
            st.header("🏠 Gestão Base Integrada")
            
            col_b1, col_b2 = st.columns([1, 2])
            
            with col_b1:
                st.subheader("📝 Agendar Base")
                
                # Calendário reativo (fora do form)
                dt_base = st.date_input("Selecione um dia da semana desejada")
                segunda_f = dt_base - datetime.timedelta(days=dt_base.weekday())
                domingo_f = segunda_f + datetime.timedelta(days=6)
                
                st.info(f"**Período:** {segunda_f.strftime('%d/%m/%Y')} a {domingo_f.strftime('%d/%m/%Y')}")

                # Formulário de Agendamento
                with st.form("form_base", clear_on_submit=True):
                    base_escolhida = st.selectbox("Selecione a Base", ["Base 1", "Base 2", "Base 3", "Base 4"])
                    unidade_base = st.selectbox("Unidade", ["Operação Pegasus", "CIPE-MA", "CIPT-ES", "CIPPA/PS", "CIPRv-Ita"])
                    
                    if st.form_submit_button("Confirmar Ocupação"):
                        df_bases = carregar_dados_bases()
                        ocupado = False
                        
                        if not df_bases.empty:
                            # Regra: Verifica se já tem alguma unidade nesta exata base e nesta exata semana
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
                                    "criado_por": user_email
                                }).execute()
                                st.success("Base agendada com sucesso!")
                                st.rerun() # Recarrega a tela instantaneamente
                            except Exception as e:
                                st.error(f"Erro ao agendar: {e}")
                
                # --- NOVA SESSÃO: EXIBIR TODAS AS BASES CADASTRADAS (SEM FILTRO) ---
                st.write("**📌 Todas as bases já cadastradas no sistema:**")
                df_todas_bases = carregar_dados_bases()
                
                if not df_todas_bases.empty:
                    # Aqui removemos o filtro da "semana selecionada" para exibir o histórico completo
                    df_exibicao = df_todas_bases[['base_nome', 'unidade', 'data_inicio', 'data_fim']]
                    
                    # Renomeando as 4 colunas conforme você solicitou
                    df_exibicao.columns = ['Base', 'Unidade Ocupante', 'Início', 'Fim']
                    
                    # Ordena para que os agendamentos mais recentes apareçam primeiro
                    df_exibicao = df_exibicao.sort_values(by=["Início", "Base"], ascending=[False, True])
                    
                    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
                else:
                    st.caption("Nenhuma base confirmada no sistema ainda.")

            with col_b2:
                st.subheader("📅 Previsão de Ocupação")
                dt_filtro = st.date_input("Ver a ocupação da semana referente ao dia:", datetime.date.today(), key="filtro_base")
                segunda_filtro = dt_filtro - datetime.timedelta(days=dt_filtro.weekday())
                domingo_filtro = segunda_filtro + datetime.timedelta(days=6)
                
                st.write(f"**Semana de:** {segunda_filtro.strftime('%d/%m/%Y')} até {domingo_filtro.strftime('%d/%m/%Y')}")
                
                df_bases = carregar_dados_bases()
                if not df_bases.empty:
                    df_semana = df_bases[df_bases['data_inicio'] == str(segunda_filtro)]
                    
                    if not df_semana.empty:
                        # Formata a tabela para ficar bonita na visualização
                        df_semana = df_semana[['base_nome', 'unidade', 'data_inicio', 'data_fim']]
                        df_semana.columns = ['Base', 'Unidade Ocupante', 'Início', 'Fim']
                        df_semana = df_semana.sort_values(by="Base")
                        st.dataframe(df_semana, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhuma base está ocupada para esta semana.")
                else:
                    st.warning("Nenhuma base está ocupada para esta semana.")
