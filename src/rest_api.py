
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import uvicorn
import subprocess
import os
import sys

app = FastAPI()

@app.post("/run-report")
def run_report(
    month: str = Query(..., description="Formato: YYYY-MM"),
    send_email: bool = Query(False, description="Enviar e-mail ao final"),
    input_path: str = Query("data/transactions.csv"),
    ai: str = Query("auto", regex="^(auto|on|off)$", description="Uso da IA: auto|on|off"),
):
    try:
        output_path = f"outputs/{month.replace('-', '')}"
        os.makedirs(output_path, exist_ok=True)

        cmd = [
            sys.executable, "app.py",
            f"--month={month}", f"--input={input_path}", f"--output={output_path}", f"--ai={ai}"
        ]
        if send_email:
            cmd.append("--send-email")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return JSONResponse(status_code=500, content={
                "status": "error",
                "message": result.stderr.strip()
            })

        return {
            "status": "ok",
            "job_id": month.replace("-", ""),
            "message": "processamento concluído",
            "stdout_tail": result.stdout.strip().splitlines()[-10:],
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    uvicorn.run("src.rest_api:app", host="127.0.0.1", port=8000, reload=True)
