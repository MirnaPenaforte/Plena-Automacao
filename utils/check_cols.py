import pandas as pd
path = 'imports/AGAPLASTIC_PE1_2026-03-28.xlsx'
print("Estoque:", pd.read_excel(path, sheet_name='Estoque').columns.tolist())
print("Vendas:", pd.read_excel(path, sheet_name='Vendas_Dev').columns.tolist())
