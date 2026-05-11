"""
Download and setup models for face detection
"""
import os
import sys
from pathlib import Path


def download_yolo_face_model():
    """Download YOLOv8-nano face detection model"""
    print("\n" + "="*60)
    print("📥 Downloading YOLOv8-nano Face Model")
    print("="*60)
    
    try:
        from ultralytics import YOLO
        
        # YOLOv8n is the base model - we'll use it for person detection
        # For dedicated face detection, you can train on WIDER FACE dataset
        # or use the base model which detects persons
        
        print("   Downloading YOLOv8n base model...")
        model = YOLO("yolov8n.pt")
        
        print("✅ YOLOv8n model downloaded successfully")
        print("   Location: ~/.cache/ultralytics/")
        print("\n   Note: For dedicated face detection, consider:")
        print("   - Training YOLOv8n on WIDER FACE dataset")
        print("   - Using BlazeFace (MediaPipe) - faster for faces")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to download YOLO model: {e}")
        return False


def check_mediapipe():
    """Check if MediaPipe (BlazeFace) is available"""
    print("\n" + "="*60)
    print("🔍 Checking MediaPipe (BlazeFace)")
    print("="*60)
    
    try:
        import mediapipe as mp
        
        print("✅ MediaPipe is installed")
        print("   BlazeFace detector available")
        print("   This is the recommended detector for Raspberry Pi")
        
        return True
        
    except ImportError:
        print("⚠️  MediaPipe not installed")
        print("   Install with: pip install mediapipe")
        print("   BlazeFace is faster than YOLO for face detection")
        
        return False


def check_face_recognition():
    """Check if face_recognition library is available"""
    print("\n" + "="*60)
    print("👤 Checking Face Recognition Library")
    print("="*60)
    
    try:
        import face_recognition
        import dlib
        
        print("✅ face_recognition library is installed")
        print(f"   dlib version: {dlib.__version__}")
        
        return True
        
    except ImportError as e:
        print("⚠️  face_recognition library not installed")
        print("   Install with: pip install face-recognition")
        print("   Note: This may take 30-60 minutes on Raspberry Pi")
        
        return False


def setup_directories():
    """Create necessary directories"""
    print("\n" + "="*60)
    print("📁 Setting Up Directories")
    print("="*60)
    
    directories = [
        "known_faces",
        "known_faces/images",
        "captures",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}/")
    
    print("\n   Directory structure:")
    print("   known_faces/")
    print("   ├── images/          # Place person folders here")
    print("   │   ├── Person1/")
    print("   │   └── Person2/")
    print("   └── encodings.pkl    # Generated after enrollment")
    print("   captures/            # Saved frames")
    
    return True


def create_example_enrollment():
    """Create example enrollment structure"""
    print("\n" + "="*60)
    print("📝 Creating Example Enrollment Structure")
    print("="*60)
    
    example_dir = Path("known_faces/images/Example_Person")
    example_dir.mkdir(parents=True, exist_ok=True)
    
    readme_content = """# Face Enrollment Instructions

## Add Your Face Images Here

1. Create a folder with your name (e.g., "John_Doe")
2. Add 3-5 photos of your face in this folder
3. Photos should be:
   - Clear and well-lit
   - Different angles (front, slight left, slight right)
   - Different expressions (neutral, smiling)
   - JPG or PNG format

## Example Structure:

known_faces/images/
├── John_Doe/
│   ├── john_1.jpg
│   ├── john_2.jpg
│   └── john_3.jpg
└── Jane_Smith/
    ├── jane_1.jpg
    └── jane_2.jpg

## Enroll Faces:

```bash
python enroll_faces.py --mode directory --directory known_faces/images
```

Or use the GUI:
```bash
python gui_tracker.py
```
Then select "Enroll New Face" mode.
"""
    
    readme_path = Path("known_faces/images/README.txt")
    with open(readme_path, "w") as f:
        f.write(readme_content)
    
    print("   ✅ Created example structure")
    print(f"   ✅ Created {readme_path}")
    print("\n   Next steps:")
    print("   1. Add your face photos to known_faces/images/YourName/")
    print("   2. Run: python enroll_faces.py --mode directory --directory known_faces/images")
    
    return True


def main():
    """Main setup function"""
    print("\n" + "="*60)
    print("🚀 Face Tracking System - Model Setup")
    print("="*60)
    
    results = {}
    
    # Setup directories
    results["Directories"] = setup_directories()
    
    # Check MediaPipe (BlazeFace) - recommended
    results["MediaPipe"] = check_mediapipe()
    
    # Check face_recognition
    results["Face Recognition"] = check_face_recognition()
    
    # Download YOLO (optional)
    download_yolo = input("\n📥 Download YOLOv8n model? (y/n, default=n): ").lower()
    if download_yolo == 'y':
        results["YOLO Model"] = download_yolo_face_model()
    else:
        print("   Skipped YOLO download (BlazeFace recommended)")
        results["YOLO Model"] = None
    
    # Create example enrollment
    results["Example Structure"] = create_example_enrollment()
    
    # Summary
    print("\n" + "="*60)
    print("📊 Setup Summary")
    print("="*60)
    
    for name, result in results.items():
        if result is None:
            status = "⏭️  SKIPPED"
        elif result:
            status = "✅ SUCCESS"
        else:
            status = "⚠️  WARNING"
        print(f"{status} - {name}")
    
    print("\n" + "="*60)
    print("🎯 Next Steps")
    print("="*60)
    print("1. Add face images to: known_faces/images/YourName/")
    print("2. Enroll faces: python enroll_faces.py --mode directory --directory known_faces/images")
    print("3. Test system: python test_system.py")
    print("4. Run GUI: python gui_tracker.py")
    print("\nOr use the GUI for everything: python gui_tracker.py")
    
    print("\n" + "="*60)
    print("✅ Setup Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
