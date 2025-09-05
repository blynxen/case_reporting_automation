
import pandas as pd
from typing import Tuple

def apply_business_rules(df: pd.DataFrame, min_amount: float = 1.00) -> Tuple[pd.DataFrame, dict]:
    summary = {
        "rows_in": len(df),
        "duplicates_removed": 0,
        "below_threshold_excluded": 0
    }

    df_before = len(df)
    df = df.drop_duplicates(subset="id")
    summary["duplicates_removed"] = df_before - len(df)

    df_before = len(df)
    df = df[df["amount"] >= min_amount]
    summary["below_threshold_excluded"] = df_before - len(df)

    df = df[[
        "id", "status", "date", "amount", "currency",
        "type", "merchant_id", "network", "category"
    ]]

    return df, summary
