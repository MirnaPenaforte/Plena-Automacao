import pandas as pd
import os
import glob
import shutil
from datetime import datetime
from utils.controler_import import MESES_PT, limpar_backups_antigos

def storage_output(diretorio_saida):
    """
    Mantém os arquivos organizados por Mês/Dia na pasta output.
    """
    try:
        hoje = datetime.now()
        mes_str = f"{hoje.month:02d}_{MESES_PT[hoje.month]}_{hoje.year}"
        dia_str = hoje.strftime('%d-%m-%Y')
        
        dir_mes = os.path.join(diretorio_saida, mes_str)
        dir_dia = os.path.join(dir_mes, dia_str)
        os.makedirs(dir_dia, exist_ok=True)
        
        # Mover os .xlsx soltos para a pasta de backup do dia
        padrao = os.path.join(diretorio_saida, "*.xlsx")
        for arquivo in glob.glob(padrao):
            shutil.move(arquivo, os.path.join(dir_dia, os.path.basename(arquivo)))
            print(f"📦 Relatório organizado: {os.path.basename(arquivo)} em {mes_str}/{dia_str}")

        # Aproveitamos a mesma função inteligente do controlador de importações
        limpar_backups_antigos(diretorio_saida, hoje)
                
    except Exception as e:
        print(f"❌ Erro ao organizar armazenamento dos relatórios: {e}")

def gerar_relatorio_vendas(df_consolidado):
    """
    Gera o relatório com a data de hoje no formato dd-mm-aa e organiza/limpa pastas.
    """
    diretorio_saida = 'output'
    
    # Adiciona a data no formato (dd/mm/aa convertido para hífens para nomes de arquivos)
    timestamp = datetime.now().strftime('%d-%m-%y')
    nome_arquivo = f"Plena_{timestamp}.xlsx"
    
    caminho_final = os.path.join(diretorio_saida, nome_arquivo)
    
    try:
        if not os.path.exists(diretorio_saida):
            os.makedirs(diretorio_saida)

        # Colunas que sempre sobem vazias para manter o formato do cliente
        colunas_vazias = ['Descrição', 'Transito', 'Pendencia', 'Mês -2', 'Mês -3']
        for col in colunas_vazias:
            df_consolidado[col] = ""

        ordem_exata = [
            'EAN', 'Descrição', 'Data Entrada', 'Data Validade', 'Mês -3',
            'Mês -2', 'Mês -1', 'Mês Atual', 'Estoque', 'Faturamento Atual', 
            'Faturamento M-1', 'Preço Custo', 'Transito', 'Pendencia'
        ]

        df_final = df_consolidado[ordem_exata]
        df_final.to_excel(caminho_final, index=False, engine='openpyxl')
        print(f"✅ Relatório gerado: {nome_arquivo}")

        # --- CHAMADA DA FUNÇÃO DE ARMAZENAMENTO E LIMPEZA ---
        storage_output(diretorio_saida)

        return True

    except Exception as e:
        print(f"❌ Erro ao exportar: {e}")
        return False