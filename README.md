# Plena-PE Multifoco Automation

Esta é uma aplicação de automação contínua (monitoramento) desenvolvida em **Python** para o processamento automatizado de planilhas de vendas e estoque. O sistema monitora a caixa de entrada de e-mails em busca de relatórios estruturados (formato `.xlsx`), realiza o processamento detalhado de métricas de negócio, consolida os dados, gera um novo relatório e realiza o envio automático desses resultados para uma API.

## 🚀 Funcionalidades

- **Monitoramento Contínuo**: A aplicação roda em loop, buscando novos arquivos na pasta `imports` ou diretamente via e-mail a cada 1 minuto.
- **Integração com E-mail (IMAP)**: Lê mensagens e extrai automaticamente os anexos necessários.
- **Processamento de Dados**: Utiliza a biblioteca `pandas` para manipular diferentes abas do relatório (como `Vendas_Dev` e `Estoque`), realizando operações como:
  - Consolidação e agrupamento de Estoque.
  - Extração e análise de Custo (com regras para preços zerados).
  - Cálculo de Prazos de Validade.
  - Agrupamento de Vendas do Mês Atual.
  - Cálculo de Faturamento.
- **Geração de Relatórios**: Exporta o DataFrame final mesclado e formatado por EAN.
- **Envio Automático via API**: Envia o relatório processado para um endpoint remoto.
- **Arquivamento Seguro**: Move os arquivos processados para uma subpasta de arquivamento (backup).
- **Conteinerização**: O projeto está totalmente preparado para ser rodado de forma isolada e contínua em **Docker** e **Docker Compose**.

## 🛠️ Tecnologias e Bibliotecas

- **[Python 3.11+](https://www.python.org/)**
- **[Pandas](https://pandas.pydata.org/)** & **[OpenPyXL](https://openpyxl.readthedocs.io/)** - Para manipulação dos dados tabulares e arquivos Excel.
- **[Requests](https://requests.readthedocs.io/)** - Para comunicação com APIs externas.
- **[imap-tools](https://pypi.org/project/imap-tools/)** - Para conexão e extração de e-mails usando o protocolo IMAP.
- **[python-dotenv](https://pypi.org/project/python-dotenv/)** - Para o gerenciamento seguro de variáveis de ambiente.
- **Docker & Docker Compose** - Para deploy integrado e escalável.

## 🗂️ Estrutura do Projeto

```text
Plena-PE_Multifoco_Automation/
├── core/                       # Lógicas de negócio e processamento de colunas
│   ├── Col_Custo.py            # Extração de preço de custo
│   ├── Col_data_entrada.py     # Preenchimento das datas de entrada
│   ├── Col_data_validade.py    # Tratativas para validades de produtos
│   ├── Col_estoque.py          # Agrupamento e processamento do estoque
│   ├── Col_faturamento_total.py# Cálculos de faturamento M e M-1
│   ├── Col_Mes_atual.py        # Processamento e agrupamento de vendas ativas
│   └── read_excel.py           # Leitura e verificação das abas Vendas_Dev e Estoque
├── utils/                      # Ferramentas utilitárias e integrações externas
│   ├── api_client.py           # Funções de integração e envio do relatório para API
│   ├── controler_import.py     # Sistema de backup/limpeza de arquivos importados
│   ├── exporter_excel.py       # Geração da saída unificada e customizada
│   └── gmail_client.py         # Módulo de acesso ao e-mail
├── imports/                    # Pasta que armazena os arquivos recém-baixados (Input)
├── output/                     # Local onde os relatórios gerados são salvos provisoriamente
├── logs/                       # Pasta designada a back-ups diários e possíveis logs
├── .env                        # [Não versionado] Configurações de API e credenciais
├── docker-compose.yml          # Manifesto do Docker Compose (volume links, environments)
├── Dockerfile                  # Instruções para criação da imagem do projeto
├── main.py                     # Script principal e orquestrador da automação
└── requirements.txt            # Dependências Python

```

## ⚙️ Pré-requisitos e Configuração Local

1. Assegure estar com o **Python instalado** ou com **Docker / Docker Compose** na máquina.
2. Clone este repositório.
3. Crie e preencha um arquivo `.env` na raiz do projeto contendo as credenciais de e-mail e os endpoints da API (solicite o `.env.example` se disponível).

### Rodando o Projeto Usando o Python Host (Local)

1. Crie um ambiente virtual e o ative (Recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Para Linux/Mac
   # venv\Scripts\activate   # Para Windows
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Certifique-se de que as pastas **`imports`**, **`output`** e **`logs`** existem na raiz (o Docker as cria automaticamente, mas localmente pode ser preciso criá-las ou rodar o script que as gerará, se aplicável).

4. Inicie o sistema:
   ```bash
   python main.py
   ```

### Rodando o Projeto com Docker (Recomendado)

O projeto mapeia perfeitamente os volumes das pastas para os caminhos de host, para que os arquivos fiquem refletidos na sua máquina, além de respeitar o timezone `America/Sao_Paulo`.

1. Confirme se as pastas locais (ex. `./imports`, `./output`, `./logs`) e o arquivo `.env` estam em root.
2. Faça a build e inicie os containers via compose:
   ```bash
   docker-compose up -d --build
   ```
3. Acompanhe os logs de execução:
   ```bash
   docker-compose logs -f automation-app
   ```
*Nota*: O aplicativo continuará validando as atualizações caso o parâmetro `restart: unless-stopped` estiver configurado.

## 📊 Regra de Negócio: Detalhes do Processamento Principal
Quando o `main.py` encontra um documento modelo `.xlsx` na pasta de `imports/`, o processo funciona nas seguintes etapas:
1. Extração dos *DataFrames* para `Estoque` e para `Vendas_Dev`.
2. Move todos os arquivos originais lidos para um arquivamento (*backup*) visando impedir duplicações nas leituras.
3. Tratamento unificado pelo ID universal do produto (**`EAN`**). 
4. Correção numérica fina: substitui faltas por **zeros**, estipula casas decimais corretas (Faturamentos com 2 casas e os Custos chegam a 3 casas como contingência onde for estritamente 0), e processa de forma oca os blocos dos *Meses Anteriores* que deixaram de ser usados (`Mês -1`);
5. Um arquivo novo consolidado e limpo é despachado para a pasta `output/` via o submódulo *Exporter Excel*.
6. O robô em tempo de execução submete esse mesmo relatório gerado no final para a API conectada.

## 📄 Informações e Considerações Adicionais

- Para parar a automação com Python puro, pressione teclado `[Ctrl + C]`.
- Se ocorrer qualquer bloqueio no upload para API, analise se não estão enfrentando limitação de requisições por segundo (Rate Limit blocks). 
- O arquivo `.dockerignore` previne que caches e ambientes virtuais subam como lixo dentro da imagem Docker. 
