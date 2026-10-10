#!/usr/bin/env python3
import argparse, os, time
from pathlib import Path
import requests

BASE = 'https://open.tiktokapis.com/v2/post/publish'
CHUNK_SIZE = 10 * 1024 * 1024

def _headers(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json; charset=UTF-8'}

def _status(token, publish_id):
    r = requests.post(f'{BASE}/status/fetch/', headers=_headers(token), json={'publish_id': publish_id}, timeout=60)
    if not r.ok:
        return None
    return (r.json().get('data') or {}).get('status')

def _wait(token, publish_id):
    for _ in range(30):
        time.sleep(5)
        status = _status(token, publish_id)
        print(f'tiktok_status: {status}')
        if status in ('PUBLISH_COMPLETE', 'FAILED'):
            if status == 'FAILED':
                raise RuntimeError('TikTok publish failed')
            return
    raise RuntimeError('TikTok publish did not complete within the polling window')

def publish(video_url, video_file, title, dry=False):
    if dry:
        print(f'[dry-run] TikTok FILE_UPLOAD {video_file}')
        return 'DRYRUN'
    token = os.environ.get('TIKTOK_ACCESS_TOKEN')
    if not token:
        raise RuntimeError('TIKTOK_ACCESS_TOKEN is missing')

    use_file_upload = os.environ.get('TIKTOK_USE_FILE_UPLOAD', '1') == '1'
    if use_file_upload:
        size = Path(video_file).stat().st_size
        chunk_size = min(CHUNK_SIZE, size)
        total_chunks = (size + chunk_size - 1) // chunk_size
        source_info = {
            'source': 'FILE_UPLOAD',
            'video_size': size,
            'chunk_size': chunk_size,
            'total_chunk_count': total_chunks,
        }
    else:
        source_info = {'source': 'PULL_FROM_URL', 'video_url': video_url}

    body = {
        'post_info': {
            'title': title[:2200],
            'privacy_level': os.environ.get('TIKTOK_PRIVACY_LEVEL', 'SELF_ONLY'),
            'disable_duet': False,
            'disable_comment': False,
            'disable_stitch': False,
        },
        'source_info': source_info,
    }
    r = requests.post(f'{BASE}/video/init/', headers=_headers(token), json=body, timeout=60)
    if not r.ok:
        raise RuntimeError(f'TikTok init failed: {r.status_code} {r.text}')
    data = r.json().get('data') or {}
    publish_id = data.get('publish_id')
    upload_url = data.get('upload_url')
    if not publish_id:
        raise RuntimeError(f'TikTok response missing publish_id: {r.text}')

    if use_file_upload:
        size = Path(video_file).stat().st_size
        with open(video_file, 'rb') as f:
            start = 0
            while start < size:
                chunk = f.read(CHUNK_SIZE)
                end = start + len(chunk) - 1
                upload = requests.put(upload_url, headers={
                    'Content-Range': f'bytes {start}-{end}/{size}',
                    'Content-Type': 'video/mp4',
                }, data=chunk, timeout=180)
                if upload.status_code not in (200, 201, 206):
                    raise RuntimeError(f'TikTok file upload failed: {upload.status_code} {upload.text}')
                start = end + 1
                print(f'tiktok_uploaded_bytes: {start}/{size}')
    _wait(token, publish_id)
    print(f'tiktok_publish_id: {publish_id}')
    return publish_id

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--video-url', required=True)
    ap.add_argument('--video-file', required=True)
    ap.add_argument('--title', default='')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    print(publish(args.video_url, args.video_file, args.title, args.dry_run))
