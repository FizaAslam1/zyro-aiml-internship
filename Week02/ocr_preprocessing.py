"""
Week 3 - Step 3: Improve OCR handling with simple image preprocessing.

Beginner-friendly preprocessing techniques applied BEFORE running OCR,
used when the plain OCR pass returns very little text (i.e. OCR "struggled"):
    - resize (upscale small/low-res images so text is easier to read)
    - grayscale conversion
    - contrast enhancement
    - simple thresholding (binarization)
    - light noise reduction (median filter)

These are deliberately simple (no OpenCV dependency) so the logic stays
readable for a beginner/intermediate project, using only Pillow + NumPy
which were already dependencies in Week 2.
"""

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """
    Apply a simple preprocessing pipeline to improve OCR accuracy on
    difficult (low quality / low contrast / small) images.
    """
    # 1) Upscale small images - OCR struggles with tiny text
    min_dim = 1000
    if min(img.size) < min_dim:
        scale = min_dim / min(img.size)
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size, Image.LANCZOS)

    # 2) Grayscale conversion - removes color noise, most OCR engines
    #    work on intensity anyway
    img = img.convert("L")

    # 3) Auto-contrast - stretches the histogram so faint text becomes clearer
    img = ImageOps.autocontrast(img, cutoff=1)

    # 4) Light noise reduction - median filter removes speckle/salt-pepper
    #    noise common in scanned documents, without blurring edges too much
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # 5) Simple thresholding (binarization) - push pixels to pure black/white
    #    which tends to help engines like Tesseract; EasyOCR is more
    #    tolerant but this still generally helps low-contrast scans
    arr = np.array(img)
    threshold = arr.mean() * 0.9  # slightly below mean brightness
    arr = np.where(arr > threshold, 255, 0).astype("uint8")
    img = Image.fromarray(arr)

    return img.convert("RGB")


def needs_preprocessing(raw_ocr_text: str, min_chars: int = 15) -> bool:
    """Decide whether OCR 'struggled' and preprocessing should be retried."""
    return len((raw_ocr_text or "").strip()) < min_chars
