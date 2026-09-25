#!/usr/bin/env node
/**
 * build_namecode_archive.mjs
 *
 * Builds the static namecode artwork archive (index + per-work pages + sitemap + feed)
 * from the real daily brief JSON files that already live in the repo.
 *
 * Zero dependencies. Node 18+ (uses only node:fs, node:path, node:url).
 *
 * Usage:
 *   node build_namecode_archive.mjs --repo-root <path-to-repo> --out <output-dir> [options]
 *
 * Options:
 *   --repo-root <dir>   Repo root that contains namecode_grid/daily/ (default: cwd)
 *   --out <dir>         Output directory for the archive (default: <repo-root>/namecode)
 *   --dates a,b,c       Only build these dates (default: all briefs found)
 *   --limit N           Keep only the N most recent dates (default: 30)
 *   --base-url URL      Absolute site base, no trailing slash
 *                       (default: https://jhbropark.github.io/pages)
 *   --asset-base PATH   Root-relative path to the daily assets as served
 *                       (default: /pages/namecode_grid/daily)
 *   --no-feed           Skip feed.xml
 *   --quiet
 *
 * Notes:
 *   - Images/videos are NOT copied. Pages reference the existing published assets.
 *   - Only facts present in the brief files are rendered. No science text is invented.
 *   - Page titles use `apod_title`. The legacy `work_name` codename is shown verbatim
 *     as the label burned into the image, with a mismatch disclosure when it does not
 *     appear in the APOD title (e.g. COMET on "Cocoon Nebula Wide Field" and on
 *     "A New Lunar Crater: McGetchin").
 */

import fs from 'node:fs';
import path from 'node:path';

/* ------------------------------------------------------------------ config */

const BRAND = {
  name: 'namecode',
  // Verified 2026-09-25: both resolve to the project's own accounts.
  instagram: 'https://www.instagram.com/namecode_original/',
  facebook: 'https://www.facebook.com/namecode.original',
  igHandle: '@namecode_original',
  fbHandle: 'namecode.original',
};

const DEFAULTS = {
  baseUrl: 'https://jhbropark.github.io/pages',
  assetBase: '/pages/namecode_grid/daily',
  limit: 30,
};

/* -------------------------------------------------------------------- args */

function parseArgs(argv) {
  const out = { feed: true, quiet: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    if (a === '--repo-root') out.repoRoot = next();
    else if (a === '--out') out.out = next();
    else if (a === '--dates') out.dates = next().split(',').map((s) => s.trim()).filter(Boolean);
    else if (a === '--limit') out.limit = parseInt(next(), 10);
    else if (a === '--base-url') out.baseUrl = next().replace(/\/+$/, '');
    else if (a === '--asset-base') out.assetBase = next().replace(/\/+$/, '');
    else if (a === '--no-feed') out.feed = false;
    else if (a === '--quiet') out.quiet = true;
    else if (a === '--help' || a === '-h') out.help = true;
    else throw new Error(`Unknown argument: ${a}`);
  }
  return out;
}

/* ------------------------------------------------------------------ helpers */

const esc = (s) =>
  String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

const escAttr = esc;

/** JSON-LD is embedded in a <script> block: neutralise the only dangerous sequence. */
const jsonld = (obj) => JSON.stringify(obj, null, 2).replace(/</g, '\\u003c');

const exists = (p) => {
  try {
    return fs.statSync(p).isFile();
  } catch {
    return false;
  }
};

const nonEmptyFile = (p) => {
  try {
    const st = fs.statSync(p);
    return st.isFile() && st.size > 0;
  } catch {
    return false;
  }
};

/** Read intrinsic PNG size from the IHDR chunk. Returns null when unreadable. */
function pngSize(file) {
  try {
    const fd = fs.openSync(file, 'r');
    const buf = Buffer.alloc(24);
    const read = fs.readSync(fd, buf, 0, 24, 0);
    fs.closeSync(fd);
    if (read < 24) return null;
    if (buf.readUInt32BE(0) !== 0x89504e47) return null;
    return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  } catch {
    return null;
  }
}

const KO_DATE = (iso) => {
  const [y, m, d] = iso.split('-');
  return `${y}년 ${Number(m)}월 ${Number(d)}일`;
};

