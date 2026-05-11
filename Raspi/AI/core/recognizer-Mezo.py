"""
Face recognizer — MobileFaceNet TFLite (tiny model, ~4 MB).

MobileFaceNet is a lightweight face embedding network trained with ArcFace
loss. It produces a 512-d embedding vector in ~30 ms on RPi4.

Backend: MobileFaceNet TFLite (tflite-runtime or tensorflow).
If the model file is missing, run:  python setup.py

Usage:
    rec = FaceRecognizer()
    name, conf = rec.identify(face_crop_bgr)   # 112×112 aligned crop
"""

import os
import sys
import pickle
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import cv2
import numpy as np

sys.path.insert(0, "..")
import config
from core.detector import align_face

log = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# TFLite backend — MobileFaceNet INT8 quantized (~4 MB)
# ════════════════════════════════════════════════════════════════════════════

class _TFLiteBackend:
    def __init__(self, model_path: str):
        interp = self._load(model_path)
        interp.allocate_tensors()
        self._interp   = interp
        self._in_idx   = interp.get_input_details()[0]["index"]
        self._out_idx  = interp.get_output_details()[0]["index"]
        self._in_shape = interp.get_input_details()[0]["shape"]   # [1,112,112,3]
        self._clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        log.info("Recognizer: MobileFaceNet TFLite (tiny model) — %s", model_path)

    @staticmethod
    def _load(path: str):
        try:
            import tflite_runtime.interpreter as tflite
            return tflite.Interpreter(model_path=path)
        except ImportError:
            pass
        try:
            import tensorflow as tf
            return tf.lite.Interpreter(model_path=path)
        except ImportError:
            raise RuntimeError("Install tflite-runtime or tensorflow to use TFLite backend")

    def embed(self, face_bgr: np.ndarray) -> np.ndarray:
        """Return normalised 512-d embedding from a BGR face crop."""
        size = self._in_shape[1]   # usually 112
        img  = cv2.resize(face_bgr, (size, size))

        # CLAHE on L-channel: normalises lighting before embedding
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = self._clahe.apply(l)
        img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)
        img = (img - 127.5) / 127.5                 # normalize to [-1, 1]
        img = img[np.newaxis]                       # (1, 112, 112, 3)

        self._interp.set_tensor(self._in_idx, img)
        self._interp.invoke()
        emb  = self._interp.get_tensor(self._out_idx)[0]
        norm = np.linalg.norm(emb)
        return emb / (norm + 1e-10)


# ════════════════════════════════════════════════════════════════════════════
# InsightFace ONNX backend — fallback when TFLite model not yet downloaded
# ════════════════════════════════════════════════════════════════════════════

class _NullBackend:
    """Used when TFLite model is missing — returns zero embeddings and warns."""
    def __init__(self):
        log.error(
            "MobileFaceNet TFLite model not found. "
            "Run:  python setup.py   to download it (~4 MB). "
            "Recognition will not work until the model is present."
        )

    def embed(self, face_bgr: np.ndarray) -> np.ndarray:
        return np.zeros(512, dtype=np.float32)


# ════════════════════════════════════════════════════════════════════════════
# FaceRecognizer — public class
# ════════════════════════════════════════════════════════════════════════════

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


