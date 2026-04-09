import requests
import urllib3
from config.settings import Settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obter_sessao_autenticada():
    
    #Faz o login e retorna um objeto de sessão com os cookies salvos.
    
    session = requests.Session()
    session.verify = False # Desabilita SSL para local mudar em produção
    
    try:
        print("Autenticando na conta")
        payload = {"email": Settings.API_EMAIL, "senha": Settings.API_PASS}
        
        response = session.post(Settings.LOGIN_URL, json=payload, timeout=Settings.NETWORK_TIMEOUT)
        
        if response.status_code == 200:
            print(f"Login realizado como: {response.json().get('nome')}")
            return session
        else:
            print(f"Falha no login: {response.status_code}")
            return None
    except Exception as e:
        print(f"Erro na conexão de login: {e}")
        return None
        print(f"Erro ao conectar ao serviço de autenticação: {e}")
    
    return None