# Observa Brasil

Aplicação web em Flask para monitoramento de focos de calor, vegetação e queimadas no Brasil, usando dados oficiais do INPE BDQueimadas e catálogo STAC do Brazil Data Cube.

## Funcionalidades implementadas

- Painel funcional em português com mapa Leaflet, filtros, cards, gráficos, tabela e exportação CSV.
- Consulta ao diretório oficial diário do INPE, descoberta automática do CSV mais recente, cache local e fallback para cache em indisponibilidade temporária.
- Endpoints REST padronizados para saúde, fontes, focos, resumo, vegetação, produtos Sentinel-2, áreas de interesse, alertas e PyRawS.
- Validação de GeoJSON com Shapely para Geometry, Feature e FeatureCollection.
- Modelos SQLAlchemy para usuários, áreas, alertas, histórico e focos processados.
- Autenticação básica com hash seguro de senha, sessão e proteção CSRF em formulários.
- Adaptador PyRawS opcional e desacoplado.
- Cálculos NDVI, NBR e dNBR com NumPy.
- Docker, Docker Compose, Render blueprint e `.env.example`.
- WSGI com Gunicorn para produção e detecção de dispositivo por cabeçalhos HTTP.
- Script educacional para Google Colab.
- Testes automatizados com mocks para não depender da internet.

## Fontes oficiais

- INPE BDQueimadas: `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/`
- Brazil Data Cube STAC: `https://data.inpe.br/bdc/stac/v1/`
- Coleção Sentinel-2 principal: `S2-16D-2`

No filtro “Data do CSV”, informe uma URL completa do CSV, o nome com `.csv` ou o nome sem extensão. Exemplos: `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_20260919.csv`, `focos_diario_br_20260919.csv` ou `focos_diario_br_20260919`.

Quando `Data do CSV` está em branco, a aplicação tenta descobrir o CSV mais recente no INPE. Se essa consulta falhar por lentidão ou timeout, ela usa o CSV mais recente existente no cache local em `instance/cache/`, quando houver um arquivo disponível. Para conexões lentas, ajuste `REQUEST_TIMEOUT` no `.env`, por exemplo `REQUEST_TIMEOUT=45`.

Foco de calor é uma detecção térmica por satélite. Ele não confirma automaticamente um incêndio, nem representa sozinho a extensão total de uma área queimada. Para análise de severidade, use NBR e dNBR com imagens antes e depois do evento.

## Instalação local no Windows 11 PowerShell

```powershell
py -3.12 -m venv ObservaBrasil
.\ObservaBrasil\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
$env:FLASK_ENV = "development"
flask --app app run --debug
```

No PowerShell, use os comandos desta seção. `python3.12` e `source ObservaBrasil/bin/activate` são comandos da seção Linux.

Acesse `http://127.0.0.1:5000`.

## Passo a passo para testar o painel

1. Abra `http://127.0.0.1:5000` no navegador.
2. Aguarde a mensagem de fontes mudar para `INPE online | BDC online`.
3. Para testar com o CSV diário de 19/09/2026, preencha os campos assim:

```text
Data do CSV: https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_20260919.csv
Estado: PARÁ
Bioma: Amazônia
Satélite: GOES-19
FRP mínimo: 50
```

4. Clique em `Atualizar painel`.
5. Verifique se os cards, mapa, gráficos e tabela foram atualizados apenas com os focos que atendem aos filtros.
6. Clique em um marcador no mapa para conferir município, estado, bioma, satélite, data, FRP, latitude e longitude.
7. Clique em `Exportar CSV` para baixar a tabela filtrada.

Você também pode informar somente o nome do arquivo no campo `Data do CSV`:

```text
focos_diario_br_20260919.csv
```

ou sem extensão:

```text
focos_diario_br_20260919
```

Para usar sempre o CSV mais recente disponível no INPE, deixe `Data do CSV` em branco.

### Sugestões de valores para os filtros

Use os valores exatamente como aparecem abaixo para facilitar o primeiro teste:

```text
Estado: PARÁ
Bioma: Amazônia
Satélite: GOES-19
FRP mínimo: 50
```

