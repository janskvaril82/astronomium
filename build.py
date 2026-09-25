#!/usr/bin/env python3
"""Verify and restore Astronomium's prebuilt site using Python's standard library.

Run on the hosting provider: python3 build.py
Check the complete bundle without replacing dist: python3 build.py --verify-only
This helper does not authenticate, install dependencies, or deploy anything.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import zipfile
import zlib


OWNER = "astronomium-browser-build-v1"
MARKER = ".astronomium-build-output.json"
MAX_FILES = 20_000
MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


class ValidationError(Exception):
    """A bundle or output failed a safety or integrity check."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def is_link(path):
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def ordinary_file(path):
    require(not is_link(path), f"Symbolic links are not allowed: {path.name}")
    require(path.is_file(), f"Required ordinary file is missing: {path.name}")


def integer(value, label, minimum=0):
    require(type(value) is int and value >= minimum, f"Invalid {label} in bundle-manifest.json.")
    return value


def digest_value(value, label):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value),
            f"Invalid SHA-256 for {label}.")
    return value.lower()


def safe_name(name):
    require(isinstance(name, str) and name, "Archive paths must be nonempty strings.")
    require("\\" not in name and ":" not in name and not name.startswith("/"),
            f"Unsafe archive path: {name!r}")
    require(all(ord(char) >= 32 and ord(char) != 127 for char in name),
            f"Control character in archive path: {name!r}")
    require(all(part not in ("", ".", "..") for part in name.split("/")),
            f"Unsafe archive path: {name!r}")
    require(not PurePosixPath(name).is_absolute(), f"Absolute archive path: {name!r}")
    return name


def load_manifest(root):
    path = root / "bundle-manifest.json"
    ordinary_file(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(manifest, dict) and manifest.get("schemaVersion") == 1,
            "Unsupported bundle manifest; expected schemaVersion 1.")
    integer(manifest.get("archiveBytes"), "archiveBytes", 1)
    manifest["archiveSHA256"] = digest_value(manifest.get("archiveSHA256"), "archive")
    parts = manifest.get("parts")
    require(isinstance(parts, list) and parts, "The manifest has no archive parts.")
    part_names = set()
    for part in parts:
        require(isinstance(part, dict), "Malformed archive-part record.")
        name = safe_name(part.get("path"))
        require(re.fullmatch(r"site-\d{3}\.part", name), f"Invalid archive-part filename: {name}")
        require(name not in part_names, f"Duplicate archive part: {name}")
        part_names.add(name)
        integer(part.get("bytes"), f"size of {name}", 1)
        part["sha256"] = digest_value(part.get("sha256"), name)
    require(sum(part["bytes"] for part in parts) == manifest["archiveBytes"],
            "Archive-part sizes do not add up to archiveBytes.")
    files = manifest.get("files")
    require(isinstance(files, list) and 0 < len(files) <= MAX_FILES,
            f"The archive must contain between 1 and {MAX_FILES:,} files.")
    by_name, folded_names = {}, set()
    for item in files:
        require(isinstance(item, dict), "Malformed asset record.")
        name = safe_name(item.get("path"))
        require(name not in by_name and name.casefold() not in folded_names,
                f"Duplicate or case-colliding asset: {name}")
        size = integer(item.get("bytes"), f"size of {name}")
        require(size <= MAX_FILE_BYTES, f"Asset exceeds 25 MiB: {name}")
        item["sha256"] = digest_value(item.get("sha256"), name)
        by_name[name] = item
        folded_names.add(name.casefold())
    for name in by_name:
        parts_of_name = name.split("/")
        for index in range(1, len(parts_of_name)):
            require("/".join(parts_of_name[:index]).casefold() not in folded_names,
                    f"Asset path conflicts with a containing directory: {name}")
    require(integer(manifest.get("fileCount"), "fileCount", 1) == len(files),
            "fileCount does not match the asset list.")
    require(integer(manifest.get("totalBytes"), "totalBytes") == sum(item["bytes"] for item in files),
            "totalBytes does not match the asset list.")
    for required in ("index.html", "404.html", "_headers"):
        require(required in by_name, f"Required site asset is missing: {required}")
    return manifest, by_name


def reconstruct(root, target, manifest):
    # All part failures occur before the output directory is touched.
    whole_hash = hashlib.sha256()
    whole_size = 0
    with target.open("xb") as output:
        for part in manifest["parts"]:
            path = root / part["path"]
            ordinary_file(path)
            require(path.stat().st_size == part["bytes"],
                    f"Wrong size for {part['path']}; upload that part again.")
            part_hash, size = hashlib.sha256(), 0
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
                    size += len(chunk)
                    require(size <= part["bytes"], f"Archive part changed while reading: {part['path']}")
                    part_hash.update(chunk)
                    whole_hash.update(chunk)
                    output.write(chunk)
            require(size == part["bytes"] and part_hash.hexdigest() == part["sha256"],
                    f"SHA-256 mismatch for {part['path']}; upload that part again.")
            whole_size += size
    require(whole_size == manifest["archiveBytes"] and whole_hash.hexdigest() == manifest["archiveSHA256"],
            "Combined archive checksum does not match. Check that all parts belong to the same release.")


