"""
Dataset manager — builds face encodings from a photo directory.

Directory layout:
    dataset/faces/
        PersonName/
            photo1.jpg
            photo2.jpg
            ... (at least MIN_PHOTOS images)

Usage:
    python dataset/manager.py
    python dataset/manager.py --validate
"""

import sys
import os
import pickle
import logging
import argparse
from pathlib import Path

import cv2

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import config

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class DatasetManager:
    def __init__(self):
        self._recognizer = None  # lazy-loaded

    def _get_recognizer(self):
        if self._recognizer is None:
            from core.recognizer import FaceRecognizer
            self._recognizer = FaceRecognizer()
            # Start fresh — don't inherit existing encodings
            self._recognizer.person_embeddings = {}
        return self._recognizer

    def build_and_save(self, dataset_dir: str = None, min_photos: int = None) -> bool:
        dataset_dir = Path(dataset_dir or config.DATASET_DIR)
        min_photos  = min_photos or config.MIN_PHOTOS

        if not dataset_dir.exists():
            print(f"Dataset directory not found: {dataset_dir}")
            print(f"Create folders: dataset/faces/YourName/*.jpg")
            return False

        person_dirs = [p for p in dataset_dir.iterdir() if p.is_dir()]
        if not person_dirs:
            print("No person folders found.")
            return False

        rec = self._get_recognizer()
        total_ok = 0

        for pd in sorted(person_dirs):
            name   = pd.name
            images = [f for f in pd.iterdir() if f.suffix.lower() in EXTS]

            if len(images) < min_photos:
                print(f"  ⚠  {name}: {len(images)} image(s) — need {min_photos}, skipping")
                continue

            enrolled = 0
            for img_path in images:
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                # Use the full image as the face crop (dataset photos should be face-only)
                if rec.enroll_face(img, name):
                    enrolled += 1

            if enrolled:
                print(f"  ✓  {name}: {enrolled}/{len(images)} enrolled")
                total_ok += enrolled
            else:
                print(f"  ✗  {name}: no valid faces found")

        if total_ok == 0:
            print("No faces enrolled. Check your photos.")
            return False

        rec.save_encodings()
        print(f"\nTotal: {total_ok} embedding(s) for {rec.person_count()} person(s)")
        return True

    def validate(self, dataset_dir: str = None, min_photos: int = None) -> bool:
        dataset_dir = Path(dataset_dir or config.DATASET_DIR)
        min_photos  = min_photos or config.MIN_PHOTOS
        ok = True

        if not dataset_dir.exists():
            print(f"Not found: {dataset_dir}")
            return False

        for pd in sorted(p for p in dataset_dir.iterdir() if p.is_dir()):
            images = [f for f in pd.iterdir() if f.suffix.lower() in EXTS]
            status = "✓" if len(images) >= min_photos else "✗"
            print(f"  {status}  {pd.name}: {len(images)} images")
            if len(images) < min_photos:
                ok = False
        return ok


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--validate", action="store_true")
    p.add_argument("--dataset-dir", default=None)
    p.add_argument("--min-photos",  type=int, default=None)
    args = p.parse_args()

    dm = DatasetManager()
    if args.validate:
        ok = dm.validate(args.dataset_dir, args.min_photos)
        sys.exit(0 if ok else 1)
    else:
        dm.build_and_save(args.dataset_dir, args.min_photos)
