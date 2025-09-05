
# Case Reporting Automation

Gera **report.xml** mensal a partir de CSV de transações, com **resumo técnico** no corpo do e-mail. Uso da OpenAI é **opcional** (para redigir o texto do e-mail). Sem IA, o sistema gera um resumo determinístico.

---

## ✅ Suporte
- **Windows 10/11**, **macOS**, **Linux**
- **Python 3.10+** (testado no Windows com **3.12**)

---

## ⚡️ Guia rápido
### 1) Crie o ambiente
**Windows (PowerShell):**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
# Windows + Python 3.12: se aparecer incompatibilidade numpy/pandas
pip install --force-reinstall "numpy==2.0.2" "pandas==2.2.3"
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 2) Configure o `.env`
Copie o exemplo e edite:
```bash
cp .env.example .env
```
**Exemplo (Gmail com senha de app):**
```
EMAIL_FROM=seu_email@gmail.com
EMAIL_TO=destinatario1@dominio.com, destinatario2@dominio.com

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASS=SUA_SENHA_DE_APP    # 16 caracteres, sem espaços
SMTP_STARTTLS=true
SMTP_USE_SSL=false

# IA (opcional)
AI_MODE=auto                  # on|off|auto
OPENAI_API_KEY=               # deixe vazio se não quiser IA
OPENAI_MODEL=gpt-4o-mini
```

**O que é senha de app (Gmail)?**  
Conta com 2FA → acesse `https://myaccount.google.com/apppasswords`, gere uma senha para *Mail*, copie (sem espaços) e cole em `SMTP_PASS`.  
**Outlook/Office 365:** prefira conta de serviço com SMTP AUTH habilitado. Porta 587 + STARTTLS.

### 3) Prepare o CSV
O parser aceita, entre outros, estes cabeçalhos (case-insensitive):
- `transaction_code` (→ **id**)
- `timestamp` (→ **date**, aceita `dd-mm-aaaa` e `yyyy-mm-dd`, com/sem `0:00:00`)
- `amount_brl` (→ **amount**, entende `9.766,46`)
- `network`, `category`, `merchant_id`
- `currency` e `type` são opcionais: se faltarem, assume `BRL` e deriva `type` de `category` (*CRED* → CREDIT; senão DEBIT).

