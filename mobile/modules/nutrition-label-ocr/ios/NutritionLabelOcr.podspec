Pod::Spec.new do |s|
  s.name           = 'NutritionLabelOcr'
  s.version        = '1.0.0'
  s.summary        = 'On-device nutrition-label OCR for My Scoope'
  s.description    = 'Recognizes nutrition-label text locally with Apple Vision.'
  s.author         = 'My Scoope'
  s.homepage       = 'https://myscoope.com'
  s.platform       = :ios, '16.4'
  s.source         = { git: 'https://github.com/DidesCabrera/my-scoope.git' }
  s.static_framework = true

  s.dependency 'ExpoModulesCore'

  # Swift/Objective-C compatibility
  s.pod_target_xcconfig = {
    'DEFINES_MODULE' => 'YES',
  }

  s.source_files = "**/*.{h,m,mm,swift,hpp,cpp}"
end
