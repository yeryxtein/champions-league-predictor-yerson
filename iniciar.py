"""Inicia ambos servicios y mantiene sus procesos asociados a esta consola."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser

ROOT=Path(__file__).resolve().parent


def busy(port):
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1",port))==0


def ready(url):
    try:
        with urlopen(url,timeout=1) as response:
            return response.status==200
    except Exception:
        return False


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--no-browser",action="store_true")
    args=parser.parse_args()
    if busy(8000) or busy(8501):
        try:
            with urlopen("http://127.0.0.1:8000/salud",timeout=2) as response:
                running=json.load(response)
            if running.get("proyecto")=="champions-lab" and ready("http://127.0.0.1:8501/_stcore/health"):
                print("Champions Lab ya está abierto: http://127.0.0.1:8501")
                if not args.no_browser:
                    webbrowser.open("http://127.0.0.1:8501")
                return 0
        except Exception:
            pass
        print("Los puertos 8000 o 8501 ya están en uso. Si este proyecto está abierto, entra a http://127.0.0.1:8501.")
        print("No se cerró ningún proceso. Detén la ejecución anterior antes de iniciar otra.")
        return 1
    if not (ROOT/"data/processed/partidos.csv").exists():
        subprocess.run([sys.executable,str(ROOT/"scripts/preparar_datos.py")],check=True,cwd=ROOT)
    processes=[]
    env=os.environ.copy()
    env["PYTHONIOENCODING"]="utf-8"
    try:
        processes.append(subprocess.Popen([sys.executable,"-m","uvicorn","api.main:app","--host","127.0.0.1","--port","8000"],cwd=ROOT,env=env))
        for _ in range(100):
            if processes[0].poll() is not None:
                raise RuntimeError("La API terminó antes de iniciar. Revisa el mensaje anterior.")
            if ready("http://127.0.0.1:8000/salud"):
                break
            time.sleep(.2)
        else:
            raise RuntimeError("La API no respondió a tiempo.")
        processes.append(subprocess.Popen([sys.executable,"-m","streamlit","run","app.py","--server.headless=true","--server.address=127.0.0.1","--server.port=8501","--browser.gatherUsageStats=false"],cwd=ROOT,env=env))
        for _ in range(150):
            if processes[-1].poll() is not None:
                raise RuntimeError("La interfaz terminó antes de iniciar. Revisa el mensaje anterior.")
            if ready("http://127.0.0.1:8501/_stcore/health"):
                break
            time.sleep(.2)
        else:
            raise RuntimeError("La interfaz no respondió a tiempo.")
        print("\nProyecto listo: http://127.0.0.1:8501\nAPI: http://127.0.0.1:8000/docs\nDeja esta consola abierta. Ctrl+C detiene ambos servicios.\n",flush=True)
        if not args.no_browser:
            webbrowser.open("http://127.0.0.1:8501")
        while all(p.poll() is None for p in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        print("Cerrando el proyecto...")
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
    return 0


if __name__=="__main__":
    raise SystemExit(main())