/**
 * The prompt string embeds a real excerpt of the NASA APOD caption between the
 * generated head and tail. Pull it out verbatim; never rewrite or extend it.
 */
function apodExcerpt(brief) {
  const p = String(brief.prompt || '');
  const head = `inspired by ${brief.apod_title}.`;
  const tail = 'Rendered as fine white particles';
  const i = p.indexOf(head);
  const j = p.indexOf(tail);
  if (i === -1 || j === -1 || j <= i) return '';
  return p
    .slice(i + head.length, j)
    .replace(/\s+/g, ' ')
    .trim();
}

/* ------------------------------------------------------------------ loading */

function loadWorks(opts) {
  const dailyDir = path.join(opts.repoRoot, 'namecode_grid', 'daily');
  if (!fs.existsSync(dailyDir)) {
    throw new Error(`Daily brief directory not found: ${dailyDir}`);
  }
  const files = fs
    .readdirSync(dailyDir)
    .filter((f) => /^brief_\d{4}-\d{2}-\d{2}\.json$/.test(f))
    .sort();

  let works = [];
  for (const f of files) {
    const date = f.slice(6, 16);
    if (opts.dates && !opts.dates.includes(date)) continue;
    let brief;
    try {
      brief = JSON.parse(fs.readFileSync(path.join(dailyDir, f), 'utf8'));
    } catch (e) {
      console.warn(`[skip] ${f}: unreadable JSON (${e.message})`);
      continue;
    }
    if (!brief.apod_title) {
      console.warn(`[skip] ${f}: no apod_title`);
      continue;
    }

    const squareFile = path.join(dailyDir, `namecode_apod_${date}.png`);
    const verticalFile = path.join(dailyDir, `namecode_apod_${date}_9x16.png`);
    const reelFile = path.join(dailyDir, `reel_${date}.mp4`);

    const square = exists(squareFile);
    if (!square) {
      console.warn(`[skip] ${date}: no rendered artwork (${path.basename(squareFile)})`);
      continue;
    }

    const size = nonEmptyFile(squareFile) ? pngSize(squareFile) : null;

    works.push({
      date,
      apodTitle: String(brief.apod_title).trim(),
      workName: String(brief.work_name || '').trim(),
      label: String(brief.label || '').trim(),
      source: String(brief.source || '').trim(),
      excerpt: apodExcerpt(brief),
      assets: {
        square: `${opts.assetBase}/namecode_apod_${date}.png`,
        squareAbs: `${opts.baseUrl}/namecode_grid/daily/namecode_apod_${date}.png`,
        vertical: exists(verticalFile) ? `${opts.assetBase}/namecode_apod_${date}_9x16.png` : null,
        reel: exists(reelFile) ? `${opts.assetBase}/reel_${date}.mp4` : null,
      },
      size,
      // Codename mismatch: the label word is a legacy auto-classification and is
      // not necessarily the subject of the APOD image.
      labelMismatch:
        !!brief.work_name &&
        !String(brief.apod_title).toUpperCase().includes(String(brief.work_name).toUpperCase()),
    });
  }

  works.sort((a, b) => (a.date < b.date ? 1 : -1)); // newest first
  if (opts.limit > 0) works = works.slice(0, opts.limit);
  return works;
}

/* -------------------------------------------------------------------- copy */

const COPY = {
  siteTitle: 'namecode 스카이 스터디 아카이브',
  tagline: '매일 하나의 하늘을 흑백으로 다시 그립니다.',
  intro:
    'NASA의 오늘의 천문 사진(APOD)에서 출발해, 그날의 하늘을 검은 바탕 위 흰 입자와 빛의 결로 다시 그린 생성 이미지입니다. 망원경으로 찍은 사진이 아니라 AI로 만든 작업물이고, NASA의 인증이나 후원을 받은 작업이 아닙니다.',
  ctaLabel: '인스타그램에서 다음 하늘 보기',
  ctaNote: '새 작업은 매일 인스타그램에 먼저 올라갑니다.',
  disclaimerHead: '이 이미지에 대하여',
  disclaimer: [
    'AI로 생성한 흑백 이미지입니다. 실제 망원경 촬영 이미지가 아닙니다.',
    '출발점이 된 NASA APOD 원본 이미지 주소를 각 작품 페이지에 그대로 적어 둡니다.',
    'NASA 및 APOD는 이 작업을 보증하거나 후원하지 않습니다.',
    '천체에 대한 설명은 쓰지 않습니다. 원본 문장 일부를 인용할 때는 출처를 함께 밝힙니다.',
  ],
  labelNote:
    '이미지 아래쪽에 찍힌 단어는 초기 자동 분류에서 붙은 시리즈 코드네임입니다. 작품의 주제는 코드네임이 아니라 APOD 원본 제목을 따릅니다.',
};

