# PLENA Automação

Serviço de automação para recebimento, processamento e distribuição de relatórios de vendas e estoque da operação PLENA.

A aplicação monitora uma conta de e-mail via IMAP, baixa anexos Excel, combina os relatórios de vendas e estoque correspondentes, calcula indicadores, gera um relatório consolidado e o envia para a API de negócio configurada. Em paralelo, disponibiliza uma API local para consulta dos relatórios recebidos mais recentemente.

## Fluxo de processamento

1. Consulta periódica à caixa de entrada configurada.
2. Download de anexos `.xlsx` de e-mails não lidos para `imports/`.
3. Associação de um relatório de vendas com um relatório de estoque pela identificação no nome dos arquivos.
4. Leitura e consolidação dos dados pelo campo `EAN`.
5. Cálculo de estoque, custo, validade, vendas do mês atual, faturamento e data de entrada.
6. Geração do relatório em `output/`.
7. Cópia dos arquivos de entrada para `imports/backups/` e remoção da raiz de `imports/`.
8. Envio do relatório consolidado mais recente para a API externa.

Quando não há um par completo de arquivos, o serviço aguarda 60 segundos antes de consultar novamente.

## Funcionalidades

- Coleta automática de anexos Excel via IMAP.
- Processamento e consolidação por `EAN`.
- Geração de relatório Excel com layout padronizado.
- Envio autenticado para a API externa.
- Backup organizado por mês e dia.
- Limpeza automática de backups com dois ou mais meses de diferença.
- API local protegida por Bearer Token.
- Execução local ou em Docker Compose.

## Tecnologias e requisitos

- Python 3.12
- Pandas, OpenPyXL, Requests e imap-tools
- FastAPI e Uvicorn
- Docker Engine e Docker Compose para implantação conteinerizada
- Acesso IMAP à conta de e-mail
- Acesso à API externa configurada em `BASE_URL`

## Configuração

Crie um arquivo `.env` na raiz do projeto. Ele contém credenciais e não deve ser versionado.

```dotenv
COMPOSE_PROJECT_NAME=plena-automacao
IMAGE_NAME=plena-automacao:latest
CONTAINER_NAME=plena-automacao

API_EMAIL=usuario@example.com
API_PASS=senha-da-api
BASE_URL=https://api.example.com
DISTRIBUIDOR_ID=seu-distribuidor-id
REPRESENTANTE_ID=seu-representante-id

GMAIL_USER=conta@example.com
GMAIL_PASS=senha-ou-app-password
IMAP_SERVER=imap.gmail.com
TERMO_BUSCA_IMAP=Plena

IMPORTS_API_HOST=0.0.0.0
IMPORTS_API_PORT=8000
IMPORTS_API_TOKEN=defina-um-token-seguro
IMPORTS_API_PROVISION_KEY=defina-uma-chave-administrativa-segura
```

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `API_EMAIL` | Sim | E-mail usado na autenticação da API externa. |
| `API_PASS` | Sim | Senha usada na autenticação da API externa. |
| `BASE_URL` | Sim | URL base da API externa. |
| `DISTRIBUIDOR_ID` | Sim | Identificador enviado no upload. |
| `REPRESENTANTE_ID` | Sim | Identificador enviado no upload. |
| `GMAIL_USER` | Sim | Conta usada no acesso IMAP. |
| `GMAIL_PASS` | Sim | Senha ou senha de aplicativo da conta IMAP. |
| `IMAP_SERVER` | Não | Servidor IMAP; padrão: `imap.gmail.com`. |
| `TERMO_BUSCA_IMAP` | Sim | Texto procurado no assunto de e-mails não lidos. |
| `IMPORTS_API_HOST` | Não | Interface da API local; padrão: `0.0.0.0`. |
| `IMPORTS_API_PORT` | Não | Porta da API local; padrão: `8000`. |
| `IMPORTS_API_TOKEN` | Recomendável | Token Bearer para consulta da API local. |
| `IMPORTS_API_PROVISION_KEY` | Recomendável | Chave administrativa para gerar o token. |

Para contas Gmail, habilite IMAP e prefira uma senha de aplicativo quando a autenticação em dois fatores estiver ativa.

## Arquivos de entrada

O serviço reconhece arquivos `.xlsx` com os marcadores:

- `_relatorio_vendas_`: relatório de vendas.
- `_mapa_estoque_`: relatório de estoque.

Os dois arquivos devem compartilhar a mesma data ou referência no nome. Exemplo:

```text
PLENA_relatorio_vendas_12-09-2026.xlsx
PLENA_mapa_estoque_12-09-2026.xlsx
```

O processamento somente começa quando os dois tipos são encontrados. As planilhas precisam conter as colunas esperadas pelos módulos de processamento, incluindo o identificador de produto usado como `EAN`.

## Execução local

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
mkdir -p imports output logs
python main.py
```

No Windows, ative o ambiente com:

```powershell
.venv\Scripts\Activate.ps1
```

A aplicação cria os diretórios de entrada e saída quando necessário. Para encerrar o monitor, pressione `Ctrl+C`.

## Implantação com Docker Compose

1. Instale e valide o Docker:

   ```bash
   docker --version
   docker compose version
   ```

2. Crie o `.env` e preencha as variáveis da seção de configuração.
3. Crie os diretórios persistidos:

   ```bash
   mkdir -p imports output logs
   ```

4. Construa a imagem e inicie o serviço:

   ```bash
   docker compose up -d --build
   ```

5. Acompanhe a execução:

   ```bash
   docker compose logs -f app
   ```

Comandos operacionais:

```bash
docker compose ps
docker compose restart app
docker compose stop
docker compose down
```

O serviço usa `restart: unless-stopped` e monta estes volumes:

| Host | Contêiner | Finalidade |
| --- | --- | --- |
| `./imports` | `/app/imports` | Anexos recebidos e backups. |
| `./output` | `/app/output` | Relatórios consolidados. |
| `./logs` | `/app/logs` | Dados operacionais. |

A API local é publicada na porta de `IMPORTS_API_PORT`, com padrão `8000`.

## API local

A API é iniciada em segundo plano junto com o monitor de e-mails.

### Gerar token

```bash
curl -X POST http://localhost:8000/plena/auth/token \
  -H "X-Provision-Key: sua-chave-administrativa"
