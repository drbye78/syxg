"""
Sample Library - Sample Management and Organization

Provides comprehensive sample library management for the XG synthesizer,
including sample organization, search, categorization, and metadata handling.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any


class SampleLibrary:
    """
    Comprehensive sample library management system.

    Provides organization, search, categorization, and metadata handling
    for professional sample management in the XG workstation.
    """

    def __init__(self, library_paths: list[str] | None = None):
        """
        Initialize sample library.

        Args:
            library_paths: List of paths to scan for samples
        """
        self.library_paths = library_paths or []
        self.samples: dict[str, dict[str, Any]] = {}
        self.categories: dict[str, list[str]] = {}
        self.metadata: dict[str, dict[str, Any]] = {}

        # Threading
        self.lock = threading.RLock()
        self.scan_in_progress = False

        # Initialize default categories
        self._initialize_categories()

    def _initialize_categories(self):
        """Initialize default sample categories."""
        self.categories = {
            "drums": [],
            "bass": [],
            "guitar": [],
            "piano": [],
            "strings": [],
            "brass": [],
            "woodwind": [],
            "percussion": [],
            "fx": [],
            "vocals": [],
            "synth": [],
            "ethnic": [],
            "loops": [],
            "oneshots": [],
        }

    def add_library_path(self, path: str) -> bool:
        """
        Add a library path to scan.

        Args:
            path: Path to add

        Returns:
            Success status
        """
        with self.lock:
            if os.path.exists(path) and path not in self.library_paths:
                self.library_paths.append(path)
                return True
            return False

    def scan_library(self, progress_callback: callable | None = None) -> bool:
        """
        Scan all library paths for samples.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            Success status
        """
        with self.lock:
            if self.scan_in_progress:
                return False

            self.scan_in_progress = True

            try:
                total_files = 0
                processed_files = 0

                # Count total files first
                for path in self.library_paths:
                    if os.path.exists(path):
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                if self._is_sample_file(file):
                                    total_files += 1

                # Scan files
                for path in self.library_paths:
                    if os.path.exists(path):
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                if self._is_sample_file(file):
                                    file_path = os.path.join(root, file)
                                    self._add_sample(file_path)

                                    processed_files += 1
                                    if progress_callback and total_files > 0:
                                        progress = processed_files / total_files
                                        progress_callback(progress, file)

                # Update categories
                self._update_categories()

                return True

            finally:
                self.scan_in_progress = False

    def _is_sample_file(self, filename: str) -> bool:
        """Check if file is a sample file."""
        sample_extensions = {".wav", ".aiff", ".flac", ".ogg", ".mp3", ".raw", ".pcm"}
        _, ext = os.path.splitext(filename.lower())
        return ext in sample_extensions

    def _add_sample(self, file_path: str):
        """Add a sample to the library."""
        sample_id = self._generate_sample_id(file_path)

        # Basic metadata
        metadata = {
            "id": sample_id,
            "path": file_path,
            "filename": os.path.basename(file_path),
            "directory": os.path.dirname(file_path),
            "size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "date_added": self._get_current_timestamp(),
            "categories": self._guess_categories(file_path),
            "tags": [],
        }

        # Try to get audio metadata
        audio_info = self._get_audio_info(file_path)
        if audio_info:
            metadata.update(audio_info)

        self.samples[sample_id] = metadata
        self.metadata[sample_id] = metadata

    def _generate_sample_id(self, file_path: str) -> str:
        """Generate unique sample ID."""
        import hashlib

        return hashlib.md5(file_path.encode()).hexdigest()[:16]

    def _guess_categories(self, file_path: str) -> list[str]:
        """Guess sample categories based on path and filename."""
        path_lower = file_path.lower()
        categories = []

        # Check path for category hints
        if any(word in path_lower for word in ["drum", "percussion", "kit"]):
            categories.append("drums")
        if any(word in path_lower for word in ["bass", "sub"]):
            categories.append("bass")
        if any(word in path_lower for word in ["guitar", "gtr"]):
            categories.append("guitar")
        if any(word in path_lower for word in ["piano", "keys"]):
            categories.append("piano")
        if any(word in path_lower for word in ["string", "violin", "cello"]):
            categories.append("strings")
        if any(word in path_lower for word in ["brass", "trumpet", "trombone"]):
            categories.append("brass")
        if any(word in path_lower for word in ["woodwind", "flute", "sax"]):
            categories.append("woodwind")
        if any(word in path_lower for word in ["fx", "effect", "sfx"]):
            categories.append("fx")
        if any(word in path_lower for word in ["vocal", "voice", "sing"]):
            categories.append("vocals")
        if any(word in path_lower for word in ["synth", "synthesis"]):
            categories.append("synth")
        if any(word in path_lower for word in ["loop", "pattern"]):
            categories.append("loops")
        if any(word in path_lower for word in ["oneshot", "hit"]):
            categories.append("oneshots")

        return categories if categories else ["uncategorized"]

    def _get_audio_info(self, file_path: str) -> dict[str, Any] | None:
        """Get audio file information."""
        try:
            # Try to get basic file info
            stat = os.stat(file_path)

            info = {
                "file_size": stat.st_size,
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
            }

            # Try to get audio metadata using PyAV
            try:
                import av

                container = av.open(file_path)

                # Find audio stream
                audio_stream = None
                for stream in container.streams:
                    if stream.type == "audio":
                        audio_stream = stream
                        break

                if audio_stream:
                    # Calculate duration
                    if audio_stream.duration and audio_stream.time_base:
                        duration_seconds = float(audio_stream.duration * audio_stream.time_base)
                    else:
                        duration_seconds = 0

                    info.update(
                        {
                            "sample_rate": audio_stream.sample_rate,
                            "channels": audio_stream.channels,
                            "frames": audio_stream.frames or 0,
                            "duration_seconds": duration_seconds,
                            "codec": audio_stream.codec.name if audio_stream.codec else "unknown",
                            "bit_depth": self._get_bit_depth_from_format(audio_stream.format.name),
                        }
                    )

                container.close()

            except ImportError:
                # Fallback: assume 44.1kHz stereo
                estimated_frames = (stat.st_size * 44100) // (2 * 2)  # rough estimate
                info.update(
                    {
                        "sample_rate": 44100,
                        "channels": 2,
                        "estimated_frames": estimated_frames,
                        "estimated_duration": estimated_frames / 44100,
                    }
                )
            except Exception:
                pass

            return info

        except Exception:
            return None

    def _get_bit_depth_from_format(self, format_name: str) -> int:
        """
        Get bit depth from PyAV format name.

        Args:
            format_name: PyAV format name (e.g., 'flt', 's16', 's32', 'u8')

        Returns:
            Bit depth in bits (8, 16, 24, 32, 64), defaults to 16
        """
        format_map = {
            "u8": 8,
            "s16": 16,
            "s32": 32,
            "flt": 32,
            "dbl": 64,
            "u8p": 8,
            "s16p": 16,
            "s32p": 32,
            "fltp": 32,
            "dblp": 64,
            "pcm_s16le": 16,
            "pcm_s24le": 24,
            "pcm_s32le": 32,
            "pcm_f32le": 32,
            "pcm_f64le": 64,
            "mp3": 16,
            "aac": 16,
            "vorbis": 16,
            "flac": 24,
        }
        base_format = format_name.lower().rstrip("p")
        return format_map.get(base_format, format_map.get(format_name.lower(), 16))

    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time

        return time.time()

    def _update_categories(self):
        """Update category listings."""
        # Reset categories
        for cat in self.categories:
            self.categories[cat] = []

        # Rebuild from samples
        for sample in self.samples.values():
            for category in sample.get("categories", []):
                if category in self.categories:
                    self.categories[category].append(sample["id"])

    def search_samples(
        self, query: str, category: str | None = None, tags: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Search samples by query.

        Args:
            query: Search query
            category: Optional category filter
            tags: Optional tag filters

        Returns:
            List of matching samples
        """
        with self.lock:
            results = []
            query_lower = query.lower()

            for sample in self.samples.values():
                # Category filter
                if category and category not in sample.get("categories", []):
                    continue

                # Tag filter
                if tags:
                    sample_tags = sample.get("tags", [])
                    if not all(tag in sample_tags for tag in tags):
                        continue

                # Text search
                searchable_text = " ".join(
                    [
                        sample.get("filename", ""),
                        " ".join(sample.get("categories", [])),
                        " ".join(sample.get("tags", [])),
                    ]
                ).lower()

                if query_lower in searchable_text:
                    results.append(sample.copy())

            return results

    def get_sample_by_id(self, sample_id: str) -> dict[str, Any] | None:
        """
        Get sample by ID.

        Args:
            sample_id: Sample ID

        Returns:
            Sample metadata or None
        """
        with self.lock:
            return self.samples.get(sample_id)

    def get_samples_by_category(self, category: str) -> list[dict[str, Any]]:
        """
        Get samples by category.

        Args:
            category: Category name

        Returns:
            List of samples in category
        """
        with self.lock:
            sample_ids = self.categories.get(category, [])
            return [self.samples[sid] for sid in sample_ids if sid in self.samples]

    def add_tag(self, sample_id: str, tag: str) -> bool:
        """
        Add tag to sample.

        Args:
            sample_id: Sample ID
            tag: Tag to add

        Returns:
            Success status
        """
        with self.lock:
            if sample_id in self.samples:
                if "tags" not in self.samples[sample_id]:
                    self.samples[sample_id]["tags"] = []
                if tag not in self.samples[sample_id]["tags"]:
                    self.samples[sample_id]["tags"].append(tag)
                return True
            return False

    def remove_tag(self, sample_id: str, tag: str) -> bool:
        """
        Remove tag from sample.

        Args:
            sample_id: Sample ID
            tag: Tag to remove

        Returns:
            Success status
        """
        with self.lock:
            if sample_id in self.samples:
                if "tags" in self.samples[sample_id]:
                    if tag in self.samples[sample_id]["tags"]:
                        self.samples[sample_id]["tags"].remove(tag)
                        return True
            return False

    def save_library_metadata(self, filename: str) -> bool:
        """
        Save library metadata to file.

        Args:
            filename: Output filename

        Returns:
            Success status
        """
        with self.lock:
            try:
                data = {
                    "library_paths": self.library_paths,
                    "samples": self.samples,
                    "categories": self.categories,
                    "metadata": self.metadata,
                }

                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)

                return True
            except Exception:
                return False

    def load_library_metadata(self, filename: str) -> bool:
        """
        Load library metadata from file.

        Args:
            filename: Input filename

        Returns:
            Success status
        """
        with self.lock:
            try:
                with open(filename) as f:
                    data = json.load(f)

                self.library_paths = data.get("library_paths", [])
                self.samples = data.get("samples", {})
                self.categories = data.get("categories", {})
                self.metadata = data.get("metadata", {})

                return True
            except Exception:
                return False

    def get_library_stats(self) -> dict[str, Any]:
        """
        Get library statistics.

        Returns:
            Library statistics
        """
        with self.lock:
            total_size = sum(s.get("size_bytes", 0) for s in self.samples.values())
            categories_count = {cat: len(samples) for cat, samples in self.categories.items()}

            return {
                "total_samples": len(self.samples),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "categories": categories_count,
                "library_paths": len(self.library_paths),
                "scan_in_progress": self.scan_in_progress,
            }

    def clear_library(self):
        """Clear all library data."""
        with self.lock:
            self.samples.clear()
            self.metadata.clear()
            for cat in self.categories:
                self.categories[cat] = []
