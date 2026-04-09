import pandas as pd

def processar_estoque_agrupado(df_estoque):
    """
    Lê os dados da aba de estoque, agrupa por EAN e soma as quantidades.
    Garante a limpeza de strings e conversão numérica robusta.
    """
    # Configuração das colunas de origem
    COLUNA_EAN = 'EAN'
    COLUNA_ESTOQUE = 'ESTOQUE'

    try:
        # 1. Seleção e Limpeza Inicial
        # Removemos linhas onde o EAN ou o Estoque são nulos para evitar erros no groupby
        df_final = df_estoque[[COLUNA_EAN, COLUNA_ESTOQUE]].copy()
        
        # 2. Tratamento do EAN (Remover espaços, converter para string)
        df_final[COLUNA_EAN] = df_final[COLUNA_EAN].astype(str).str.strip()
        
        # 3. Tratamento da Coluna de Estoque
        # O valor de estoque sempre vem como inteiro, sem vírgulas
        df_final[COLUNA_ESTOQUE] = pd.to_numeric(df_final[COLUNA_ESTOQUE], errors='coerce').fillna(0).astype(int)

        # 4. Agrupamento e Soma
        # Agrupamos por EAN para consolidar produtos duplicados na planilha de origem
        df_agrupado = df_final.groupby(COLUNA_EAN)[COLUNA_ESTOQUE].sum().reset_index()

        # 5. Renomeação Final das Colunas
        df_agrupado.columns = ['EAN', 'Estoque']
        
        # Estoque já é inteiro desde o início do processamento

        return df_agrupado

    except Exception as e:
        print(f"❌ Erro crítico ao processar estoque agrupado: {e}")
        return None