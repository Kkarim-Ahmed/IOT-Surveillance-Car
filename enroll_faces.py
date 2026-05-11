"""
Face Enrollment Script
Add new faces to the recognition system
"""
import os
import sys
import cv2
import argparse
from pathlib import Path
from face_recognition_module import FaceRecognitionSystem
import config


def capture_from_camera(person_name, num_images=5):
    """
    Capture face images from camera for enrollment
    
    Args:
        person_name: Name of the person
        num_images: Number of images to capture
    """
    print(f"\n📷 Starting camera capture for {person_name}")
    print(f"   Will capture {num_images} images")
    print("   Press SPACE to capture, ESC to cancel")
    
    # Create directory for person
    person_dir = Path(config.FACE_IMAGES_DIR) / person_name
    person_dir.mkdir(parents=True, exist_ok=True)
    
    # Open camera
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    
    if not cap.isOpened():
        print("❌ Failed to open camera")
        return []
    
    captured_images = []
    capture_count = 0
    
    try:
        while capture_count < num_images:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to capture frame")
                break
            
            # Display frame with instructions
            display = frame.copy()
            cv2.putText(
                display,
                f"Captured: {capture_count}/{num_images}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            cv2.putText(
                display,
                "Press SPACE to capture",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            cv2.putText(
                display,
                "Press ESC to cancel",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            
            cv2.imshow("Face Enrollment", display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 32:  # SPACE
                # Save image
                filename = person_dir / f"{person_name}_{capture_count + 1}.jpg"
                cv2.imwrite(str(filename), frame)
                captured_images.append(str(filename))
                capture_count += 1
                print(f"✅ Captured image {capture_count}/{num_images}")
                
            elif key == 27:  # ESC
                print("❌ Enrollment cancelled")
                break
        
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    return captured_images


def enroll_from_images(image_paths, person_name):
    """
    Enroll face from existing images
    
    Args:
        image_paths: List of image file paths
        person_name: Name of the person
    """
    recognizer = FaceRecognitionSystem()
    
    success_count = 0
    for image_path in image_paths:
        if recognizer.enroll_face(image_path, person_name):
            success_count += 1
    
    if success_count > 0:
        recognizer.save_encodings()
        print(f"\n✅ Successfully enrolled {success_count} images for {person_name}")
    else:
        print(f"\n❌ Failed to enroll any images for {person_name}")
    
    return success_count > 0


def enroll_from_directory(directory_path):
    """
    Enroll all faces from directory structure
    
    Args:
        directory_path: Path to directory with person folders
    """
    recognizer = FaceRecognitionSystem()
    recognizer.enroll_from_directory(directory_path)


def main():
    parser = argparse.ArgumentParser(description="Enroll faces for recognition system")
    parser.add_argument(
        "--mode",
        choices=["camera", "images", "directory"],
        default="camera",
        help="Enrollment mode"
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Person name (required for camera and images mode)"
    )
    parser.add_argument(
        "--images",
        nargs="+",
        help="Image file paths (for images mode)"
    )
    parser.add_argument(
        "--directory",
        type=str,
        help="Directory path (for directory mode)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of images to capture (camera mode)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("👤 Face Enrollment System")
    print("=" * 60)
    
    if args.mode == "camera":
        if not args.name:
            print("❌ Error: --name is required for camera mode")
            sys.exit(1)
        
        # Capture images from camera
        captured_images = capture_from_camera(args.name, args.count)
        
        if captured_images:
            # Enroll captured images
            enroll_from_images(captured_images, args.name)
    
    elif args.mode == "images":
        if not args.name or not args.images:
            print("❌ Error: --name and --images are required for images mode")
            sys.exit(1)
        
        # Enroll from provided images
        enroll_from_images(args.images, args.name)
    
    elif args.mode == "directory":
        if not args.directory:
            print("❌ Error: --directory is required for directory mode")
            sys.exit(1)
        
        # Enroll from directory
        enroll_from_directory(args.directory)
    
    print("\n" + "=" * 60)
    print("✅ Enrollment complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
