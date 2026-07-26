#!/usr/bin/env python3
"""Tiny shared Krea API client — submit a generation job and poll for its URL.

Both apod_namecode.py (image) and krea_reel.py (video) hit the same endpoints:
  POST /generate/<subpath>  -> {"job_id": ...}
  GET  /jobs/<job_id>       -> {"status": ..., "result": {"urls": [...]}}

Env: KREA_API_KEY (required), KREA_BASE (default https://api.krea.ai).
"""
import os, time, requests


def _cfg():
    return os.environ.get("KREA_BASE", "https://api.krea.ai"), os.environ["KREA_API_KEY"]


def submit(subpath, body):
    """Start a job. `subpath` is e.g. 'image/bfl/flux-1-dev' or 'video/kling/kling-1.6'."""
    base, key = _cfg()
    r = requests.post(f"{base}/generate/{subpath}", json=body,
                      headers={"Authorization": f"Bearer {key}"}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"krea POST /generate/{subpath} -> {r.status_code} {r.text}")
    return r.json()["job_id"]


def wait(job_id, timeout=900, delay=3):
    """Poll until the job completes; return its first result URL."""
    base, key = _cfg()
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = requests.get(f"{base}/jobs/{job_id}",
                         headers={"Authorization": f"Bearer {key}"}, timeout=30)
        r.raise_for_status()
        j = r.json()
        st = j.get("status")
        if st == "completed":
            res = j.get("result")
            if isinstance(res, dict):
                urls = res.get("urls") or ([res["url"]] if res.get("url") else [])
            elif isinstance(res, list):
                urls = res
            else:
                urls = []
            urls = urls or j.get("urls") or []
            if not urls:
                raise RuntimeError(f"krea completed but no result url: {j}")
            return urls[0]
        if st == "failed":
            raise RuntimeError(f"krea job failed: {j}")
        time.sleep(delay)
    raise TimeoutError("krea job timed out")