class FaceRecognizer:
    """
    Identifies faces using MobileFaceNet TFLite embeddings.

    person_embeddings: Dict[name, List[512-d ndarray]]
    """

    def __init__(self):
        self._backend = self._choose_backend()
        self.person_embeddings: Dict[str, List[np.ndarray]] = {}
        self._load_encodings()

    # ── Backend selection ─────────────────────────────────────────────────────

    def _choose_backend(self):
        tflite_path = config.TFLITE_RECOGNIZER
        if os.path.exists(tflite_path):
            try:
                return _TFLiteBackend(tflite_path)
            except Exception as e:
                log.warning("TFLite backend failed (%s) — falling back to null backend", e)
        else:
            log.info("TFLite model not found at %s — run setup.py to download", tflite_path)
        return _NullBackend()

    @property
    def backend_name(self) -> str:
        if isinstance(self._backend, _TFLiteBackend):
            return "MobileFaceNet-TFLite"
        return "unavailable (run setup.py)"

    # ── Encodings persistence ─────────────────────────────────────────────────

    def _load_encodings(self) -> None:
        for path in [config.ENCODINGS_PATH, config.FALLBACK_ENCODINGS]:
            p = Path(path)
            if p.exists():
                self._load_file(p)
                return
        log.warning("No encodings found — run setup.py or enroll faces via the GUI")

    def _load_file(self, path: Path) -> None:
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            if "person_embeddings" in data:
                self.person_embeddings = data["person_embeddings"]
            elif "encodings" in data and "names" in data:
                for name, enc in zip(data["names"], data["encodings"]):
                    self.person_embeddings.setdefault(name, []).append(enc)
            n = sum(len(v) for v in self.person_embeddings.values())
            log.info("Loaded %d embedding(s) for %d person(s) from %s",
                     n, len(self.person_embeddings), path.name)
        except Exception as e:
            log.error("Load encodings failed: %s", e)

    def reload(self) -> None:
        self.person_embeddings = {}
        self._load_encodings()

    def save_encodings(self) -> None:
        path = Path(config.ENCODINGS_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        flat_encs  = [e for embs in self.person_embeddings.values() for e in embs]
        flat_names = [n for n, embs in self.person_embeddings.items() for _ in embs]
        with open(path, "wb") as f:
            pickle.dump({
                "person_embeddings": self.person_embeddings,
                "encodings": flat_encs,
                "names": flat_names,
            }, f)
        log.info("Saved %d person(s) → %s", len(self.person_embeddings), path)

    # ── Enrollment ────────────────────────────────────────────────────────────

    def enroll_face(self, face_bgr: np.ndarray, name: str) -> bool:
        """Enroll a single face crop (any size) under the given name."""
        emb = self._backend.embed(face_bgr)
        if np.all(emb == 0):
            return False
        bucket = self.person_embeddings.setdefault(name, [])
        bucket.append(emb)
        if len(bucket) > config.MAX_EMBS_PERSON:
            bucket.pop(0)
        log.info("Enrolled %s (%d embeddings)", name, len(bucket))
        return True

    # ── Identification ────────────────────────────────────────────────────────

    def identify(self, face_bgr: np.ndarray) -> Tuple[str, float]:
        """
        Identify one face crop.

        Returns:
            (name, confidence) — name is "Unknown" if below threshold.
        """
        emb = self._backend.embed(face_bgr)
        if np.all(emb == 0):
            return "Unknown", 0.0
        return self._match(emb)

    def identify_detections(
        self,
        frame: np.ndarray,
        detections: list,
    ) -> List[Tuple[str, float]]:
        """Identify faces for a list of detections from FaceDetector."""
        results = []
        for det in detections:
            crop = align_face(frame, det, size=112)
            name, conf = self.identify(crop)
            results.append((name, conf))
        return results

    def _match(self, emb: np.ndarray) -> Tuple[str, float]:
        # Compute weighted similarity score for every enrolled person
        scores: List[Tuple[str, float]] = []
        for person, embs in self.person_embeddings.items():
            sims = [_cosine(emb, e) for e in embs]
            sim  = max(sims) * 0.7 + float(np.mean(sims)) * 0.3
            scores.append((person, sim))

        if not scores:
            return "Unknown", 0.0

        scores.sort(key=lambda x: x[1], reverse=True)
        best_name, best_sim = scores[0]

        # Threshold gate
        if best_sim < config.RECOG_THRESHOLD:
            return "Unknown", best_sim

        # Ambiguity gate: reject if top-1 margin over top-2 is too narrow
        if len(scores) >= 2:
            margin = best_sim - scores[1][1]
            if margin < config.RECOG_AMBIGUITY_MARGIN:
                return "Unknown", best_sim

        return best_name, best_sim

    # ── Metadata ──────────────────────────────────────────────────────────────

    def known_names(self) -> List[str]:
        return sorted(self.person_embeddings.keys())

    def person_count(self) -> int:
        return len(self.person_embeddings)

    def delete_person(self, name: str) -> bool:
        if name in self.person_embeddings:
            del self.person_embeddings[name]
            return True
        return False
