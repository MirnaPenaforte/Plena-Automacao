import pandas as pd

def preencher_data_entrada(df_final, df_estoque=None):
    """
    Busca a data da coluna 'ULT.ENTRADA' no arquivo de estoque e vincula ao
    DataFrame final através do EAN.
    """
    try:
        if df_estoque is None:
            print("⚠️ Aviso: Arquivo de estoque não encontrado para extrair data de entrada.")
            df_final['Data Entrada'] = ""
            return df_final

        if df_estoque is None or df_estoque.empty:
            df_final['Data Entrada'] = ""
            return df_final

        # Configuração das colunas
        COLUNA_EAN = 'EAN'
        COLUNA_DATA = 'ULT.ENTRADA'

        if COLUNA_DATA not in df_estoque.columns:
            print(f"⚠️ Coluna '{COLUNA_DATA}' não encontrada no arquivo de estoque.")
            df_final['Data Entrada'] = ""
            return df_final

        # 3. Limpeza dos dados
        df_datas = df_estoque[[COLUNA_EAN, COLUNA_DATA]].copy()
        df_datas[COLUNA_EAN] = df_datas[COLUNA_EAN].astype(str).str.strip()
        
        # Remove duplicatas de EAN na aba estoque (mantendo a última entrada se houver mais de uma)
        df_datas = df_datas.drop_duplicates(subset=[COLUNA_EAN], keep='last')

        # 4. Cruzamento de Dados (Merge)
        # Primeiro, garantimos que a coluna 'EAN' no df_final também esteja limpa
        df_final['EAN'] = df_final['EAN'].astype(str).str.strip()

        # Fazemos o merge para trazer a data
        df_final = pd.merge(df_final, df_datas, on=COLUNA_EAN, how='left')
        
        # Renomeia para o nome padrão da coluna de saída
        df_final['Data Entrada'] = df_final[COLUNA_DATA].fillna("")
        
        # Remove a coluna temporária do merge
        df_final = df_final.drop(columns=[COLUNA_DATA])

        return df_final

    except Exception as e:
        print(f"❌ Erro ao buscar ULTI.ENTRADA: {e}")
        if 'Data Entrada' not in df_final.columns:
            df_final['Data Entrada'] = ""
        return df_final