function altText(w) {
  return `${w.apodTitle}에서 출발한 흑백 생성 이미지. 검은 배경 위에 흰 입자와 가느다란 빛줄기가 퍼져 있고 여백이 넓다. ${w.date} namecode 스카이 스터디.`;
}

function metaDescription(w) {
  const base = `${KO_DATE(w.date)} namecode 스카이 스터디. NASA APOD "${w.apodTitle}"에서 출발한 AI 생성 흑백 이미지와 원본 출처, 이미지에 새겨진 레이블(${w.label || w.workName}) 기록.`;
  return base.length > 320 ? base.slice(0, 317) + '…' : base;
}

/* ---------------------------------------------------------------------- css */

const CSS = `
:root{
  --void:#000000;
  --ink:#ededed;
  --dim:#8f8f8f;
  --faint:#5a5a5a;
  --rule:#1e1e1e;
  --sans:"Pretendard","Apple SD Gothic Neo","Noto Sans KR","Segoe UI",system-ui,-apple-system,"Malgun Gothic",sans-serif;
  --mono:ui-monospace,"SFMono-Regular","Roboto Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;background:var(--void);color:var(--ink);
  font-family:var(--sans);font-size:17px;line-height:1.75;
  font-weight:400;letter-spacing:.005em;
  word-break:keep-all;
}
a{color:var(--ink);text-underline-offset:.22em;text-decoration-thickness:1px;text-decoration-color:var(--faint)}
a:hover{text-decoration-color:var(--ink)}
a:focus-visible,button:focus-visible,video:focus-visible{outline:2px solid #fff;outline-offset:3px}
img,video{display:block;max-width:100%;height:auto;background:#000}
.wrap{width:min(1180px,100% - 2.5rem);margin-inline:auto}
.text{max-width:62ch}

.masthead{padding:2rem 0 0}
.masthead nav{display:flex;gap:1.5rem;align-items:baseline;flex-wrap:wrap}
.wordmark{font-family:var(--mono);font-size:.95rem;letter-spacing:.34em;text-decoration:none;color:var(--ink)}
.masthead .where{font-family:var(--mono);font-size:.78rem;color:var(--faint);letter-spacing:.16em}

.lede{padding:3.5rem 0 2.75rem}
.lede h1{
  font-size:clamp(1.9rem,5.2vw,3.1rem);line-height:1.22;font-weight:500;
  margin:0 0 1rem;max-width:20ch;letter-spacing:-.015em;
}
.lede p{margin:0;color:var(--dim);max-width:58ch}

.hero{margin:0 0 4.5rem}
.hero figure{margin:0}
.hero img{width:100%;max-height:88vh;object-fit:contain;object-position:left}
.hero figcaption{padding-top:1rem;display:flex;flex-wrap:wrap;gap:.35rem 1.6rem;align-items:baseline}
.stamp{font-family:var(--mono);font-size:.78rem;color:var(--faint);letter-spacing:.14em}
.hero figcaption .src{font-size:1.05rem}

.works{border-top:1px solid var(--rule);padding-top:.5rem}
.work{padding:3rem 0;border-bottom:1px solid var(--rule);display:grid;gap:1.75rem}
@media (min-width:860px){
  .work{grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:3rem;align-items:start}
}
.work img{width:100%}
.work h2{margin:.25rem 0 .5rem;font-size:1.45rem;font-weight:500;line-height:1.3;letter-spacing:-.01em}
.work h2 a{text-decoration:none}
.work h2 a:hover{text-decoration:underline}
.work p{margin:0 0 .9rem;color:var(--dim);font-size:.97rem}
.work .go{font-size:.95rem}

.panel{padding:4rem 0;border-bottom:1px solid var(--rule)}
.panel h2{font-size:1.25rem;font-weight:500;margin:0 0 1rem}
.panel ul{margin:0;padding-left:1.1rem;color:var(--dim)}
.panel li{margin-bottom:.4rem}

.follow{padding:4.5rem 0 5rem}
.follow p{margin:0 0 1.5rem;color:var(--dim);max-width:52ch}
.cta{
  display:inline-block;padding:.85rem 1.6rem;border:1px solid var(--ink);
  text-decoration:none;font-size:1rem;background:transparent;color:var(--ink);
}
.cta:hover{background:var(--ink);color:var(--void)}
.follow .alt{display:block;margin-top:1.1rem;font-size:.9rem;color:var(--faint)}

.plate{padding:1.5rem 0 3.5rem}
.plate img{width:100%;max-height:86vh;object-fit:contain;object-position:left}
.plate figcaption{padding-top:.9rem;color:var(--faint);font-size:.88rem;max-width:62ch}

.record{padding:0 0 3rem;border-bottom:1px solid var(--rule)}
.record dl{display:grid;grid-template-columns:1fr;gap:0;margin:0}
@media (min-width:720px){.record dl{grid-template-columns:13rem minmax(0,1fr)}}
.record dt{color:var(--faint);font-size:.9rem;padding:.7rem 0 0;border-top:1px solid var(--rule)}
.record dd{margin:0;padding:.7rem 0 1rem;border-top:1px solid var(--rule);overflow-wrap:anywhere}
@media (max-width:719px){.record dt{border-top:1px solid var(--rule)}.record dd{border-top:0;padding-top:0}}
.record .mono{font-family:var(--mono);font-size:.9rem}

.quote{padding:3rem 0;border-bottom:1px solid var(--rule)}
.quote blockquote{margin:0;padding-left:1.25rem;border-left:1px solid var(--rule);max-width:62ch;color:var(--ink)}
.quote cite{display:block;margin-top:.9rem;font-style:normal;font-size:.88rem;color:var(--faint)}

.motion{padding:3rem 0;border-bottom:1px solid var(--rule)}
.motion h2{font-size:1.1rem;font-weight:500;margin:0 0 1rem}
.motion video{width:min(420px,100%)}
.motion p{color:var(--faint);font-size:.88rem;max-width:52ch}

.pager{display:flex;justify-content:space-between;gap:1.5rem;padding:2.5rem 0;flex-wrap:wrap}
.pager a{font-size:.95rem;max-width:22ch}
.pager .none{color:var(--faint);font-size:.95rem}

footer{border-top:1px solid var(--rule);padding:2.5rem 0 4rem;color:var(--faint);font-size:.88rem}
footer p{margin:0 0 .5rem;max-width:62ch}
footer a{color:var(--dim)}
`.trim();

