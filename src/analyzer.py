
import os
import json
from openai import OpenAI


def generate_insight(summary_dict: dict) -> str:
    """
    Usa a OpenAI API para gerar um parágrafo técnico com base no dicionário de métricas.
    Requer OPENAI_API_KEY definido. Levanta exceção se a chave não existir.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY ausente — IA desativada.")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    prompt = (
        "Com base nas métricas abaixo, gere um parágrafo conciso e técnico para incluir no corpo de um "
        "e-mail mensal de análise de transações. Destaque alertas e insights relevantes.\n\n"
        f"{json.dumps(summary_dict, indent=2, ensure_ascii=False)}\n\n"
        "Seja objetivo, direto e use linguagem clara. Evite floreios."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Você é um analista técnico de dados."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=250,
        temperature=0.4,
    )

    return resp.choices[0].message.content.strip()
