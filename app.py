"""
Aplicação Streamlit para visualização de dados populacionais do IBGE
Design moderno e minimalista com CSS externo
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
    page_title="População IBGE",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar CSS externo
def load_css():
    with open("styles.css", "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

load_css()

# Título principal
st.markdown('<h1>📍 População Municipal</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Dados oficiais do IBGE | Tabela SIDRA 6579</p>', unsafe_allow_html=True)

# Inicializa o extrator
@st.cache_resource
def init_extractor():
    return PopulacaoDataExtractor()

extractor = init_extractor()

# Sidebar
with st.sidebar:
    st.markdown('<div class="caption">⚡ Controles</div>', unsafe_allow_html=True)
    
    # Seleção do ano
    anos_disponiveis = ['2024', '2023', '2022', '2021', '2020']
    ano_selecionado = st.selectbox(
        "Ano",
        anos_disponiveis,
        index=0
    )
    
    # Botão de carregamento
    if st.button("Carregar dados", type="primary"):
        with st.spinner("Carregando..."):
            try:
                df = extractor.extrair_populacao_municipios(ano=ano_selecionado)
                st.session_state['dados_populacao'] = df
                st.session_state['ultimo_ano'] = ano_selecionado
                st.success("✓ Dados carregados com sucesso")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao carregar: {str(e)}")
    
    # Carregamento automático
    if 'dados_populacao' not in st.session_state:
        cache_file = f"populacao_municipios_{ano_selecionado}.csv"
        df_cache = extractor.carregar_dados_cache(cache_file)
        if df_cache is not None:
            st.session_state['dados_populacao'] = df_cache
            st.session_state['ultimo_ano'] = ano_selecionado
            st.markdown('<p class="caption">📁 Dados carregados do cache</p>', unsafe_allow_html=True)
    
    # Filtros
    if 'dados_populacao' in st.session_state:
        st.markdown('<div class="divider-light"></div>', unsafe_allow_html=True)
        st.markdown('<div class="caption">🔍 Filtros</div>', unsafe_allow_html=True)
        
        # Filtro UF
        ufs = get_uf_list()
        uf_selecionada = st.selectbox(
            "Unidade Federativa",
            ['Todos'] + list(ufs.values())
        )
        
        # Filtro população
        df_filtrado = st.session_state['dados_populacao']
        if not df_filtrado.empty:
            min_pop = int(df_filtrado['populacao'].min())
            max_pop = int(df_filtrado['populacao'].max())
            
            faixa_populacao = st.slider(
                "Faixa populacional",
                min_pop, max_pop,
                (min_pop, max_pop),
                format="%d"
            )

# Área principal - condicional
if 'dados_populacao' in st.session_state:
    df = st.session_state['dados_populacao'].copy()
    
    # Aplica filtros
    if uf_selecionada != 'Todos':
        uf_codigo = [k for k, v in ufs.items() if v == uf_selecionada][0]
        df = df[df['id_municipio'].astype(str).str.startswith(uf_codigo)]
    
    df = df[(df['populacao'] >= faixa_populacao[0]) & 
            (df['populacao'] <= faixa_populacao[1])]
    
    # Estatísticas
    stats = get_summary_stats(df)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Municípios</div>
            <div class="metric-value">{stats['total_municipios']:,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">População total</div>
            <div class="metric-value">{formatar_populacao(stats['populacao_total'])}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Média por município</div>
            <div class="metric-value">{formatar_populacao(stats['populacao_media'])}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Mediana</div>
            <div class="metric-value">{formatar_populacao(stats['populacao_mediana'])}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider-light"></div>', unsafe_allow_html=True)
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3>🏆 Mais populosos</h3>', unsafe_allow_html=True)
        top_municipios = get_top_municipios(df, 10)
        
        fig1 = px.bar(
            top_municipios,
            x='populacao',
            y='municipio',
            orientation='h',
            labels={'populacao': '', 'municipio': ''},
            color='populacao',
            color_continuous_scale=['#e0e0e0', '#1a1a1a'],
            text='populacao'
        )
        fig1.update_layout(
            height=450,
            showlegend=False,
            xaxis=dict(showgrid=False, showticklabels=False, title=''),
            yaxis=dict(showgrid=False, title='', tickfont=dict(size=11)),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=0, r=0, t=0, b=0)
        )
        fig1.update_traces(texttemplate='%{text:,}', textposition='outside', textfont=dict(size=10))
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.markdown('<h3>📊 Distribuição</h3>', unsafe_allow_html=True)
        
        df['faixa_populacional'] = pd.cut(
            df['populacao'],
            bins=8,
            labels=[f'{int(b.left):,}' for b in pd.cut(df['populacao'], bins=8).cat.categories]
        )
        distrib = df['faixa_populacional'].value_counts().sort_index()
        
        fig2 = px.bar(
            x=distrib.index,
            y=distrib.values,
            labels={'x': '', 'y': ''},
            color=distrib.values,
            color_continuous_scale=['#e0e0e0', '#1a1a1a']
        )
        fig2.update_layout(
            height=450,
            showlegend=False,
            xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title=''),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=0, r=0, t=0, b=0)
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Tabela de dados
    st.markdown('<h3>📋 Dados</h3>', unsafe_allow_html=True)
    
    view_option = st.radio(
        "",
        ["Top 50", "Top 100", "Todos"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if view_option == "Top 50":
        df_display = df.nlargest(50, 'populacao')
    elif view_option == "Top 100":
        df_display = df.nlargest(100, 'populacao')
    else:
        df_display = df
    
    df_exibicao = df_display[['municipio', 'populacao']].copy()
    df_exibicao.columns = ['Município', 'População']
    df_exibicao['População'] = df_exibicao['População'].apply(formatar_populacao)
    
    st.dataframe(
        df_exibicao,
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    # Download
    csv = df.to_csv(index=False, sep=',', encoding='utf-8-sig')
    st.download_button(
        label="📥 Exportar CSV",
        data=csv,
        file_name=f"populacao_{ano_selecionado}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
else:
    # Estado inicial
    st.markdown("""
    <div class="text-center" style="padding: 3rem 1rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">📍</div>
        <div style="font-size: 1.25rem; color: var(--color-secondary); margin-bottom: 0.5rem;">
            Dados populacionais dos municípios brasileiros
        </div>
        <div style="font-size: 0.875rem; color: var(--color-secondary-light);">
            Selecione um ano e clique em "Carregar dados" no menu lateral
        </div>
    </div>
    """, unsafe_allow_html=True)