/* -------------------------------------------------------------------- pages */

function head({ title, description, canonical, ogImage, ogType, imageAlt }) {
  return `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${escAttr(description)}">
<link rel="canonical" href="${escAttr(canonical)}">
<meta property="og:type" content="${escAttr(ogType)}">
<meta property="og:site_name" content="namecode">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="${escAttr(title)}">
<meta property="og:description" content="${escAttr(description)}">
<meta property="og:url" content="${escAttr(canonical)}">
<meta property="og:image" content="${escAttr(ogImage)}">
<meta property="og:image:alt" content="${escAttr(imageAlt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${escAttr(title)}">
<meta name="twitter:description" content="${escAttr(description)}">
<meta name="twitter:image" content="${escAttr(ogImage)}">
<meta name="twitter:image:alt" content="${escAttr(imageAlt)}">
<style>${CSS}</style>
</head>
<body>`;
}

function masthead(where, homeHref) {
  return `<header class="masthead"><div class="wrap"><nav>
<a class="wordmark" href="${escAttr(homeHref)}">namecode</a>
<span class="where">${esc(where)}</span>
</nav></div></header>`;
}

function footer(baseUrl) {
  return `<footer><div class="wrap">
<p>namecode는 NASA APOD를 출발점으로 삼은 독립 작업입니다. NASA와 APOD는 이 작업과 무관하며 이를 보증하지 않습니다.</p>
<p>모든 이미지는 AI로 생성한 흑백 작업물입니다. 망원경 촬영 사진이 아닙니다.</p>
<p><a href="${escAttr(BRAND.instagram)}" rel="me noopener">인스타그램 ${esc(BRAND.igHandle)}</a> · <a href="${escAttr(BRAND.facebook)}" rel="me noopener">페이스북 ${esc(BRAND.fbHandle)}</a> · <a href="${escAttr(baseUrl)}/namecode/">아카이브 처음으로</a></p>
</div></footer>
</body>
</html>
`;
}

