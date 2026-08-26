import pandas as pd
import os

def ler_planilha_excel(caminho_arquivo, nome_aba=None):
    """
    Lê um arquivo Excel que contém uma única planilha.
    """
    if not os.path.exists(caminho_arquivo):
        print(f"ERRO CRÍTICO: Arquivo não encontrado em: {caminho_arquivo}")
        return None

    try:
        # O dtype=str é preservado para evitar problemas com EANs longos 
        # (notação científica). Os arquivos Col_* cuidam das conversões numéricas.
        df = pd.read_excel(caminho_arquivo, dtype=str)
        return df
    except Exception as e:
        print(f"ERRO CRÍTICO ao ler o arquivo {caminho_arquivo}: {e}")
        return None
