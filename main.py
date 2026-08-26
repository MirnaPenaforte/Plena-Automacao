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
            
            # Vendas e estoque chegam em arquivos independentes. Entradas não
            # participa do processamento desta automação.
            todos_arquivos = glob.glob(os.path.join('imports', '*.xlsx'))
            grupos = {}
            for caminho in todos_arquivos:
                nome = os.path.basename(caminho)
                nome_lower = nome.lower()

                if '_mapa_estoque_' in nome_lower:
                    tipo = 'estoque'
                    marcador = '_mapa_estoque_'
                elif '_relatorio_vendas_' in nome_lower:
                    tipo = 'vendas'
                    marcador = '_relatorio_vendas_'
                else:
                    continue

                chave = nome_lower.replace(marcador, '_data_', 1)
                grupos.setdefault(chave, {})[tipo] = caminho

            novos_arquivos = [
                grupo for grupo in grupos.values()
                if 'vendas' in grupo and 'estoque' in grupo
            ]

            if novos_arquivos:
                print(f"🔔 {len(novos_arquivos) * 2} arquivo(s) detectado(s). Iniciando processamento...")

                for grupo in novos_arquivos:
                    processar_arquivos(grupo['vendas'], grupo['estoque'])
                
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




def processar_arquivos(path_vendas, path_estoque):
    """
    Versão refatorada do fluxo original para processar um arquivo específico.
    """
    diretorio_imports = 'imports'
    print(
        f"\n--- ⚙️ Processando: {os.path.basename(path_vendas)} + "
        f"{os.path.basename(path_estoque)} ---"
    )

    df_vendas_bruto = ler_planilha_excel(path_vendas)
    df_estoque_bruto = ler_planilha_excel(path_estoque)

    if df_vendas_bruto is not None and df_estoque_bruto is not None:
        print("✅ Dados carregados com sucesso dos arquivos de vendas e estoque.")

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

            df_final = preencher_data_entrada(df_final, df_estoque_bruto.copy())

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
            for path in (path_vendas, path_estoque):
                if os.path.exists(path):
                    os.remove(path)
                    print(f"🗑️ Arquivo original removido: {os.path.basename(path)}")
    else:
        print(
            f"❌ Erro fatal: Falha ao carregar os arquivos "
            f"{path_vendas} e/ou {path_estoque}"
        )

if __name__ == "__main__":
    main()