function organizationNode(baseUrl) {
  return {
    '@type': 'Organization',
    '@id': `${baseUrl}/namecode/#namecode`,
    name: 'namecode',
    url: `${baseUrl}/namecode/`,
    description:
      'NASA APOD에서 출발한 흑백 AI 생성 이미지를 매일 한 점씩 발표하는 독립 작업 시리즈.',
    sameAs: [BRAND.instagram, BRAND.facebook],
  };
}

function creativeWorkNode(w, opts) {
  const url = `${opts.baseUrl}/namecode/artwork/${w.date}.html`;
  const image = {
    '@type': 'ImageObject',
    '@id': `${url}#image`,
    contentUrl: w.assets.squareAbs,
    url: w.assets.squareAbs,
    encodingFormat: 'image/png',
    caption: altText(w),
    representativeOfPage: true,
  };
  if (w.size) {
    image.width = w.size.width;
    image.height = w.size.height;
  }

  const node = {
    '@type': 'CreativeWork',
    '@id': `${url}#work`,
    url,
    name: w.apodTitle,
    inLanguage: 'ko',
    identifier: w.date,
    genre: 'Generative monochrome artwork',
    abstract: `NASA APOD "${w.apodTitle}"를 출발점으로 만든 흑백 AI 생성 이미지.`,
    creditText: 'namecode',
    creator: { '@id': `${opts.baseUrl}/namecode/#namecode` },
    isPartOf: { '@id': `${opts.baseUrl}/namecode/#archive` },
    image: { '@id': `${url}#image` },
    associatedMedia: image,
    materialExtent: 'AI-generated image, not a telescope photograph',
    isBasedOn: {
      '@type': 'ImageObject',
      name: w.apodTitle,
      contentUrl: w.source,
      url: w.source,
      temporalCoverage: w.date,
      provider: {
        '@type': 'Organization',
        name: 'NASA Astronomy Picture of the Day',
        url: 'https://apod.nasa.gov/apod/',
      },
    },
  };
  if (w.label) node.alternateName = w.label;
  if (w.assets.reel) {
    node.workExample = {
      '@type': 'MediaObject',
      contentUrl: `${opts.baseUrl}${w.assets.reel.replace(/^\/pages/, '')}`,
      encodingFormat: 'video/mp4',
      name: `${w.apodTitle} 세로 영상`,
    };
  }
  return node;
}

