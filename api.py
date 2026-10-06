"""API REST do relatório consolidado gerado pela automação PLENA.

O endpoint /plena/imports/atuais publica o relatório mais recente em output/,
incluindo todas as suas colunas no JSON.
"""

import json
import os
import re
import secrets
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


BASE_DIR = Path(__file__).resolve().parent
IMPORTS_DIR = BASE_DIR / "imports"
OUTPUT_DIR = BASE_DIR / "output"
TOKEN_FILE = IMPORTS_DIR / ".api_token"
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

PADRAO_RELATORIO = re.compile(r"Plena_(\d{2})-(\d{2})-(\d{2})\.xlsx$", re.IGNORECASE)


def _token_configurado() -> str:
    """Lê o token persistido pelo servidor ou o token definido no .env."""
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip() or os.getenv("IMPORTS_API_TOKEN", "").strip()
    except OSError:
        return os.getenv("IMPORTS_API_TOKEN", "").strip()


def validar_token_bearer(
    credenciais: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    """Valida o token estático configurado em IMPORTS_API_TOKEN."""
    token_esperado = _token_configurado()
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


@app.post("/plena/auth/token", summary="Gerar token Bearer da PLENA")
def gerar_token_bearer(
    chave_provisionamento: str | None = Header(default=None, alias="X-Provision-Key"),
) -> dict[str, str]:
    """Gera e persiste um token mediante chave administrativa."""
    chave_esperada = os.getenv("IMPORTS_API_PROVISION_KEY", "").strip()
    if not chave_esperada:
        raise HTTPException(status_code=503, detail="IMPORTS_API_PROVISION_KEY não configurada.")
    if chave_provisionamento is None or not secrets.compare_digest(chave_provisionamento, chave_esperada):
        raise HTTPException(status_code=401, detail="Chave de provisionamento inválida.")

    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(48)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    return {"token_type": "Bearer", "access_token": token}


def _encontrar_relatorio_atual() -> Path:
    """Encontra o relatório de output com a data mais recente no nome."""
    relatorios = []
    for arquivo in OUTPUT_DIR.rglob("Plena_*.xlsx"):
        busca = PADRAO_RELATORIO.fullmatch(arquivo.name)
        if arquivo.is_file() and busca:
            dia, mes, ano = (int(parte) for parte in busca.groups())
            try:
                referencia = date(2000 + ano, mes, dia)
            except ValueError:
                continue
            relatorios.append((referencia, arquivo.stat().st_mtime, arquivo))
    if not relatorios:
        raise HTTPException(status_code=404, detail="Nenhum relatório foi encontrado em output/.")
    return max(relatorios, key=lambda item: (item[0], item[1]))[2]


def _valor_json(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (pd.Timestamp, datetime, date)):
        return valor.isoformat()
    if hasattr(valor, "item"):
        return valor.item()
    return valor


def _texto_coluna(valor) -> str:
    """Converte o valor da planilha em string limpa para o contrato."""
    texto = _valor_json(valor)
    if texto is None:
        return ""
    if isinstance(texto, float) and texto.is_integer():
        texto = int(texto)
    return str(texto).strip()


def _data_iso(valor) -> str:
    """Converte datas da planilha (Timestamp ou DD/MM/AAAA) para AAAA-MM-DD."""
    texto = _texto_coluna(valor)
    if not texto:
        return ""
    try:
        if isinstance(valor, (pd.Timestamp, datetime)):
            return valor.date().isoformat()
        if isinstance(valor, date):
            return valor.isoformat()
        return pd.to_datetime(texto, dayfirst=True).date().isoformat()
    except ValueError:
        return ""


def _data_dd_mm_aaaa(valor) -> str:
    """Formata uma data como DD/MM/AAAA para o JSON da API."""
    data_iso = _data_iso(valor)
    return date.fromisoformat(data_iso).strftime("%d/%m/%Y") if data_iso else ""


CAMPOS_VENDA_ANTIGOS = (
    "CFOP", "Saida_Codigo", "Saida_Data_Venda", "Saida_Numero_Nota",
    "Saida_Filial_Cnpj", "Saida_Quantidade", "Saida_Valor_Unitario",
    "Produto_Ean", "Vendedor_Codigo", "Vendedor_Nome", "Vendedor_Ativo",
    "Cliente_Codigo", "Cliente_Nome_Razao_Social", "Cliente_Cep", "UF", "Cidade",
)
CAMPOS_ESTOQUE_ANTIGOS = (
    "Filial_Cnpj", "Codigo_Barras", "Est_Disponivel", "Lote",
    "Data_Entrada", "Data_Vencimento", "Preco_Custo",
)


def _ler_relatorio(arquivo: Path) -> list[dict]:
    """Lê todas as linhas e colunas do relatório consolidado de output/."""
    try:
        dataframe = pd.read_excel(arquivo, dtype=object)
    except Exception as erro:
        raise HTTPException(
            status_code=422,
            detail=f"Não foi possível ler o relatório {arquivo.name}: {erro}",
        ) from erro
    dataframe = dataframe.dropna(axis=0, how="all")
    if dataframe.empty:
        raise HTTPException(status_code=422, detail="O relatório de output não contém registros.")
    if "EAN" not in dataframe.columns or "Estoque" not in dataframe.columns:
        raise HTTPException(status_code=422, detail="O relatório de output precisa das colunas EAN e Estoque.")

    registros = []
    for linha in dataframe.to_dict(orient="records"):
        registro = {coluna: _valor_json(valor) for coluna, valor in linha.items()}
        registro["EAN"] = _texto_coluna(linha["EAN"])
        for coluna in ("Data Entrada", "Data Validade"):
            if coluna in registro:
                registro[coluna] = _data_dd_mm_aaaa(linha[coluna]) or None
        registros.append(registro)
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
    registros = _ler_relatorio(_encontrar_relatorio_atual())
    vendas = [{**linha, **dict.fromkeys(CAMPOS_VENDA_ANTIGOS, "")} for linha in registros]
    estoque = [
        {"EAN": linha["EAN"], "Estoque": linha["Estoque"],
         **dict.fromkeys(CAMPOS_ESTOQUE_ANTIGOS, "")}
        for linha in registros
    ]

    return {
        "METAS": [],
        "VENDAS": vendas,
        "VENDEDORES": [],
        "ESTOQUE": estoque,
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
