import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const errors = [];
const walk = dir => readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
  if (['archive', '.git', 'node_modules', 'target', 'dist', '.venv', 'venv', '__pycache__', '.pytest_cache'].includes(entry.name)) return [];
  const path = join(dir, entry.name);
  return entry.isDirectory() ? walk(path) : [path];
});
const markdown = walk(root).filter(file => file.endsWith('.md'));
let examples = 0;
for (const file of markdown) {
  const text = readFileSync(file, 'utf8');
  if ((text.match(/^```/gm) || []).length % 2) errors.push(`Unclosed code fence: ${file}`);
  let columns = 0;
  let inFence = false;
  for (const line of text.split(/\r?\n/)) {
    if (line.startsWith('```')) { inFence = !inFence; columns = 0; continue; }
    if (inFence) continue;
    if (!line.startsWith('|')) { columns = 0; continue; }
    const count = line.split('|').length - 2;
    if (columns && count !== columns) errors.push(`Inconsistent table columns: ${file}: ${line}`);
    columns = count;
  }
  for (const match of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    if (/^(https?:|#|mailto:)/.test(match[1])) continue;
    if (!existsSync(resolve(dirname(file), match[1].split('#')[0]))) errors.push(`Broken link: ${file}: ${match[1]}`);
  }
  for (const match of text.matchAll(/```json\s*\r?\n([\s\S]*?)\r?\n```/g)) {
    examples++;
    try { JSON.parse(match[1]); } catch { errors.push(`Invalid JSON: ${file}`); }
  }
}
const api = readFileSync(join(root, 'docs/04-api-contracts.md'), 'utf8');
const operations = new Set();
for (const match of api.matchAll(/^\| (GET|POST|PUT|PATCH|DELETE) \| ([^|]+) \|/gm)) {
  const key = `${match[1]} ${match[2].trim()}`;
  if (operations.has(key)) errors.push(`Duplicate endpoint: ${key}`);
  operations.add(key);
}
if (operations.size !== 32) errors.push(`Expected 32 endpoints, found ${operations.size}`);
for (const dir of ['business', 'intelligence', 'platform', 'common']) {
  if (!existsSync(join(root, 'backend/app', dir))) errors.push(`Missing Python area: ${dir}`);
}
if (existsSync(join(root, 'backend/src/main/java'))) errors.push('Active Java skeleton must not coexist with Python design');
if (!existsSync(join(root, 'backend/.env.example'))) errors.push('Missing Python environment template');
const majorDocs = readdirSync(join(root, 'docs')).filter(name => /^\d{2}-.*\.md$/.test(name));
if (majorDocs.length !== 6) errors.push(`Expected 6 active design docs, found ${majorDocs.length}`);
const pages = ['pages/home', 'pages/publish', 'pages/me', 'packages/post/detail',
  'packages/claim/apply', 'packages/claim/list', 'packages/claim/detail'];
for (const page of pages) {
  if (!existsSync(join(root, 'miniprogram', page))) errors.push(`Missing page directory: ${page}`);
}
const requirements = readFileSync(join(root, 'docs/01-requirements.md'), 'utf8');
for (const state of ['OPEN', 'PROCESSING', 'RESOLVED', 'CLOSED', 'PENDING', 'ACCEPTED', 'REJECTED', 'CANCELLED', 'COMPLETED']) {
  if (!new RegExp(`\\b${state}\\b`).test(requirements)) errors.push(`Missing documented state: ${state}`);
}
const db = readFileSync(join(root, 'docs/03-database.md'), 'utf8');
for (const table of ['app_user', 'post', 'file_asset', 'claim', 'clue', 'report']) {
  if (!new RegExp(`^## \\d+\\. ${table}（`, 'm').test(db)) errors.push(`Missing documented table: ${table}`);
}
const acceptance = readFileSync(join(root, 'docs/06-development-and-testing.md'), 'utf8');
const cases = [...acceptance.matchAll(/^\| (T\d{2}) \|/gm)].map(match => match[1]);
if (cases.length !== 18 || new Set(cases).size !== 18) errors.push('Expected 18 distinct acceptance cases');
for (let number = 1; number <= 18; number++) {
  const id = `T${String(number).padStart(2, '0')}`;
  if (!cases.includes(id)) errors.push(`Missing acceptance case: ${id}`);
}
console.log(`Checked ${markdown.length} current Markdown files, ${examples} JSON examples, ${operations.size} endpoints, 7 page directories and ${cases.length} acceptance cases.`);
console.log('Historical archive excluded. No runtime functionality was tested.');
if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
else console.log('PASS');
