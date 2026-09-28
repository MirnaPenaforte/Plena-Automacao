import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import api

EXEMPLOS_DIR = Path(__file__).resolve().parent / "Exemplos"
VENDAS_EXEMPLO = EXEMPLOS_DIR / "MCG_PE_relatorio_vendas_2026-09-26.xlsx"
ESTOQUE_EXEMPLO = EXEMPLOS_DIR / "MCG_PE_mapa_estoque_2026-09-26.xlsx"
VENDAS_OUTRO_DISTRIBUIDOR = EXEMPLOS_DIR / "AGAPLASTIC_PE_relatorio_vendas_2026-09-26.xlsx"


def _copiar_exemplos(destino: Path):
    backups = destino / "09_Setembro_2026" / "26-09-2026"
    backups.mkdir(parents=True)
    if VENDAS_EXEMPLO.exists():
        (backups / VENDAS_EXEMPLO.name).write_bytes(VENDAS_EXEMPLO.read_bytes())
    if ESTOQUE_EXEMPLO.exists():
        (backups / ESTOQUE_EXEMPLO.name).write_bytes(ESTOQUE_EXEMPLO.read_bytes())
    if VENDAS_OUTRO_DISTRIBUIDOR.exists():
        (backups / VENDAS_OUTRO_DISTRIBUIDOR.name).write_bytes(VENDAS_OUTRO_DISTRIBUIDOR.read_bytes())
    return backups