def validate_archive(archive, expected):
    entries = archive.infolist()
    require(len(entries) == len(expected) and len(entries) <= MAX_FILES,
            "ZIP file count does not match the manifest.")
    seen = set()
    for entry in entries:
        name = safe_name(entry.filename)
        require(safe_name(entry.orig_filename) == name, f"Altered or truncated ZIP path: {name!r}")
        require(name not in seen, f"Duplicate ZIP entry: {name}")
        seen.add(name)
        require(name in expected, f"Unexpected ZIP entry: {name}")
        kind = stat.S_IFMT(entry.external_attr >> 16)
        require(not entry.is_dir() and kind in (0, stat.S_IFREG),
                f"ZIP entry is not an ordinary file: {name}")
        require(not entry.flag_bits & 1, f"Encrypted ZIP entries are not supported: {name}")
        require(entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                f"Unsupported compression for {name}.")
        require(entry.file_size == expected[name]["bytes"] and entry.file_size <= MAX_FILE_BYTES,
                f"ZIP size does not match the manifest: {name}")
    require(seen == set(expected), "The ZIP is missing assets listed in the manifest.")
    # Verify CRC and every file hash before replacing an existing output.
    for entry in entries:
        check_entry(archive, entry, expected[entry.filename])
    return entries


def check_entry(archive, entry, expected, destination=None):
    digest, size = hashlib.sha256(), 0
    with archive.open(entry, "r") as source:
        for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
            size += len(chunk)
            require(size <= expected["bytes"] and size <= MAX_FILE_BYTES,
                    f"Uncompressed asset exceeds its declared size: {entry.filename}")
            digest.update(chunk)
            if destination is not None:
                destination.write(chunk)
    require(size == expected["bytes"] and digest.hexdigest() == expected["sha256"],
            f"Asset checksum mismatch: {entry.filename}")


def checked_output(root):
    output = root / "dist"
    require(output.is_absolute() and output.name == "dist" and output.parent == root,
            "Unsafe output directory.")
    require(not is_link(output), "Refusing a symbolic link or junction at dist.")
    require(output.resolve().parent == root and output.resolve() != root,
            "The resolved output must be the project's own dist directory.")
    return output


def prepare_output(root, manifest):
    output = checked_output(root)
    marker = root / MARKER
    marker_exists = os.path.lexists(marker)
    if marker_exists:
        ordinary_file(marker)
        ownership = json.loads(marker.read_text(encoding="utf-8"))
        require(isinstance(ownership, dict) and ownership.get("owner") == OWNER
                and ownership.get("dist") == str(output),
                "Output marker belongs to a different build; refusing to replace dist.")
    if os.path.lexists(output):
        require(marker_exists and output.is_dir(),
                "Existing dist is not owned by this helper. Move it aside before building.")
        # Reject links anywhere in the old output, including Windows junctions.
        for folder, directories, files in os.walk(output, followlinks=False):
            for name in directories + files:
                require(not is_link(Path(folder) / name),
                        "Existing dist contains a symbolic link; refusing recursive removal.")
        output = checked_output(root)  # Check the resolved absolute target immediately before deletion.
        shutil.rmtree(output)
    ownership = {"owner": OWNER, "dist": str(output), "archiveSHA256": manifest["archiveSHA256"]}
    # This marker deliberately lives outside uploaded dist.
    marker.write_text(json.dumps(ownership, indent=2) + "\n", encoding="utf-8")
    output.mkdir()
    return output


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true",
                        help="Verify all parts, ZIP entries, CRCs and asset hashes without modifying dist.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest, expected = load_manifest(root)
    print(f"Verifying {len(manifest['parts'])} archive parts and {len(expected):,} site assets...", flush=True)
    # A uniquely created temporary directory is the only reconstruction workspace.
    with tempfile.TemporaryDirectory(prefix=".astronomium-archive-", dir=root) as temporary:
        temp_root = Path(temporary).resolve()
        require(temp_root.parent == root and temp_root.name.startswith(".astronomium-archive-")
                and not is_link(temp_root), "Unsafe temporary archive directory.")
        reconstructed = temp_root / "site.zip"
        reconstruct(root, reconstructed, manifest)
        with zipfile.ZipFile(reconstructed, "r") as archive:
            entries = validate_archive(archive, expected)
            if args.verify_only:
                print(f"Verified {len(entries):,} assets ({manifest['totalBytes']:,} bytes). dist was not changed.")
                return
            output = prepare_output(root, manifest)
            for entry in entries:
                target = output.joinpath(*entry.filename.split("/"))
                require(target.resolve().is_relative_to(output), f"Unsafe extraction target: {entry.filename}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as destination:
                    check_entry(archive, entry, expected[entry.filename], destination)
    print(f"Build complete: {len(expected):,} verified assets ({manifest['totalBytes']:,} bytes) in dist.")


if __name__ == "__main__":
    try:
        run()
    except (ValidationError, OSError, ValueError, zipfile.BadZipFile, zlib.error, EOFError, RuntimeError, NotImplementedError) as error:
        print(f"Astronomium build failed: {error}", file=sys.stderr)
        sys.exit(1)
