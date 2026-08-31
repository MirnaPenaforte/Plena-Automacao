import pandas as pd

def extrair_preco_custo(df_estoque):
    """
    Extrai o preço de custo a partir da coluna 'PREÇO_COMPRA' da aba de ESTOQUE,
    convertendo para o tipo FLOAT (ex: 15.20).
    """
    # Configuração das colunas de origem
    COLUNA_EAN = 'EAN'
    COLUNA_PRECO = 'PREÇO_COMPRA'
    COLUNA_DATA_ENTRADA = 'ULT.ENTRADA'

    try:
        if df_estoque is None or df_estoque.empty:
            return pd.DataFrame(columns=['EAN', 'Preço Custo'])

        # 1. Seleção e Cópia (garante que as colunas existem)
        if any(coluna not in df_estoque.columns for coluna in (
            COLUNA_EAN, COLUNA_PRECO, COLUNA_DATA_ENTRADA
        )):
            print(
                f"⚠️ Erro: Coluna {COLUNA_EAN}, {COLUNA_PRECO} ou "
                f"{COLUNA_DATA_ENTRADA} não encontrada na aba Estoque."
            )
            return pd.DataFrame(columns=['EAN', 'Preço Custo'])

        # Considera o custo somente para EANs com data de entrada preenchida.
        data_entrada = df_estoque[COLUNA_DATA_ENTRADA]
        tem_data_entrada = (
            data_entrada.notna()
            & data_entrada.astype(str).str.strip().ne('')
            & data_entrada.astype(str).str.strip().str.lower().ne('nan')
            & data_entrada.astype(str).str.strip().str.lower().ne('none')
        )
        df_custo = df_estoque.loc[tem_data_entrada, [COLUNA_EAN, COLUNA_PRECO]].copy()
        df_custo.columns = ['EAN', 'Preço Custo']
        
        # 2. Limpeza do EAN
        df_custo['EAN'] = df_custo['EAN'].astype(str).str.strip()
        
        # 3. Tratamento Numérico do Preço (Conversão para Float)
        def robust_float(val):
            val = str(val).strip()
            if pd.isna(val) or val in ('', 'nan', 'None'): return 0.0
            if ',' in val:
                val = val.replace('.', '').replace(',', '.')
            try:
                return float(val)
            except:
                return 0.0

        df_custo['Preço Custo'] = df_custo['Preço Custo'].apply(robust_float).round(3)

        # Remove duplicatas de EAN para não inflar o merge final
        df_custo = df_custo.drop_duplicates(subset=['EAN'], keep='last')

        return df_custo

    except Exception as e:
        print(f"❌ Erro ao capturar preço de compra do estoque: {e}")
        return None