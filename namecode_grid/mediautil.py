#!/usr/bin/env python3
"""Shared media helpers."""
from shutil import which


def ffmpeg_exe():
    """Prefer a system ffmpeg; fall back to the imageio-ffmpeg static binary."""
    return which("ffmpeg") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
