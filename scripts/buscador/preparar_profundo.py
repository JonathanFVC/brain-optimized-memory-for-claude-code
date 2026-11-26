"""Prepara el modo --profundo de buscar_sesiones.py (una sola vez por equipo). Uso: python3 -I scripts/buscador/preparar_profundo.py
1) Entorno aislado ~/.memoria-local/profundo/venv (solo ruedas, versiones de requirements-profundo.txt)   [paso con red, solo si no existe]
2) Dos modelos (multilingual-e5-small y gte-multilingual-reranker-base) con commit fijado y huellas SHA-256 verificadas   [paso con red, solo si no existen]
3) Manifiesto de huellas (manifiesto.json) y modelos de SOLO LECTURA.
4) BLINDAJE AUTOMÁTICO al terminar: se comprueba que los modelos no traen código ejecutable; se instalan aislar_red.pth y aislar_red.py en el entorno (sin red para cualquier uso de ese Python, aun con -I); se comprueba que sockets, DNS, TCP y UDP
   están bloqueados y que los dos modelos funcionan sin red; en macOS se comprueba que sandbox-exec bloquea aun una conexión de bajo nivel y se marcan los archivos de los modelos como inmutables. Solo entonces se escribe aislado.ok.
Desde ese momento no hay forma de conectarse: volver a correr este script no hace nada ("ya está aislado"); para reinstalar o actualizar hay que pedirlo con --reinstalar (necesita red y vuelve a blindar al terminar).
Para borrarlo todo: chflags -R nouchg ~/.memoria-local/profundo (macOS), chmod -R u+w ~/.memoria-local/profundo y borrar la carpeta."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PROF = Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local") / "profundo"
MODELOS = ["intfloat__multilingual-e5-small", "Alibaba-NLP__gte-multilingual-reranker-base"]
ap = argparse.ArgumentParser(); ap.add_argument("--reinstalar", action="store_true"); a = ap.parse_args()
PROF.mkdir(parents=True, exist_ok=True); os.chmod(PROF, 0o700)
BLINDAJE = '''# Instalado por preparar_profundo.py al terminar la instalación: ESTE ENTORNO NO PUEDE CONECTARSE A INTERNET (ni siquiera si se corre su Python directamente).
import os, socket
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1")
def _sin_red(*a, **k):
    raise OSError("sin red: este entorno quedó aislado al instalarse (aislar_red.pth); reinstalar exige preparar_profundo.py --reinstalar")
_AF = getattr(socket, "AF_UNIX", None); _c, _ce, _s = socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto
def _connect(self, *a, **k):
    return _c(self, *a, **k) if self.family == _AF else _sin_red()
def _connect_ex(self, *a, **k):
    return _ce(self, *a, **k) if self.family == _AF else _sin_red()
def _sendto(self, *a, **k):
    return _s(self, *a, **k) if self.family == _AF else _sin_red()
socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto = _connect, _connect_ex, _sendto
socket.create_connection = _sin_red; socket.getaddrinfo = _sin_red
'''


def _desbloquear():
    """Quita el aislamiento instalado (solo para --reinstalar): aislar_red, bandera inmutable y permisos de escritura."""
    sc = subprocess.run([str(PROF / "venv" / "bin" / "python"), "-I", "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], capture_output=True, text=True).stdout.strip()
    if sc: [(Path(sc) / n).unlink(missing_ok=True) for n in ("aislar_red.py", "aislar_red.pth", "sitecustomize.py")]
    if sys.platform == "darwin": subprocess.run(["chflags", "-R", "nouchg", str(PROF / "modelos")], capture_output=True)
    subprocess.run(["chmod", "-R", "u+w", str(PROF / "modelos")], capture_output=True); shutil.rmtree(PROF / "modelos", ignore_errors=True); (PROF / "aislado.ok").unlink(missing_ok=True)


if (PROF / "aislado.ok").exists():
    if not a.reinstalar:
        print("Ya está instalado y AISLADO de internet. Para reinstalar (necesita red; desbloquea el aislamiento y lo vuelve a poner al terminar): preparar_profundo.py --reinstalar"); sys.exit(0)
    _desbloquear(); print("aislamiento anterior retirado; se reinstala")
py = PROF / "venv" / "bin" / "python"
if not py.exists():
    subprocess.run([sys.executable, "-m", "venv", str(PROF / "venv")], check=True)
    env = dict(os.environ, PIP_DISABLE_PIP_VERSION_CHECK="1")
    subprocess.run([str(py), "-I", "-m", "pip", "install", "--only-binary=:all:", "-r", str(AQUI / "requirements-profundo.txt")], check=True, env=env)
chk = subprocess.run([str(py), "-I", "-c", "import torch, transformers, sentence_transformers; print('entorno ok: torch', torch.__version__)"], capture_output=True, text=True)
print(chk.stdout.strip() or chk.stderr.strip()[-300:]); 
if chk.returncode: sys.exit("ALTO: el entorno no importa los paquetes")
sub = PROF / "modelos"; sub.mkdir(exist_ok=True)
falta = [m for m in MODELOS if not (sub / m / "config.json").exists()]
if [m for m in MODELOS if not (sub / m / "config.json").exists()]:
    subprocess.run([str(py), "-I", str(AQUI / "descargar_modelos_profundo.py")], check=True)
    for m in MODELOS:  # el descargador deja .cache y .gitignore de Hugging Face: no son parte del modelo
        shutil.rmtree(sub / m / ".cache", ignore_errors=True); (sub / m / ".gitignore").unlink(missing_ok=True)
for m in MODELOS:  # por si una copia previa trae restos
    for p in (sub / m / ".cache", sub / m / ".gitignore"):
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()
arch = {}
for m in MODELOS:
    for p in sorted((sub / m).rglob("*")):
        if p.is_file():
            os.chmod(p, 0o644); st = p.stat(); arch[str(p.relative_to(PROF))] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns, "sha256": sha(p)}
(PROF / "manifiesto.json").write_text(json.dumps({"creado": time.strftime("%Y-%m-%d %H:%M"), "modelos": MODELOS, "archivos": arch}, indent=1), encoding="utf-8")
for p in sorted(sub.rglob("*"), reverse=True):  # solo lectura: archivos 0444 y carpetas 0555
    os.chmod(p, 0o444 if p.is_file() else 0o555)
os.chmod(sub, 0o555)
print(f"huellas listas: {len(arch)} archivos en {PROF / 'manifiesto.json'}; modelos de solo lectura en {sub}")


def blindar():
    """ÚLTIMO PASO (automático): deja los modelos y el entorno sin forma de conectarse a internet y lo comprueba. Si algo falla, la instalación NO queda marcada como lista."""
    print("== blindaje: aislando los modelos de internet")
    codigo = [p for p in sub.rglob("*") if p.is_file() and (p.suffix.lower() in {".py", ".so", ".dylib", ".pkl", ".pickle", ".bin", ".pt", ".pth", ".onnx", ".sh"})]
    remoto = [p for p in sub.rglob("config.json") if "auto_map" in p.read_text(encoding="utf-8", errors="ignore")]
    if codigo or remoto: sys.exit(f"ALTO: los modelos traen código ejecutable ({[str(p.relative_to(PROF)) for p in codigo + remoto][:4]}); no se aíslan ni se usan")
    print("   1) los modelos no traen código ejecutable (ni .py, .bin, pickle ni auto_map)")
    purelib = subprocess.run([str(py), "-I", "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], capture_output=True, text=True).stdout.strip()
    (Path(purelib) / "aislar_red.py").write_text(BLINDAJE, encoding="utf-8"); (Path(purelib) / "aislar_red.pth").write_text("import aislar_red\n", encoding="utf-8")  # un .pth se procesa siempre al arrancar (el sitecustomize de Homebrew lo taparía)
    print(f"   2) entorno aislado: aislar_red.pth y aislar_red.py en {purelib} (se aplican a cualquier uso de ese Python, aun con -I)")
    prueba = f"""
