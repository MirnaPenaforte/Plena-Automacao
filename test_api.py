import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import api


class ApiJsonTests(unittest.TestCase):
    def test_rota_da_plena_e_distinta(self):
        rotas = {rota.path for rota in api.app.routes}
        self.assertIn("/plena/imports/atuais", rotas)
        self.assertNotIn("/plena/imports/atuais.zip", rotas)

    def test_anexos_sao_separados_no_contrato_da_nova(self):
        with tempfile.TemporaryDirectory() as pasta:
            imports = Path(pasta)
            vendas = imports / "PLENA_relatorio_vendas_12-09-2026.xlsx"
            estoque = imports / "PLENA_mapa_estoque_12-09-2026.xlsx"
            pd.DataFrame({"Produto_Ean": ["789"], "Quantidade": [3]}).to_excel(vendas, index=False)
            pd.DataFrame({"Produto_Ean": ["789"], "Estoque_Quantidade": [8]}).to_excel(estoque, index=False)

            with patch.object(api, "IMPORTS_DIR", imports), patch.dict(
                "os.environ", {"IMPORTS_API_TOKEN": "teste"}
            ):
                resultado = json.loads("".join(api._gerar_json(api._tabelas_atuais())))

        self.assertEqual(list(resultado), ["METAS", "VENDAS", "VENDEDORES", "ESTOQUE"])
        self.assertEqual(resultado["METAS"], [])
        self.assertEqual(resultado["VENDAS"][0]["Produto_Ean"], "789")
        self.assertEqual(resultado["ESTOQUE"][0]["Estoque_Quantidade"], 8)

    def test_anexo_arquivado_tambem_e_encontrado(self):
        with tempfile.TemporaryDirectory() as pasta:
            imports = Path(pasta) / "imports"
            backup = imports / "backups" / "09_Setembro_2026" / "12-09-2026"
            backup.mkdir(parents=True)
            caminho = backup / "PLENA_relatorio_vendas_12-09-2026_12h00.xlsx"
            caminho.touch()
            with patch.object(api, "IMPORTS_DIR", imports):
                self.assertEqual(api._ultimo_anexo(api.PADROES_ANEXOS["VENDAS"]), caminho)


if __name__ == "__main__":
    unittest.main()