class ApiJsonTests(unittest.TestCase):
    def test_rota_da_plena_e_distinta(self):
        rotas = {rota.path for rota in api.app.routes}
        self.assertIn("/plena/imports/atuais", rotas)
        self.assertNotIn("/plena/imports/atuais.zip", rotas)
        self.assertIn("/plena/auth/token", rotas)

    @unittest.skipUnless(VENDAS_EXEMPLO.exists() and ESTOQUE_EXEMPLO.exists(),
                         "planilhas de exemplo ausentes")
    def test_exemplos_reais_geram_contrato_completo(self):
        with tempfile.TemporaryDirectory() as pasta:
            _copiar_exemplos(Path(pasta))
            with patch.object(api, "BACKUP_DIR", Path(pasta)):
                resultado = json.loads("".join(api._gerar_json(api._tabelas_atuais())))

        self.assertEqual(list(resultado), ["METAS", "VENDAS", "VENDEDORES", "ESTOQUE"])
        self.assertEqual(resultado["METAS"], [])

        # vendas do AGAPLASTIC (sem estoque correspondente) ficam de fora do par
        self.assertEqual(len(resultado["VENDAS"]), 1284)

        venda = resultado["VENDAS"][0]
        self.assertEqual(
            list(venda),
            [
                "CFOP", "Saida_Codigo", "Saida_Data_Venda", "Saida_Numero_Nota",
                "Saida_Filial_Cnpj", "Saida_Quantidade", "Saida_Valor_Unitario",
                "Produto_Ean", "Vendedor_Codigo", "Vendedor_Nome", "Vendedor_Ativo",
                "Cliente_Codigo", "Cliente_Nome_Razao_Social", "Cliente_Cep",
                "UF", "Cidade",
            ],
        )
        self.assertIn(venda["CFOP"], (api.CFOP_VENDA, api.CFOP_DEVOLUCAO))
        self.assertEqual(venda["UF"], "PE")
        self.assertTrue(venda["Vendedor_Ativo"])
        self.assertEqual(venda["Saida_Filial_Cnpj"], "")
        self.assertTrue(all(venda[campo] == "" for campo in
                            ("Cliente_Codigo", "Cliente_Nome_Razao_Social", "Cliente_Cep", "Cidade")))

        vendedor = resultado["VENDEDORES"][0]
        self.assertEqual(
            list(vendedor),
            ["Vendedor_Codigo", "Vendedor_Nome", "Vendedor_Ativo", "CPF",
             "Telefone", "Grupo"],
        )
        self.assertTrue(all(v["Vendedor_Ativo"] for v in resultado["VENDEDORES"]))
        codigos = [v["Vendedor_Codigo"] for v in resultado["VENDEDORES"]]
        self.assertEqual(len(codigos), len(set(codigos)))

        estoque = resultado["ESTOQUE"][0]
        self.assertEqual(
            list(estoque),
            ["Filial_Cnpj", "Codigo_Barras", "Est_Disponivel", "Lote",
             "Data_Entrada", "Data_Vencimento", "Preco_Custo"],
        )
        self.assertEqual(estoque["Filial_Cnpj"], "")
        self.assertEqual(estoque["Lote"], "")
        self.assertEqual(estoque["Data_Vencimento"], "")

    @unittest.skipUnless(ESTOQUE_EXEMPLO.exists(), "planilha de exemplo ausente")
    def test_estoque_deduplicado_pega_linha_com_estoque_positivo(self):
        if not ESTOQUE_EXEMPLO.exists():
            self.skipTest("planilha de exemplo ausente")

        linhas_por_ean = {}
        for linha in api._ler_excel(ESTOQUE_EXEMPLO):
            linhas_por_ean.setdefault(api._texto_coluna(linha["EAN"]), []).append(linha)

        com_duplicidade = {
            ean: grupo for ean, grupo in linhas_por_ean.items() if len(grupo) > 1
        }
        self.assertTrue(com_duplicidade)

        escolhidas = {
            api._texto_coluna(l["EAN"]): l
            for l in api._linhas_estoque_por_ean(ESTOQUE_EXEMPLO)
        }
        for ean, grupo in com_duplicidade.items():
            escolhida = escolhidas[ean]
            maior = max((api._numero_decimal(l["ESTOQUE"]) or 0) for l in grupo)
            esperado = next(l for l in grupo if (api._numero_decimal(l["ESTOQUE"]) or 0) == maior)
            self.assertEqual(escolhida, esperado)

    def test_mapeamento_manual_sem_exemplos(self):
        venda = api._registro_venda({
            "OPERACAO": "VENDA",
            "COD_PRODUTO": 123,
            "DATA_FATURAMENTO": "01/09/2026",
            "NF": 456,
            "QTD_VENDIDA": 2,
            "VALOR_LIQUIDO": 39.80,
            "COD_EAN": "7891234567890",
            "COD_VENDEDOR": 1,
            "VENDEDOR": "Ana Souza",
            "EMPRESA": "PE",
        })
        self.assertEqual(venda["CFOP"], api.CFOP_VENDA)
        self.assertEqual(venda["Saida_Codigo"], "123")
        self.assertEqual(venda["Saida_Data_Venda"], "2026-09-01")
        self.assertEqual(venda["Saida_Numero_Nota"], "NF-456")
        self.assertEqual(venda["Saida_Quantidade"], 2)
        self.assertEqual(venda["Saida_Valor_Unitario"], 19.9)
        self.assertEqual(venda["Produto_Ean"], "7891234567890")
        self.assertEqual(venda["Vendedor_Codigo"], "1")
        self.assertEqual(venda["UF"], "PE")

        devolucao = api._registro_venda({
            "OPERACAO": "DEVOLUCAO",
            "DATA_FATURAMENTO": "2026-09-02",
            "NF": 457,
            "QTD_VENDIDA": 1,
            "VALOR_LIQUIDO": -10.0,
            "EMPRESA": "PE",
        })
        self.assertEqual(devolucao["CFOP"], api.CFOP_DEVOLUCAO)

        estoque = api._registro_estoque({
            "EAN": "7891234567890",
            "ESTOQUE": 15,
            "ULT.ENTRADA": "10/08/2026",
            "PREÇO_COMPRA": 12.5,
        })
        self.assertEqual(estoque["Codigo_Barras"], "7891234567890")
        self.assertEqual(estoque["Est_Disponivel"], 15)
        self.assertEqual(estoque["Data_Entrada"], "2026-08-10")
        self.assertEqual(estoque["Preco_Custo"], 12.5)

        vendedores = api._registros_vendedores([
            {"COD_VENDEDOR": 1, "VENDEDOR": "Ana Souza", "SUPERVISAO": "Capital"},
            {"COD_VENDEDOR": 1, "VENDEDOR": "Ana Souza", "SUPERVISAO": "Capital"},
            {"COD_VENDEDOR": 2, "VENDEDOR": "Bruno Lima", "SUPERVISAO": "Interior"},
        ])
        self.assertEqual(len(vendedores), 2)
        self.assertEqual(vendedores[0], {
            "Vendedor_Codigo": "1", "Vendedor_Nome": "Ana Souza",
            "Vendedor_Ativo": True, "CPF": "", "Telefone": "", "Grupo": "Capital",
        })


if __name__ == "__main__":
    unittest.main()
