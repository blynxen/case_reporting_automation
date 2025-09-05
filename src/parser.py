# src/parser.py
import os
import re
from typing import Tuple, List, Optional

import pandas as pd

# Campos mínimos que PRECISAM existir após o mapeamento
MANDATORY_AFTER_MAP = ["id", "date", "amount", "merchant_id"]  # currency/type podem ser assumidos/derivados

ALLOWED_TYPE = {"DEBIT", "CREDIT"}
ALLOWED_CURRENCY = {"BRL"}

# aliases -> nome normalizado
ALIASES = {
    "id": ["id", "transaction_id", "tx_id", "transactionid", "txid", "transaction_code", "code"],
    "status": ["status", "estado"],
    "date": ["date", "timestamp", "transaction_date", "posted_date", "data", "data_transacao", "dt"],
    "amount": ["amount", "amount_brl", "valor", "value", "transaction_amount", "amt"],
    "currency": ["currency", "moeda"],
    "type": ["type", "direction"],
    "merchant_id": ["merchant_id", "merchant", "cnpj", "merchant_cnpj", "merchantid", "merchant_tax_id"],
    "network": ["network", "rede", "scheme", "bandeira", "network_id"],
    "category": ["category", "categoria", "cat", "class"],
}

def _read_csv_smart(path: str) -> pd.DataFrame:
    """
    Tenta ler como CSV padrão (vírgula). Se vier 1 coluna (sinal de separador ';'),
    tenta novamente com sep=';'. Sempre preserva tudo como string.
    """
    df = pd.read_csv(path, dtype=str)
    if df.shape[1] == 1:
        df = pd.read_csv(path, dtype=str, sep=";")
    return df

def _find_col(columns: set, candidates: list) -> Optional[str]:
    for c in candidates:
        if c in columns:
            return c
    return None

def _parse_date_series(s: pd.Series) -> pd.Series:
    """
    Interpreta datas em formatos:
    - dd-mm-aaaa (com/sem ' 0:00:00')
    - yyyy-mm-dd (com/sem ' 00:00:00')
    - dd/mm/aaaa
    """
    s = (
        s.astype(str)
        .str.strip()
        .str.replace('"', "", regex=False)
        .str.replace("'", "", regex=False)
        .str.replace("/", "-", regex=False)
        .str.replace(r"\s+\d{1,2}:\d{2}:\d{2}$", "", regex=True)
    )

    # Passo 1: heurística com dayfirst (sem infer_datetime_format)
    d = pd.to_datetime(s, errors="coerce", dayfirst=True)

    # Passo 2: tentativas explícitas
    fmts = [
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]
    mask = d.isna()
    if mask.any():
        for fmt in fmts:
            try_d = pd.to_datetime(s[mask], format=fmt, errors="coerce")
            # preenche somente onde continua NaT
            d.loc[mask] = try_d
            mask = d.isna()
            if not mask.any():
                break

    return d

_amount_ptbr_re = re.compile(r"[^0-9,.\-]")

def _clean_amount_series(s: pd.Series) -> pd.Series:
    """
    Remove símbolos, trata ponto de milhar e padroniza vírgula para ponto.
    - Se houver vírgula, assume pt-BR: remove pontos, troca vírgula por ponto.
    - Caso contrário, usa ponto como decimal.
    """
    s = (
        s.astype(str)
        .str.strip()
        .str.replace('"', "", regex=False)
        .str.replace("'", "", regex=False)
        .str.replace(_amount_ptbr_re, "", regex=True)
    )

    has_comma = s.str.contains(",", regex=False)
    if has_comma.any():
        s.loc[has_comma] = (
            s.loc[has_comma]
            .str.replace(".", "", regex=False)   # remove milhar
            .str.replace(",", ".", regex=False) # vírgula -> ponto
        )

    return pd.to_numeric(s, errors="coerce")

