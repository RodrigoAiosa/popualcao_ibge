"""
Módulo para extração de dados populacionais do SIDRA/IBGE
"""
import pandas as pd
import sidrapy
from typing import Optional, Dict, Any
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PopulacaoDataExtractor:
    """Classe para extrair dados populacionais do SIDRA"""
    
    TABELA_POPULACAO = "6579"  # Estimativas de população
    NIVEL_MUNICIPIO = "6"
    NIVEL_UF = "3"  # Código para UF (Unidade da Federação)
    
    def __init__(self, data_dir: str = "data"):
        """
        Inicializa o extrator
        
        Args:
            data_dir: Diretório onde os dados serão salvos
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def extrair_populacao_municipios(
        self, 
        ano: str = "2024",
        salvar_csv: bool = True,
        nome_arquivo: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extrai estimativas populacionais por município
        
        Args:
            ano: Ano desejado (formato 'YYYY')
            salvar_csv: Se True, salva o DataFrame em CSV
            nome_arquivo: Nome do arquivo CSV (opcional)
            
        Returns:
            DataFrame com dados populacionais
        """
        try:
            logger.info(f"Extraindo dados populacionais para o ano {ano}...")
            
            # Extrai dados do SIDRA
            dados = sidrapy.get_table(
                table_code=self.TABELA_POPULACAO,
                territorial_level=self.NIVEL_MUNICIPIO,
                ibge_territorial_code="all",
                period=ano,
                format="pandas"
            )
            
            # Converte para DataFrame se necessário
            df = pd.DataFrame(dados) if isinstance(dados, list) else dados.copy()
            
            # Processa os dados
            df = self._processar_dados(df)
            
            # Salva CSV se solicitado
            if salvar_csv:
                nome_arquivo = nome_arquivo or f"populacao_municipios_{ano}.csv"
                caminho_arquivo = self.data_dir / nome_arquivo
                df.to_csv(caminho_arquivo, index=False, sep=",", encoding="utf-8-sig")
                logger.info(f"Dados salvos em: {caminho_arquivo}")
            
            return df
            
        except Exception as e:
            logger.error(f"Erro na extração dos dados: {str(e)}")
            raise
    
    def extrair_por_uf(
        self, 
        codigo_uf: str,
        ano: str = "2024"
    ) -> pd.DataFrame:
        """
        Extrai dados populacionais para uma UF específica
        
        Args:
            codigo_uf: Código da UF (ex: '35' para SP)
            ano: Ano desejado
            
        Returns:
            DataFrame com dados da UF
        """
        df_completo = self.extrair_populacao_municipios(ano, salvar_csv=False)
        
        # Filtra por UF (primeiros 2 dígitos do ID do município)
        df_filtrado = df_completo[
            df_completo['id_municipio'].astype(str).str.startswith(codigo_uf)
        ]
        
        return df_filtrado
    
    def _processar_dados(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processa e normaliza os dados do SIDRA
        
        Args:
            df: DataFrame cru do SIDRA
            
        Returns:
            DataFrame processado
        """
        # Mapeamento de colunas
        rename_map = {
            "D1C": "id_municipio",
            "D1N": "municipio",
            "D2C": "ano",
            "D2N": "periodo",
            "V": "populacao"
        }
        
        # Renomeia colunas existentes
        colunas_existentes = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=colunas_existentes)
        
        # Seleciona colunas desejadas
        colunas_desejadas = ["id_municipio", "municipio", "ano", "populacao"]
        colunas_presentes = [col for col in colunas_desejadas if col in df.columns]
        df = df[colunas_presentes]
        
        # Ajusta tipos de dados
        if "populacao" in df.columns:
            df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce")
        
        if "ano" in df.columns:
            df["ano"] = df["ano"].astype(str).str[:4]
        
        # Remove valores nulos
        df = df.dropna(subset=["id_municipio", "municipio", "populacao"])
        
        # Ordena por município
        df = df.sort_values("municipio").reset_index(drop=True)
        
        return df
    
    def carregar_dados_cache(self, nome_arquivo: str) -> Optional[pd.DataFrame]:
        """
        Carrega dados de um arquivo CSV cache
        
        Args:
            nome_arquivo: Nome do arquivo CSV
            
        Returns:
            DataFrame ou None se arquivo não existir
        """
        caminho_arquivo = self.data_dir / nome_arquivo
        if caminho_arquivo.exists():
            logger.info(f"Carregando dados do cache: {caminho_arquivo}")
            return pd.read_csv(caminho_arquivo)
        return None
