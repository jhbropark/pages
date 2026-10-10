import {copyFile, mkdir, readFile, rm, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';

const args = process.argv.slice(2);
const getArg = (name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
};

const jobPath = path.resolve(getArg('--job', 'jobs/example.json'));
const outputDir = path.resolve(getArg('--output-dir', 'outputs'));
const job = JSON.parse(await readFile(jobPath, 'utf8'));
if (!job.sourceAbsolutePath) throw new Error('job.sourceAbsolutePath is required');

await mkdir('public/input', {recursive: true});
await mkdir(outputDir, {recursive: true});
await rm('public/input/source.mp4', {force: true});
await rm('public/input/source.avi', {force: true});
await rm('public/input/source.mov', {force: true});

const ext = path.extname(job.sourceAbsolutePath).toLowerCase() || '.mp4';
const sourceName = `source${ext}`;
await copyFile(job.sourceAbsolutePath, path.join('public/input', sourceName));
const props = {...job, source: `input/${sourceName}`};
await writeFile('public/input/job.json', JSON.stringify(props, null, 2));

const outputPath = path.join(outputDir, `${job.id || 'render'}-${job.preset || 'vertical'}.mp4`);
const remotionCli = path.resolve('node_modules/@remotion/cli/remotion-cli.js');
const composition = job.preset === 'landscape' ? 'Landscape' : job.preset === 'square' ? 'Square' : 'Vertical';
const cliArgs = [remotionCli, 'render', 'src/index.ts', composition, outputPath, '--props', JSON.stringify(props), '--log', 'verbose'];
console.log(`Rendering ${job.sourceAbsolutePath}`);
console.log(`Output: ${outputPath}`);

await new Promise((resolve, reject) => {
  const child = spawn(process.execPath, cliArgs, {stdio: 'inherit', shell: false});
  child.on('error', reject);
  child.on('exit', (code) => code === 0 ? resolve() : reject(new Error(`Remotion exited with code ${code}`)));
});
console.log(JSON.stringify({ok: true, outputPath, jobId: job.id || 'render'}));
