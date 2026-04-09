import pandas as pd
import os

def ler_planilha_excel(caminho_arquivo, nome_aba):
    """
    Lê uma aba específica de um arquivo Excel com colunas nomeadas.
    """
    if not os.path.exists(caminho_arquivo):
        print(f"ERRO CRÍTICO: Arquivo não encontrado em: {caminho_arquivo}")
        return None

    try:
        # O dtype=str é preservado para evitar problemas com EANs longos 
        # (notação científica). Os arquivos Col_* cuidam das conversões numéricas.
        df = pd.read_excel(
            caminho_arquivo,
            sheet_name=nome_aba,
            dtype=str
        )
        return df
    except ValueError as ve:
        # Pega o erro específico se a aba não for encontrada
        print(f"ERRO: A aba '{nome_aba}' não foi encontrada no arquivo '{caminho_arquivo}'")
        return None
    except Exception as e:
        print(f"ERRO CRÍTICO ao ler o arquivo {caminho_arquivo}: {e}")
        return None
