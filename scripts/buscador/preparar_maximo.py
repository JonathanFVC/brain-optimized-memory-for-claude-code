"""Agrega el nivel MÁXIMO (Qwen3-Reranker-0.6B) a una instalación ya hecha por preparar_profundo.py, sin reinstalar el entorno. Uso: python3 -I scripts/buscador/preparar_maximo.py
ÚNICO paso con red de este nivel. 1) abre SOLO la carpeta de modelos (el entorno sigue aislado); 2) descarga Qwen/Qwen3-Reranker-0.6B con commit fijado (e61197ed4502, Apache-2.0), solo json, safetensors y texto, con SHA-256 contra la API de Hugging Face y sin código remoto (auto_map);
3) agrega sus archivos al manifiesto; 4) comprueba SIN red que carga y puntúa (en el entorno sellado y dentro de sandbox-exec); 5) vuelve a sellar todo (solo lectura e inmutable). Si algo falla, quita lo descargado y la instalación queda sellada como estaba."""
import hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

PROF = Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local") / "profundo"; MOD = PROF / "modelos"; MF = PROF / "manifiesto.json"; py = PROF / "venv" / "bin" / "python"
REPO, ESPERADO = "Qwen/Qwen3-Reranker-0.6B", "e61197ed4502"; NOMBRE = REPO.replace("/", "__"); destino = MOD / NOMBRE
PERMITIDO = re.compile(r"(\.json|\.safetensors|\.txt|\.md|\.model|\.jinja)$|^(LICENSE|NOTICE)")
CODIGO = {".py", ".so", ".dylib", ".pkl", ".pickle", ".bin", ".pt", ".pth", ".onnx", ".sh"}


def abrir():
    if sys.platform == "darwin": subprocess.run(["chflags", "-R", "nouchg", str(MOD)], capture_output=True)
    subprocess.run(["chmod", "-R", "u+w", str(MOD)], capture_output=True)


def sellar():
    for p in sorted(MOD.rglob("*"), reverse=True): os.chmod(p, 0o444 if p.is_file() else 0o555)
    os.chmod(MOD, 0o555)
    if sys.platform == "darwin": subprocess.run(["chflags", "-R", "uchg", str(MOD)], capture_output=True)


def api(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "cliente-generico"}), timeout=30) as f: return json.load(f)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def salir(msg):
    shutil.rmtree(destino, ignore_errors=True); sellar(); sys.exit(msg)


if not (PROF / "aislado.ok").exists() or not py.exists(): sys.exit("ALTO: primero instala el modo profundo: python3 -I scripts/buscador/preparar_profundo.py")
mf = json.loads(MF.read_text(encoding="utf-8"))
if (destino / "config.json").exists() and any(k.startswith(f"modelos/{NOMBRE}/") for k in mf["archivos"]):
    print("El nivel Máximo ya está instalado (Qwen3-Reranker-0.6B en el manifiesto)."); sys.exit(0)
abrir(); shutil.rmtree(destino, ignore_errors=True)
try:
    sh = api(f"https://huggingface.co/api/models/{REPO}")["sha"]
    if not sh.startswith(ESPERADO): salir(f"ALTO: {REPO} cambió (esperado {ESPERADO}, hoy {sh[:12]}). No se descarga; revisar.")
    info = api(f"https://huggingface.co/api/models/{REPO}/revision/{sh}?blobs=true")
    destino.mkdir(parents=True)
    for s in info["siblings"]:
        n = s["rfilename"]
        if not PERMITIDO.search(n.split("/")[-1]): continue
        p = destino / n; p.parent.mkdir(parents=True, exist_ok=True); h = hashlib.sha256()
        with urllib.request.urlopen(urllib.request.Request(f"https://huggingface.co/{REPO}/resolve/{sh}/{n}", headers={"User-Agent": "cliente-generico"}), timeout=120) as r, open(p, "wb") as f:
            for b in iter(lambda: r.read(1 << 22), b""): f.write(b); h.update(b)
        esp = (s.get("lfs") or {}).get("sha256")
        if esp and esp != h.hexdigest(): salir(f"ALTO: huella distinta en {n}")
        print(f"   {n:36} {p.stat().st_size / 1e6:9.1f} MB", "huella OK" if esp else "")
except SystemExit: raise
except Exception as e: salir(f"ALTO: la descarga falló ({type(e).__name__}: {str(e)[:120]}); la instalación sigue como estaba")
codigo = [p for p in destino.rglob("*") if p.is_file() and p.suffix.lower() in CODIGO]; remoto = [p for p in destino.rglob("config.json") if "auto_map" in p.read_text(encoding="utf-8", errors="ignore")]
if codigo or remoto: salir(f"ALTO: el modelo trae código ejecutable ({[p.name for p in codigo + remoto][:4]}); no se instala")
for p in sorted(destino.rglob("*")):
    if p.is_file(): os.chmod(p, 0o644); st = p.stat(); mf["archivos"][str(p.relative_to(PROF))] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns, "sha256": sha(p)}
if NOMBRE not in mf["modelos"]: mf["modelos"].append(NOMBRE)
mf["maximo"] = {"modelo": REPO, "commit": sh, "agregado": time.strftime("%Y-%m-%d %H:%M")}
MF.write_text(json.dumps(mf, indent=1), encoding="utf-8")
prueba = f"""
import os
os.environ["HF_HUB_OFFLINE"] = "1"
from sentence_transformers import CrossEncoder
s = CrossEncoder({str(destino)!r}, device="cpu", local_files_only=True, trust_remote_code=False).predict([("¿cómo se llama la capital de México?", "La capital de México es la Ciudad de México."), ("¿cómo se llama la capital de México?", "El queso se hace con leche cuajada.")])
assert s[0] > s[1], s
print("OK", [round(float(x), 3) for x in s])
"""
r = subprocess.run([str(py), "-I", "-c", prueba], capture_output=True, text=True)
if r.returncode or "OK" not in r.stdout: salir(f"ALTO: Qwen3 no carga o no puntúa bien sin red: {(r.stderr or r.stdout)[-300:]}")
print("   comprobado sin red en el entorno sellado: Qwen3 carga y ordena bien un par de prueba", r.stdout.strip())
sb = "/usr/bin/sandbox-exec"
if os.path.exists(sb):
    r = subprocess.run([sb, "-p", "(version 1)(allow default)(deny network*)", str(py), "-I", "-c", prueba], capture_output=True, text=True)
    if r.returncode or "OK" not in r.stdout: salir(f"ALTO: Qwen3 falla dentro de sandbox-exec: {(r.stderr or r.stdout)[-300:]}")
    print("   comprobado también dentro de sandbox-exec (sin red a nivel de sistema)")
sellar()
print(f"LISTO: nivel Máximo instalado ({len([k for k in mf['archivos'] if k.startswith(f'modelos/{NOMBRE}/')])} archivos en el manifiesto), modelos de solo lectura e inmutables. El entorno sigue aislado de internet.")
