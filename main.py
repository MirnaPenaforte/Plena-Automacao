import os
import time
import glob
import pandas as pd
from core.read_excel import ler_planilha_excel
from core.Col_estoque import processar_estoque_agrupado
from core.Col_data_validade import processar_validade_estoque
from core.Col_Custo import extrair_preco_custo
from core.Col_Mes_atual import agrupar_vendas
from core.Col_faturamento_total import calcular_faturamento_atual
from core.Col_data_entrada import preencher_data_entrada
from utils.exporter_excel import gerar_relatorio_vendas 
from utils.controler_import import arquivar_arquivos_importacao
from utils.gmail_client import buscar_arquivos_email
from utils.api_client import enviar_ultimo_relatorio

def main():
    print("🚀 Automação ligada em modo MONITORAMENTO.")
    print("Verificando novos e-mails a cada 1 minuto (se ocioso)...")
    
    while True:
        try:
            # Busca de e-mails
            buscar_arquivos_email()
            
            # Busca arquivos diretamente na pasta 'imports'
            novos_arquivos = glob.glob(os.path.join('imports', '*.xlsx'))
            
            if novos_arquivos:
                print(f"🔔 {len(novos_arquivos)} arquivo(s) detectado(s). Iniciando processamento...")
                
                for path_excel in novos_arquivos:
                    processar_arquivo(path_excel)
                
                # Se achou e processou, recomeça o ciclo imediatamente para pegar outros possíveis e-mails novos
                print("🔄 Arquivos processados. Retornando imediatamente para nova busca...")
                continue
            
            # Se não achou nada, aguarda 1 minuto para buscar novamente
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n🛑 Automação encerrada pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro na execução principal: {e}")
            time.sleep(60)




def processar_arquivo(path_excel):
    """
    Versão refatorada do fluxo original para processar um arquivo específico.
    """
    diretorio_imports = 'imports'
    print(f"\n--- ⚙️ Processando: {os.path.basename(path_excel)} ---")

    df_vendas_bruto = ler_planilha_excel(path_excel, 'Vendas_Dev')
    df_estoque_bruto = ler_planilha_excel(path_excel, 'Estoque')

    if df_vendas_bruto is not None and df_estoque_bruto is not None:
        print("✅ Dados carregados com sucesso das abas 'Vendas_Dev' e 'Estoque'.")

        # --- BACKUP E LIMPEZA ---
        # Arquiva apenas o arquivo que estamos processando no momento ou a pasta toda
        # O arquivamento original move todos os arquivos da pasta 'imports' para 'logs/imports_archive'
        arquivar_arquivos_importacao(diretorio_imports)

        # --- PROCESSAMENTOS ---
        estoque_final = processar_estoque_agrupado(df_estoque_bruto.copy())
        custo_final = extrair_preco_custo(df_estoque_bruto.copy()) 
        validade_final = processar_validade_estoque(df_estoque_bruto.copy())
        
        vendas_final = agrupar_vendas(df_vendas_bruto.copy())
        faturamento_final = calcular_faturamento_atual(df_vendas_bruto.copy())

        # --- CONSOLIDAÇÃO FINAL ---
        try:
            df_final = pd.merge(estoque_final, custo_final, on='EAN', how='outer')
            df_final = pd.merge(df_final, validade_final, on='EAN', how='outer')
            df_final = pd.merge(df_final, vendas_final, on='EAN', how='outer')
            df_final = pd.merge(df_final, faturamento_final, on='EAN', how='outer')

            df_final = preencher_data_entrada(df_final)

            colunas_numericas = ['Estoque', 'Mês Atual', 'Mês -1']
            df_final[colunas_numericas] = df_final[colunas_numericas].fillna(0).astype(int)
            
            # Faturamento Atual e M-1: Float com 2 casas
            df_final['Faturamento Atual'] = df_final['Faturamento Atual'].fillna(0.0).astype(float).round(2)
            df_final['Faturamento M-1'] = df_final['Faturamento M-1'].fillna(0.0).astype(float).round(2)
            
            # Preço Custo: Float, mas se zero, usar 0.001
            df_final['Preço Custo'] = df_final['Preço Custo'].fillna(0.0).astype(float)
            estoque_zero = (df_final['Estoque'] == 0) | (df_final['Preço Custo'] == 0.0)
            df_final.loc[estoque_zero, 'Preço Custo'] = 0.001
            
            # Arredondar os demais para 2 casas
            df_final['Preço Custo'] = df_final['Preço Custo'].round(3) # 3 casas para garantir o 0.001


            # --- EXPORTAÇÃO ---
            gerar_relatorio_vendas(df_final)
            print("--- Relatório gerado com sucesso. ---")
            
            # --- ENVIO PARA API ---
            print("🚀 Enviando para a API...")
            sucesso_envio = enviar_ultimo_relatorio()
            if sucesso_envio:
                print("✅ Sucesso no envio!")
            else:
                print("❌ Falha no envio.")
            
        except Exception as e:
            print(f"❌ Erro crítico no processamento final: {e}")
        finally:
            # Garante que o arquivo seja removido após o processamento (já está no backup)
            if os.path.exists(path_excel):
                os.remove(path_excel)
                print(f"🗑️ Arquivo original removido: {os.path.basename(path_excel)}")
    else:
        print(f"❌ Erro fatal: Falha ao carregar os dados de {path_excel}")
        if os.path.exists(path_excel):
            os.remove(path_excel)

if __name__ == "__main__":
    main()