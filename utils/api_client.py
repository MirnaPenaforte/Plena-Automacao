import os
import glob
import requests
from config.settings import Settings
from config.token import obter_sessao_autenticada

def obter_ultimo_relatorio(diretorio_output="output") -> str:
    """Retorna o caminho do arquivo mais recente na pasta de output."""
    if not os.path.exists(diretorio_output):
        print(f"Erro: O diretório '{diretorio_output}' não existe.")
        return None
        
    arquivos = glob.glob(os.path.join(diretorio_output, "**", "*.xlsx"), recursive=True)
    if not arquivos:
        print(f"Erro: Nenhum arquivo .xlsx encontrado no diretório '{diretorio_output}'.")
        return None
        
    # Ordena os arquivos pela data de modificação (o mais recente por último)
    arquivos.sort(key=os.path.getmtime)
    ultimo_arquivo = arquivos[-1]
    return ultimo_arquivo

def enviar_relatorio_api(caminho_arquivo: str) -> bool:
    """Envia o arquivo de relatório para a API usando uma sessão autenticada."""
    if not os.path.isfile(caminho_arquivo):
        print(f"Erro: O arquivo não foi encontrado em {caminho_arquivo}")
        return False

    session = obter_sessao_autenticada()
    if not session:
        print("Erro: Não foi possível obter uma sessão autenticada.")
        return False

    try:
        payload = {
            Settings.FIELD_DISTRIBUIDOR: Settings.DISTRIBUIDOR_ID,
            Settings.FIELD_REPRESENTANTE: Settings.REPRESENTANTE_ID
        }

        nome_ficheiro = os.path.basename(caminho_arquivo)

        with open(caminho_arquivo, 'rb') as f:
            ficheiros = {
                Settings.FIELD_ARQUIVO: (
                    nome_ficheiro, 
                    f, 
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            }

            print(f"Enviando arquivo: {nome_ficheiro} ...")
            
            response = session.post(
                Settings.VENDAS_URL,
                data=payload,
                files=ficheiros,
                timeout=Settings.NETWORK_TIMEOUT
            )

            if response.status_code in [200, 201, 207]:
                print(f"Sucesso: API processou o arquivo.")
                return True
            else:
                print(f"Erro no Upload ({response.status_code}): {response.text}")
                return False

    except requests.exceptions.Timeout:
        print("Erro técnico: O envio excedeu o tempo limite (Timeout).")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão com a API: {e}")
        return False
    except Exception as e:
        print(f"Erro técnico inesperado: {e}")
        return False

def enviar_ultimo_relatorio():
    """Busca o último relatório na pasta output e faz o envio para a API."""
    ultimo_arquivo = obter_ultimo_relatorio()
    if ultimo_arquivo:
        return enviar_relatorio_api(ultimo_arquivo)
    return False