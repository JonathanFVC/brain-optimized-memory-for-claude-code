#!/bin/zsh
# Inicio automático del icono al iniciar sesión (macOS; LaunchAgent del usuario). Uso: inicio-automatico.sh instalar | quitar | estado
# Sin KeepAlive a propósito: si eliges «Salir» en el menú, el icono no vuelve hasta el próximo inicio de sesión (o abre la app, o: launchctl kickstart gui/$(id -u)/local.memoria-local.modo-de-busqueda).
BASE="${BUSCADOR_HOME:-$HOME/.memoria-local}"; ETQ="local.memoria-local.modo-de-busqueda"; PLIST="$HOME/Library/LaunchAgents/$ETQ.plist"; BIN="$BASE/app/Modo de busqueda.app/Contents/MacOS/BuscadorModo"; DOM="gui/$(id -u)"
case "$1" in
  instalar)
    [ -x "$BIN" ] || { echo "No existe $BIN: compila antes con construir.sh"; exit 1; }
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$PLIST" <<PLISTA
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$ETQ</string>
<key>ProgramArguments</key><array><string>$BIN</string><string>--archivo</string><string>$BASE/modo</string></array>
<key>RunAtLoad</key><true/>
<key>LimitLoadToSessionType</key><string>Aqua</string>
<key>StandardOutPath</key><string>/dev/null</string><key>StandardErrorPath</key><string>/dev/null</string>
</dict></plist>
PLISTA
    plutil -lint "$PLIST" >/dev/null || { echo "plist inválido"; exit 1; }
    launchctl bootout "$DOM/$ETQ" 2>/dev/null; launchctl bootstrap "$DOM" "$PLIST" && echo "Instalado: el icono arrancará en cada inicio de sesión ($PLIST)";;
  quitar)
    launchctl bootout "$DOM/$ETQ" 2>/dev/null; rm -f "$PLIST"; echo "Quitado: el icono ya no arranca solo (si estaba abierto, se cerró)";;
  estado)
    [ -f "$PLIST" ] && echo "plist: instalado" || echo "plist: no instalado"; launchctl print "$DOM/$ETQ" 2>/dev/null | /usr/bin/grep -E "state =|pid =" | head -2; echo "procesos del icono: $(pgrep -f BuscadorModo | wc -l | tr -d ' ')";;
  *) echo "uso: inicio-automatico.sh instalar | quitar | estado"; exit 2;;
esac
