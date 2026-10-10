#!/usr/bin/env python3
import argparse, os
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def publish(video_file, title, description, tags, privacy='private', dry=False):
    if dry:
        print(f'[dry-run] YouTube upload {video_file} title={title!r} privacy={privacy}')
        return 'DRYRUN'
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    required = ['YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REFRESH_TOKEN']
    missing = [x for x in required if not os.environ.get(x)]
    if missing:
        raise RuntimeError('Missing YouTube secrets: ' + ', '.join(missing))
    creds = Credentials(
        token=None,
        refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ['YOUTUBE_CLIENT_ID'],
        client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],
        scopes=SCOPES,
    )
    youtube = build('youtube', 'v3', credentials=creds, cache_discovery=False)
    body = {
        'snippet': {
            'title': title[:100],
            'description': description[:5000],
            'tags': tags[:500],
            'categoryId': os.environ.get('YOUTUBE_CATEGORY_ID', '22'),
        },
        'status': {
            'privacyStatus': privacy,
            'selfDeclaredMadeForKids': False,
        },
    }
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=MediaFileUpload(video_file, chunksize=8 * 1024 * 1024, resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response['id']
    print(f'youtube_video_id: {video_id}')
    print(f'youtube_url: https://www.youtube.com/watch?v={video_id}')
    return video_id

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', required=True)
    ap.add_argument('--title', required=True)
    ap.add_argument('--description', default='')
    ap.add_argument('--tags', default='')
    ap.add_argument('--privacy', default='private')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    print(publish(args.file, args.title, args.description, [x for x in args.tags.split(',') if x], args.privacy, args.dry_run))
