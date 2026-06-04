"""
Aplicação Streamlit para visualização de dados populacionais do IBGE
Versão otimizada para Streamlit Cloud
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from src.data_extractor import PopulacaoDataExtractor
from src.utils import get_uf_list, formatar_populacao
import time
import warnings
warnings.filterwarnings('ignore')

# Configuração da página DEVE ser o primeiro comando Streamlit
st.set_page_config(
    page_title="População dos Municípios Brasileiros",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cache para o extrator
@st.cache_resource
def init_extractor():
    return PopulacaoDataExtractor()

# Cache para carregamento de dados
@st.cache_data(ttl=3600)  # Cache por 1 hora
def load_population_data(ano):
    """Carrega dados populacionais com cache"""
    try:
        extractor = init_extractor()
        df = extractor.extrair_populacao_municipios(ano=ano, salvar_csv=False)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None

def criar_grafico_barras(df, titulo):
    """Cria gráfico de barras com tratamento de erro"""
    try:
        fig = px.bar(
            df.head(10), 
            x='municipio', 
            y='populacao',
            title=titulo,
            labels={'populacao': 'População', 'municipio': 'Município'},
            color='populacao',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(
            showlegend=False, 
            xaxis_tickangle=-45,
            height=400,
            margin=dict(l=20, r=20, t=40, b=80)
        )
        return fig
    except Exception as e:
        st.warning(f"Não foi possível criar o gráfico: {str(e)}")
        return None

def criar_grafico_distribuicao(df):
    """Cria gráfico de distribuição com fallback"""
    try:
        # Criar bins para distribuição
        df_copy = df.copy()
        df_copy['faixa'] = pd.cut(
            df_copy['populacao'], 
            bins=10,
            precision=0
        )
        distrib = df_copy['faixa'].value_counts().sort_index()
        
        fig = px.bar(
            x=[str(x) for x in distrib.index],
            y=distrib.values,
            title="Distribuição dos municípios por faixa populacional",
            labels={'x': 'Faixa Populacional', 'y': 'Número de Municípios'}
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            height=400,
            margin=dict(l=20, r=20, t=40, b=80)
        )
        return fig
    except Exception as e:
        st.warning(f"Não foi possível criar o gráfico de distribuição: {str(e)}")
        return None

def main():
    """Função principal da aplicação"""
    
    # Título principal
    st.title("📊 Estimativas Populacionais dos Municípios Brasileiros")
    st.markdown("Dados do IBGE - Tabela SIDRA 6579")
    
    # Sidebar
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
                df = load_population_data(ano_selecionado)
                if df is not None:
                    st.session_state['dados_populacao'] = df
                    st.session_state['ultimo_ano'] = ano_selecionado
                    st.success(f"✅ Dados de {ano_selecionado} carregados! Total: {len(df):,} municípios")
                    time.sleep(1)
                    st.rerun()
        
        # Verificar se já existem dados
        if 'dados_populacao' not in st.session_state:
            # Tentar carregar automaticamente dados de 2024
            with st.spinner("Carregando dados padrão..."):
                df_default = load_population_data("2024")
                if df_default is not None:
                    st.session_state['dados_populacao'] = df_default
                    st.session_state['ultimo_ano'] = "2024"
                    st.info("📊 Dados de 2024 carregados automaticamente")
        
        # Filtros (apenas se dados carregados)
        if 'dados_populacao' in st.session_state:
            st.markdown("---")
            st.header("🔍 Filtros")
            
            df_original = st.session_state['dados_populacao']
            
            # Filtro por UF
            ufs = get_uf_list()
            uf_selecionada = st.selectbox(
                "Filtrar por UF:",
                ['Todos (Brasil)'] + list(ufs.values())
            )
            
            # Filtro por faixa populacional
            min_pop = int(df_original['populacao'].min())
            max_pop = int(df_original['populacao'].max())
            
            faixa_populacao = st.slider(
                "Faixa populacional:",
                min_pop, max_pop,
                (min_pop, max_pop),
                format="%d"
            )
            
            # Número de itens para exibir
            num_itens = st.selectbox(
                "Número de municípios no topo:",
                [10, 20, 50, 100],
                index=0
            )
    
    # Área principal
    if 'dados_populacao' in st.session_state:
        df = st.session_state['dados_populacao'].copy()
        
        # Aplica filtros
        if uf_selecionada != 'Todos (Brasil)':
            uf_codigo = [k for k, v in ufs.items() if v == uf_selecionada][0]
            df = df[df['id_municipio'].astype(str).str.startswith(uf_codigo)]
            st.info(f"📌 Exibindo dados para: {uf_selecionada}")
        
        df = df[(df['populacao'] >= faixa_populacao[0]) & 
                (df['populacao'] <= faixa_populacao[1])]
        
        # Estatísticas gerais
        st.header("📈 Estatísticas Gerais")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🏙️ Total de Municípios",
                f"{len(df):,}",
                help="Número total de municípios na seleção atual"
            )
        
        with col2:
            populacao_total = df['populacao'].sum()
            st.metric(
                "👥 População Total",
                formatar_populacao(populacao_total),
                help="Soma da população de todos os municípios"
            )
        
        with col3:
            if not df.empty:
                municipio_max = df.loc[df['populacao'].idxmax(), 'municipio']
                populacao_max = df['populacao'].max()
                st.metric(
                    "⭐ Mais Populoso",
                    municipio_max[:25],
                    formatar_populacao(populacao_max),
                    help="Município com maior população"
                )
        
        with col4:
            if not df.empty:
                municipio_min = df.loc[df['populacao'].idxmin(), 'municipio']
                populacao_min = df['populacao'].min()
                st.metric(
                    "📉 Menos Populoso",
                    municipio_min[:25],
                    formatar_populacao(populacao_min),
                    help="Município com menor população"
                )
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"🏆 Top {num_itens} Municípios Mais Populosos")
            if not df.empty:
                top_municipios = df.nlargest(num_itens, 'populacao')[['municipio', 'populacao']]
                fig1 = criar_grafico_barras(
                    top_municipios,
                    f"Municípios mais populosos - {ano_selecionado}"
                )
                if fig1:
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    # Fallback: tabela simples
                    st.dataframe(
                        top_municipios,
                        column_config={
                            "municipio": "Município",
                            "populacao": st.column_config.NumberColumn("População", format="%d")
                        },
                        use_container_width=True
                    )
        
        with col2:
            st.subheader("📊 Distribuição Populacional")
            if not df.empty and len(df) > 1:
                fig2 = criar_grafico_distribuicao(df)
                if fig2:
                    st.plotly_chart(fig2, use_container_width=True)
        
        # Tabela de dados
        st.subheader("📋 Dados Detalhados")
        
        # Opção de ordenação
        ordenar_por = st.radio(
            "Ordenar por:",
            ["População (maior para menor)", "População (menor para maior)"],
            horizontal=True
        )
        
        if ordenar_por == "População (maior para menor)":
            df_display = df.nlargest(1000, 'populacao')
        elif ordenar_por == "População (menor para maior)":
            df_display = df.nsmallest(1000, 'populacao')
        else:
            df_display = df.nsmallest(1000, 'municipio')
        
        # Preparar dataframe para exibição
        df_exibicao = df_display[['municipio', 'populacao']].copy()
        df_exibicao.columns = ['Município', 'População']
        
        # Exibir tabela
        st.dataframe(
            df_exibicao,
            use_container_width=True,
            height=400,
            column_config={
                "Município": st.column_config.TextColumn("Município", width="large"),
                "População": st.column_config.NumberColumn("População", format="%d")
            }
        )
        
        # Botão para download
        csv = df.to_csv(index=False, encoding='utf-8-sig')
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

if __name__ == "__main__":
    main()
