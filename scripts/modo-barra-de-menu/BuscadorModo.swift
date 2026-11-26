// Icono de la barra de menú (macOS) para elegir el MODO BASE de la búsqueda en conversaciones.
// Escribe/lee un archivo de una línea (por defecto ~/.memoria-local/modo) con: ultraligero | ligero | profundo | maximo. buscar_sesiones.py lo lee cuando no se le pasa ninguna bandera.
// Sin red, sin permisos especiales. Uso: BuscadorModo [--archivo <ruta>]  (la ruta alterna sirve si cambiaste BUSCADOR_HOME).
import Cocoa

let archivo: String = {
    let a = CommandLine.arguments
    if let i = a.firstIndex(of: "--archivo"), i + 1 < a.count { return a[i + 1] }
    return NSString(string: "~/.memoria-local/modo").expandingTildeInPath
}()

struct Modo { let clave: String; let titulo: String; let corto: String; let detalle: String }
let modos: [Modo] = [
    Modo(clave: "ultraligero", titulo: "Ultra ligero", corto: "Ultra", detalle: "sin modelos · precisión MRR 0.47 · la más rápida"),
    Modo(clave: "ligero", titulo: "Ligero", corto: "Lig", detalle: "V2 + gte · MRR 0.60"),
    Modo(clave: "profundo", titulo: "Profundo", corto: "Prof", detalle: "V2 + e5 + gte · MRR 0.63"),
    Modo(clave: "maximo", titulo: "Máximo", corto: "Máx", detalle: "+ Qwen3 · MRR 0.66 · el más preciso"),
]

func modoActual() -> String {
    guard let s = try? String(contentsOfFile: archivo, encoding: .utf8) else { return "maximo" }
    var v = s.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    if v == "v2" { v = "ultraligero" }
    return modos.contains { $0.clave == v } ? v : "maximo"
}

func guardar(_ clave: String) {
    let dir = (archivo as NSString).deletingLastPathComponent
    try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
    try? (clave + "\n").write(toFile: archivo, atomically: true, encoding: .utf8)
}

final class App: NSObject, NSApplicationDelegate, NSMenuDelegate {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let menu = NSMenu()

    func applicationDidFinishLaunching(_ n: Notification) {
        menu.delegate = self; item.menu = menu
        reconstruir(); actualizar()
        Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in self?.actualizar() }  // refleja cambios hechos con `--modo`
    }

    func reconstruir() {
        menu.removeAllItems()
        let t = NSMenuItem(title: "Modo base de la búsqueda en conversaciones", action: nil, keyEquivalent: ""); t.isEnabled = false; menu.addItem(t)
        for m in modos {
            let it = NSMenuItem(title: m.titulo + "   —   " + m.detalle, action: #selector(elegir(_:)), keyEquivalent: "")
            it.target = self; it.representedObject = m.clave; menu.addItem(it)
        }
        menu.addItem(.separator())
        let nota = NSMenuItem(title: "Si pides algo urgente, Claude usa Ligero solo esa vez", action: nil, keyEquivalent: ""); nota.isEnabled = false; menu.addItem(nota)
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Salir", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
    }

    @objc func elegir(_ s: NSMenuItem) { if let c = s.representedObject as? String { guardar(c); actualizar() } }

    func actualizar() {
        let a = modoActual(); let m = modos.first { $0.clave == a }!
        if let b = item.button {
            b.image = NSImage(systemSymbolName: "text.magnifyingglass", accessibilityDescription: "Modo de búsqueda")
            b.imagePosition = .imageLeading; b.title = " " + m.corto; b.toolTip = "Búsqueda en conversaciones: " + m.titulo
        }
        for it in menu.items { if let c = it.representedObject as? String { it.state = (c == a) ? .on : .off } }
    }

    func menuWillOpen(_ m: NSMenu) { actualizar() }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)  // sin icono en el Dock
let delegado = App(); app.delegate = delegado; app.run()
