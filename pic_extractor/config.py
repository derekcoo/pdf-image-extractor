from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from pic_extractor.services.pdf_extractor import DEFAULT_MAX_FILE_SIZE_BYTES, DEFAULT_MAX_PAGES


DEFAULT_MAX_FILE_SIZE_MB = DEFAULT_MAX_FILE_SIZE_BYTES // (1024 * 1024)


@dataclass(frozen=True)
class RuntimeConfig:
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB
    max_pages: int = DEFAULT_MAX_PAGES

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


def load_runtime_config(environ: Mapping[str, str] | None = None) -> RuntimeConfig:
    env = environ or os.environ
    return RuntimeConfig(
        max_file_size_mb=_get_positive_int(env, "PIC_EXTRACTOR_MAX_FILE_SIZE_MB", DEFAULT_MAX_FILE_SIZE_MB),
        max_pages=_get_positive_int(env, "PIC_EXTRACTOR_MAX_PAGES", DEFAULT_MAX_PAGES),
    )


def _get_positive_int(environ: Mapping[str, str], key: str, default: int) -> int:
    raw_value = environ.get(key)
    if raw_value is None or raw_value == "":
        return default

    value = int(raw_value)
    if value <= 0:
        raise ValueError(f"{key} must be a positive integer.")
    return value
