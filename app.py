
import argparse
import os
import sys
from dotenv import load_dotenv

from src.parser import load_and_validate_csv
from src.transformer import apply_business_rules
from src.xml_generator import generate_xml
from src.emailer import send_email
from src.summarizer import save_summary_json
from src.analyzer import generate_insight

load_dotenv()

def plain_text_insight(summary: dict) -> str:
    """Gera um corpo de e-mail determinístico sem IA, com base nas métricas."""
    rows_in = summary.get("rows_in", 0)
    rows_out = summary.get("rows_out", 0)
    dups = summary.get("duplicates_removed", 0)
    below = summary.get("below_threshold_excluded", 0)
    parse_errors = summary.get("parse_errors", []) or []
    parse_line = (
        f"Erros/alertas de parsing: {len(parse_errors)} ocorrência(s)."
        if parse_errors else "Sem erros de parsing reportados."
    )
    return (
        "Relatório mensal de transações:\n"
        f"- Entradas processadas: {rows_in}\n"
        f"- Duplicatas removidas: {dups}\n"
        f"- Abaixo do limite excluídas: {below}\n"
        f"- Saída final (transações válidas): {rows_out}\n"
        f"- {parse_line}\n"
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Relatório transacional mensal")
    parser.add_argument("--month", required=True, help="Formato: YYYY-MM")
    parser.add_argument("--input", required=True, help="Caminho do arquivo CSV de entrada")
    parser.add_argument("--output", required=True, help="Diretório para salvar a saída")
    parser.add_argument("--send-email", action="store_true", help="Se deve enviar o e-mail com o XML")
    parser.add_argument(
        "--ai",
        choices=["auto", "on", "off"],
        default=os.getenv("AI_MODE", "auto"),
        help=(
            "Controle de uso da OpenAI: 'on' força uso; 'off' desativa; 'auto' usa se OPENAI_API_KEY estiver definido."
        ),
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    try:
        print("▶️ Lendo e validando CSV...")
        df, parse_errors = load_and_validate_csv(args.input)
        if parse_errors:
            print("⚠️  Erros/alertas de parsing:")
            for e in parse_errors:
                print("  -", e)

        print("🔧 Aplicando regras de negócio...")
        df_filtered, summary = apply_business_rules(df)
        summary["parse_errors"] = parse_errors
        summary["rows_out"] = len(df_filtered)

        print("📄 Gerando XML...")
        xml_path = generate_xml(df_filtered, args.month, args.output)

        print("🧮 Salvando resumo opcional...")
        save_summary_json(summary, args.output)

        if args.send_email:
            subject = f"Relatório Transacional — {args.month}"

            # Política de uso da IA
            openai_key = os.getenv("OPENAI_API_KEY")
            use_ai = (args.ai == "on") or (args.ai == "auto" and openai_key)

            if use_ai:
                print("🧠 Gerando corpo do e-mail via IA (OpenAI)...")
                try:
                    body = generate_insight(summary)
                except Exception as e:
                    print(f"⚠️ IA indisponível ({e}); usando texto padrão.")
                    body = plain_text_insight(summary)
            else:
                print("📝 IA desativada — gerando corpo de e-mail padrão.")
                body = plain_text_insight(summary)

            print("✉️ Enviando e-mail...")
            try:
                send_email(subject, body, None, xml_path)
                print("✅ E-mail enviado.")
            except Exception as e:
                print(f"❌ Falha ao enviar e-mail: {e}")

        print("✅ Processo concluído com sucesso.")
        return 0

    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
