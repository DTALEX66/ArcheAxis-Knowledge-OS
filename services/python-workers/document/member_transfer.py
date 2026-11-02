"""Shared, bounded member publication for the mail and XLS workers.

Observed links, reparse points, hardlinks, and differing existing files are
rejected. Identical existing regular files are verified without rewriting.
These checks are not an OS sandbox: a path component may change between an
observation and a later filesystem operation. A failed create/write/close may
leave a partial file, which is deliberately not deleted or declared as a
successful member. Callers materialize each payload in memory first; the
64 KiB comparison/write chunks are not a process-memory or filesystem quota.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat


def _checked_directory_chain(path: Path, native_path) -> None:
    """Reject links, reparse points and non-directories observed in the chain."""
    absolute = path.absolute()
    for component in reversed((absolute, *absolute.parents)):
        try:
            info = os.lstat(native_path(component))
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
                or not stat.S_ISDIR(info.st_mode)):
            raise OSError("member directory contains a link or non-directory")


def _regular_member_identity(info) -> tuple[int, int, int, int, int]:
    if (not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
            or info.st_nlink != 1 or not info.st_ino):
        raise OSError("member target is not an observed single regular file")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)


def _compare_member_bytes(fd: int, payload: bytes) -> None:
    """Read at most one byte beyond the expected content, even on growth."""
    total = 0
    while total <= len(payload):
        chunk = os.read(fd, min(65_536, len(payload) + 1 - total))
        if not chunk:
            break
        if chunk != payload[total:total + len(chunk)]:
            raise FileExistsError("member target contains different bytes")
        total += len(chunk)
    if total != len(payload):
        raise OSError("member target changed during verification")


def _verify_existing_member(target: Path, payload: bytes, native_path) -> None:
    path = native_path(target)
    before = _regular_member_identity(os.lstat(path))
    if before[2] != len(payload):
        raise FileExistsError("member target already contains different bytes")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        if _regular_member_identity(os.fstat(fd)) != before:
            raise OSError("member target changed before verification")
        _checked_directory_chain(target.parent, native_path)
        _compare_member_bytes(fd, payload)
        if _regular_member_identity(os.fstat(fd)) != before:
            raise OSError("member target changed during verification")
        if _regular_member_identity(os.lstat(path)) != before:
            raise OSError("member target path changed during verification")
        _checked_directory_chain(target.parent, native_path)
    finally:
        os.close(fd)


def prepare_directory(path: Path, native_path) -> None:
    """Prepare a transfer directory after checking its observed ancestors."""
    path = Path(path)
    _checked_directory_chain(path, native_path)
    Path(native_path(path)).mkdir(parents=True, exist_ok=True)
    _checked_directory_chain(path, native_path)


def offer_member(target: Path, payload: bytes, native_path) -> None:
    """Exclusively create or verify identical bytes; never remove failures."""
    if not isinstance(payload, bytes):
        raise TypeError("member payload must be immutable bytes")
    target = Path(target)
    _checked_directory_chain(target.parent, native_path)
    path = native_path(target)
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        _verify_existing_member(target, payload, native_path)
        return
    try:
        opened = _regular_member_identity(os.fstat(fd))
        if _regular_member_identity(os.lstat(path)) != opened:
            raise OSError("member target path changed before writing")
        _checked_directory_chain(target.parent, native_path)
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:offset + 65_536])
            if written <= 0:
                raise OSError("member write made no progress")
            offset += written
        after = _regular_member_identity(os.fstat(fd))
        if after[:2] != opened[:2] or after[2] != len(payload):
            raise OSError("member target changed during writing")
        os.lseek(fd, 0, os.SEEK_SET)
        _compare_member_bytes(fd, payload)
        if _regular_member_identity(os.fstat(fd)) != after:
            raise OSError("member target changed during verification")
        if _regular_member_identity(os.lstat(path)) != after:
            raise OSError("member target path changed during writing")
        _checked_directory_chain(target.parent, native_path)
    finally:
        os.close(fd)
