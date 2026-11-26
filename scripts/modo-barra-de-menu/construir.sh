#!/bin/zsh
# Compila el icono de la barra de menú (macOS) y arma «Modo de busqueda.app» (sin Dock, firma ad hoc local).
# Uso: construir.sh [carpeta de salida]   (por defecto: ${BUSCADOR_HOME:-~/.memoria-local}/app)
set -e
BASE="${BUSCADOR_HOME:-$HOME/.memoria-local}"; SALIDA="${1:-$BASE/app}"; AQUI="${0:A:h}"; APP="$SALIDA/Modo de busqueda.app"
command -v swiftc >/dev/null || { echo "Hace falta swiftc (herramientas de línea de comandos de Xcode: xcode-select --install)"; exit 1; }
rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS"
swiftc -O -o "$APP/Contents/MacOS/BuscadorModo" "$AQUI/BuscadorModo.swift"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Modo de busqueda</string><key>CFBundleIdentifier</key><string>local.memoria-local.modo-de-busqueda</string>
<key>CFBundleExecutable</key><string>BuscadorModo</string><key>CFBundlePackageType</key><string>APPL</string><key>CFBundleVersion</key><string>1</string>
<key>LSUIElement</key><true/><key>LSMinimumSystemVersion</key><string>12.0</string>
</dict></plist>
PLIST
codesign --force -s - "$APP" >/dev/null 2>&1 || true
echo "listo: $APP   (ábrela con: open \"$APP\")"
