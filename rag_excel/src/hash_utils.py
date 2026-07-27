"""
hash_utils.py
-------------
Utilities to compute a stable SHA-256 hash of a file and to persist /
compare that hash so the application can decide whether the FAISS
vector database needs to be rebuilt.
"""

import hashlib
import json
import os
from typing import Optional


def compute_file_hash(file_path: str, chunk_size: int = 65536) -> str:
    """Compute the SHA-256 hash of a file's raw bytes, streamed in chunks
    so arbitrarily large Excel files do not need to fit in memory."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def read_stored_hash(hash_file_path: str) -> Optional[str]:
    """Return the previously stored hash, or None if it doesn't exist / is invalid."""
    if not os.path.exists(hash_file_path):
        return None
    try:
        with open(hash_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("sha256")
    except (json.JSONDecodeError, OSError):
        return None


def write_stored_hash(hash_file_path: str, file_hash: str, source_path: str) -> None:
    """Persist the hash (and a bit of metadata) for future comparisons."""
    os.makedirs(os.path.dirname(hash_file_path), exist_ok=True)
    payload = {
        "sha256": file_hash,
        "source_file": os.path.abspath(source_path),
        "source_file_name": os.path.basename(source_path),
    }
    with open(hash_file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def file_has_changed(file_path: str, hash_file_path: str) -> bool:
    """True if the file's current hash differs from the stored one
    (or if there is no stored hash yet)."""
    current_hash = compute_file_hash(file_path)
    stored_hash = read_stored_hash(hash_file_path)
    return current_hash != stored_hash