def load_and_validate_csv(path: str) -> Tuple[pd.DataFrame, List[str]]:
    errors: List[str] = []
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    try:
        df = _read_csv_smart(path)
    except Exception as e:
        raise RuntimeError(f"Erro ao ler o CSV: {e}")

    # normaliza cabeçalhos
    df.columns = df.columns.str.strip().str.lower()
    cols = set(df.columns)

    # mapeamento de aliases -> colunas reais no arquivo
    colmap: dict[str, Optional[str]] = {}
    for target, cands in ALIASES.items():
        colmap[target] = _find_col(cols, cands)

    # checa obrigatórios mínimos (mesmo via alias)
    missing_min = [k for k in MANDATORY_AFTER_MAP if colmap.get(k) is None]
    if missing_min:
        raise ValueError(f"Colunas essenciais ausentes no CSV (mesmo via aliases): {missing_min}")

    # constrói dataframe normalizado
    out = pd.DataFrame()
    for target in ALIASES.keys():
        src = colmap.get(target)
        out[target] = df[src].astype(str).str.strip() if src else pd.NA

    # datas (robusto, sem warning)
    out["date"] = _parse_date_series(out["date"])
    n_invalid_date = int(out["date"].isna().sum())
    if n_invalid_date:
        errors.append(f"Datas inválidas em {n_invalid_date} linha(s)")

    # amount (pt-BR, vírgula -> ponto, remove milhar)
    out["amount"] = _clean_amount_series(out["amount"])
    n_invalid_amount = int(out["amount"].isna().sum())
    if n_invalid_amount:
        errors.append(f"Valores inválidos em {n_invalid_amount} linha(s)")

    # normalizações semânticas
    out["status"] = out["status"].astype(str).str.lower()
    out["status"] = out["status"].where(~out["status"].isin([pd.NA, None, "", "nan", "NA", "<NA>"]), "approved")

    out["category"] = out["category"].astype(str).str.upper()

    # currency: default BRL
    out["currency"] = out["currency"].astype(str).str.upper()
    mask_cur = out["currency"].isna() | out["currency"].isin(["", "NAN", "NA", "<NA>"])
    out.loc[mask_cur, "currency"] = "BRL"
    invalid_currency = ~out["currency"].isin(ALLOWED_CURRENCY)
    if int(invalid_currency.sum()):
        errors.append(
            f"Moeda fora do permitido em {int(invalid_currency.sum())} linha(s) — permitido: {sorted(ALLOWED_CURRENCY)}"
        )
        out.loc[invalid_currency, "currency"] = "BRL"

    # type: derivar de category se ausente
    out["type"] = out["type"].astype(str).str.upper()
    type_missing = out["type"].isin(["", "NAN", "NA", "<NA>"]) | out["type"].isna()
    cat = out["category"].fillna("").str.upper()
    derived = pd.Series("DEBIT", index=out.index)
    derived[cat.str.contains("CRED", na=False)] = "CREDIT"  # pega CREDIT, CRÉDITO, CREDITO, etc.
    out.loc[type_missing, "type"] = derived

    invalid_type = ~out["type"].isin(ALLOWED_TYPE)
    if int(invalid_type.sum()):
        errors.append(
            f"Tipo fora do permitido em {int(invalid_type.sum())} linha(s) — permitido: {sorted(ALLOWED_TYPE)}"
        )
        out.loc[invalid_type, "type"] = "DEBIT"

    # merchant_id como string (preserva zeros/formatos)
    out["merchant_id"] = out["merchant_id"].astype(str)

    # network numérico opcional
    out["network"] = pd.to_numeric(out["network"], errors="coerce").astype("Int64")

    # descarta linhas realmente inviáveis (typo corrigido: usa 'dropped' corretamente)
    drop_mask = out["id"].isna() | out["date"].isna() | out["amount"].isna() | out["merchant_id"].isna()
    dropped = int(drop_mask.sum())
    if dropped:
        errors.append(f"Linhas descartadas por invalidez: {dropped}")
    out = out.loc[~drop_mask].copy()

    return out, errors