function renderWorkPage(w, prev, next, opts) {
  const canonical = `${opts.baseUrl}/namecode/artwork/${w.date}.html`;
  const title = `${w.apodTitle} — ${KO_DATE(w.date)} namecode 스카이 스터디`;
  const desc = metaDescription(w);
  const alt = altText(w);

  const graph = {
    '@context': 'https://schema.org',
    '@graph': [
      organizationNode(opts.baseUrl),
      creativeWorkNode(w, opts),
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'namecode 아카이브', item: `${opts.baseUrl}/namecode/` },
          { '@type': 'ListItem', position: 2, name: w.apodTitle, item: canonical },
        ],
      },
    ],
  };

  const sizeAttrs = w.size ? ` width="${w.size.width}" height="${w.size.height}"` : '';

  const rows = [];
  rows.push(['출처 기준일', `<span class="mono">${esc(w.date)}</span> · ${esc(KO_DATE(w.date))}`]);
  rows.push(['APOD 원본 제목', `<span lang="en">${esc(w.apodTitle)}</span>`]);
  rows.push([
    '원본 이미지 주소',
    `<a class="mono" href="${escAttr(w.source)}" rel="nofollow noopener external">${esc(w.source)}</a>`,
  ]);
  if (w.label) rows.push(['이미지에 새겨진 레이블', `<span class="mono">${esc(w.label)}</span>`]);
  const formats = ['정사각형 이미지'];
  if (w.assets.vertical) formats.push('세로 9:16 이미지');
  if (w.assets.reel) formats.push('세로 영상');
  rows.push(['남아 있는 형식', esc(formats.join(', '))]);
  rows.push(['만든 방식', 'AI 생성 흑백 이미지. 망원경 촬영 사진 아님.']);

  const labelBlock = w.labelMismatch
    ? `<p class="text" style="color:var(--dim);margin:1.75rem 0 0">${esc(COPY.labelNote)} 이 날의 코드네임 <span class="mono">${esc(w.workName)}</span>은 APOD 원본 제목 <span lang="en">“${esc(w.apodTitle)}”</span>과 일치하지 않습니다. 기록을 위해 레이블은 고치지 않고 그대로 둡니다.</p>`
    : `<p class="text" style="color:var(--dim);margin:1.75rem 0 0">${esc(COPY.labelNote)}</p>`;

  const quote = w.excerpt
    ? `<section class="quote"><div class="wrap">
<blockquote lang="en"><p>${esc(w.excerpt)}…</p></blockquote>
<cite>NASA APOD 원문 일부 발췌. 전체 문장과 설명은 <a href="${escAttr(w.source)}" rel="nofollow noopener external">원본</a>을 확인하세요. namecode는 천체에 대한 설명을 따로 쓰지 않습니다.</cite>
</div></section>`
    : '';

  const motion = w.assets.reel
    ? `<section class="motion"><div class="wrap">
<h2>세로 영상</h2>
<video controls preload="none" playsinline poster="${escAttr(w.assets.vertical || w.assets.square)}" width="405" height="720">
<source src="${escAttr(w.assets.reel)}" type="video/mp4">
이 브라우저에서는 영상을 재생할 수 없습니다. <a href="${escAttr(w.assets.reel)}">영상 파일 열기</a>
</video>
<p>같은 날 작업의 세로 버전입니다. 재생을 눌러야 불러옵니다.</p>
</div></section>`
    : '';

  const pager = `<nav class="pager wrap" aria-label="다른 날 작업">
${
    next
      ? `<a href="${escAttr(`${next.date}.html`)}"><span class="stamp">이전 ${esc(next.date)}</span><br><span lang="en">${esc(next.apodTitle)}</span></a>`
      : '<span class="none">이전 작업 없음</span>'
  }
${
    prev
      ? `<a href="${escAttr(`${prev.date}.html`)}" style="text-align:right"><span class="stamp">다음 ${esc(prev.date)}</span><br><span lang="en">${esc(prev.apodTitle)}</span></a>`
      : '<span class="none">다음 작업 없음</span>'
  }
</nav>`;

  return `${head({
    title,
    description: desc,
    canonical,
    ogImage: w.assets.squareAbs,
    ogType: 'article',
    imageAlt: alt,
  })}
<script type="application/ld+json">
${jsonld(graph)}
</script>
${masthead(`스카이 스터디 ${w.date}`, '../')}
<main>
<section class="lede"><div class="wrap">
<h1 lang="en">${esc(w.apodTitle)}</h1>
<p>${esc(KO_DATE(w.date))}의 하늘을 검은 바탕 위 흰 입자로 다시 그린 작업입니다. 출발점은 NASA APOD 이미지이고, 아래 이미지는 AI로 생성한 흑백 작업물입니다.</p>
</div></section>

<figure class="plate wrap">
<img src="${escAttr(w.assets.square)}" alt="${escAttr(alt)}"${sizeAttrs} decoding="async">
<figcaption>${esc(alt)}</figcaption>
</figure>

<section class="record"><div class="wrap">
<dl>
${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join('\n')}
</dl>
${labelBlock}
</div></section>

${quote}
${motion}

<section class="follow"><div class="wrap">
<p>${esc(COPY.ctaNote)}</p>
<a class="cta" href="${escAttr(BRAND.instagram)}" rel="me noopener">${esc(COPY.ctaLabel)}</a>
<span class="alt">아카이브 전체는 <a href="../">namecode 스카이 스터디 목록</a>에 있습니다.</span>
</div></section>

${pager}
</main>
${footer(opts.baseUrl)}`;
}

