"""
Multi-face Kalman filter tracker.

State (8-D): [cx, cy, ar, h,  vcx, vcy, var, vh]
  cx/cy  — bounding-box centre
  ar     — aspect ratio (w/h)
  h      — height
  v*     — respective velocities

Measurement (4-D): [cx, cy, ar, h]

Tracks are matched to detections via greedy IoU.
Unmatched tracks age out after MAX_FRAMES_LOST frames.
"""

import sys
import logging
from typing import List, Tuple, Optional

import cv2
import numpy as np

sys.path.insert(0, "..")
import config

log = logging.getLogger(__name__)

_next_id = 0
def _new_id() -> int:
    global _next_id
    _next_id += 1
    return _next_id


def _to_meas(x1, y1, x2, y2) -> np.ndarray:
    w  = x2 - x1
    h  = y2 - y1
    return np.array([[x1 + w/2], [y1 + h/2], [w/(h+1e-6)], [h]], np.float32)

def _to_bbox(s) -> Tuple[int,int,int,int]:
    cx, cy, ar, h = float(s[0]), float(s[1]), float(s[2]), float(s[3])
    w = ar * h
    return int(cx-w/2), int(cy-h/2), int(cx+w/2), int(cy+h/2)

def _iou(a, b) -> float:
    ix1, iy1 = max(a[0],b[0]), max(a[1],b[1])
    ix2, iy2 = min(a[2],b[2]), min(a[3],b[3])
    inter = max(0, ix2-ix1) * max(0, iy2-iy1)
    if inter == 0: return 0.0
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / (ua + 1e-6)


class Track:
    def __init__(self, bbox, name="Unknown", conf=0.0):
        self.id          = _new_id()
        self.name        = name
        self.confidence  = conf
        self.age         = 0
        self.lost        = 0
        self._kf         = self._make_kf(bbox)

    def _make_kf(self, bbox):
        kf = cv2.KalmanFilter(8, 4)
        kf.transitionMatrix = np.eye(8, dtype=np.float32)
        for i in range(4): kf.transitionMatrix[i, i+4] = 1
        kf.measurementMatrix = np.zeros((4, 8), np.float32)
        for i in range(4): kf.measurementMatrix[i, i] = 1
        kf.processNoiseCov     = np.eye(8, np.float32) * 1e-2
        kf.measurementNoiseCov = np.eye(4, np.float32) * 1e-1
        kf.errorCovPost        = np.eye(8, np.float32)
        kf.statePost[:4]       = _to_meas(*bbox)
        return kf

    def predict(self):
        self._kf.predict()
        self.age += 1
        return _to_bbox(self._kf.statePre)

    def update(self, bbox, name=None, conf=None):
        self._kf.correct(_to_meas(*bbox))
        self.lost = 0
        if name and name != "Unknown":
            self.name       = name
            self.confidence = conf or self.confidence

    def bbox(self):
        return _to_bbox(self._kf.statePost)

    def center(self):
        s = self._kf.statePost
        return float(s[0]), float(s[1])

    @property
    def alive(self):
        return self.lost <= config.MAX_FRAMES_LOST


class Tracker:
    def __init__(self):
        self.tracks: List[Track] = []

    def update(self, detections: list, names=None) -> List[Track]:
        # Predict all tracks
        preds = [t.predict() for t in self.tracks]

        matched_t, matched_d = set(), set()
        if self.tracks and detections:
            iou_mat = np.zeros((len(self.tracks), len(detections)), np.float32)
            for ti, pb in enumerate(preds):
                for di, d in enumerate(detections):
                    iou_mat[ti, di] = _iou(pb, d["bbox"])

            for flat in np.argsort(-iou_mat, axis=None):
                ti, di = divmod(int(flat), len(detections))
                if ti in matched_t or di in matched_d:
                    continue
                if iou_mat[ti, di] >= config.IOU_THRESHOLD:
                    n, c = (names[di] if names else ("Unknown", 0.0))
                    self.tracks[ti].update(detections[di]["bbox"], n, c)
                    matched_t.add(ti); matched_d.add(di)

        for ti, t in enumerate(self.tracks):
            if ti not in matched_t:
                t.lost += 1

        for di, d in enumerate(detections):
            if di not in matched_d:
                n, c = (names[di] if names else ("Unknown", 0.0))
                self.tracks.append(Track(d["bbox"], n, c))

        self.tracks = [t for t in self.tracks if t.alive]
        return self.tracks

    def reset(self):
        self.tracks = []

    @property
    def primary(self) -> Optional[Track]:
        if not self.tracks:
            return None
        return max(self.tracks, key=lambda t: (t.bbox()[2]-t.bbox()[0])*(t.bbox()[3]-t.bbox()[1]))
