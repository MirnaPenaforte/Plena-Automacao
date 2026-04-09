import pandas as pd
from datetime import datetime

def agrupar_vendas(df_vendas):
    """
    Soma as vendas da Coluna (quantidade) por EAN, mantendo a regra de meses.
    Removeu o filtro de OPERACAO conforme solicitado.
    """
    COLUNA_EAN = 'COD_EAN'     
    COLUNA_VALOR = 'QTD_VENDIDA'   
    COLUNA_MES_FAT = 'MES_FATURAMENTO'

    try:
        if df_vendas is None or df_vendas.empty:
            return pd.DataFrame(columns=['EAN', 'Mês Atual', 'Mês -1'])

        # 1. Limpeza do EAN e da Quantidade
        df_vendas[COLUNA_EAN] = df_vendas[COLUNA_EAN].astype(str).str.strip()
        
        # Converte quantidade para numérico (trata vírgula caso exista)
        df_vendas[COLUNA_VALOR] = df_vendas[COLUNA_VALOR].astype(str).str.replace(',', '.')
        df_vendas[COLUNA_VALOR] = pd.to_numeric(df_vendas[COLUNA_VALOR], errors='coerce').fillna(0)

        # 2. Categorização de Mês (Lógica Mantida)
        data_hoje = datetime.now()
        ano_atual = data_hoje.year
        mes_atual = data_hoje.month

        def categorizar_mes(val):
            if pd.isna(val) or str(val).strip() == '':
                return 'Outros'
            try:
                # Tenta converter o valor (que pode ser o número do mês ou uma data)
                try:
                    mes_val = int(float(str(val)))
                    ano_val = ano_atual
                except ValueError:
                    dt = pd.to_datetime(val, dayfirst=True)
                    mes_val = dt.month
                    ano_val = dt.year
                
                # Cálculo da diferença absoluta em meses
                diff = (ano_atual * 12 + mes_atual) - (ano_val * 12 + mes_val)
                
                if diff == 0: return 'Mês Atual'
                return 'Outros'
            except:
                return 'Outros'

        df_vendas['CATEGORIA_MES'] = df_vendas[COLUNA_MES_FAT].apply(categorizar_mes)

        # 3. Agrupamento Final (Pivot)
        pivot_vendas = df_vendas.pivot_table(
            index=COLUNA_EAN,
            columns='CATEGORIA_MES',
            values=COLUNA_VALOR,
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        # 4. Garantia das Colunas de Saída
        if 'Mês Atual' not in pivot_vendas.columns:
            pivot_vendas['Mês Atual'] = 0
                
        # Mantém apenas o necessário e renomeia
        df_final = pivot_vendas[[COLUNA_EAN, 'Mês Atual']].copy()
        df_final.columns = ['EAN', 'Mês Atual']
        
        # Garante que as quantidades sejam inteiras
        df_final['Mês Atual'] = df_final['Mês Atual'].astype('int64')

        # Deixa a coluna Mês -1 em branco
        df_final['Mês -1'] = ''

        return df_final

    except Exception as e:
        print(f"❌ Erro ao somar vendas por EAN/Mês: {e}")
        return None