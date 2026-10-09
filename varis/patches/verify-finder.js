/**
 * varis.kr 진단기(#vs-finder) 가중치 검증 스크립트
 *
 *   node varis/patches/verify-finder.js
 *
 * varis-kr-vs-finder.html 의 QUESTIONS / TIE_PRIORITY 를 그대로 옮겨 놓고
 * 가능한 응답 조합(3^4 = 81가지)을 전수로 돌려서 확인합니다.
 *
 *   · 1위로 추천될 수 없는 과정이 있는가  (있으면 그 과정은 사실상 죽은 카드)
 *   · 1·2위 어디에도 못 뜨는 과정이 있는가
 *   · 동점이라 타이브레이커로 결정되는 조합이 얼마나 되는가
 *
 * 가중치를 손보면 이 파일도 같이 고치고 다시 돌리세요.
 * (원본과 이 파일이 어긋나면 검증이 의미가 없습니다.)
 */

const COURSES = ['vod', 'ai', 'workshop', 'pro', 'elite', 'prem'];

const QUESTIONS = [
  [ { t: '취미입문',   w: { vod: 3, ai: 2 } },
    { t: '이직',       w: { pro: 3, workshop: 2, elite: 2, ai: 1 } },
    { t: '실무스킬업', w: { elite: 3, prem: 2, ai: 2, workshop: 1 } } ],

  [ { t: '완전초보',   w: { vod: 3, ai: 1 } },
    { t: '툴조금',     w: { ai: 3, workshop: 2, pro: 2, vod: 1 } },
    { t: '실무경험',   w: { elite: 3, prem: 2, pro: 1 } } ],

  [ { t: '가볍게',     w: { vod: 3, ai: 2 } },
    { t: '6개월',      w: { pro: 3, elite: 3, workshop: 1 } },
    { t: '1:1',        w: { prem: 4, elite: 1 } } ],

  [ { t: '자기주도',   w: { vod: 3, ai: 3 } },
    { t: '코호트화상', w: { pro: 2, elite: 2, ai: 1, prem: 1 } },
    { t: '오프라인',   w: { workshop: 4, pro: 2, elite: 1, prem: 1 } } ],
];

const TIE_PRIORITY = ['prem', 'elite', 'pro', 'workshop', 'ai', 'vod'];

const winCount = {}, altCount = {};
COURSES.forEach(c => { winCount[c] = 0; altCount[c] = 0; });

const rows = [];
let ties = 0;

for (let a = 0; a < 3; a++)
for (let b = 0; b < 3; b++)
for (let c = 0; c < 3; c++)
for (let d = 0; d < 3; d++) {
  const picks = [QUESTIONS[0][a], QUESTIONS[1][b], QUESTIONS[2][c], QUESTIONS[3][d]];

  const s = {};
  COURSES.forEach(k => { s[k] = 0; });
  picks.forEach(o => { for (const k in o.w) s[k] += o.w[k]; });

  const order = COURSES.slice().sort((x, y) =>
    s[y] !== s[x] ? s[y] - s[x] : TIE_PRIORITY.indexOf(x) - TIE_PRIORITY.indexOf(y));

  winCount[order[0]]++;
  altCount[order[1]]++;
  if (s[order[0]] === s[order[1]]) ties++;

  rows.push({ path: picks.map(p => p.t).join(' / '), top: order[0], alt: order[1] });
}

console.log('총 조합:', rows.length);

console.log('\n=== 노출 횟수 ===');
COURSES.forEach(c => console.log(
  `  ${c.padEnd(9)} 1위 ${String(winCount[c]).padStart(2)}회 · 2위 ${String(altCount[c]).padStart(2)}회`));

const unreachable = COURSES.filter(c => winCount[c] === 0);
const neverShown  = COURSES.filter(c => winCount[c] === 0 && altCount[c] === 0);

console.log('\n1위 불가 과정:', unreachable.length ? unreachable.join(', ') : '없음');
console.log('아예 노출 안 되는 과정:', neverShown.length ? neverShown.join(', ') : '없음');
console.log(`1·2위 동점(타이브레이커로 결정):  ${ties} / ${rows.length}`);

console.log('\n=== 과정별 대표 경로 (1위가 되는 첫 조합) ===');
COURSES.forEach(c => {
  const r = rows.find(r => r.top === c);
  console.log(`  ${c.padEnd(9)} ← ${r ? r.path : '(도달 불가)'}`);
});

process.exitCode = unreachable.length ? 1 : 0;