Outras combinações úteis:

```text
Estado: MARANHÃO
Bioma: Cerrado
Satélite: GOES-19
FRP mínimo: 100
```

```text
Estado: TOCANTINS
Bioma: Cerrado
Satélite: METOP-B
FRP mínimo:
```

O campo `FRP mínimo` aceita números decimais, como `10`, `50`, `100` ou `150.5`. Deixe em branco para não aplicar filtro por FRP.

### Testes rápidos da API

Com o ambiente virtual ativo, execute:

```powershell
python -m pytest -q
```

Para testar a saúde da aplicação pelo navegador, acesse:

```text
http://127.0.0.1:5000/api/health
```

Para testar uma consulta filtrada diretamente pela API, acesse:

```text
http://127.0.0.1:5000/api/queimadas?data=focos_diario_br_20260919&estado=PARÁ&bioma=Amazônia&satelite=GOES-19&frp_min=50&limite=10
```

## Instalação no Linux

```bash
python3.12 -m venv ObservaBrasil
source ObservaBrasil/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
flask --app app run --debug
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

O serviço Flask usa Gunicorn com o arquivo WSGI `wsgi.py` e lê a porta pela variável `PORT`.

## Produção com Gunicorn e WSGI

O ponto de entrada de produção é:

```text
wsgi:application
```

O arquivo `wsgi.py` cria a aplicação Flask sem iniciar o servidor de desenvolvimento. Esse é o formato esperado por servidores WSGI como o Gunicorn e por plataformas de produção como Render.

Para executar localmente com Gunicorn em Linux ou dentro do contêiner:

```bash
gunicorn "wsgi:application" --bind "0.0.0.0:${PORT:-5000}" --workers 2 --threads 4 --timeout 120 --forwarded-allow-ips="*"
```

No Dockerfile e no `Procfile`, esse comando já está configurado. O `--forwarded-allow-ips="*"` permite que o Flask receba corretamente cabeçalhos encaminhados por proxy ou plataforma de nuvem.

## Render Web Service

O projeto está pronto para subir no Render como **Web Service**. A opção recomendada é usar **Runtime: Docker**, porque o projeto depende de bibliotecas geoespaciais como GDAL, GeoPandas e Rasterio, que são mais estáveis dentro do Dockerfile já incluído.

### 1. Antes de entrar no Render

Confirme que o projeto já foi enviado para o GitHub e que estes arquivos existem na raiz do repositório:

```text
Dockerfile
Procfile
README.md
render.yaml
requirements.txt
wsgi.py
```

No PowerShell, confira localmente:

```powershell
cd C:\Users\massa\Documents\ChatGPT\ObservaBrasil
git status
Test-Path .\Dockerfile
Test-Path .\Procfile
Test-Path .\wsgi.py
Test-Path .\requirements.txt
```

Rode os testes antes de publicar:

```powershell
python -m pytest -q
```

Depois envie tudo para o GitHub:

```powershell
git add .
git commit -m "Prepara deploy no Render com WSGI e Gunicorn"
git branch -M main
git push -u origin main
```

Se não houver alterações para commit, o Git pode responder `nothing to commit`; nesse caso, apenas confirme que o push já foi feito.

### 2. Criar o banco PostgreSQL no Render

No painel do Render:

```text
New > PostgreSQL
Name: observa-brasil-db
Region: escolha a região mais próxima
Plan: escolha o plano desejado
Create Database
```

Após a criação, abra o banco e copie a `Internal Database URL`. Ela será usada como `DATABASE_URL` no Web Service.

### 3. Criar o Web Service

No painel do Render:

```text
New > Web Service
Build and deploy from a Git repository
Conecte sua conta GitHub
Repository: SEU_USUARIO/ObservaBrasil
Branch: main
Runtime: Docker
Root Directory: deixe em branco
Dockerfile Path: ./Dockerfile
Health Check Path: /api/health
```

Com Runtime Docker, deixe `Build Command` e `Start Command` em branco. O Render usará o `CMD` do `Dockerfile`, que já inicia o Gunicorn:

```text
gunicorn "wsgi:application" --bind "0.0.0.0:${PORT:-5000}" --workers 2 --threads 4 --timeout 120 --forwarded-allow-ips="*"
```

### 4. Configurar variáveis de ambiente

No Web Service, abra `Environment` e cadastre:

```text
FLASK_ENV=production
SECRET_KEY=gere-um-valor-seguro-no-render
DATABASE_URL=cole-a-Internal-Database-URL-do-PostgreSQL-do-Render
BDC_STAC_URL=https://data.inpe.br/bdc/stac/v1/
INPE_QUEIMADAS_URL=https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/
REQUEST_TIMEOUT=45
```

Para gerar um `SECRET_KEY` no PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Não coloque `SECRET_KEY`, `DATABASE_URL` nem `.env` no GitHub.

O Render normalmente fornece `DATABASE_URL` começando com `postgresql://`. Você pode colar esse valor exatamente como aparece no Render; a aplicação converte automaticamente para o driver `postgresql+psycopg://` usado pelo SQLAlchemy.

