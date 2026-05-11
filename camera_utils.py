"""
camera_utils.py
===============
Single source of truth for camera orientation correction.

Call apply_camera_flip(frame) immediately after cap.read() and
BEFORE passing the frame to any detector, recogniser, or display.
That way:
  - BlazeFace / YOLO see the correctly-oriented frame
  - Bounding boxes are in correct pixel space
  - Servo PID error direction is correct
  - The display shows the natural (non-mirrored) view
"""

import cv2
import numpy as np
import config


def apply_camera_flip(frame: np.ndarray) -> np.ndarray:
    """
    Apply horizontal and/or vertical flip based on config flags.

    Args:
        frame: Raw BGR frame from cap.read()

    Returns:
        Corrected frame (same array if no flip needed)
    """
    h_flip = getattr(config, "FLIP_HORIZONTAL", False)
    v_flip = getattr(config, "FLIP_VERTICAL",   False)

    if h_flip and v_flip:
        return cv2.flip(frame, -1)   # both axes
    elif h_flip:
        return cv2.flip(frame, 1)    # horizontal only
    elif v_flip:
        return cv2.flip(frame, 0)    # vertical only
    return frame


def open_camera() -> cv2.VideoCapture:
    """
    Open camera with correct resolution and FPS settings.

    Returns:
        Opened VideoCapture object.
    """
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          config.FPS_TARGET)

    # Disable any built-in mirroring the driver might apply
    # (not all drivers support this property — safe to ignore if it fails)
    try:
        cap.set(cv2.CAP_PROP_SETTINGS, 0)
    except Exception:
        pass

    return cap


def read_frame(cap: cv2.VideoCapture):
    """
    Read one frame and apply orientation correction immediately.

    Returns:
        (success: bool, corrected_frame: np.ndarray)
    """
    ret, frame = cap.read()
    if not ret:
        return False, None
    return True, apply_camera_flip(frame)