### 4) Rode pela **CLI**
> **Windows:** use **uma linha só** (no CMD quebre com `^`; no PowerShell com crase `` ` ``).

**Exemplo com o CSV do projeto:**
```powershell
python app.py --month=2025-09 --input data	ransactions.csv --output outputs509 --ai off
```

**Com seu CSV (ex.: Database_Automation.csv):**
```powershell
python app.py --month=2025-09 --input "D:\cloudwalk\case_reporting_automation\Database_Automation.csv" --output outputs509 --ai off
```

**Enviar e-mail (com `.env` preenchido):**
```powershell
python app.py --month=2025-09 --input data	ransactions.csv --output outputs509 --send-email --ai auto
```
- `--ai off` → texto determinístico (sem OpenAI)  
- `--ai auto` → usa OpenAI **só** se `OPENAI_API_KEY` estiver definido  
- `--ai on` → força uso da OpenAI

**Saídas:**
```
outputs/<YYYYMM>/report.xml
outputs/<YYYYMM>/summary.json
```

### 5) (Opcional) Rode via **API local**
```bash
uvicorn src.rest_api:app --reload
```
Teste:
```bash
curl -X POST "http://127.0.0.1:8000/run-report?month=2025-09&input_path=data/transactions.csv&send_email=false&ai=off"
```

---

## 🧠 Como o parser lida com o seu CSV
- Mapeia automaticamente `transaction_code→id`, `timestamp→date`, `amount_brl→amount`.
- Datas: aceita `dd-mm-aaaa` e `yyyy-mm-dd` (remove “0:00:00”).
- Valores PT-BR: remove ponto de milhar e troca vírgula por ponto.
- `currency`: se ausente/estranha, vira `BRL`.
- `type`: derivado de `category` (contém “CRED” → `CREDIT`; caso contrário `DEBIT`).
- Descarta apenas linhas realmente inviáveis: `id/date/amount/merchant_id` vazios.

---

## ✉️ E-mail gerado
- **Assunto:** `Relatório Transacional — <YYYY-MM>`
- **Corpo:** resumo técnico conciso (IA opcional)
- **Anexo:** `report.xml` do mês

Exemplo (sem IA):
```
Relatório mensal de transações:
- Entradas processadas: 60
- Duplicatas removidas: 0
- Abaixo do limite excluídas: 0
- Saída final (transações válidas): 60
- Sem erros de parsing reportados.
```

---

## 🧩 Problemas comuns (e consertos)
- **Windows + Python 3.12 — erro `numpy.dtype size changed`**
  ```powershell
  pip install --force-reinstall "numpy==2.0.2" "pandas==2.2.3"
  ```
- **`'--input' não é reconhecido…`** → você quebrou a linha com `\`. No Windows, use **uma linha**, ou quebre com `^` (CMD) / crase `` ` `` (PowerShell).
- **`Nenhum destinatário definido`** → preencha `EMAIL_TO` no `.env` (lista separada por vírgula).
- **Falha STARTTLS/porta** → tente SSL puro:
  ```
  SMTP_PORT=465
  SMTP_STARTTLS=false
  SMTP_USE_SSL=true
  ```
- **Autenticação (Gmail)** → use **senha de app** (16 caracteres) e 2FA ativa.
- **`FileNotFoundError` para o CSV** → verifique o caminho e use aspas se houver espaços.

---

## 🗂 Estrutura do projeto
```
.
├─ app.py
├─ data/
│  └─ transactions.csv              # exemplo
├─ outputs/
│  └─ <YYYYMM>/
│     ├─ report.xml
│     └─ summary.json
└─ src/
   ├─ parser.py
   ├─ transformer.py
   ├─ xml_generator.py
   ├─ emailer.py
   ├─ analyzer.py
   └─ rest_api.py
```

---

## 🧪 Prompts úteis para co-criar o projeto
> Use estes prompts (ou variações) para iterar com IA.

1. **Parser flexível (aliases e PT-BR)**  
   *“Atualize o `parser.py` para mapear `transaction_code→id`, `timestamp→date`, `amount_BRL→amount`, assumir `currency=BRL` e derivar `type` pela `category` (contém CRED→CREDIT, senão DEBIT). Trate datas `dd-mm-aaaa` com `0:00:00` e valores `9.766,46`.”*

2. **IA opcional**  
   *“Adicione o parâmetro `--ai=auto|on|off` no `app.py`. Em `auto`, use OpenAI só se `OPENAI_API_KEY` existir; em `off`, gere texto determinístico.”*

3. **Resumo determinístico (fallback)**  
   *“Implemente uma função `plain_text_insight(summary)` para montar o corpo do e-mail sem IA.”*

4. **SMTP seguro**  
   *“Crie `.env.example` com variáveis SMTP (Gmail/Outlook) e explique senha de app no README.”*

5. **Windows-friendly**  
   *“Inclua no README exemplos de execução **em uma linha** no PowerShell e correção de pandas/numpy em Python 3.12.”*

6. **REST rápido**  
   *“Exponha um endpoint `POST /run-report` no `src/rest_api.py` que chame `app.py` por subprocess, aceitando `month`, `input_path`, `send_email` e `ai`.”*

7. **Validação**  
   *“Gere um `summary.json` com métricas: `rows_in`, `duplicates_removed`, `below_threshold_excluded`, `rows_out` e quantidades de erros de parsing.”*

8. **E-mail com anexo**  
   *“Envie o `report.xml` por e-mail com assunto ‘Relatório Transacional — <YYYY-MM>’ e corpo gerado (IA opcional).”*

---

## Licença
Uso interno / teste técnico.
