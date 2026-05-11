"""
Face Recognition Module — InsightFace backend
No dlib / no compilation required. Works on Python 3.14+.

InsightFace uses ArcFace (ResNet-based) embeddings — more accurate
than dlib's 128-d model and runs fully via ONNX (no GPU needed).
"""

import os
import pickle
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict

import config


# ─────────────────────────────────────────────────────────────────────────────
# InsightFace app (lazy-loaded once)
# ─────────────────────────────────────────────────────────────────────────────

_app = None   # insightface.app.FaceAnalysis singleton


def _get_app():
    """Return (and lazily initialise) the InsightFace FaceAnalysis app."""
    global _app
    if _app is not None:
        return _app

    try:
        import insightface
        from insightface.app import FaceAnalysis

        # buffalo_sc  = small, fast (recommended for Pi)
        # buffalo_l   = large, accurate (better for laptop)
        model_name = "buffalo_sc"

        _app = FaceAnalysis(
            name=model_name,
            providers=["CPUExecutionProvider"],   # CPU only
        )
        # det_size must be a multiple of 32; 320 is fast, 640 is accurate
        # det_thresh lowered from default 0.5 → 0.35 to handle dim/real-world lighting
        _app.prepare(ctx_id=0, det_size=(320, 320), det_thresh=0.35)
        print(f"✅ InsightFace ready (model: {model_name})")

    except Exception as e:
        print(f"❌ InsightFace init failed: {e}")
        _app = None

    return _app