```

O valor retornado em `access_token` é salvo em `imports/.api_token`.

### Consultar imports atuais

```bash
curl http://localhost:8000/plena/imports/atuais \
  -H "Authorization: Bearer seu-token"
```

A resposta segue o contrato:

```json
{
  "METAS": [],
  "VENDAS": [
    {
      "CFOP": "5102",
      "Saida_Codigo": "12345",
      "Saida_Data_Venda": "01/09/2026",
      "Saida_Numero_Nota": "NF-9876",
      "Saida_Filial_Cnpj": "",
      "Saida_Quantidade": 2,
      "Saida_Valor_Unitario": 25.5,
      "Produto_Ean": "7890000000000",
      "Vendedor_Codigo": "42",
      "Vendedor_Nome": "Maria Silva",
      "Vendedor_Ativo": true,
      "Cliente_Codigo": "",
      "Cliente_Nome_Razao_Social": "",
      "Cliente_Cep": "",
      "UF": "PE",
      "Cidade": ""
    }
  ],
  "VENDEDORES": [
    {
      "Vendedor_Codigo": "42",
      "Vendedor_Nome": "Maria Silva",
      "Vendedor_Ativo": true,
      "CPF": "",
      "Telefone": "",
      "Grupo": "Equipe A"
    }
  ],
  "ESTOQUE": [
    {
      "Filial_Cnpj": "",
      "Codigo_Barras": "7890000000000",
      "Est_Disponivel": 8,
      "Lote": "",
      "Data_Entrada": "15/08/2026",
      "Data_Vencimento": "",
      "Preco_Custo": 18.75
    }
  ]
}
```

Na PLENA, o endpoint usa o par de arquivos de vendas e estoque mais recente em `imports/backups/`, considerando a data no nome e exigindo que ambos pertençam ao mesmo distribuidor. `VENDAS` contém as linhas do import de vendas mapeadas para o contrato acima. `VENDEDORES` é derivado desse mesmo import, sem duplicar código e nome. `ESTOQUE` contém um registro por EAN, escolhendo a linha com maior estoque. `Saida_Data_Venda` e `Data_Entrada` são publicadas em `DD/MM/AAAA`. `METAS` permanece vazio. Se nenhum par for encontrado, o endpoint retorna HTTP 404.

## Relatório gerado

O arquivo é criado como `Plena_DD-MM-AA.xlsx` e contém:

```text
EAN, Descrição, Data Entrada, Data Validade
Mês -3, Mês -2, Mês -1, Mês Atual, Estoque
Faturamento Atual, Faturamento M-1, Preço Custo
Transito, Pendencia
```

Os relatórios são organizados em `output/<mês>/<dia>/`. Os backups ficam em `imports/backups/<mês>/<dia>/`. O sistema mantém o mês atual e o mês anterior, removendo referências mais antigas.

## API externa

O serviço utiliza:

- Autenticação: `POST {BASE_URL}/api/conta/login`
- Upload: `POST {BASE_URL}/api/import/vendas`

O login envia `API_EMAIL` e `API_PASS`. O upload envia o arquivo no campo `arquivo`, além de `distribuidorId` e `representanteId`.

## Testes

Execute os testes da API local com:

```bash
python -m unittest test_api.py
```

## Estrutura do projeto

```text
.
├── api.py                       API local de consulta dos imports
├── main.py                      Monitoramento e processamento
├── config/
│   ├── settings.py              Configurações do ambiente
│   └── token.py                 Autenticação na API externa
├── core/                        Regras de transformação e cálculo
├── utils/
│   ├── api_client.py            Upload do relatório
│   ├── controler_import.py      Backup e retenção
│   ├── exporter_excel.py        Geração do relatório final
│   └── gmail_client.py          Coleta de anexos via IMAP
├── imports/                     Entradas e backups
├── output/                      Relatórios gerados
├── logs/                        Dados operacionais
├── Dockerfile                   Imagem da aplicação
├── docker-compose.yml           Definição do serviço
└── requirements.txt             Dependências Python
```

## Diagnóstico

Se nenhum arquivo for processado, confirme:

1. As credenciais e o termo de busca do IMAP.
2. Se a mensagem está não lida.
3. Se os nomes contêm os marcadores esperados.
4. Se vendas e estoque formam o mesmo grupo.
5. Se os diretórios têm permissão de leitura e escrita.

Se o upload falhar, valide `BASE_URL`, as credenciais da API, os identificadores e a conectividade do contêiner.

A sessão usada pela API externa atualmente desabilita a verificação de certificado TLS. Em produção, corrija a cadeia de certificados e remova essa configuração antes da operação definitiva.

## Segurança

- Nunca versione `.env`, tokens ou senhas.
- Restrinja o acesso à porta da API local em redes compartilhadas.
- Use senhas de aplicativo para contas de e-mail quando possível.
- Monitore os logs e o espaço disponível em `imports/` e `output/`.
