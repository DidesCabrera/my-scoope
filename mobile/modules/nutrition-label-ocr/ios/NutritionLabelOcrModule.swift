import ExpoModulesCore
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
        defer {
          try? FileManager.default.removeItem(at: imageUri)
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

          promise.resolve([
            "engine": "apple_vision",
            "engineVersion": "1",
            "durationMs": Int((CFAbsoluteTimeGetCurrent() - startedAt) * 1000),
            "observations": observations
          ])
        }
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        request.recognitionLanguages = ["es-CL", "es-ES", "en-US"]

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
