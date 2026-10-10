import path from 'node:path';
import {execFileSync} from 'node:child_process';

const args = process.argv.slice(2);
const get = (name, fallback = '') => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : fallback;
};
const file = path.resolve(get('--file'));
const title = get('--title', path.basename(file, path.extname(file)));
const description = get('--description', '');
const channels = get('--channels', 'youtube,instagram,facebook,tiktok');
const live = args.includes('--live');
if (!file || !args.includes('--file')) throw new Error('Usage: node dispatch-local.mjs --file outputs/video.mp4 --title "Title" [--live]');

const repo = process.env.GITHUB_REPO || 'jhbropark/pages';
const tag = `video-local-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`;
const assetName = path.basename(file);
const assetUrl = `https://github.com/${repo}/releases/download/${tag}/${encodeURIComponent(assetName)}`;
const dryRun = live ? 'false' : 'true';

execFileSync('gh', ['release', 'create', tag, file, '--repo', repo, '--title', `Local video ${tag}`, '--notes', 'Uploaded by local Remotion dispatch.', '--prerelease'], {stdio: 'inherit'});
execFileSync('gh', ['workflow', 'run', 'video-publish.yml', '--repo', repo, '--ref', 'main', '-f', `media_url=${assetUrl}`, '-f', `title=${title}`, '-f', `description=${description}`, '-f', `channels=${channels}`, '-f', `dry_run=${dryRun}`], {stdio: 'inherit'});
console.log(JSON.stringify({repo, tag, assetUrl, dryRun}, null, 2));
