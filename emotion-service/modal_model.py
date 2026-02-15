import modal

app = modal.App("emotion-detector")
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("deepface", "tf-keras", "opencv-python-headless", "numpy", "Pillow")
    .run_commands("python -c \"from deepface import DeepFace; DeepFace.build_model('Emotion')\"")
)


@app.function(image=image, timeout=30)
def analyze_emotions(image_bytes: bytes) -> dict:
    """Detect all faces in a gallery view frame and classify emotions."""
    from deepface import DeepFace
    import numpy as np
    import io
    from PIL import Image

    img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    results = DeepFace.analyze(
        img,
        actions=["emotion"],
        enforce_detection=False,
        detector_backend="opencv",
        silent=True,
    )
    if not isinstance(results, list):
        results = [results]

    return {
        "faces": [
            {
                "emotion": r["emotion"],
                "dominant_emotion": r["dominant_emotion"],
                "region": r.get("region", {}),
                "confidence": r.get("face_confidence", 0),
            }
            for r in results
        ]
    }
