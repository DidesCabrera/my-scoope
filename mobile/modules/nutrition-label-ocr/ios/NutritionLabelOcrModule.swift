import ExpoModulesCore
import CoreImage
import Foundation
import ImageIO
import UIKit
import Vision

private final class NutritionLabelImageException: GenericException<String> {
  override var reason: String {
    "Could not read nutrition-label image at: \(param)"
  }
}

private final class NutritionLabelRecognitionException: GenericException<String> {
  override var reason: String {
    "Nutrition-label recognition failed: \(param)"
  }
}

public class NutritionLabelOcrModule: Module {
  public func definition() -> ModuleDefinition {
    Name("NutritionLabelOcr")

    AsyncFunction("recognizeAsync") { (imageUri: URL, promise: Promise) in
      DispatchQueue.global(qos: .userInitiated).async {
        guard imageUri.isFileURL,
          let image = UIImage(contentsOfFile: imageUri.path),
          let cgImage = image.cgImage else {
          promise.reject(NutritionLabelImageException(imageUri.absoluteString))
          return
        }

        let startedAt = CFAbsoluteTimeGetCurrent()
        let request = VNRecognizeTextRequest { request, error in
          if let error {
            promise.reject(NutritionLabelRecognitionException(error.localizedDescription))
            return
          }
          let observations = (request.results as? [VNRecognizedTextObservation] ?? [])
            .compactMap { observation -> [String: Any]? in
              guard let candidate = observation.topCandidates(1).first else {
                return nil
              }
              let bounds = observation.boundingBox
              return [
                "text": candidate.string,
                "confidence": candidate.confidence,
                "boundingBox": [
                  "x": bounds.minX,
                  "y": 1 - bounds.maxY,
                  "width": bounds.width,
                  "height": bounds.height
                ]
              ]
            }

          let visionObservations = request.results as? [VNRecognizedTextObservation] ?? []
          let confidences = visionObservations.compactMap { $0.topCandidates(1).first?.confidence }
          let averageConfidence = confidences.isEmpty
            ? 0
            : confidences.reduce(0, +) / Float(confidences.count)
          let textCoverage = min(
            1,
            visionObservations.reduce(0) { total, observation in
              total + Float(observation.boundingBox.width * observation.boundingBox.height)
            }
          )
          let visualQuality = imageQuality(cgImage: cgImage)

          promise.resolve([
            "engine": "apple_vision",
            "engineVersion": "3",
            "durationMs": Int((CFAbsoluteTimeGetCurrent() - startedAt) * 1000),
            "observations": observations,
            "imageQuality": [
              "brightness": visualQuality.brightness,
              "sharpness": visualQuality.sharpness,
              "textObservationCount": visionObservations.count,
              "averageTextConfidence": averageConfidence,
              "textCoverage": textCoverage
            ]
          ])
        }
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        request.recognitionLanguages = ["es-CL", "es-ES", "en-US"]
        request.customWords = [
          "Información nutricional",
          "Energía",
          "Proteínas",
          "Carbohidratos",
          "Grasas totales",
          "Grasas saturadas",
          "Azúcares",
          "Fibra alimentaria",
          "Sodio",
          "Porción"
        ]

        do {
          let handler = VNImageRequestHandler(
            cgImage: cgImage,
            orientation: image.imageOrientation.cgImagePropertyOrientation,
            options: [:]
          )
          try handler.perform([request])
        } catch {
          promise.reject(NutritionLabelRecognitionException(error.localizedDescription))
        }
      }
    }
  }
}

private func imageQuality(cgImage: CGImage) -> (brightness: Float, sharpness: Float) {
  let context = CIContext()
  let image = CIImage(cgImage: cgImage)
  let brightness = averageLuminance(image: image, context: context)
  guard let edges = CIFilter(
    name: "CIEdges",
    parameters: [kCIInputImageKey: image, kCIInputIntensityKey: 1.0]
  )?.outputImage else {
    return (brightness, 0)
  }
  return (brightness, averageLuminance(image: edges, context: context))
}

private func averageLuminance(image: CIImage, context: CIContext) -> Float {
  guard !image.extent.isEmpty,
    let average = CIFilter(
      name: "CIAreaAverage",
      parameters: [kCIInputImageKey: image, kCIInputExtentKey: CIVector(cgRect: image.extent)]
    )?.outputImage else {
    return 0
  }
  var pixel = [UInt8](repeating: 0, count: 4)
  context.render(
    average,
    toBitmap: &pixel,
    rowBytes: 4,
    bounds: CGRect(x: 0, y: 0, width: 1, height: 1),
    format: .RGBA8,
    colorSpace: CGColorSpaceCreateDeviceRGB()
  )
  return (0.2126 * Float(pixel[0]) + 0.7152 * Float(pixel[1]) + 0.0722 * Float(pixel[2])) / 255
}

private extension UIImage.Orientation {
  var cgImagePropertyOrientation: CGImagePropertyOrientation {
    switch self {
    case .up: return .up
    case .upMirrored: return .upMirrored
    case .down: return .down
    case .downMirrored: return .downMirrored
    case .left: return .left
    case .leftMirrored: return .leftMirrored
    case .right: return .right
    case .rightMirrored: return .rightMirrored
    @unknown default: return .up
    }
  }
}
