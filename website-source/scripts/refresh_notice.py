#!/usr/bin/env python3
"""Correct only NOTICE inside an existing source release, preserving every other entry."""

import argparse
import copy
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile

NOTICE_NAME = "SecureClockVault/NOTICE"
REPO = Path(__file__).resolve().parents[2]


def digest(stream):
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        result.update(chunk)
    return result.hexdigest()


def refresh(source):
    notice = (REPO / "NOTICE").read_bytes()
    if not source.is_file() or source.suffix != ".zip":
        raise ValueError("Provide an existing matching source ZIP.")
    with ZipFile(source) as old:
        if len(old.namelist()) != len(set(old.namelist())):
            raise ValueError("Duplicate archive entries are not accepted.")
        previous_notice = old.read(NOTICE_NAME)
        if previous_notice == notice:
            print("Source notice is already current.")
            return
        if not previous_notice.startswith((b"Secure Clock Vault 3.12.1\n", b"Secure Clock Vault\n")):
            raise ValueError("Unexpected notice; review the source archive before changing it.")
    descriptor, temporary = tempfile.mkstemp(prefix="source-notice-", suffix=".zip", dir=source.parent)
    os.close(descriptor)
    staged = Path(temporary)
    try:
        with ZipFile(source) as old, ZipFile(staged, "w") as new:
            new.comment = old.comment
            for entry in old.infolist():
                if entry.filename == NOTICE_NAME:
                    new.writestr(copy.copy(entry), notice)
                else:
                    with old.open(entry) as original, new.open(copy.copy(entry), "w") as target:
                        shutil.copyfileobj(original, target, 1024 * 1024)
        with ZipFile(source) as old, ZipFile(staged) as new:
            if old.namelist() != new.namelist():
                raise ValueError("Source entries changed unexpectedly.")
            for name in old.namelist():
                if name == NOTICE_NAME:
                    if new.read(name) != notice:
                        raise ValueError("Updated notice does not match.")
                else:
                    with old.open(name) as before, new.open(name) as after:
                        if digest(before) != digest(after):
                            raise ValueError(f"Source content changed unexpectedly: {name}")
        os.replace(staged, source)
    finally:
        if staged.exists():
            staged.unlink()
    with source.open("rb") as stream:
        print(json.dumps({"sourceBytes": source.stat().st_size, "sourceSha256": digest(stream),
                          "onlyChangedEntry": NOTICE_NAME}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    refresh(parser.parse_args().source.resolve())
