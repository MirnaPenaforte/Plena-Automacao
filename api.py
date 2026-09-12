"""API REST dos dados recebidos pela automação PLENA.

Mantém o mesmo contrato da API da NOVA: /imports/atuais retorna um objeto
com as categorias METAS, VENDAS, VENDEDORES e ESTOQUE. A PLENA recebe apenas
os dois relatórios por e-mail, portanto as categorias inexistentes retornam
listas vazias.
"""

import json
import os
import secrets
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


BASE_DIR = Path(__file__).resolve().parent
IMPORTS_DIR = BASE_DIR / "imports"
load_dotenv(BASE_DIR / ".env")

bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(
    title="PLENA Automação - Imports",
    description="Disponibiliza em JSON os relatórios recebidos por e-mail.",
    version="1.0.0",
)

# Rota fixa da automação PLENA. A diferenciação entre NOVA, PLENA RN e PLENA
# PE é feita pelo endpoint; a porta segue o mesmo padrão da NOVA.
API_PREFIX = "/plena"

# Os nomes refletem o modelo dos anexos baixados por utils.gmail_client.
PADROES_ANEXOS = {
    "VENDAS": "*_relatorio_vendas_*.xlsx",
    "ESTOQUE": "*_mapa_estoque_*.xlsx",
}


def validar_token_bearer(
    credenciais: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    """Valida o token estático configurado em IMPORTS_API_TOKEN."""
    token_esperado = os.getenv("IMPORTS_API_TOKEN", "").strip()
    if not token_esperado:
        raise HTTPException(status_code=503, detail="Token de acesso da API não configurado.")
    if (
        credenciais is None
        or credenciais.scheme.lower() != "bearer"
        or not secrets.compare_digest(credenciais.credentials, token_esperado)
    ):
        raise HTTPException(
            status_code=401,
            detail="Token Bearer ausente ou inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _ultimo_anexo(padrao: str) -> Path | None:
    """Encontra o anexo mais recente, inclusive dentro de imports/backups."""
    arquivos = [arquivo for arquivo in IMPORTS_DIR.rglob(padrao) if arquivo.is_file()]
    return max(arquivos, key=lambda arquivo: arquivo.stat().st_mtime, default=None)


def _encontrar_anexos_atuais() -> dict[str, Path]:
    encontrados = {
        categoria: _ultimo_anexo(padrao)
        for categoria, padrao in PADROES_ANEXOS.items()
    }
    ausentes = [categoria for categoria, arquivo in encontrados.items() if arquivo is None]
    if ausentes:
        raise HTTPException(
            status_code=404,
            detail=f"Não foram encontrados os anexos atuais: {', '.join(ausentes)}.",
        )
    return {categoria: arquivo for categoria, arquivo in encontrados.items() if arquivo}


def _valor_json(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (pd.Timestamp, datetime, date)):
        return valor.isoformat()
    if hasattr(valor, "item"):
        return valor.item()
    return valor


def _ler_excel(arquivo: Path) -> list[dict]:
    """Lê todas as abas não vazias do anexo e forma uma lista de objetos."""
    try:
        abas = pd.read_excel(arquivo, sheet_name=None, dtype=object)
    except Exception as erro:
        raise HTTPException(
            status_code=422,
            detail=f"Não foi possível ler o anexo {arquivo.name}: {erro}",
        ) from erro

    registros = []
    for dataframe in abas.values():
        dataframe = dataframe.dropna(axis=0, how="all").dropna(axis=1, how="all")
        if dataframe.empty:
            continue
        dataframe.columns = [str(coluna).strip() or f"coluna_{indice + 1}"
                             for indice, coluna in enumerate(dataframe.columns)]
        for registro in dataframe.to_dict(orient="records"):
            registros.append({chave: _valor_json(valor) for chave, valor in registro.items()})
    return registros


def _gerar_json(tabelas: dict[str, list[dict]]) -> Iterator[str]:
    """Serializa o contrato da NOVA em blocos para não acumular texto."""
    yield "{"
    for indice, (categoria, registros) in enumerate(tabelas.items()):
        if indice:
            yield ","
        yield json.dumps(categoria, ensure_ascii=False) + ":["
        for indice_registro, registro in enumerate(registros):
            if indice_registro:
                yield ","
            yield json.dumps(registro, ensure_ascii=False, separators=(",", ":"))
        yield "]"
    yield "}"


def _tabelas_atuais() -> dict[str, list[dict]]:
    anexos = _encontrar_anexos_atuais()
    return {
        "METAS": [],
        "VENDAS": _ler_excel(anexos["VENDAS"]),
        "VENDEDORES": [],
        "ESTOQUE": _ler_excel(anexos["ESTOQUE"]),
    }


@app.get(f"{API_PREFIX}/imports/atuais", summary="Consultar os imports atuais em JSON")
def consultar_imports_atuais(
    _: None = Security(validar_token_bearer),
) -> StreamingResponse:
    return StreamingResponse(
        _gerar_json(_tabelas_atuais()),
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
