import pandas as pd
import os
import glob
from datetime import datetime

# CFOPs de devolução de mercadoria.
# Quando o estoque aumenta mas todos os CFOPs do EAN são de devolução,
# o aumento NÃO representa uma entrada nova — a data de entrada não é atualizada.
CFOPS_DEVOLUCAO = {'6202', '5202', '1202', '1411'}

def preencher_data_entrada(df_final):
    """
    Atualiza a 'Data Entrada' comparando o estoque ATUAL (ESTOQUE.csv) com
    o estoque ANTERIOR (ESTOQUE.csv de backup), e validando pelo CFOP de vendas.

    Lógica por EAN:
    1. EAN novo (não existia no estoque anterior) → data de hoje.
    2. Estoque NÃO aumentou em relação ao ESTOQUE anterior → mantém data antiga.
    3. Estoque AUMENTOU → verifica os CFOPs do EAN na planilha de vendas:
        - Todos os CFOPs são de devolução (6202, 5202, 1202, 1411)?
          → mantém data antiga (o aumento veio de uma devolução, não é entrada nova).
        - Há qualquer CFOP que NÃO seja de devolução?
          → atualiza para data de hoje (entrada real de mercadoria).
    """
    try:
        data_hoje = datetime.now().strftime('%d/%m/%Y')

        # --- 1. Ler ESTOQUE.csv atual (pasta imports/) ---
        # Índice [1]=EAN, [2]=Estoque
        mapa_estoque_atual = _mapear_estoque_csv('imports')

        # --- 2. Ler ESTOQUE.csv anterior (backup) ---
        caminho_estoque_antigo = _buscar_csv_estoque_anterior()
        mapa_estoque_anterior = {}
        if caminho_estoque_antigo:
            dir_backup = os.path.dirname(caminho_estoque_antigo)
            mapa_estoque_anterior = _mapear_estoque_csv(dir_backup)
            print(f"📂 Estoque anterior carregado: {caminho_estoque_antigo} ({len(mapa_estoque_anterior)} EANs)")
        else:
            print("⚠️  Nenhum ESTOQUE.csv de backup encontrado. Todos os EANs serão tratados como novos.")

        # --- 3. Ler data de entrada anterior do XLSX (para preservar datas históricas) ---
        mapa_datas_antigas = _carregar_datas_anteriores()

        # --- 4. Mapa de CFOPs por EAN (planilha de vendas) ---
        mapa_cfops_venda = _mapear_cfops_venda()

        # --- 5. Avaliar cada linha do df_final ---
        datas_entrada = []
        for _, row in df_final.iterrows():
            ean = str(row['EAN']).replace('.0', '').strip()
            estoque_atual = float(row['Estoque']) if pd.notna(row.get('Estoque')) else 0.0

            # EAN não existia no estoque anterior → produto novo → data de hoje
            if ean not in mapa_estoque_anterior:
                datas_entrada.append(data_hoje)
                continue

            estoque_anterior = mapa_estoque_anterior.get(ean, 0.0)
            estoque_subiu = estoque_atual > estoque_anterior

            if not estoque_subiu:
                # Estoque não aumentou → mantém data antiga do XLSX
                data_antiga = mapa_datas_antigas.get(ean, data_hoje)
                datas_entrada.append(data_antiga)
                continue

            # Estoque aumentou → verifica CFOPs do EAN na planilha de vendas
            cfops_do_ean = mapa_cfops_venda.get(ean, set())

            if cfops_do_ean and cfops_do_ean.issubset(CFOPS_DEVOLUCAO):
                # Todos os CFOPs são de devolução → aumento veio de devolução, não entrada nova
                data_antiga = mapa_datas_antigas.get(ean, data_hoje)
                datas_entrada.append(data_antiga)
            else:
                # Há CFOP que NÃO é de devolução → entrada real de mercadoria → data de hoje
                datas_entrada.append(data_hoje)

        df_final['Data Entrada'] = datas_entrada
        return df_final

    except Exception as e:
        print(f"❌ Erro ao preencher Data de Entrada: {e}")
        df_final['Data Entrada'] = datetime.now().strftime('%d/%m/%Y')
        return df_final


# ──────────────────────────────────────────────────────────────────────────────
# Funções auxiliares
# ──────────────────────────────────────────────────────────────────────────────

