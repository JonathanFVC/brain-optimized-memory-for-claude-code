"""Comprueba que la instalación de los modelos sigue AISLADA de internet. No usa red y no modifica nada. Uso: python3 -I scripts/buscador/verificar_aislamiento.py
Revisa: marca de instalación aislada, entorno sin forma de conectarse (aun usando su Python directamente), modelos sin código ejecutable, huellas de los archivos contra manifiesto.json y aislamiento de red del sistema."""
import hashlib, json, os, subprocess, sys
from pathlib import Path

PROF = Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local") / "profundo"; py = PROF / "venv" / "bin" / "python"; fallas = []


def chequeo(nombre, ok, detalle=""):
    print(("OK   " if ok else "FALLA"), nombre, detalle); fallas.append(nombre) if not ok else None


chequeo("instalación marcada como aislada (aislado.ok)", (PROF / "aislado.ok").exists(), "" if (PROF / "aislado.ok").exists() else "corre preparar_profundo.py")
if py.exists():
    r = subprocess.run([str(py), "-I", "-c", """
import socket, urllib.request, os
ok = []
for f in (lambda: socket.create_connection(("1.1.1.1", 443), timeout=3), lambda: socket.getaddrinfo("huggingface.co", 443), lambda: urllib.request.urlopen("https://huggingface.co", timeout=3)):
    try: f(); ok.append("SALIO")
    except Exception: ok.append("bloqueado")
print(ok, os.environ.get("HF_HUB_OFFLINE"), os.environ.get("TRANSFORMERS_OFFLINE"))"""], capture_output=True, text=True)
    chequeo("el Python del entorno NO puede conectarse (conexión, DNS, urllib) y fuerza el modo sin conexión", "SALIO" not in r.stdout and "bloqueado" in r.stdout and r.stdout.strip().endswith("1 1"), r.stdout.strip()[-60:])
else:
    chequeo("entorno instalado", False, f"no existe {py}")
mod = PROF / "modelos"; codigo = [p for p in mod.rglob("*") if p.is_file() and p.suffix.lower() in {".py", ".so", ".dylib", ".pkl", ".pickle", ".bin", ".pt", ".pth", ".onnx", ".sh"}] if mod.exists() else ["(sin modelos)"]
remoto = [p for p in mod.rglob("config.json") if "auto_map" in p.read_text(encoding="utf-8", errors="ignore")] if mod.exists() else []
chequeo("los modelos no traen código ejecutable (ni .py, .bin, pickle ni auto_map)", not codigo and not remoto, str(codigo + remoto)[:100])
try:
    mf = json.loads((PROF / "manifiesto.json").read_text(encoding="utf-8")); malos = []
    for rel, m in mf["archivos"].items():
        p = PROF / rel
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
        if h.hexdigest() != m["sha256"]: malos.append(rel)
    chequeo(f"huellas SHA-256 de {len(mf['archivos'])} archivos de modelos coinciden con el manifiesto", not malos, str(malos[:3]))
except Exception as e:
    chequeo("manifiesto de huellas", False, f"{type(e).__name__}: {e}")
sb = "/usr/bin/sandbox-exec"
if os.path.exists(sb) and py.exists():
    r = subprocess.run([sb, "-p", "(version 1)(allow default)(deny network*)", str(py), "-I", "-c", "import _socket; s = _socket.socket(); s.connect(('1.1.1.1', 443)); print('SALIO')"], capture_output=True, text=True)
    chequeo("el sistema (sandbox-exec) bloquea aun una conexión de bajo nivel", "SALIO" not in r.stdout and r.returncode != 0)
else:
    chequeo("aislamiento de red del sistema disponible (sandbox-exec; unshare o bwrap en Linux, no probado)", any(os.path.exists(p) for p in ("/usr/bin/unshare", "/usr/bin/bwrap", "/bin/unshare")), "sin él, buscar_sesiones.py se niega a correr los modelos")
print("\n" + ("AISLADO: todo en orden" if not fallas else "PROBLEMAS: " + ", ".join(fallas))); sys.exit(1 if fallas else 0)
