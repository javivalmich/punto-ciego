import UIKit
import AVFoundation
import Capacitor

/// Sesión de audio de la app. Por defecto `.ambient`: los sonidos del juego respetan el interruptor de silencio del iPhone.
/// Mientras el walkie está abierto pasa a `.playAndRecord` (grabar y oír la voz aunque el móvil esté en silencio) y,
/// al cerrarlo, vuelve a `.ambient`. La web lo pide con `Capacitor.Plugins.AudioSesion.modo({ modo: 'walkie' | 'ambient' })`.
enum AudioSesion {
    private(set) static var walkie = false

    static func aplicar(walkie nuevo: Bool) {
        walkie = nuevo
        let s = AVAudioSession.sharedInstance()
        do {
            if nuevo {
                try s.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker, .allowBluetooth, .mixWithOthers])
            } else {
                try s.setCategory(.ambient, mode: .default, options: [])
            }
            try s.setActive(true)
            print("AUDIO sesión \(nuevo ? "playAndRecord" : "ambient") ok (categoría real: \(s.category.rawValue))")
        } catch {
            print("AUDIO sesión error \(error)")
        }
    }

    /// Tras una interrupción (llamada, Siri…) o un reinicio del sistema de audio se vuelve a dejar el modo que tocaba.
    static func vigilar() {
        let nc = NotificationCenter.default
        nc.addObserver(forName: AVAudioSession.interruptionNotification, object: nil, queue: .main) { n in
            if let v = n.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
               AVAudioSession.InterruptionType(rawValue: v) == .ended { aplicar(walkie: walkie) }
        }
        nc.addObserver(forName: AVAudioSession.mediaServicesWereResetNotification, object: nil, queue: .main) { _ in
            aplicar(walkie: walkie)
        }
    }
}

@objc(AudioSesionPlugin)
public class AudioSesionPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "AudioSesionPlugin"
    public let jsName = "AudioSesion"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "modo", returnType: CAPPluginReturnPromise)
    ]

    @objc public func modo(_ call: CAPPluginCall) {
        let walkie = call.getString("modo") == "walkie"
        DispatchQueue.main.async {
            AudioSesion.aplicar(walkie: walkie)
            call.resolve()
        }
    }
}

/// Igual que CAPBridgeViewController, pero registra el plugin local de la sesión de audio.
class PuntoViewController: CAPBridgeViewController {
    override func capacitorDidLoad() {
        bridge?.registerPluginInstance(AudioSesionPlugin())
    }
}