def _mapear_estoque_csv(diretorio):
    """
    Lê o ESTOQUE.csv dentro do diretório informado e retorna:
        EAN (str) -> estoque total (float), somado por EAN (deduplicando lotes).

    Estrutura esperada (sem cabeçalho, separador ';'):
        [0]: CNPJ Filial
        [1]: EAN (Código de Barras)
        [2]: Estoque disponível
        [3]: Lote
    """
    padrao = os.path.join(diretorio, 'ESTOQUE*.csv')
    arquivos = sorted(glob.glob(padrao), key=os.path.getmtime, reverse=True)

    mapa = {}
    if not arquivos:
        return mapa

    caminho = arquivos[0]
    try:
        df = pd.read_csv(caminho, header=None, sep=';', dtype=str)
    except Exception as e:
        print(f"⚠️  Erro ao ler {caminho}: {e}")
        return mapa

    if df.empty or len(df.columns) < 3:
        return mapa

    df[1] = df[1].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df[2] = pd.to_numeric(df[2], errors='coerce').fillna(0)
    df[3] = df[3].astype(str).str.strip() if len(df.columns) > 3 else ''

    # Deduplica por EAN+Lote (mesmo critério do Col_estoque.py)
    if len(df.columns) > 3:
        df = df.drop_duplicates(subset=[1, 3], keep='first')

    mapa = df.groupby(1)[2].sum().to_dict()
    return mapa


def _buscar_csv_estoque_anterior():
    """
    Busca o ESTOQUE.csv de backup mais recente (excluindo o backup de hoje),
    retornando o caminho completo do arquivo.
    """
    dir_backups = os.path.join('imports', 'backups')
    padrao = os.path.join(dir_backups, '**', 'ESTOQUE*.csv')
    arquivos = glob.glob(padrao, recursive=True)

    hoje_str = datetime.now().strftime('%d-%m-%Y')
    arquivos_antigos = [f for f in arquivos if hoje_str not in f]

    if not arquivos_antigos:
        return None

    arquivos_antigos.sort(key=os.path.getmtime)
    return arquivos_antigos[-1]


def _carregar_datas_anteriores():
    """
    Lê o relatório XLSX mais recente da pasta output/ e retorna:
        EAN (str) -> Data Entrada (str)
    Usado para preservar datas históricas quando o estoque não aumentou.
    """
    mapa = {}
    padrao = os.path.join('output', '**', '*.xlsx')
    arquivos = glob.glob(padrao, recursive=True)
    arquivos = [f for f in arquivos if not os.path.basename(f).startswith('~$')]

    if not arquivos:
        return mapa

    arquivos.sort(key=os.path.getmtime)
    try:
        df = pd.read_excel(arquivos[-1])
        if 'EAN' in df.columns and 'Data Entrada' in df.columns:
            df['EAN'] = df['EAN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            mapa = dict(zip(df['EAN'], df['Data Entrada'].astype(str)))
    except Exception as e:
        print(f"⚠️  Erro ao ler XLSX anterior: {e}")

    return mapa


def _mapear_cfops_venda():
    """
    Lê o arquivo VENDA*.csv (da pasta imports/) e retorna:
        EAN (str) -> set de CFOPs (str)

    Estrutura esperada (sem cabeçalho, separador ';'):
        [0]: CFOP
        [6]: EAN (Código de Barras)
    """
    mapa = {}
    padrao = os.path.join('imports', 'VENDA*.csv')
    arquivos = sorted(glob.glob(padrao), key=os.path.getmtime, reverse=True)

    if not arquivos:
        print("⚠️  Arquivo de vendas não encontrado em imports/")
        return mapa

    try:
        df = pd.read_csv(arquivos[0], header=None, sep=';', dtype=str)
    except Exception as e:
        print(f"⚠️  Erro ao ler VENDA.csv: {e}")
        return mapa

    if df.empty or len(df.columns) < 7:
        return mapa

    for _, row in df.iterrows():
        try:
            cfop = str(row[0]).strip()
            ean  = str(row[6]).replace('.0', '').strip()
            if ean and cfop:
                mapa.setdefault(ean, set()).add(cfop)
        except Exception:
            pass

    return mapa