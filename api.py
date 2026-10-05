"""API REST do relatório consolidado gerado pela automação PLENA.

O endpoint /plena/imports/atuais publica, a partir dos imports arquivados em
imports/backups, o par de arquivos de vendas e estoque mais recente (pela data
no nome dos arquivos). Cada registro mantém os nomes das colunas dos Excel de
origem e é identificado pelo campo EAN.
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
BACKUP_DIR = IMPORTS_DIR / "backups"
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

MARCADOR_VENDAS = "_relatorio_vendas_"
MARCADOR_ESTOQUE = "_mapa_estoque_"
SUFIXO_BACKUP = re.compile(r"_\d{2}-\d{2}-\d{4}_\d{2}h\d{2}m\.xlsx$")


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


def _data_referencia(nome_arquivo: str) -> tuple[int, int, int]:
    """Extrai a data de referência embutida no nome do import (ano, mês, dia)."""
    busca = re.search(r"(\d{2})-(\d{2})-(\d{4})", nome_arquivo)
    if not busca:
        return (0, 0, 0)
    dia, mes, ano = (int(parte) for parte in busca.groups())
    return (ano, mes, dia)


def _ultimo_par_de_imports() -> tuple[Path, Path] | None:
    """Encontra, nos backups, o par de imports (vendas + estoque) mais recente.

    O agrupamento usa o nome do arquivo com o marcador substituído por
    `_data_` e a data de referência embutida, no formato DD-MM-AAAA,
    garantindo que vendas e estoque sejam o par correspondente do mesmo
    distribuidor.
    """
    grupos: dict[tuple[str, tuple[int, int, int]], dict[str, Path]] = {}
    for arquivo in BACKUP_DIR.rglob("*.xlsx"):
        if not arquivo.is_file():
            continue
        nome = SUFIXO_BACKUP.sub("", arquivo.name.lower())
        if MARCADOR_VENDAS in nome:
            tipo, marcador = "vendas", MARCADOR_VENDAS
        elif MARCADOR_ESTOQUE in nome:
            tipo, marcador = "estoque", MARCADOR_ESTOQUE
        else:
            continue
        chave = (nome.replace(marcador, "_data_", 1), _data_referencia(nome))
        grupos.setdefault(chave, {})[tipo] = arquivo

    pares = [(chave, grupo) for chave, grupo in grupos.items()
             if "vendas" in grupo and "estoque" in grupo]
    if not pares:
        return None
    chave, par = max(pares, key=lambda item: item[0][1])
    return par["vendas"], par["estoque"]


def _encontrar_relatorio_atual() -> tuple[Path, Path]:
    par = _ultimo_par_de_imports()
    if par is None:
        raise HTTPException(
            status_code=404,
            detail="Nenhum par de imports (vendas + estoque) foi encontrado em imports/backups.",
        )
    return par


CFOP_VENDA = "5102"
CFOP_DEVOLUCAO = "6202"


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
        if isinstance(valor, (pd.Timestamp, datetime, date)):
            return valor.date().isoformat()
        return pd.to_datetime(texto, dayfirst=True).date().isoformat()
    except ValueError:
        return ""


def _data_dd_mm_aaaa(valor) -> str:
    """Formata uma data como DD-MM_AAAA para o JSON da API."""
    data_iso = _data_iso(valor)
    return date.fromisoformat(data_iso).strftime("%d-%m_%Y") if data_iso else ""


def _numero_decimal(valor) -> float | int | None:
    texto = _texto_coluna(valor)
    if not texto:
        return None
    try:
        numero = round(float(texto.replace(",", ".")), 2)
    except ValueError:
        return None
    if numero.is_integer():
        return int(numero)
    return numero


def _registro_venda(linha: dict) -> dict:
    """Mapeia uma linha do import de vendas para o contrato Saida_*."""
    quantidade = _numero_decimal(linha.get("QTD_VENDIDA"))
    valor = _numero_decimal(linha.get("VALOR_LIQUIDO"))

    unitario = None
    if quantidade and valor is not None and quantidade != 0:
        unitario = round(valor / quantidade, 2)

    operacao = _texto_coluna(linha.get("OPERACAO")).upper()
    cfop = CFOP_VENDA if operacao == "VENDA" else CFOP_DEVOLUCAO

    return {
        "CFOP": cfop,
        "Saida_Codigo": _texto_coluna(linha.get("COD_PRODUTO")),
        "Saida_Data_Venda": _data_dd_mm_aaaa(linha.get("DATA_FATURAMENTO")),
        "Saida_Numero_Nota": "NF-" + _texto_coluna(linha.get("NF")),
        "Saida_Filial_Cnpj": "",
        "Saida_Quantidade": quantidade,
        "Saida_Valor_Unitario": unitario,
        "Produto_Ean": _texto_coluna(linha.get("COD_EAN")),
        "Vendedor_Codigo": _texto_coluna(linha.get("COD_VENDEDOR")),
        "Vendedor_Nome": _texto_coluna(linha.get("VENDEDOR")),
        "Vendedor_Ativo": True,
        "Cliente_Codigo": "",
        "Cliente_Nome_Razao_Social": "",
        "Cliente_Cep": "",
        "UF": _texto_coluna(linha.get("EMPRESA")),
        "Cidade": "",
    }


def _registro_estoque(linha: dict) -> dict:
    """Mapeia uma linha do mapa de estoque para o contrato de estoque."""
    return {
        "Filial_Cnpj": "",
        "Codigo_Barras": _texto_coluna(linha.get("EAN")),
        "Est_Disponivel": _numero_decimal(linha.get("ESTOQUE")),
        "Lote": "",
        "Data_Entrada": _data_dd_mm_aaaa(linha.get("ULT.ENTRADA")),
        "Data_Vencimento": "",
        "Preco_Custo": _numero_decimal(linha.get("PREÇO_COMPRA")),
    }


def _registros_vendedores(linhas: list[dict]) -> list[dict]:
    """Deriva do import de vendas a lista deduplicada de vendedores."""
    vendedores = {}
    for linha in linhas:
        codigo = _texto_coluna(linha.get("COD_VENDEDOR"))
        nome = _texto_coluna(linha.get("VENDEDOR"))
        chave = (codigo, nome)
        if chave in vendedores:
            continue
        vendedores[chave] = {
            "Vendedor_Codigo": codigo,
            "Vendedor_Nome": nome,
            "Vendedor_Ativo": True,
            "CPF": "",
            "Telefone": "",
            "Grupo": _texto_coluna(linha.get("SUPERVISAO")),
        }
    return list(vendedores.values())


def _ler_excel(arquivo: Path) -> list[dict]:
    """Lê todas as abas não vazias do import e retorna as linhas em dicionários."""
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
        registros.extend(dataframe.to_dict(orient="records"))
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


def _linhas_estoque_por_ean(arquivo: Path) -> list[dict]:
    """Agrupa o mapa de estoque por EAN e mantém a linha com estoque > 0.

    Cada produto aparece uma vez por filial; uma delas vem com estoque zerado,
    então escolhemos a linha cujo estoque seja positivo.
    """
    linhas = {}
    for linha in _ler_excel(arquivo):
        ean = _texto_coluna(linha.get("EAN"))
        if not ean:
            continue
        estoque = _numero_decimal(linha.get("ESTOQUE")) or 0
        atual = linhas.get(ean)
        if atual is None:
            linhas[ean] = linha
        elif estoque > (_numero_decimal(atual.get("ESTOQUE")) or 0):
            linhas[ean] = linha
    return [linhas[ean] for ean in linhas]


def _tabelas_atuais() -> dict[str, list[dict]]:
    arquivo_vendas, arquivo_estoque = _encontrar_relatorio_atual()
    linhas_vendas = _ler_excel(arquivo_vendas)
    vendas = [_registro_venda(linha) for linha in linhas_vendas]
    estoque = [_registro_estoque(linha) for linha in _linhas_estoque_por_ean(arquivo_estoque)]

    if not vendas and not estoque:
        raise HTTPException(
            status_code=422,
            detail="Os arquivos de import não contêm registros.",
        )

    return {
        "METAS": [],
        "VENDAS": vendas,
        "VENDEDORES": _registros_vendedores(linhas_vendas),
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
