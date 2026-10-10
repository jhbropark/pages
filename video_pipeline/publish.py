#!/usr/bin/env python3
import argparse, json, os, subprocess, sys
from pathlib import Path
from youtube_publish import publish as publish_youtube
from tiktok_publish import publish as publish_tiktok

ROOT = Path(__file__).resolve().parents[1]
IG_SCRIPT = ROOT / 'namecode_grid' / 'ig_publish.py'
FB_SCRIPT = ROOT / 'namecode_grid' / 'fb_publish.py'

def run_meta(script, args, dry):
    cmd = [sys.executable, str(script), *args]
    if dry:
        cmd.append('--dry-run')
    p = subprocess.run(cmd, text=True, capture_output=True, env=os.environ.copy())
    if p.stdout: print(p.stdout, end='')
    if p.stderr: print(p.stderr, end='', file=sys.stderr)
    if p.returncode:
        raise RuntimeError(f'{script.name} exited with {p.returncode}')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', required=True)
    ap.add_argument('--video-url', required=True, help='Public HTTPS URL used by Meta and TikTok')
    ap.add_argument('--title', required=True)
    ap.add_argument('--description', default='')
    ap.add_argument('--instagram-caption', default='')
    ap.add_argument('--facebook-caption', default='')
    ap.add_argument('--tiktok-title', default='')
    ap.add_argument('--tags', default='')
    ap.add_argument('--channels', default='youtube,instagram,facebook,tiktok')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    channels = [x.strip().lower() for x in args.channels.split(',') if x.strip()]
    instagram_caption = args.instagram_caption or args.description
    facebook_caption = args.facebook_caption or args.description
    tiktok_title = args.tiktok_title or args.title
    results = {}
    for channel in channels:
        try:
            if channel == 'youtube':
                results[channel] = publish_youtube(args.file, args.title, args.description, [x for x in args.tags.split(',') if x], os.environ.get('YOUTUBE_PRIVACY', 'private'), args.dry_run)
            elif channel == 'instagram':
                run_meta(IG_SCRIPT, ['--reel', '--video-url', args.video_url, '--caption', instagram_caption], args.dry_run)
                results[channel] = 'ok'
            elif channel == 'facebook':
                run_meta(FB_SCRIPT, ['--video-url', args.video_url, '--caption', facebook_caption], args.dry_run)
                results[channel] = 'ok'
            elif channel == 'tiktok':
                results[channel] = publish_tiktok(args.video_url, args.file, tiktok_title, args.dry_run)
            else:
                raise RuntimeError(f'Unknown channel: {channel}')
        except Exception as exc:
            results[channel] = {'error': str(exc)}
            print(f'[error] {channel}: {exc}', file=sys.stderr)
    print(json.dumps({'channels': results}, ensure_ascii=False, indent=2))
    if any(isinstance(v, dict) and 'error' in v for v in results.values()):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
