import hashlib


def sha256_of_file(path, chunk_size=8192):
    """Return the SHA256 fingerprint of a file as a 64-character hex string."""
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
