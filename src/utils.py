"""
Funções utilitárias para o projeto
"""
import pandas as pd
from typing import Dict, List

def get_uf_list() -> Dict[str, str]:
    """
    Retorna dicionário com códigos e nomes das UFs brasileiras
    
    Returns:
        Dict com código UF como chave e nome como valor
    """
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
    """
    Formata valor populacional para exibição
    
    Args:
        valor: Número populacional
        
    Returns:
        String formatada (ex: 1.234.567)
    """
    if pd.isna(valor):
        return "N/A"
    return f"{int(valor):,}".replace(",", ".")

def get_top_municipios(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Retorna os N municípios mais populosos
    
    Args:
        df: DataFrame com dados populacionais
        n: Número de municípios a retornar
        
    Returns:
        DataFrame ordenado por população (decrescente)
    """
    return df.nlargest(n, 'populacao')[['municipio', 'populacao']]

def get_summary_stats(df: pd.DataFrame) -> Dict:
    """
    Calcula estatísticas resumidas dos dados
    
    Args:
        df: DataFrame com dados populacionais
        
    Returns:
        Dicionário com estatísticas
    """
    return {
        'total_municipios': len(df),
        'populacao_total': df['populacao'].sum(),
        'populacao_media': df['populacao'].mean(),
        'populacao_mediana': df['populacao'].median(),
        'populacao_min': df['populacao'].min(),
        'populacao_max': df['populacao'].max(),
        'municipio_mais_populoso': df.loc[df['populacao'].idxmax(), 'municipio'],
        'municipio_menos_populoso': df.loc[df['populacao'].idxmin(), 'municipio']
    }