function renderIndex(works, opts) {
  const canonical = `${opts.baseUrl}/namecode/`;
  const latest = works[0];
  const title = 'namecode 스카이 스터디 — 매일 한 장의 흑백 하늘 아카이브';
  const desc = `NASA APOD에서 출발해 매일 한 점씩 만든 AI 생성 흑백 이미지 아카이브. ${works.length}개의 작업과 각 작업의 원본 출처 기록. 최근 작업: ${latest.apodTitle} (${latest.date}).`;

  const graph = {
    '@context': 'https://schema.org',
    '@graph': [
      organizationNode(opts.baseUrl),
      {
        '@type': 'CollectionPage',
        '@id': `${canonical}#archive`,
        url: canonical,
        name: title,
        description: desc,
        inLanguage: 'ko',
        isPartOf: { '@type': 'WebSite', url: `${opts.baseUrl}/`, name: 'jhbropark pages' },
        about: { '@id': `${opts.baseUrl}/namecode/#namecode` },
        publisher: { '@id': `${opts.baseUrl}/namecode/#namecode` },
        primaryImageOfPage: {
          '@type': 'ImageObject',
          contentUrl: latest.assets.squareAbs,
          caption: altText(latest),
        },
        mainEntity: {
          '@type': 'ItemList',
          numberOfItems: works.length,
          itemListOrder: 'https://schema.org/ItemListOrderDescending',
          itemListElement: works.map((w, i) => ({
            '@type': 'ListItem',
            position: i + 1,
            url: `${opts.baseUrl}/namecode/artwork/${w.date}.html`,
            name: `${w.apodTitle} (${w.date})`,
          })),
        },
      },
    ],
  };

  const heroSize = latest.size ? ` width="${latest.size.width}" height="${latest.size.height}"` : '';

  const list = works
    .map((w, i) => {
      const size = w.size ? ` width="${w.size.width}" height="${w.size.height}"` : '';
      const extra = [];
      if (w.assets.vertical) extra.push('세로 이미지');
      if (w.assets.reel) extra.push('영상');
      return `<article class="work">
<a href="artwork/${escAttr(w.date)}.html" tabindex="-1" aria-hidden="true"><img src="${escAttr(w.assets.square)}" alt=""${size} loading="lazy" decoding="async"></a>
<div>
<p class="stamp">${esc(w.date)}${extra.length ? ` · ${esc(extra.join(', '))}` : ''}</p>
<h2><a href="artwork/${escAttr(w.date)}.html" lang="en">${esc(w.apodTitle)}</a></h2>
<p>${esc(KO_DATE(w.date))}의 하늘. 이미지에 새겨진 레이블은 <span class="stamp">${esc(w.label || w.workName || '없음')}</span>입니다.</p>
<p class="go"><a href="artwork/${escAttr(w.date)}.html">출처 기록과 함께 크게 보기</a></p>
</div>
</article>`;
    })
    .join('\n');

  return `${head({
    title,
    description: desc,
    canonical,
    ogImage: latest.assets.squareAbs,
    ogType: 'website',
    imageAlt: altText(latest),
  })}
<script type="application/ld+json">
${jsonld(graph)}
</script>
${masthead('스카이 스터디 아카이브', './')}
<main>
<section class="lede"><div class="wrap">
<h1>${esc(COPY.tagline)}</h1>
<p>${esc(COPY.intro)}</p>
</div></section>

<section class="hero"><div class="wrap"><figure>
<img src="${escAttr(latest.assets.square)}" alt="${escAttr(altText(latest))}"${heroSize} decoding="async" fetchpriority="high">
<figcaption>
<span class="stamp">${esc(latest.date)} 가장 최근 작업</span>
<span class="src" lang="en"><a href="artwork/${escAttr(latest.date)}.html">${esc(latest.apodTitle)}</a></span>
</figcaption>
</figure></div></section>

<section class="works"><div class="wrap">
${list}
</div></section>

<section class="panel"><div class="wrap text">
<h2>${esc(COPY.disclaimerHead)}</h2>
<ul>
${COPY.disclaimer.map((d) => `<li>${esc(d)}</li>`).join('\n')}
<li>${esc(COPY.labelNote)}</li>
</ul>
</div></section>

<section class="follow"><div class="wrap">
<p>${esc(COPY.ctaNote)} 이 아카이브에는 지난 작업이 기록으로 남습니다.</p>
<a class="cta" href="${escAttr(BRAND.instagram)}" rel="me noopener">${esc(COPY.ctaLabel)}</a>
<span class="alt">페이스북에서도 같은 작업을 올립니다: <a href="${escAttr(BRAND.facebook)}" rel="me noopener">${esc(BRAND.fbHandle)}</a></span>
</div></section>
</main>
${footer(opts.baseUrl)}`;
}

