import {mkdir, readdir, stat, writeFile} from 'node:fs/promises';
import path from 'node:path';

const sourceDir = process.env.VIDEO_SOURCE_DIR || 'E:\\00_Project_Videos';
const outputPath = process.env.ASSET_CATALOG || path.resolve('jobs/catalog.json');
const allowed = new Set(['.mp4', '.avi', '.mov', '.m4v', '.mkv']);

async function walk(dir) {
  const entries = await readdir(dir, {withFileTypes: true});
  const result = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) result.push(...await walk(fullPath));
    else if (allowed.has(path.extname(entry.name).toLowerCase())) result.push(fullPath);
  }
  return result;
}

const files = await walk(sourceDir);
const assets = [];
for (const fullPath of files) {
  const info = await stat(fullPath);
  assets.push({
    id: Buffer.from(fullPath).toString('base64url'),
    absolutePath: fullPath,
    relativePath: path.relative(sourceDir, fullPath),
    filename: path.basename(fullPath),
    extension: path.extname(fullPath).toLowerCase(),
    bytes: info.size,
    modifiedAt: info.mtime.toISOString(),
  });
}
assets.sort((a, b) => b.modifiedAt.localeCompare(a.modifiedAt));
await mkdir(path.dirname(outputPath), {recursive: true});
await writeFile(outputPath, JSON.stringify({sourceDir, generatedAt: new Date().toISOString(), count: assets.length, assets}, null, 2));
console.log(`Discovered ${assets.length} videos from ${sourceDir}`);
console.log(`Catalog: ${outputPath}`);
