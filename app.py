"""
Aplicação Streamlit para visualização de dados populacionais do IBGE
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.data_extractor import PopulacaoDataExtractor
from src.utils import get_uf_list, formatar_populacao, get_top_municipios, get_summary_stats
import time

# Configuração da página
st.set_page_config(
    page_title="População dos Municípios Brasileiros",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("📊 Estimativas Populacionais dos Municípios Brasileiros")
st.markdown("Dados do IBGE - Tabela SIDRA 6579")

# Inicializa o extrator
@st.cache_resource
def init_extractor():
    return PopulacaoDataExtractor()

extractor = init_extractor()

# Sidebar para controles
with st.sidebar:
    st.header("⚙️ Controles")
    
    # Seleção do ano
    anos_disponiveis = ['2024', '2023', '2022', '2021', '2020']
    ano_selecionado = st.selectbox(
        "Selecione o ano:",
        anos_disponiveis,
        index=0
    )
    
    # Botão para carregar dados
    if st.button("🔄 Carregar Dados", type="primary", use_container_width=True):
        with st.spinner("Carregando dados do IBGE..."):
            try:
                df = extractor.extrair_populacao_municipios(ano=ano_selecionado)
                st.session_state['dados_populacao'] = df
                st.session_state['ultimo_ano'] = ano_selecionado
                st.success(f"✅ Dados de {ano_selecionado} carregados com sucesso!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao carregar dados: {str(e)}")
    
    # Tentar carregar dados do cache se existirem
    if 'dados_populacao' not in st.session_state:
        cache_file = f"populacao_municipios_{ano_selecionado}.csv"
        df_cache = extractor.carregar_dados_cache(cache_file)
        if df_cache is not None:
            st.session_state['dados_populacao'] = df_cache
            st.session_state['ultimo_ano'] = ano_selecionado
            st.info(f"📁 Dados de {ano_selecionado} carregados do cache")
        else:
            st.info("ℹ️ Clique em 'Carregar Dados' para iniciar")
    
    # Filtros (apenas se dados carregados)
    if 'dados_populacao' in st.session_state:
        st.markdown("---")
        st.header("🔍 Filtros")
        
        # Filtro por UF
        ufs = get_uf_list()
        uf_selecionada = st.selectbox(
            "Filtrar por UF:",
            ['Todos'] + list(ufs.values())
        )
        
        # Filtro por faixa populacional
        df_filtrado = st.session_state['dados_populacao']
        if not df_filtrado.empty:
            min_pop = int(df_filtrado['populacao'].min())
            max_pop = int(df_filtrado['populacao'].max())
            
            faixa_populacao = st.slider(
                "Faixa populacional:",
                min_pop, max_pop,
                (min_pop, max_pop)
            )

# Área principal
if 'dados_populacao' in st.session_state:
    df = st.session_state['dados_populacao'].copy()
    
    # Aplica filtros
    if uf_selecionada != 'Todos':
        uf_codigo = [k for k, v in ufs.items() if v == uf_selecionada][0]
        df = df[df['id_municipio'].astype(str).str.startswith(uf_codigo)]
    
    df = df[(df['populacao'] >= faixa_populacao[0]) & 
            (df['populacao'] <= faixa_populacao[1])]
    
    # Estatísticas gerais
    st.header("📈 Estatísticas Gerais")
    stats = get_summary_stats(df)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏙️ Total de Municípios", formatar_populacao(stats['total_municipios']))
    with col2:
        st.metric("👥 População Total", formatar_populacao(stats['populacao_total']))
    with col3:
        st.metric("⭐ Município mais populoso", stats['municipio_mais_populoso'][:20])
    with col4:
        st.metric("📉 Município menos populoso", stats['municipio_menos_populoso'][:20])
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top 10 Municípios Mais Populosos")
        top_municipios = get_top_municipios(df, 10)
        fig1 = px.bar(
            top_municipios, 
            x='municipio', 
            y='populacao',
            title=f"Municípios mais populosos - {ano_selecionado}",
            labels={'populacao': 'População', 'municipio': 'Município'},
            color='populacao',
            color_continuous_scale='Viridis'
        )
        fig1.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("📊 Distribuição Populacional")
        # Criando bins para distribuição
        df['faixa_populacional'] = pd.cut(
            df['populacao'], 
            bins=10,
            labels=[f'{int(b.left):,}' for b in pd.cut(df['populacao'], bins=10).cat.categories]
        )
        distrib = df['faixa_populacional'].value_counts().sort_index()
        fig2 = px.bar(
            x=distrib.index, 
            y=distrib.values,
            title="Distribuição dos municípios por faixa populacional",
            labels={'x': 'Faixa Populacional', 'y': 'Número de Municípios'}
        )
        fig2.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Tabela de dados
    st.subheader("📋 Dados Detalhados")
    
    # Opção de mostrar todos ou apenas top N
    show_option = st.radio(
        "Exibir:",
        ["Todos os municípios", "Top 50", "Top 100"],
        horizontal=True
    )
    
    if show_option == "Top 50":
        df_display = df.nlargest(50, 'populacao')
    elif show_option == "Top 100":
        df_display = df.nlargest(100, 'populacao')
    else:
        df_display = df
    
    # Formata população para exibição
    df_display['populacao_formatada'] = df_display['populacao'].apply(formatar_populacao)
    df_exibicao = df_display[['municipio', 'populacao_formatada']]
    df_exibicao.columns = ['Município', 'População']
    
    st.dataframe(
        df_exibicao,
        use_container_width=True,
        height=400,
        column_config={
            "Município": st.column_config.TextColumn("Município", width="large"),
            "População": st.column_config.TextColumn("População", width="medium")
        }
    )
    
    # Botão para download
    csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button(
        label="📥 Baixar dados completos (CSV)",
        data=csv,
        file_name=f"populacao_municipios_{ano_selecionado}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
else:
    # Estado inicial - sem dados
    st.info("👈 Use o painel lateral para carregar os dados populacionais do IBGE")
    st.markdown("""
    ### Sobre este aplicativo
    
    Este aplicativo permite visualizar e explorar as estimativas populacionais 
    dos municípios brasileiros, utilizando dados oficiais do IBGE (SIDRA - Tabela 6579).
    
    **Funcionalidades:**
    - 📊 Carregamento automático de dados do SIDRA
    - 🔍 Filtros por UF e faixa populacional
    - 📈 Gráficos interativos
    - 💾 Download dos dados em CSV
    
    **Como usar:**
    1. Selecione o ano desejado no painel lateral
    2. Clique em "Carregar Dados"
    3. Explore os dados usando os filtros e visualizações
    """)
