"""Canonical JSON and file checksums. SPDX-License-Identifier: MIT."""
import hashlib
import json
from pathlib import Path


def encode(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def present(value):
    return isinstance(value, str) and value.strip().lower() not in {
        '', 'unknown', 'unresolved', 'n/a', 'na', 'not reported'}
