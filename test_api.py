import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi import HTTPException

import api


class ApiJsonTests(unittest.TestCase):
    def test_rota_da_plena_e_distinta(self):
        rotas = {rota.path for rota in api.app.routes}
        self.assertIn("/plena/imports/atuais", rotas)
        self.assertNotIn("/plena/imports/atuais.zip", rotas)
        self.assertIn("/plena/auth/token", rotas)

    def test_busca_relatorio_mais_recente_em_output(self):
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            antigo = raiz / "09_Setembro_2026" / "26-09-2026" / "Plena_26-09-26.xlsx"
            recente = raiz / "10_Outubro_2026" / "06-10-2026" / "Plena_06-10-26.xlsx"
            antigo.parent.mkdir(parents=True)
            recente.parent.mkdir(parents=True)
            antigo.touch()
            recente.touch()
            with patch.object(api, "OUTPUT_DIR", raiz):
                self.assertEqual(api._encontrar_relatorio_atual(), recente)

    def test_sem_relatorio_retorna_404(self):
        with tempfile.TemporaryDirectory() as pasta:
            with patch.object(api, "OUTPUT_DIR", Path(pasta)):
                with self.assertRaises(HTTPException) as contexto:
                    api._tabelas_atuais()
        self.assertEqual(contexto.exception.status_code, 404)

    def test_json_usa_todas_as_colunas_do_output_e_campos_antigos_vazios(self):
        relatorio = pd.DataFrame([{
            "EAN": 7891234567890,
            "Descrição": "Produto exemplo",
            "Data Entrada": pd.Timestamp("2026-08-10"),
            "Data Validade": "01/09/2027",
            "Mês -3": None,
            "Mês -2": None,
            "Mês -1": 3,
            "Mês Atual": 5,
            "Estoque": 8,
            "Faturamento Atual": 125.5,
            "Faturamento M-1": 75.3,
            "Preço Custo": 3.5,
            "Transito": None,
            "Pendencia": None,
        }])
        with patch.object(api, "_encontrar_relatorio_atual", return_value=Path("Plena_06-10-26.xlsx")):
            with patch.object(api.pd, "read_excel", return_value=relatorio):
                resultado = json.loads("".join(api._gerar_json(api._tabelas_atuais())))

        self.assertEqual(list(resultado), ["METAS", "VENDAS", "VENDEDORES", "ESTOQUE"])
        self.assertEqual(resultado["METAS"], [])
        self.assertEqual(resultado["VENDEDORES"], [])

        venda = resultado["VENDAS"][0]
        self.assertEqual(list(venda)[:len(relatorio.columns)], list(relatorio.columns))
        self.assertEqual(venda["EAN"], "7891234567890")
        self.assertEqual(venda["Data Entrada"], "10/08/2026")
        self.assertEqual(venda["Data Validade"], "01/09/2027")
        self.assertEqual(venda["Faturamento Atual"], 125.5)
        self.assertIsNone(venda["Transito"])
        self.assertTrue(all(venda[campo] == "" for campo in api.CAMPOS_VENDA_ANTIGOS))

        estoque = resultado["ESTOQUE"][0]
        self.assertEqual(estoque["EAN"], "7891234567890")
        self.assertEqual(estoque["Estoque"], 8)
        self.assertTrue(all(estoque[campo] == "" for campo in api.CAMPOS_ESTOQUE_ANTIGOS))

    def test_relatorio_sem_colunas_obrigatorias_retorna_422(self):
        with patch.object(api.pd, "read_excel", return_value=pd.DataFrame([{"EAN": "123"}])):
            with self.assertRaises(HTTPException) as contexto:
                api._ler_relatorio(Path("Plena_06-10-26.xlsx"))
        self.assertEqual(contexto.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
