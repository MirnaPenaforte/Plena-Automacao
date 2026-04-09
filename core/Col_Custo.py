import pandas as pd

def extrair_preco_custo(df_estoque):
    """
    Extrai o preço de custo a partir da coluna 'PREÇO_COMPRA' da aba de ESTOQUE,
    convertendo para o tipo FLOAT (ex: 15.20).
    """
    # Configuração das colunas de origem
    COLUNA_EAN = 'EAN'
    COLUNA_PRECO = 'PREÇO_COMPRA'

    try:
        if df_estoque is None or df_estoque.empty:
            return pd.DataFrame(columns=['EAN', 'Preço Custo'])

        # 1. Seleção e Cópia (garante que as colunas existem)
        if COLUNA_EAN not in df_estoque.columns or COLUNA_PRECO not in df_estoque.columns:
            print(f"⚠️ Erro: Coluna {COLUNA_EAN} ou {COLUNA_PRECO} não encontrada na aba Estoque.")
            return pd.DataFrame(columns=['EAN', 'Preço Custo'])

        df_custo = df_estoque[[COLUNA_EAN, COLUNA_PRECO]].copy()
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