function renderSitemap(works, opts) {
  const urls = [
    { loc: `${opts.baseUrl}/namecode/`, lastmod: works[0].date, priority: '1.0' },
    ...works.map((w) => ({
      loc: `${opts.baseUrl}/namecode/artwork/${w.date}.html`,
      lastmod: w.date,
      priority: '0.8',
      image: { loc: w.assets.squareAbs, title: w.apodTitle, caption: altText(w) },
    })),
  ];
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
${urls
    .map(
      (u) => `  <url>
    <loc>${esc(u.loc)}</loc>
    <lastmod>${esc(u.lastmod)}</lastmod>
    <priority>${u.priority}</priority>${
        u.image
          ? `
    <image:image>
      <image:loc>${esc(u.image.loc)}</image:loc>
      <image:title>${esc(u.image.title)}</image:title>
      <image:caption>${esc(u.image.caption)}</image:caption>
    </image:image>`
          : ''
      }
  </url>`
    )
    .join('\n')}
</urlset>
`;
}

function renderFeed(works, opts) {
  const now = new Date().toUTCString();
  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>namecode 스카이 스터디</title>
  <link>${esc(opts.baseUrl)}/namecode/</link>
  <atom:link href="${esc(opts.baseUrl)}/namecode/feed.xml" rel="self" type="application/rss+xml"/>
  <description>NASA APOD에서 출발한 매일 한 점의 AI 생성 흑백 이미지 아카이브.</description>
  <language>ko</language>
  <lastBuildDate>${now}</lastBuildDate>
${works
    .map(
      (w) => `  <item>
    <title>${esc(w.apodTitle)} (${esc(w.date)})</title>
    <link>${esc(opts.baseUrl)}/namecode/artwork/${esc(w.date)}.html</link>
    <guid isPermaLink="true">${esc(opts.baseUrl)}/namecode/artwork/${esc(w.date)}.html</guid>
    <description>${esc(metaDescription(w))}</description>
  </item>`
    )
    .join('\n')}
</channel>
</rss>
`;
}

/* --------------------------------------------------------------------- main */

function main() {
  const argv = process.argv.slice(2);
  const cli = parseArgs(argv);
  if (cli.help) {
    console.log(fs.readFileSync(new URL(import.meta.url), 'utf8').split('*/')[0]);
    return;
  }
  const repoRoot = path.resolve(cli.repoRoot || process.cwd());
  const opts = {
    repoRoot,
    out: path.resolve(cli.out || path.join(repoRoot, 'namecode')),
    dates: cli.dates || null,
    limit: Number.isFinite(cli.limit) ? cli.limit : DEFAULTS.limit,
    baseUrl: (cli.baseUrl || DEFAULTS.baseUrl).replace(/\/+$/, ''),
    assetBase: (cli.assetBase || DEFAULTS.assetBase).replace(/\/+$/, ''),
    feed: cli.feed,
    quiet: cli.quiet,
  };

  const works = loadWorks(opts);
  if (!works.length) throw new Error('No buildable briefs found.');

  fs.mkdirSync(path.join(opts.out, 'artwork'), { recursive: true });

  fs.writeFileSync(path.join(opts.out, 'index.html'), renderIndex(works, opts), 'utf8');
  works.forEach((w, i) => {
    // works[] is newest-first: prev = newer, next = older
    const prev = works[i - 1] || null;
    const next = works[i + 1] || null;
    fs.writeFileSync(
      path.join(opts.out, 'artwork', `${w.date}.html`),
      renderWorkPage(w, prev, next, opts),
      'utf8'
    );
  });
  fs.writeFileSync(path.join(opts.out, 'sitemap.xml'), renderSitemap(works, opts), 'utf8');
  if (opts.feed) fs.writeFileSync(path.join(opts.out, 'feed.xml'), renderFeed(works, opts), 'utf8');

  if (!opts.quiet) {
    console.log(`namecode archive built → ${opts.out}`);
    console.log(`  pages : index.html + ${works.length} artwork pages`);
    console.log(`  dates : ${works[works.length - 1].date} … ${works[0].date}`);
    console.log(`  base  : ${opts.baseUrl}/namecode/`);
    console.log(`  assets: ${opts.assetBase}/ (not copied)`);
  }
}

main();
