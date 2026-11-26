"""Descarga SEGURA de los dos modelos del modo --profundo (único paso con red). Lo lanza preparar_profundo.py con el Python del entorno aislado.
Reglas: commit fijado; solo texto/json/.safetensors (nada de .bin, .py, onnx ni pickle); huella SHA-256 de cada archivo grande contra la API de Hugging Face; escribe manifiesto."""
import hashlib, json, os, re, sys, urllib.request
from pathlib import Path
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
from huggingface_hub import snapshot_download

BASE = Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local") / "profundo"; MOD = BASE / "modelos"; MOD.mkdir(parents=True, exist_ok=True)
# repo, prefijo del commit revisado el 2026-11-25 (verifica los commits y las huellas antes de cambiarlos) (None = se toma el actual y se registra)
MODELOS = [("intfloat/multilingual-e5-small", "614241f622f5"), ("Alibaba-NLP/gte-multilingual-reranker-base", "9ba3cad4568f")]
PERMITIDO = re.compile(r"(\.json|\.safetensors|\.txt|\.md|\.model|\.jinja)$|^(LICENSE|NOTICE)")
PROHIBIDO_DIR = ("onnx/", "openvino/", "scripts/", "original/", "assets/", "images/")


def api(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "cliente-generico"}), timeout=30) as f:
        return json.load(f)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


manifiesto = {}
for repo, esperado in MODELOS:
    d = api(f"https://huggingface.co/api/models/{repo}")
    sha = d["sha"]
    if esperado and not sha.startswith(esperado):
        sys.exit(f"ALTO: {repo} cambió desde la revisión (esperado {esperado}…, hoy {sha[:12]}). No se descarga; revisar.")
    info = api(f"https://huggingface.co/api/models/{repo}/revision/{sha}?blobs=true")
    archivos = [s for s in info["siblings"] if PERMITIDO.search(s["rfilename"].split("/")[-1]) and not s["rfilename"].startswith(PROHIBIDO_DIR)]
    omitidos = sorted(s["rfilename"] for s in info["siblings"] if s not in archivos)
    destino = MOD / repo.replace("/", "__")
    print(f"== {repo} @ {sha[:12]}: {len(archivos)} archivos ({sum(s['size'] for s in archivos)/1e9:.2f} GB); omitidos: {omitidos[:8]}{'…' if len(omitidos) > 8 else ''}", flush=True)
    snapshot_download(repo_id=repo, revision=sha, local_dir=str(destino), allow_patterns=[s["rfilename"] for s in archivos])
    ok = True
    for s in archivos:
        esp = (s.get("lfs") or {}).get("sha256")
        if esp:
            real = sha256(destino / s["rfilename"])
            if real != esp:
                ok = False; print("  HUELLA DISTINTA:", s["rfilename"])
    cfg = json.load(open(destino / "config.json"))
    remoto = bool(cfg.get("auto_map"))
    print(f"  huellas SHA-256 {'COINCIDEN' if ok else 'NO COINCIDEN'} · código remoto en config: {'SÍ (ALTO)' if remoto else 'no'}", flush=True)
    if not ok or remoto:
        sys.exit(f"ALTO: {repo} no pasa la verificación.")
    manifiesto[repo] = {"commit": sha, "archivos": len(archivos), "omitidos": omitidos, "huellas_ok": ok, "auto_map": remoto}
(BASE / "manifiesto-descarga.json").write_text(json.dumps(manifiesto, indent=1, ensure_ascii=False))
print("listo: manifiesto en", BASE / "manifiesto-descarga.json")
