import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    # --- Configurações de Autenticação ---
    # Pegamos do .env para segurança
    API_EMAIL = os.getenv("API_EMAIL")
    API_PASS = os.getenv("API_PASS")
    
    # Endpoints
    BASE_URL = os.getenv("BASE_URL")

    if not BASE_URL:
        raise ValueError("ERROR CRÍTICO: BASE_URL não encontrada no ambiente")
    
    LOGIN_URL = f"{BASE_URL}/api/conta/login"
    VENDAS_URL = f"{BASE_URL}/api/import/vendas"

    # --- IDs e Campos Fixos ---
    DISTRIBUIDOR_ID = os.getenv("DISTRIBUIDOR_ID")
    REPRESENTANTE_ID = os.getenv("REPRESENTANTE_ID")
    FIELD_ARQUIVO = "arquivo"
    FIELD_DISTRIBUIDOR = "distribuidorId"
    FIELD_REPRESENTANTE = "representanteId"

    # --- Caminhos ---
    IMPORTS_DIR = BASE_DIR / "imports"
    OUTPUT_DIR = BASE_DIR / "output"
    NETWORK_TIMEOUT = 60

    # --- Configurações de E-mail (Gmail) ---
    GMAIL_USER = os.getenv("GMAIL_USER")
    GMAIL_PASS = os.getenv("GMAIL_PASS")
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
    TERMO_BUSCA_IMAP = os.getenv("TERMO_BUSCA_IMAP")

    # --- Configurações de Armazenamento ---
    # Limite de arquivos para manter nas pastas (conforme sua solicitação)
    MAX_FILES_RETAINED = 3

    @classmethod
    def create_dirs(cls):
        cls.IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

Settings.create_dirs()