### 5. Fazer o deploy

Clique em:

```text
Create Web Service
```

Depois acompanhe:

```text
Web Service > Logs
Web Service > Events
Web Service > Deploys
```

Quando o deploy terminar, o Render disponibilizará uma URL no formato:

```text
https://observa-brasil.onrender.com
```

### 6. Testar a publicação

No PowerShell, substitua a URL pela URL real gerada pelo Render:

```powershell
$RENDER_URL = "https://observa-brasil.onrender.com"
Invoke-RestMethod -Uri "$RENDER_URL/api/health"
Invoke-RestMethod -Uri "$RENDER_URL/api/fontes/status"
Invoke-RestMethod -Uri "$RENDER_URL/api/queimadas?data=focos_diario_br_20260919&estado=SÃO%20PAULO&limite=10"
Start-Process $RENDER_URL
```

O endpoint `/api/health` deve retornar `status: ok`. O painel principal deve abrir no navegador e carregar mapa, cards, gráficos e tabela.

### 7. Atualizar depois de publicado

Depois de novas alterações locais:

```powershell
git status
git add .
git commit -m "Descreva a alteracao"
git push
```

Com `Auto-Deploy` ativado no Render, cada push na branch `main` inicia um novo deploy automaticamente.

### 8. Opção Blueprint

O arquivo `render.yaml` também permite criar os recursos pelo modo Blueprint:

```text
New > Blueprint > conecte o GitHub > selecione SEU_USUARIO/ObservaBrasil > Apply
```

Esse caminho cria o Web Service Docker e o PostgreSQL conforme o arquivo `render.yaml`.

### Alternativa sem Docker

Se quiser testar como Runtime Python no Render, use:

```text
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn "wsgi:application" --bind "0.0.0.0:$PORT" --workers 2 --threads 4 --timeout 120 --forwarded-allow-ips="*"
Health Check Path: /api/health
```

Essa alternativa pode falhar se o ambiente nativo do Render não tiver bibliotecas de sistema compatíveis com GDAL/Rasterio. Para este projeto, Docker é o caminho mais confiável.

Referências úteis do Render:

