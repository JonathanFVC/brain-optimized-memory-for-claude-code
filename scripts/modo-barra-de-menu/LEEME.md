# Icono de la barra de menú para elegir el modo de búsqueda (macOS) · Menu-bar icon to pick the search mode (macOS)

**ES:** muestra los cuatro modos (Ultra ligero, Ligero, Profundo, Máximo) y escribe el modo base en `~/.memoria-local/modo`; `buscar_sesiones.py` lo lee cuando no se le pasa ninguna bandera. Una bandera explícita (`--ligero`, `--profundo`, `--maximo`, `--ultraligero`) manda sobre el modo base. Sin red y sin permisos especiales; necesita `swiftc` (`xcode-select --install`).
```
./construir.sh                      # compila a ~/.memoria-local/app (o a la carpeta que le des)
open ~/.memoria-local/app/"Modo de busqueda.app"
./inicio-automatico.sh instalar     # opcional: que arranque al iniciar sesión (quitar / estado)
```
En cualquier sistema, sin icono: `python3 -I scripts/buscador/buscar_sesiones.py --modo ligero` (sin valor muestra el actual).

**EN:** shows the four modes (Ultra-light, Light, Deep, Max) and writes the base mode to `~/.memoria-local/modo`; `buscar_sesiones.py` reads it when no flag is given. An explicit flag (`--ligero`, `--profundo`, `--maximo`, `--ultraligero`) always wins over the base mode. No network, no special permissions; needs `swiftc` (`xcode-select --install`). Same commands as above. On any system, without the icon: `python3 -I scripts/buscador/buscar_sesiones.py --modo ligero` (values: `ultraligero | ligero | profundo | maximo`; with no value it shows the current one).