import os, socket
fallos = []
for nombre, f in [("connect", lambda: socket.create_connection(("1.1.1.1", 443), timeout=3)), ("dns", lambda: socket.getaddrinfo("huggingface.co", 443)),
                  ("tcp", lambda: socket.socket().connect(("1.1.1.1", 443))), ("udp", lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b"x", ("1.1.1.1", 53)))]:
    try: f(); fallos.append(nombre)
    except OSError: pass
assert not fallos, "conexión NO bloqueada: " + str(fallos)
assert os.environ.get("HF_HUB_OFFLINE") == "1" and os.environ.get("TRANSFORMERS_OFFLINE") == "1"
from sentence_transformers import CrossEncoder, SentenceTransformer
v = SentenceTransformer({str(sub / MODELOS[0])!r}, device="cpu", local_files_only=True, trust_remote_code=False).encode(["query: hola"])
s = CrossEncoder({str(sub / MODELOS[1])!r}, device="cpu", local_files_only=True, trust_remote_code=False).predict([("hola", "saludo")])
print("OK", len(v[0]), float(s[0]))
"""
    r = subprocess.run([str(py), "-I", "-c", prueba], capture_output=True, text=True)
    if r.returncode or "OK" not in r.stdout: sys.exit(f"ALTO: la comprobación de aislamiento falló: {(r.stderr or r.stdout)[-300:]}")
    print("   3) comprobado: sockets, DNS, TCP y UDP bloqueados; los dos modelos cargan y funcionan sin red")
    sb = "/usr/bin/sandbox-exec"
    if os.path.exists(sb):
        bypass = "import _socket; s = _socket.socket(); s.connect(('1.1.1.1', 443)); print('SALIO')"
        r = subprocess.run([sb, "-p", "(version 1)(allow default)(deny network*)", str(py), "-I", "-c", bypass], capture_output=True, text=True)
        if "SALIO" in r.stdout or r.returncode == 0: sys.exit("ALTO: el aislamiento del sistema (sandbox-exec) no bloqueó una conexión de bajo nivel")
        print("   4) comprobado: el sistema (sandbox-exec) bloquea aun una conexión de bajo nivel que salta el bloqueo de Python")
    else:
        print("   4) AVISO: no hay aislamiento de red del sistema aquí (sandbox-exec en macOS; unshare o bwrap en Linux): sin él, buscar_sesiones.py se niega a correr los modelos salvo BUSCADOR_PERMITIR_SIN_SANDBOX=1")
    for p in sorted(sub.rglob("*"), reverse=True): os.chmod(p, 0o444 if p.is_file() else 0o555)
    os.chmod(sub, 0o555)
    if sys.platform == "darwin": subprocess.run(["chflags", "-R", "uchg", str(sub)], capture_output=True); print("   5) archivos de los modelos de solo lectura e inmutables (chflags uchg)")
    (PROF / "aislado.ok").write_text(time.strftime("%Y-%m-%d %H:%M") + "\n", encoding="utf-8")
    print("LISTO: los modelos quedaron AISLADOS de internet. Para reinstalar o actualizar (necesita red): preparar_profundo.py --reinstalar")


blindar()
