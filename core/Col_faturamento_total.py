import pandas as pd
import re
from datetime import datetime


def calcular_faturamento_atual(df_vendas):
    """
    Soma o VALOR_LIQUIDO por EAN e por mês de faturamento.

    - MES_FATURAMENTO igual ao mês atual  → coluna 'Faturamento Atual'
    - MES_FATURAMENTO igual ao mês anterior → coluna 'Faturamento M-1'

    Devoluções já vêm com valor negativo e naturalmente reduzem o total.
    Trata valores monetários (R$, pontos como separador de milhar, vírgula como decimal).
    """
    COLUNA_EAN = 'COD_EAN'
    COLUNA_VALOR_LIQUIDO = 'VALOR_LIQUIDO'
    COLUNA_MES = 'MES_FATURAMENTO'

    try:
        # Validações básicas
        for col in [COLUNA_VALOR_LIQUIDO, COLUNA_EAN, COLUNA_MES]:
            if col not in df_vendas.columns:
                print(f"⚠️ Coluna '{col}' não encontrada no DataFrame de vendas.")
                return None

        df_vendas = df_vendas.copy()

        if df_vendas.empty:
            return pd.DataFrame(columns=['EAN', 'Faturamento Atual', 'Faturamento M-1'])

        # Determina mês atual e mês anterior
        mes_atual = datetime.now().month          # ex: 4 (abril)
        mes_anterior = mes_atual - 1 if mes_atual > 1 else 12  # ex: 3 (março)

        print(f"📅 Mês atual: {mes_atual} | Mês M-1: {mes_anterior}")

        # Limpeza do EAN
        df_vendas[COLUNA_EAN] = df_vendas[COLUNA_EAN].astype(str).str.strip()

        # Garante que MES_FATURAMENTO é numérico inteiro
        df_vendas[COLUNA_MES] = pd.to_numeric(df_vendas[COLUNA_MES], errors='coerce')

        # Tratamento monetário
        def parse_monetario(val):
            if pd.isna(val):
                return 0.0

            val = str(val).strip()

            if val in ('', 'nan', 'None'):
                return 0.0

            # Remove símbolo monetário (R$, $, €, etc.) e espaços
            val = re.sub(r'[R$€£\s]', '', val)

            # Detecta o formato do número:
            # Caso 1: separador de milhar é ponto e decimal é vírgula → "1.234,56"
            # Caso 2: separador de milhar é vírgula e decimal é ponto  → "1,234.56"
            # Caso 3: só vírgula sem milhar                            → "10,50"
            # Caso 4: só ponto sem milhar                              → "10.50"

            if ',' in val and '.' in val:
                if val.index(',') < val.index('.'):
                    # Formato: 1,234.56 → remove vírgula, mantém ponto
                    val = val.replace(',', '')
                else:
                    # Formato: 1.234,56 → remove ponto, troca vírgula por ponto
                    val = val.replace('.', '').replace(',', '.')
            elif ',' in val:
                # Formato: 10,50 → troca vírgula por ponto
                val = val.replace(',', '.')

            try:
                return float(val)
            except ValueError:
                print(f"⚠️ Valor não convertível ignorado: '{val}'")
                return 0.0

        df_vendas[COLUNA_VALOR_LIQUIDO] = df_vendas[COLUNA_VALOR_LIQUIDO].apply(parse_monetario)

        # Separa os dados por mês
        df_atual    = df_vendas[df_vendas[COLUNA_MES] == mes_atual]
        df_anterior = df_vendas[df_vendas[COLUNA_MES] == mes_anterior]

        print(f"📊 Linhas mês atual ({mes_atual}): {len(df_atual)} | Linhas M-1 ({mes_anterior}): {len(df_anterior)}")

        # Agrupamento e soma por EAN — mês atual
        fat_atual = (
            df_atual
            .groupby(COLUNA_EAN)[COLUNA_VALOR_LIQUIDO]
            .sum()
            .round(2)
            .reset_index()
            .rename(columns={COLUNA_EAN: 'EAN', COLUNA_VALOR_LIQUIDO: 'Faturamento Atual'})
        )

        # Agrupamento e soma por EAN — mês anterior (M-1)
        fat_anterior = (
            df_anterior
            .groupby(COLUNA_EAN)[COLUNA_VALOR_LIQUIDO]
            .sum()
            .round(2)
            .reset_index()
            .rename(columns={COLUNA_EAN: 'EAN', COLUNA_VALOR_LIQUIDO: 'Faturamento M-1'})
        )

        # Junta os dois DataFrames pelo EAN (outer join para manter todos os EANs)
        df_resultado = pd.merge(fat_atual, fat_anterior, on='EAN', how='outer').fillna(0.0)

        # Garante tipos float nas colunas de valor
        df_resultado['Faturamento Atual'] = df_resultado['Faturamento Atual'].round(2)
        df_resultado['Faturamento M-1']   = df_resultado['Faturamento M-1'].round(2)

        print(f"✅ Faturamento calculado para {len(df_resultado)} EANs distintos.")
        return df_resultado

    except Exception as e:
        print(f"❌ Erro ao calcular faturamento agrupado: {e}")
        return None