// Draws the app icon (a HUD ring around a graduation cap) and writes an .iconset folder.
// Usage: swift MakeIcon.swift <out.iconset>
import Cocoa

let out = URL(fileURLWithPath: CommandLine.arguments[1])
try? FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)

func draw(_ px: Int) -> Data? {
    guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8, samplesPerPixel: 4,
                                     hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0) else { return nil }
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let s = CGFloat(px), inset = s * 0.1, box = NSRect(x: inset, y: inset, width: s - 2 * inset, height: s - 2 * inset)

    // Rounded square, near-black like the HUD panel.
    let bg = NSBezierPath(roundedRect: box, xRadius: box.width * 0.225, yRadius: box.width * 0.225)
    NSGradient(starting: NSColor(srgbRed: 0.16, green: 0.16, blue: 0.17, alpha: 1), ending: NSColor(srgbRed: 0.02, green: 0.02, blue: 0.03, alpha: 1))?
        .draw(in: bg, angle: -90)
    NSColor(white: 1, alpha: 0.12).setStroke(); bg.lineWidth = s * 0.006; bg.stroke()

    // Ring: grey track and a mint arc, like the pill.
    let c = NSPoint(x: box.midX, y: box.midY), r = box.width * 0.32, w = box.width * 0.055
    let track = NSBezierPath(); track.appendArc(withCenter: c, radius: r, startAngle: 0, endAngle: 360)
    NSColor(srgbRed: 0.17, green: 0.17, blue: 0.18, alpha: 1).setStroke(); track.lineWidth = w; track.stroke()
    let arc = NSBezierPath(); arc.appendArc(withCenter: c, radius: r, startAngle: 90, endAngle: 90 - 250, clockwise: true)
    NSColor(srgbRed: 0.56, green: 0.89, blue: 0.66, alpha: 1).setStroke(); arc.lineWidth = w; arc.lineCapStyle = .round; arc.stroke()

    // Graduation cap in the middle.
    if let cap = NSImage(systemSymbolName: "graduationcap.fill", accessibilityDescription: nil)?
        .withSymbolConfiguration(NSImage.SymbolConfiguration(pointSize: box.width * 0.3, weight: .semibold)
            .applying(NSImage.SymbolConfiguration(paletteColors: [NSColor(srgbRed: 0.04, green: 0.52, blue: 1, alpha: 1)]))) {
        let sz = cap.size
        cap.draw(in: NSRect(x: c.x - sz.width / 2, y: c.y - sz.height / 2, width: sz.width, height: sz.height))
    }
    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using: .png, properties: [:])
}

for base in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let name = scale == 1 ? "icon_\(base)x\(base).png" : "icon_\(base)x\(base)@2x.png"
        try draw(base * scale)?.write(to: out.appendingPathComponent(name))
    }
}
