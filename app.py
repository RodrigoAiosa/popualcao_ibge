"""
Aplicação Streamlit para visualização de dados populacionais do IBGE
Com CSS externo funcionando
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sidrapy
from typing import Dict, Optional
import time
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="População IBGE",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CARREGAR CSS EXTERNO
# ============================================
def load_css():
    """Carrega o arquivo CSS externo"""
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        return True
    except FileNotFoundError:
        st.warning("Arquivo styles.css não encontrado. Usando estilo padrão.")
        return False
    except Exception as e:
        st.warning(f"Erro ao carregar CSS: {str(e)}")
        return False

# Carregar CSS (opcional, se não encontrar, usa estilo inline)
css_loaded = load_css()

# Se CSS não foi carregado, aplica estilo básico inline
if not css_loaded:
    st.markdown("""
    <style>
        .main { padding: 1rem; }
        .metric-card { 
            background: #ffffff; 
            border: 1px solid #eaeaea; 
            border-radius: 12px; 
            padding: 1rem; 
        }
        .metric-label { font-size: 0.75rem; color: #666; text-transform: uppercase; }
        .metric-value { font-size: 1.5rem; font-weight: 600; color: #1a1a1a; }
        .divider-light { margin: 1rem 0; border-top: 1px solid #eaeaea; }
        .caption { font-size: 0.75rem; color: #999; text-transform: uppercase; }
        .text-center { text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# FUNÇÕES UTILITÁRIAS
# ============================================

def get_uf_list() -> Dict[str, str]:
    """Retorna dicionário com códigos e nomes das UFs brasileiras"""
    return {
        '11': 'Rondônia', '12': 'Acre', '13': 'Amazonas', '14': 'Roraima',
        '15': 'Pará', '16': 'Amapá', '17': 'Tocantins', '21': 'Maranhão',
        '22': 'Piauí', '23': 'Ceará', '24': 'Rio Grande do Norte', '25': 'Paraíba',
        '26': 'Pernambuco', '27': 'Alagoas', '28': 'Sergipe', '29': 'Bahia',
        '31': 'Minas Gerais', '32': 'Espírito Santo', '33': 'Rio de Janeiro',
        '35': 'São Paulo', '41': 'Paraná', '42': 'Santa Catarina', '43': 'Rio Grande do Sul',
        '50': 'Mato Grosso do Sul', '51': 'Mato Grosso', '52': 'Goiás', '53': 'Distrito Federal'
    }

def formatar_populacao(valor: float) -> str:
    """Formata valor populacional para exibição"""
    if pd.isna(valor):
        return "N/A"
    return f"{int(valor):,}".replace(",", ".")

@st.cache_data(ttl=3600)
def extrair_dados_populacao(ano: str) -> Optional[pd.DataFrame]:
    """Extrai dados populacionais do SIDRA/IBGE com cache"""
    try:
        dados = sidrapy.get_table(
            table_code="6579",
            territorial_level="6",
            ibge_territorial_code="all",
            period=ano,
            format="pandas"
        )
        
        # Converte para DataFrame
        df = pd.DataFrame(dados) if isinstance(dados, list) else dados.copy()
        
        if df.empty:
            return None
        
        # Mapeamento de colunas
        col_mapping = {
            "D1C": "id_municipio",
            "D1N": "municipio",
            "D2C": "ano",
            "V": "populacao"
        }
        
        for old, new in col_mapping.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        # Garantir coluna de população
        if "populacao" not in df.columns:
            for col in df.columns:
                if col.upper() in ['V', 'VALOR', 'POPULACAO']:
                    df = df.rename(columns={col: "populacao"})
                    break
        
        # Selecionar colunas
        cols_to_keep = [c for c in ["id_municipio", "municipio", "populacao"] if c in df.columns]
        if not cols_to_keep:
            return None
        
        df = df[cols_to_keep]
        
        # Converter população
        df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce")
        df = df.dropna(subset=["populacao"])
        df = df[df["populacao"] > 0]
        df["ano"] = ano
        
        # Limpar nomes
        if "municipio" in df.columns:
            df["municipio"] = df["municipio"].astype(str).str.strip()
        
        # Garantir ID como string
        if "id_municipio" in df.columns:
            df["id_municipio"] = df["id_municipio"].astype(str).str.zfill(7)
        
        df = df.sort_values("municipio").reset_index(drop=True)
        
        return df
        
    except Exception as e:
        st.error(f"Erro na extração: {str(e)}")
        return None

# ============================================
# INICIALIZAÇÃO DO ESTADO
# ============================================
if 'dados_populacao' not in st.session_state:
    st.session_state['dados_populacao'] = None
if 'ultimo_ano' not in st.session_state:
    st.session_state['ultimo_ano'] = None
if 'faixa_populacao' not in st.session_state:
    st.session_state['faixa_populacao'] = (0, 1)
if 'uf_selecionada' not in st.session_state:
    st.session_state['uf_selecionada'] = 'Todos'
if 'dados_carregados' not in st.session_state:
    st.session_state['dados_carregados'] = False

# ============================================
# TÍTULO PRINCIPAL
# ============================================
st.markdown('<h1>📍 População Municipal</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Dados oficiais do IBGE | Tabela SIDRA 6579</p>', unsafe_allow_html=True)

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown('<div class="caption">⚡ Controles</div>', unsafe_allow_html=True)
    
    anos_disponiveis = ['2024', '2023', '2022', '2021', '2020']
    ano_selecionado = st.selectbox("Ano", anos_disponiveis, index=0)
    
    if st.button("📥 Carregar dados", type="primary", use_container_width=True):
        with st.spinner(f"Baixando dados do IBGE para {ano_selecionado}..."):
            df = extrair_dados_populacao(ano_selecionado)
            
            if df is not None and not df.empty:
                st.session_state['dados_populacao'] = df
                st.session_state['ultimo_ano'] = ano_selecionado
                st.session_state['dados_carregados'] = True
                
                min_pop = int(df['populacao'].min())
                max_pop = int(df['populacao'].max())
                st.session_state['faixa_populacao'] = (min_pop, max_pop)
                
                st.success(f"✅ {len(df):,} municípios carregados")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"❌ Nenhum dado encontrado para {ano_selecionado}")
    
    # Filtros (apenas se dados carregados)
    if st.session_state['dados_carregados'] and st.session_state['dados_populacao'] is not None:
        st.markdown('<div class="divider-light"></div>', unsafe_allow_html=True)
        st.markdown('<div class="caption">🔍 Filtros</div>', unsafe_allow_html=True)
        
        df_filtrado = st.session_state['dados_populacao']
        
        if not df_filtrado.empty:
            # Filtro UF
            ufs = get_uf_list()
            uf_options = ['Todos'] + list(ufs.values())
            
            current_index = 0
            if st.session_state['uf_selecionada'] in uf_options:
                current_index = uf_options.index(st.session_state['uf_selecionada'])
            
            uf_selecionada = st.selectbox("Unidade Federativa", uf_options, index=current_index)
            st.session_state['uf_selecionada'] = uf_selecionada
            
            # Filtro população
            min_pop_total = int(df_filtrado['populacao'].min())
            max_pop_total = int(df_filtrado['populacao'].max())
            
            if st.session_state['faixa_populacao'] is None or len(st.session_state['faixa_populacao']) != 2:
                st.session_state['faixa_populacao'] = (min_pop_total, max_pop_total)
            
            faixa_populacao = st.slider(
                "Faixa populacional",
                min_pop_total, max_pop_total,
                st.session_state['faixa_populacao'],
                format="%d"
            )
            st.session_state['faixa_populacao'] = faixa_populacao

# ============================================
# ÁREA PRINCIPAL
# ============================================
if st.session_state['dados_carregados'] and st.session_state['dados_populacao'] is not None:
    df = st.session_state['dados_populacao'].copy()
    
    if df.empty:
        st.warning("⚠️ Nenhum dado disponível")
    else:
        # Aplicar filtros
        uf_selecionada = st.session_state.get('uf_selecionada', 'Todos')
        if uf_selecionada != 'Todos':
            ufs = get_uf_list()
            uf_codigo = [k for k, v in ufs.items() if v == uf_selecionada][0]
            if 'id_municipio' in df.columns:
                df = df[df['id_municipio'].astype(str).str.startswith(uf_codigo)]
        
        faixa_populacao = st.session_state.get('faixa_populacao')
        if faixa_populacao and len(faixa_populacao) == 2:
            df = df[(df['populacao'] >= faixa_populacao[0]) & (df['populacao'] <= faixa_populacao[1])]
        
        if df.empty:
            st.warning("⚠️ Nenhum município encontrado com os filtros selecionados")
        else:
            # ====================================
            # CARDS DE ESTATÍSTICAS
            # ====================================
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Municípios</div>
                    <div class="metric-value">{len(df):,}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">População total</div>
                    <div class="metric-value">{formatar_populacao(df['populacao'].sum())}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Média por município</div>
                    <div class="metric-value">{formatar_populacao(df['populacao'].mean())}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                cidade_mais_populosa = df.loc[df['populacao'].idxmax(), 'municipio']
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Mais populoso</div>
                    <div class="metric-value">{cidade_mais_populosa[:25]}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('<div class="divider-light"></div>', unsafe_allow_html=True)
            
            # ====================================
            # GRÁFICOS
            # ====================================
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<h3>🏆 Mais populosos</h3>', unsafe_allow_html=True)
                top10 = df.nlargest(10, 'populacao')[['municipio', 'populacao']]
                
                fig1 = px.bar(
                    top10,
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
                
                if len(df) > 5:
                    n_bins = min(8, max(3, len(df) // 100))
                    df['faixa'] = pd.cut(df['populacao'], bins=n_bins)
                    distrib = df['faixa'].value_counts().sort_index()
                    
                    # Criar labels legíveis
                    labels = []
                    for interval in distrib.index:
                        if interval is not None:
                            labels.append(f"{int(interval.left):,}")
                    
                    fig2 = px.bar(
                        x=labels,
                        y=distrib.values,
                        labels={'x': 'Faixa populacional (habitantes)', 'y': 'Número de municípios'},
                        color=distrib.values,
                        color_continuous_scale=['#e0e0e0', '#1a1a1a']
                    )
                    fig2.update_layout(
                        height=450,
                        showlegend=False,
                        xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
                        yaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        margin=dict(l=0, r=0, t=0, b=0)
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info(f"📊 Dados insuficientes para gráfico de distribuição ({len(df)} municípios)")
            
            # ====================================
            # TABELA
            # ====================================
            st.markdown('<h3>📋 Dados</h3>', unsafe_allow_html=True)
            
            col_view, col_empty = st.columns([1, 3])
            with col_view:
                view = st.selectbox("Exibir", ["Top 50", "Top 100", "Todos"], label_visibility="collapsed")
            
            if view == "Top 50":
                df_display = df.nlargest(50, 'populacao')
            elif view == "Top 100":
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
                hide_index=True,
                column_config={
                    "Município": st.column_config.TextColumn("Município", width="large"),
                    "População": st.column_config.TextColumn("População", width="medium")
                }
            )
            
            # ====================================
            # BOTÃO DE DOWNLOAD
            # ====================================
            st.markdown('<div class="divider-light"></div>', unsafe_allow_html=True)
            
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Exportar dados completos (CSV)",
                data=csv,
                file_name=f"populacao_municipios_{st.session_state['ultimo_ano']}.csv",
                mime="text/csv",
                use_container_width=True
            )

else:
    # ====================================
    # ESTADO INICIAL
    # ====================================
    st.markdown("""
    <div class="text-center" style="padding: 3rem 1rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">📍</div>
        <div style="font-size: 1.25rem; color: #666; margin-bottom: 0.5rem;">
            Dados populacionais dos municípios brasileiros
        </div>
        <div style="font-size: 0.875rem; color: #999;">
            Selecione um ano e clique em "Carregar dados" no menu lateral
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("ℹ️ Sobre o projeto"):
        st.markdown("""
        **Fonte dos dados:** IBGE - SIDRA Tabela 6579 (Estimativas populacionais)
        
        **Anos disponíveis:** 2020, 2021, 2022, 2023, 2024
        
        **Funcionalidades:**
        - 📊 Visualização gráfica dos 10 municípios mais populosos
        - 📈 Distribuição populacional por faixas
        - 🔍 Filtros por UF e faixa populacional
        - 📥 Exportação para CSV
        - 💾 Cache automático dos dados
        """)

# ====================================
# FOOTER
# ====================================
st.markdown('<div class="divider-light"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="text-center" style="font-size: 0.7rem; color: #999;">'
    '📊 Dados: IBGE - Tabela SIDRA 6579 | Estimativas populacionais municipais'
    '</div>', 
    unsafe_allow_html=True
)
