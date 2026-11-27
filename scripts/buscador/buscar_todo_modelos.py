"""BUSCAR TODO (2026-11-26): una consulta, dos fuentes, un solo arranque. Corre dentro del entorno aislado (sin red; lo lanza buscar_todo.py dentro de sandbox-exec).
📁 Carpeta = V1 Profunda (buscar.py + e5 + gte) · 💬 Conversaciones = V2 Máxima (V2 + e5 + gte + Qwen3 en los 5 mejores). Con --urgente (o --ligero): V1 Ligera (buscar.py + gte) y V2 Ligera (V2 + gte), sin e5 ni Qwen3.
Los modelos se cargan una sola vez y se comparten. Salida: k resultados por fuente (3 por defecto), etiquetados."""
import argparse, importlib.util, os, re, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def cargar(nombre, archivo):
    sp = importlib.util.spec_from_file_location(nombre, AQUI / archivo); m = importlib.util.module_from_spec(sp); sys.modules[nombre] = m; sp.loader.exec_module(m); return m


bp = cargar("buscar_profundo_mod", "buscar_profundo.py"); bs = bp.bs  # bloquea la red y fija el modo sin conexión ANTES de importar torch
B = cargar("buscar_v1_mod", "buscar.py"); CP = cargar("carpeta_profunda_mod", "buscar_carpeta_profundo.py")


def main():
    ap = argparse.ArgumentParser(description="Busca en la carpeta (V1) y en las conversaciones (V2) a la vez.")
    ap.add_argument("pregunta"); ap.add_argument("-k", type=int, default=3)
    ap.add_argument("--excluir", nargs="*", default=[], help="prefijos de uuid de sesiones a no indexar (p. ej. la sesión actual)")
    ap.add_argument("--urgente", "--ligero", dest="urgente", action="store_true", help="modo rápido: gte sin e5 ni Qwen3, en las dos fuentes")
    ap.add_argument("--solo", choices=["carpeta", "conversaciones"]); ap.add_argument("--sesiones", default=str(bs.SES_DEF), help="carpeta de .jsonl de sesiones (por defecto, las de este proyecto)"); ap.add_argument("--raiz", default=str(AQUI.parents[1]), help="carpeta del proyecto a buscar (V1)"); ap.add_argument("--sin-sync", action="store_true"); ap.add_argument("--ocultar", action="store_true")
    a = ap.parse_args(); T = {}; t0 = time.time(); raiz = Path(a.raiz)
    bp.LIGERO = a.urgente; bp.MAXIMO = (not a.urgente) and (bp.QWEN / "config.json").exists(); bp.verificar_modelos()
    con = bs.abrir(bs.DB_DEF)
    if not a.sin_sync: bs.sincronizar(con, a.sesiones, a.excluir)
    S = bp.preparar(con); T["carga de modelos y sesiones"] = time.time() - t0
    if a.solo != "carpeta":
        t = time.time(); r = bp.buscar_p(con, a.pregunta, k=a.k, ocultar=a.ocultar); T["conversaciones"] = time.time() - t
        nombre = "V2 Ligera" if a.urgente else ("V2 Máxima" if bp.MAXIMO else "V2 Profunda")
        print(f"== 💬 Conversaciones ({nombre}) ==")
        for i, x in enumerate(r["resultados"][:a.k], 1):
            print(f"{i}. [{x['sesion']}:L{x['linea']}] {x['fecha']} · {x['titulo'][:60]} · confianza {x['confianza']} ({x['cobertura']})\n   {x['fragmento']}")
        if not r["resultados"]: print("Sin resultados.")
    if a.solo != "conversaciones":
        t = time.time(); ci = B.abrir(os.environ.get("BUSCADOR_DB", str(Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local") / "index.db")))
        if not a.sin_sync: B.sincronizar(ci, raiz, False)
        carpeta = CP.Carpeta(B, ci, raiz, bp.PROF / "vectores_carpeta.db", None if a.urgente else S["e5"], S["ce"]); carpeta.preparar(); T["índice y vectores de la carpeta"] = time.time() - t
        t = time.time(); filas = carpeta.buscar(a.pregunta, "ligero" if a.urgente else "profundo"); T["carpeta"] = time.time() - t
        fr, co, pal, ext = B.terminos_nuevos(a.pregunta, raiz); terminos = fr + [re.sub(r"[_.]", " ", c) for c in co] + pal + ext
        print(f"== 📁 Carpeta ({'V1 Ligera' if a.urgente else 'V1 Profunda'}) ==")
        vistos, n = set(), 0
        for path, l1, l2, enc, body, _ in filas:
            if path in vistos: continue
            vistos.add(path); n += 1; res = B.resumen(raiz, path) if n <= 2 else ""
            print(f"{n}. {path}:L{l1}-L{l2} | {enc[:90]}" + (f"\n   ↳ {res}" if res else "") + f"\n   {B.fragmento(body, terminos, ocultar=a.ocultar)}")
            if n >= a.k: break
        if n == 0: print("Sin resultados.")
    print("→ Es un mapa: abre el rango citado (ruta:línea o sesión:línea), mira la fecha y verifica el estado vivo.")
    print("[tiempos] " + " · ".join(f"{k} {v:.1f} s" for k, v in T.items()) + f" · total {time.time() - t0:.1f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
