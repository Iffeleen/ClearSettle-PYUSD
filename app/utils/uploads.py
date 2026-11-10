ALLOWED_TYPES = {"jpeg": ".jpg", "png": ".png"}


def detect_image_type(header):
    """Return 'jpeg', 'png', or None, based on the file's first bytes."""
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return None
