"""
Módulo para extração de dados populacionais do SIDRA/IBGE
Versão robusta - Compatível com todos os anos
"""
import pandas as pd
import sidrapy
from typing import Optional
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PopulacaoDataExtractor:
    """Classe para extrair dados populacionais do SIDRA"""
    
    TABELA_POPULACAO = "6579"
    NIVEL_MUNICIPIO = "6"
    
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
    ) -> Optional[pd.DataFrame]:
        """
        Extrai estimativas populacionais por município
        
        Args:
            ano: Ano desejado (formato 'YYYY')
            salvar_csv: Se True, salva o DataFrame em CSV
            nome_arquivo: Nome do arquivo CSV (opcional)
            
        Returns:
            DataFrame com dados populacionais ou None se erro
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
            if isinstance(dados, list):
                df = pd.DataFrame(dados)
            else:
                df = dados.copy()
            
            # Verifica se o DataFrame está vazio
            if df.empty:
                logger.warning(f"Nenhum dado retornado para o ano {ano}")
                return None
            
            # Processa os dados
            df = self._processar_dados(df)
            
            if df is None or df.empty:
                logger.warning(f"Processamento resultou em DataFrame vazio para {ano}")
                return None
            
            # Salva CSV se solicitado
            if salvar_csv:
                nome_arquivo = nome_arquivo or f"populacao_municipios_{ano}.csv"
                caminho_arquivo = self.data_dir / nome_arquivo
                df.to_csv(caminho_arquivo, index=False, sep=",", encoding="utf-8-sig")
                logger.info(f"Dados salvos em: {caminho_arquivo}")
            
            logger.info(f"Extração concluída: {len(df)} municípios")
            return df
            
        except Exception as e:
            logger.error(f"Erro na extração dos dados para {ano}: {str(e)}")
            return None
    
    def _processar_dados(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Processa e normaliza os dados do SIDRA
        
        Args:
            df: DataFrame cru do SIDRA
            
        Returns:
            DataFrame processado ou None se erro
        """
        try:
            # Mapeamento de colunas (versão estendida para diferentes estruturas)
            possible_renames = {
                "D1C": "id_municipio",
                "D1N": "municipio",
                "D2C": "ano",
                "D2N": "periodo",
                "V": "populacao",
                # Fallbacks para nomes alternativos
                "Município (código)": "id_municipio",
                "Município": "municipio",
                "Valor": "populacao",
                "Ano (código)": "ano"
            }
            
            # Renomeia colunas existentes
            for old_name, new_name in possible_renames.items():
                if old_name in df.columns:
                    df = df.rename(columns={old_name: new_name})
            
            # Identificar coluna de população (pode ter nomes diferentes)
            pop_column = None
            for col in df.columns:
                if col.lower() in ['v', 'valor', 'populacao', 'população']:
                    pop_column = col
                    break
            
            if pop_column and pop_column != 'populacao':
                df = df.rename(columns={pop_column: 'populacao'})
            
            # Seleciona colunas desejadas
            colunas_desejadas = ["id_municipio", "municipio", "ano", "populacao"]
            colunas_presentes = [col for col in colunas_desejadas if col in df.columns]
            
            if not colunas_presentes:
                logger.error("Nenhuma coluna esperada encontrada no DataFrame")
                logger.info(f"Colunas disponíveis: {df.columns.tolist()}")
                return None
            
            df = df[colunas_presentes]
            
            # Ajusta tipos de dados
            if "populacao" in df.columns:
                df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce")
            
            if "ano" in df.columns:
                df["ano"] = df["ano"].astype(str).str[:4]
            else:
                # Se não tiver coluna ano, adiciona a partir do contexto
                df["ano"] = "2024"  # Valor padrão
            
            # Remove valores nulos
            df = df.dropna(subset=["populacao"])
            df = df[df["populacao"] > 0]  # Remove população zero ou negativa
            
            # Remove linhas com município vazio
            if "municipio" in df.columns:
                df = df.dropna(subset=["municipio"])
                df["municipio"] = df["municipio"].astype(str).str.strip()
                df = df[df["municipio"] != ""]
            
            # Ordena por município
            if "municipio" in df.columns:
                df = df.sort_values("municipio").reset_index(drop=True)
            else:
                df = df.reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro no processamento dos dados: {str(e)}")
            return None
    
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
            try:
                logger.info(f"Carregando dados do cache: {caminho_arquivo}")
                df = pd.read_csv(caminho_arquivo)
                
                # Verificar se as colunas essenciais existem
                if 'populacao' in df.columns:
                    return df
                else:
                    logger.warning(f"Cache inválido: coluna 'populacao' não encontrada")
                    return None
            except Exception as e:
                logger.error(f"Erro ao carregar cache: {str(e)}")
                return None
        return None