- [Deploy Flask App](https://render.com/docs/deploy-flask)
- [Blueprint YAML Reference](https://render.com/docs/blueprint-spec)
- [Deploys](https://render.com/docs/deploys)

## Suporte multidispositivo

A aplicação é responsiva e identifica se o acesso vem de celular, tablet ou desktop lendo cabeçalhos da requisição:

- `User-Agent`
- `Sec-CH-UA-Mobile`
- `Sec-CH-UA-Platform`

O resultado é disponibilizado no Flask em `g.device`, injetado nos templates como `device` e retornado no endpoint `/api/health`.

Exemplo de resposta em `/api/health`:

```json
{
  "sucesso": true,
  "dados": {
    "status": "ok",
    "servico": "Observa Brasil",
    "dispositivo": {
      "tipo": "desktop",
      "is_mobile": false,
      "is_tablet": false,
      "is_desktop": true
    }
  }
}
```

Para testar a detecção de celular via PowerShell:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:5000/api/health" `
  -Headers @{
    "User-Agent" = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
    "Sec-CH-UA-Mobile" = "?1"
  }
```

Para testar tablet:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:5000/api/health" `
  -Headers @{
    "User-Agent" = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Safari/604.1"
  }
```

Na interface, o painel mostra `Acesso: celular`, `Acesso: tablet` ou `Acesso: desktop` no menu lateral.

## PostgreSQL

Em produção, configure `DATABASE_URL`, por exemplo:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/observa_brasil
```

SQLite é usado apenas quando `DATABASE_URL` não é informado.

## Alertas

Configure canais por variáveis de ambiente:

- `SMTP_HOST`, `SMTP_PORT`, `SMTP_TLS`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `ALERTA_WEBHOOK_URL`

A base de dados já possui estruturas para evitar alertas duplicados por `foco_id` e `area_id`. O envio programado deve ser ligado a APScheduler ou Celery conforme a infraestrutura escolhida.

## Testes

```bash
pytest
```

Os testes de INPE e STAC usam mocks e não dependem da internet.

## GitHub e Render via PowerShell

Use este roteiro quando quiser reiniciar a autenticação do GitHub, enviar o projeto para um repositório remoto e publicar no Render. Troque `SEU_USUARIO` e `ObservaBrasil` pelos valores da sua conta e do seu repositório.

### 1. Sair da conta GitHub salva no Windows

Liste as credenciais GitHub salvas:

```powershell
cmdkey /list | findstr /i github
```

Remova as credenciais mais comuns:

```powershell
cmdkey /delete:git:https://github.com
cmdkey /delete:github.com
```

Se você usa GitHub CLI, saia também pela CLI:

```powershell
gh auth logout
```

Confira o status da autenticação:

```powershell
gh auth status
```

Opcionalmente, remova nome e e-mail globais do Git para configurar tudo novamente:

```powershell
git config --global --unset user.name
git config --global --unset user.email
```

Configure novamente seu usuário de commit:

```powershell
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@example.com"
```

### 2. Preparar o projeto local

Entre na pasta do projeto:

```powershell
cd C:\Users\massa\Documents\ChatGPT\ObservaBrasil
```

Garanta que arquivos sensíveis e ambientes locais não sejam enviados:

```powershell
Add-Content -Path .gitignore -Value "`n.env"
Add-Content -Path .gitignore -Value ".venv/"
Add-Content -Path .gitignore -Value "ObservaBrasil/"
Add-Content -Path .gitignore -Value "instance/"
Add-Content -Path .gitignore -Value "__pycache__/"
Add-Content -Path .gitignore -Value ".pytest_cache/"
```

Ative o ambiente virtual:

```powershell
.\ObservaBrasil\Scripts\Activate.ps1
```

Se o seu ambiente ainda for `.venv`, use:

```powershell
.\.venv\Scripts\Activate.ps1
```

Rode os testes:

```powershell
python -m pytest -q
```

Teste a aplicação localmente:

```powershell
python app.py
```

Em outro PowerShell, teste o health check:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health"
```

### 3. Criar o repositório no GitHub pela CLI

Faça login novamente no GitHub:

```powershell
gh auth login
```

Crie o repositório remoto pelo PowerShell:

```powershell
gh repo create SEU_USUARIO/ObservaBrasil --private --source . --remote origin
```

Se preferir repositório público:

```powershell
gh repo create SEU_USUARIO/ObservaBrasil --public --source . --remote origin
```

Se o remote `origin` já existir, ajuste a URL:

```powershell
git remote set-url origin https://github.com/SEU_USUARIO/ObservaBrasil.git
```

Confira o remote:

```powershell
git remote -v
```

### 4. Commit e push para o GitHub

Confira os arquivos alterados:

```powershell
git status
```

Adicione os arquivos:

```powershell
git add .
```

Crie o commit:

```powershell
git commit -m "Publica versao inicial do Observa Brasil"
```

Garanta a branch `main`:

```powershell
git branch -M main
```

Envie para o GitHub:

```powershell
git push -u origin main
```

Abra o repositório no navegador:

```powershell
gh repo view --web
```

### 5. Conferir arquivos antes do Render

Confirme que estes arquivos existem no projeto antes de publicar:

```powershell
Test-Path .\Dockerfile
Test-Path .\Procfile
Test-Path .\render.yaml
Test-Path .\wsgi.py
Test-Path .\requirements.txt
```

Confirme que o Dockerfile usa Gunicorn com WSGI:

```powershell
Select-String -Path .\Dockerfile -Pattern "gunicorn"
```

Confirme que o `render.yaml` está na raiz:

```powershell
Get-Content .\render.yaml
```

### 6. Publicar no Render

Abra o painel do Render pelo PowerShell:

```powershell
Start-Process "https://dashboard.render.com/"
```

O caminho recomendado para este projeto é Web Service com Docker:

```text
New > Web Service > conecte o GitHub > selecione SEU_USUARIO/ObservaBrasil
Runtime: Docker
Dockerfile Path: ./Dockerfile
Health Check Path: /api/health
Build Command: vazio
Start Command: vazio
```

Antes ou durante a configuração do Web Service, crie um PostgreSQL no Render:

```text
New > PostgreSQL
Name: observa-brasil-db
```

Copie a `Internal Database URL` do PostgreSQL para a variável `DATABASE_URL` do Web Service.

Se preferir usar Blueprint:

```text
New > Blueprint > conecte o GitHub > selecione SEU_USUARIO/ObservaBrasil > use render.yaml > Apply
```

Depois de criado, abra os logs pelo painel do Render e aguarde o build Docker finalizar.

### 7. Configurar variáveis no Render

No Web Service criado pelo Render, configure ou confira:

```text
FLASK_ENV=production
SECRET_KEY=gere-um-valor-seguro-no-render
DATABASE_URL=cole-a-Internal-Database-URL-do-PostgreSQL-do-Render
BDC_STAC_URL=https://data.inpe.br/bdc/stac/v1/
INPE_QUEIMADAS_URL=https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/
REQUEST_TIMEOUT=45
```

Para gerar `SECRET_KEY` pelo PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Não coloque essas variáveis com segredos no GitHub.

Se a URL do Render começar com `postgresql://`, não altere manualmente. O projeto converte automaticamente para `postgresql+psycopg://` ao iniciar.

### 8. Testar a aplicação publicada

Quando o Render fornecer a URL HTTPS, defina-a no PowerShell:

```powershell
$RENDER_URL = "https://sua-url-no-render.onrender.com"
```

Teste o health check:

```powershell
Invoke-RestMethod -Uri "$RENDER_URL/api/health"
```

Teste o status das fontes:

```powershell
Invoke-RestMethod -Uri "$RENDER_URL/api/fontes/status"
```

Teste uma consulta de focos:

```powershell
Invoke-RestMethod -Uri "$RENDER_URL/api/queimadas?data=focos_diario_br_20260919&estado=SÃO%20PAULO&limite=10"
```

Abra o painel publicado:

```powershell
Start-Process $RENDER_URL
```

### 9. Atualizações futuras

Depois de qualquer alteração local:

```powershell
git status
git add .
git commit -m "Descreva a alteracao"
git push
```

O Render deve iniciar um novo deploy automaticamente se o auto-deploy estiver ativado.

## PyRawS

PyRawS é opcional e serve apenas para cenas Sentinel-2 RAW locais. A consulta da coleção `S2-16D-2` usa STAC/COG do Brazil Data Cube. Para instalar:

```bash
pip install -r requirements-pyraws.txt
```

Verifique o estado em `/api/pyraws/status`.

## Limitações restantes

- Envio real de e-mail, Telegram e webhook está estruturado, mas ainda precisa de ativação operacional com agendador.
- Exportação PDF, Excel, PNG do mapa e GeoTIFF processado ainda não foram implementadas nesta primeira base.
- Camadas oficiais de limites estaduais, municipais, biomas e unidades de conservação ainda dependem de ingestão de bases geográficas externas.
- Processamento raster de janelas COG está preparado conceitualmente pelos serviços de índice, mas ainda precisa de fluxo de download/leitura por janela.