# ─────────────────────────────────────────────────────────────────────────────
# Cosine similarity helper
# ─────────────────────────────────────────────────────────────────────────────

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Return cosine similarity in [0, 1]."""
    a = a / (np.linalg.norm(a) + 1e-10)
    b = b / (np.linalg.norm(b) + 1e-10)
    return float(np.dot(a, b))


# ─────────────────────────────────────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────────────────────────────────────

class FaceRecognitionSystem:
    """
    Face recognition system — enroll faces, recognise at runtime.

    Stores 512-d ArcFace embeddings (InsightFace buffalo_sc model).
    No dlib, no compilation, works on Python 3.14+.
    """

    # Cosine similarity threshold: faces above this are considered a match.
    # 0.25 = more lenient (may have false positives)
    # 0.35 = balanced (recommended)
    # 0.45 = stricter (may miss some matches)
    SIMILARITY_THRESHOLD = 0.30  # Lowered from 0.35 for better recognition

    def __init__(self, encodings_path: str = None):
        self.encodings_path = encodings_path or config.FACE_ENCODINGS_PATH

        # In-memory database - ENHANCED with multiple embeddings per person
        self.known_face_encodings: List[np.ndarray] = []
        self.known_face_names:     List[str]        = []
        
        # NEW: Multiple embeddings per person for better accuracy
        self.person_embeddings: Dict[str, List[np.ndarray]] = {}  # name -> [embeddings]
        self.max_embeddings_per_person = 5  # Store best 5 embeddings

        # Create directories
        Path(config.FACE_IMAGES_DIR).mkdir(parents=True, exist_ok=True)
        Path(os.path.dirname(self.encodings_path)).mkdir(parents=True, exist_ok=True)

        # Load existing encodings
        self.load_encodings()

        # Warm up InsightFace
        _get_app()

    # ── Enrollment ────────────────────────────────────────────────────────────

    def enroll_face(self, image_path: str, person_name: str) -> bool:
        """
        Enroll a face from an image file.

        Args:
            image_path:  Path to a JPEG/PNG image.
            person_name: Name to associate with this face.

        Returns:
            True if at least one face was enrolled.
        """
        app = _get_app()
        if app is None:
            print("❌ InsightFace not available")
            return False

        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ Cannot read image: {image_path}")
            return False

        faces = app.get(img)

        if len(faces) == 0:
            print(f"❌ No face found in {image_path}")
            return False

        if len(faces) > 1:
            print(f"⚠️  {len(faces)} faces found in {image_path} — using largest")
            # Pick largest by bounding-box area
            faces = sorted(
                faces,
                key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
                reverse=True,
            )

        embedding = faces[0].normed_embedding   # 512-d unit vector
        self.known_face_encodings.append(embedding.copy())
        self.known_face_names.append(person_name)
        
        # NEW: Add to person_embeddings for multi-embedding support
        if person_name not in self.person_embeddings:
            self.person_embeddings[person_name] = []
        
        self.person_embeddings[person_name].append(embedding.copy())
        
        # Keep only best N embeddings per person
        if len(self.person_embeddings[person_name]) > self.max_embeddings_per_person:
            self.person_embeddings[person_name].pop(0)  # Remove oldest

        print(f"✅ Enrolled {person_name} from {os.path.basename(image_path)}")
        return True

    def enroll_from_directory(self, directory_path: str):
        """
        Enroll all faces from a directory tree.

        Expected structure:
            directory_path/
                PersonName/
                    photo1.jpg
                    photo2.jpg
        """
        directory = Path(directory_path)
        if not directory.exists():
            print(f"❌ Directory not found: {directory_path}")
            return

        enrolled = 0
        for person_folder in sorted(directory.iterdir()):
            if not person_folder.is_dir():
                continue
            name = person_folder.name
            for img_file in person_folder.glob("*"):
                if img_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
                    if self.enroll_face(str(img_file), name):
                        enrolled += 1

        print(f"\n📊 Total enrolled: {enrolled} face(s)")
        self.save_encodings()

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_encodings(self):
        """Persist face embeddings to disk."""
        try:
            data = {
                "encodings": self.known_face_encodings,
                "names":     self.known_face_names,
                "person_embeddings": self.person_embeddings,  # NEW: Save multiple embeddings
            }
            with open(self.encodings_path, "wb") as f:
                pickle.dump(data, f)
            print(f"💾 Saved {len(self.known_face_names)} encoding(s) → {self.encodings_path}")
        except Exception as e:
            print(f"❌ Save failed: {e}")

    def load_encodings(self):
        """Load face embeddings from disk."""
        if not os.path.exists(self.encodings_path):
            print(f"ℹ️  No encodings file at {self.encodings_path} — starting fresh")
            return
        try:
            with open(self.encodings_path, "rb") as f:
                data = pickle.load(f)
            self.known_face_encodings = data["encodings"]
            self.known_face_names     = data["names"]
            
            # NEW: Load multiple embeddings if available
            if "person_embeddings" in data:
                self.person_embeddings = data["person_embeddings"]
            else:
                # Build from existing encodings
                self._build_person_embeddings()
            
            print(f"✅ Loaded {len(self.known_face_names)} encoding(s) from {self.encodings_path}")
            print(f"✅ Loaded {len(self.person_embeddings)} person profile(s)")
        except Exception as e:
            print(f"❌ Load failed: {e}")
    
    def _build_person_embeddings(self):
        """Build person_embeddings from existing encodings."""
        self.person_embeddings = {}
        for name, encoding in zip(self.known_face_names, self.known_face_encodings):
            if name not in self.person_embeddings:
                self.person_embeddings[name] = []
            self.person_embeddings[name].append(encoding)

    # ── Recognition ───────────────────────────────────────────────────────────

    def recognize_faces(
        self,
        frame: np.ndarray,
        face_locations: List[Tuple[int, int, int, int]],
    ) -> List[Tuple[str, float]]:
        """
        Recognise faces in a BGR frame.

        Args:
            frame:          BGR image (from OpenCV).
            face_locations: List of (top, right, bottom, left) bounding boxes
                            — same format as face_recognition library.

        Returns:
            List of (name, confidence) tuples, one per face_location.
            confidence is cosine similarity in [0, 1].
        """
        if not face_locations:
            return []

        app = _get_app()
        if app is None:
            return [("Unknown", 0.0)] * len(face_locations)

        if not self.known_face_encodings:
            print("⚠️  No known face encodings loaded!")
            return [("Unknown", 0.0)] * len(face_locations)

        results = []

        for (top, right, bottom, left) in face_locations:
            # Crop face region with a small margin
            pad = 10
            h, w = frame.shape[:2]
            y1 = max(0, top    - pad)
            y2 = min(h, bottom + pad)
            x1 = max(0, left   - pad)
            x2 = min(w, right  + pad)

            face_crop = frame[y1:y2, x1:x2]
            if face_crop.size == 0:
                results.append(("Unknown", 0.0))
                continue

            # Get embedding for this crop
            faces = app.get(face_crop)

            if not faces:
                results.append(("Unknown", 0.0))
                continue

            # Use the face closest to the crop centre
            crop_cx = face_crop.shape[1] / 2
            crop_cy = face_crop.shape[0] / 2
            best_face = min(
                faces,
                key=lambda f: abs((f.bbox[0] + f.bbox[2]) / 2 - crop_cx)
                            + abs((f.bbox[1] + f.bbox[3]) / 2 - crop_cy),
            )
            query_emb = best_face.normed_embedding

            # NEW: Enhanced recognition with multiple embeddings
            best_name = "Unknown"
            best_similarity = 0.0
            
            # Compare against each person's multiple embeddings
            for person_name, embeddings in self.person_embeddings.items():
                # Calculate similarity with each embedding
                similarities = [
                    _cosine_similarity(query_emb, stored_emb)
                    for stored_emb in embeddings
                ]
                
                if not similarities:
                    continue
                
                # Use BEST match (max similarity)
                max_sim = max(similarities)
                
                # Also consider AVERAGE for consistency
                avg_sim = np.mean(similarities)
                
                # Weighted combination (70% max, 30% avg)
                combined_sim = 0.7 * max_sim + 0.3 * avg_sim
                
                # Consistency boost (low variance = more confident)
                if len(similarities) >= 3:
                    std_sim = np.std(similarities)
                    if std_sim < 0.05:  # Very consistent
                        consistency_boost = 0.10
                    elif std_sim < 0.10:  # Somewhat consistent
                        consistency_boost = 0.05
                    else:
                        consistency_boost = 0.0
                    
                    combined_sim = min(0.95, combined_sim + consistency_boost)
                
                # Update best match
                if combined_sim > best_similarity:
                    best_similarity = combined_sim
                    best_name = person_name
            
            # Check threshold
            if best_similarity >= self.SIMILARITY_THRESHOLD:
                print(f"✅ Recognized: {best_name} (similarity: {best_similarity:.3f})")
                results.append((best_name, best_similarity))
            else:
                print(f"❌ Unknown face (best match: {best_name} with {best_similarity:.3f}, threshold: {self.SIMILARITY_THRESHOLD})")
                results.append(("Unknown", best_similarity))

        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_face_count(self) -> int:
        return len(self.known_face_names)

    def get_enrolled_names(self) -> List[str]:
        return sorted(set(self.known_face_names))

    def delete_person(self, name: str) -> int:
        """Remove all encodings for a person. Returns number removed."""
        pairs = [
            (e, n)
            for e, n in zip(self.known_face_encodings, self.known_face_names)
            if n != name
        ]
        removed = len(self.known_face_names) - len(pairs)
        if pairs:
            encs, names = zip(*pairs)
            self.known_face_encodings = list(encs)
            self.known_face_names     = list(names)
        else:
            self.known_face_encodings = []
            self.known_face_names     = []
        return removed
