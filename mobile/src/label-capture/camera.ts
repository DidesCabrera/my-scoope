import type { FocusMode } from "expo-camera";

// Expo Camera 57 maps `off` to AVCaptureDevice.continuousAutoFocus.
// `on` performs a single autofocus operation and then locks the lens.
export const LABEL_CAMERA_AUTOFOCUS: FocusMode = "off";
export const LABEL_CAMERA_FOCUS_SETTLE_MS = 700;
export const LABEL_CAMERA_MAX_ZOOM = 0.15;
export const LABEL_CAMERA_ZOOM_STEP = 0.025;
