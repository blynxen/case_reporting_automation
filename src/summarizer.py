
import json
from typing import Dict
import os

def save_summary_json(summary: Dict, output_path: str):
    """
    Salva o resumo técnico (métricas de execução) em formato JSON
    """
    path = os.path.join(output_path, "summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return path
