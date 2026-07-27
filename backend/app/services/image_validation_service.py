from pathlib import Path
from typing import Any, Dict

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError


def check_image_quality(file_path: str) -> Dict[str, Any]:
    """Perform lightweight, non-destructive quality checks with Pillow."""
    issues: list[str] = []
    can_continue = True

    try:
        with Image.open(Path(file_path)) as image:
            image.verify()
        with Image.open(Path(file_path)) as image:
            image = image.convert("L")
            width, height = image.size

            if width < 800 or height < 800:
                issues.append(
                    "Low resolution: text extraction may be inaccurate."
                )

            statistics = ImageStat.Stat(image)
            mean_brightness = statistics.mean[0]
            contrast = statistics.stddev[0]

            if contrast < 8:
                issues.append(
                    "Blank or low-contrast image: report text may not be readable."
                )
                if contrast < 3:
                    can_continue = False

            if mean_brightness < 50:
                issues.append("Too dark: improve lighting and retake the photo.")
            elif mean_brightness > 235:
                issues.append("Overexposed: glare may hide report text.")

            edges = image.filter(ImageFilter.FIND_EDGES)
            edge_variance = ImageStat.Stat(edges).var[0]
            if edge_variance < 120:
                issues.append("Blurry: the image may be out of focus.")

            if width > height * 1.3:
                issues.append("The report may be sideways or rotated.")

    except (UnidentifiedImageError, OSError):
        return {
            "status": "error",
            "issues": ["The image is corrupted or cannot be opened."],
            "can_continue": False,
            "recommendation": "Upload a valid JPG, PNG, or WEBP image.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "issues": [f"Image quality validation failed: {exc}"],
            "can_continue": False,
            "recommendation": "Try uploading the image again.",
        }

    return {
        "status": "quality_warning" if issues else "clear",
        "issues": issues,
        "can_continue": can_continue,
        "recommendation": (
            "Upload a clearer and complete image for better extraction."
            if issues
            else "Image quality is sufficient."
        ),
    }
