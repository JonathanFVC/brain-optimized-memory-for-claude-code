"""Prueba de la ELECCIÓN del modo base (archivo `modo`, `--modo` y banderas) SIN modelos y SIN tocar tu índice real: sustituye el lanzador de los modelos por una función que imprime la bandera elegida.
Uso: python3 -I tests/test_modo.py"""
import contextlib, importlib.util, io, os, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]; TMP = Path(tempfile.mkdtemp(prefix="memoria-local-modo-"))
QWEN = TMP / "profundo" / "modelos" / "Qwen__Qwen3-Reranker-0.6B"; QWEN.mkdir(parents=True); (QWEN / "config.json").write_text("{}")
os.environ.update(BUSCADOR_HOME=str(TMP), BUSCADOR_MODO_ARCHIVO=str(TMP / "modo"), CLAUDE_PROJECT_DIR=str(TMP))


def cargar(modo_archivo, con_qwen=True):
    (TMP / "modo").unlink(missing_ok=True)
    if modo_archivo is not None: (TMP / "modo").write_text(modo_archivo)
    sp = importlib.util.spec_from_file_location("bs", REPO / "scripts/buscador/buscar_sesiones.py"); bs = importlib.util.module_from_spec(sp); sp.loader.exec_module(bs)
    bs.PROF = TMP / "profundo" if con_qwen else TMP / "sin-qwen"; return bs


def elegir(modo_archivo, args, con_qwen=True):
    bs = cargar(modo_archivo, con_qwen); visto = []; bs.lanzar_profundo = lambda m: (visto.append(m), 0)[1]
    sys.argv = ["x", "pregunta", "--sin-sync", "--sin-registro", "--sesiones", str(TMP)] + args
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try: bs.main()
        except SystemExit: pass
    return visto[0] if visto else "(ultra ligero: sin modelos)"


casos = [(None, [], True, "--maximo"), ("maximo", [], True, "--maximo"), ("profundo", [], True, "--profundo"), ("ligero", [], True, "--ligero"), ("ultraligero", [], True, "(ultra ligero: sin modelos)"), ("v2", [], True, "(ultra ligero: sin modelos)"),
         ("basura", [], True, "--maximo"), (None, [], False, "--profundo"), ("maximo", [], False, "--profundo"),
         ("ligero", ["--maximo"], True, "--maximo"), ("ultraligero", ["--ligero"], True, "--ligero"), ("maximo", ["--ligero"], True, "--ligero"), ("ligero", ["--profundo"], True, "--profundo")]
fallas = []
try:
    for arch, args, qwen, esperado in casos:
        r = elegir(arch, args, qwen); ok = r == esperado; fallas += [] if ok else [str((arch, args))]
        print(("OK   " if ok else "FALLA"), f"archivo={arch!r:13} banderas={args!s:14} Qwen3 instalado={qwen!s:5} → {r}" + ("" if ok else f"   (esperado {esperado})"))
    for valor, esperado in (("ligero", "ligero"), ("v2", "ultraligero")):
        bs = cargar(None); sys.argv = ["x", "--modo", valor]; b = io.StringIO()
        with contextlib.redirect_stdout(b): bs.main()
        ok = b.getvalue().strip() == f"Modo base: {esperado}" and (TMP / "modo").read_text().strip() == esperado; fallas += [] if ok else [f"--modo {valor}"]
        print(("OK   " if ok else "FALLA"), f"--modo {valor} guarda «{esperado}» y lo muestra: {b.getvalue().strip()}")
    bs = cargar("profundo"); sys.argv = ["x", "--modo"]; b = io.StringIO()
    with contextlib.redirect_stdout(b): bs.main()
    ok = b.getvalue().strip() == "Modo base: profundo"; fallas += [] if ok else ["--modo sin valor"]; print(("OK   " if ok else "FALLA"), "--modo sin valor muestra el actual:", b.getvalue().strip())
finally:
    import shutil; shutil.rmtree(TMP, ignore_errors=True)
print("\n" + ("TODO OK" if not fallas else "FALLAS: " + ", ".join(fallas))); sys.exit(1 if fallas else 0)
