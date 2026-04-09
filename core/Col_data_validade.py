import pandas as pd

def processar_validade_estoque(df_estoque):
    """
    Pega a data de validade mais próxima (mínima) para cada EAN.
    """
    # VARIÁVEIS DE CONFIGURAÇÃO - Atualizadas para usar o nome da coluna no Excel
    COLUNA_EAN = 'EAN'
    COLUNA_VALIDADE = 'Validade'

    try:
        # Se a coluna não existir, retorna df vazio para não quebrar o script
        if COLUNA_VALIDADE not in df_estoque.columns or COLUNA_EAN not in df_estoque.columns:
            return pd.DataFrame(columns=['EAN', 'Data Validade'])

        # PONTO DE APRENDIZADO 1: Sanitização
        df_estoque[COLUNA_EAN] = df_estoque[COLUNA_EAN].astype(str).str.strip()

        # PONTO DE APRENDIZADO 2: Conversão de Data
        # O 'dayfirst=True' é vital para o padrão brasileiro (DD/MM/AAAA)
        # 'errors=coerce' transforma datas inválidas em NaT (Not a Time)
        df_estoque[COLUNA_VALIDADE] = pd.to_datetime(
            df_estoque[COLUNA_VALIDADE], 
            dayfirst=True, 
            errors='coerce'
        )

        # Removemos linhas onde a data de validade ficou NaT (inválida/nula)
        # pois não conseguimos calcular o menor vencimento para elas
        df_estoque = df_estoque.dropna(subset=[COLUNA_VALIDADE])

        # PONTO DE APRENDIZADO 3: Agrupando para achar a menor data (min)
        # Para cada EAN, qual a data de validade mais próxima?
        df_validade = df_estoque.groupby(COLUNA_EAN)[COLUNA_VALIDADE].min().reset_index()

        # 3. Renomear para a saída desejada
        df_validade.columns = ['EAN', 'Data Validade']

        df_validade['Data Validade'] = df_validade['Data Validade'].dt.strftime('%d/%m/%Y')

        # Opcional: Substituir valores vazios (NaT) por uma string amigável ou manter vazio
        df_validade['Data Validade'] = df_validade['Data Validade'].fillna('')

        return df_validade

    except Exception as e:
        print(f"❌ Erro ao processar validade: {e}")
        return None