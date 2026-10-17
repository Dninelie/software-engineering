import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Static design checks only. This does not start or test the application.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const errors = [];
const assert = (ok, message) => { if (!ok) errors.push(message); };
const read = path => readFileSync(join(root, path), 'utf8');
const walk = dir => readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
  const path = join(dir, entry.name);
  if (['node_modules', '.git', 'target', 'dist'].includes(entry.name)) return [];
  return entry.isDirectory() ? walk(path) : [path];
});
const files = walk(root);
let jsonExamples = 0;
for (const file of files.filter(path => path.endsWith('.md'))) {
  const text = readFileSync(file, 'utf8');
  assert((text.match(/^```/gm) || []).length % 2 === 0, `Unclosed fence: ${file}`);
  for (const match of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    const target = match[1];
    if (/^(https?:|mailto:|#)/.test(target)) continue;
    assert(existsSync(resolve(dirname(file), target.split('#')[0])), `Broken link: ${file}: ${target}`);
  }
  for (const match of text.matchAll(/```json\s*\r?\n([\s\S]*?)\r?\n```/g)) {
    jsonExamples++;
    try { JSON.parse(match[1]); } catch { errors.push(`Invalid JSON example: ${file}`); }
  }
  let inCode = false;
  let width = 0;
  for (const line of text.split(/\r?\n/)) {
    if (line.startsWith('```')) { inCode = !inCode; width = 0; continue; }
    if (inCode) continue;
    if (line.startsWith('|')) {
      const current = (line.match(/\|/g) || []).length;
      assert(!width || width === current, `Uneven table: ${file}: ${line}`);
      width = current;
    } else width = 0;
  }
}

const spec = JSON.parse(read('docs/contracts/openapi.json'));
const graph = JSON.parse(read('docs/contracts/module-dependencies.json'));
assert(spec.openapi === '3.0.3', 'Unexpected contract version');
const refs = [];
const inspect = value => {
  if (!value || typeof value !== 'object') return;
  if (value.$ref) refs.push(value.$ref);
  if (value.type === 'object' && value.required && value.properties) {
    for (const name of value.required) assert(name in value.properties, `Unknown required property: ${name}`);
  }
  for (const child of Object.values(value)) inspect(child);
};
inspect(spec);
for (const ref of refs) {
  assert(ref.startsWith('#/'), `External reference not checked: ${ref}`);
  const target = ref.slice(2).split('/').map(s => s.replaceAll('~1', '/').replaceAll('~0', '~'))
    .reduce((value, key) => value?.[key], spec);
  assert(target !== undefined, `Unresolved reference: ${ref}`);
}

const methods = new Set(['get', 'post', 'put', 'patch', 'delete']);
const operations = new Map();
const ids = new Set();
const normalized = new Set();
for (const [path, item] of Object.entries(spec.paths)) {
  for (const [method, op] of Object.entries(item)) {
    if (!methods.has(method)) continue;
    const key = `${method.toUpperCase()} ${path}`;
    operations.set(key, op);
    assert(!ids.has(op.operationId), `Duplicate operationId: ${op.operationId}`);
    ids.add(op.operationId);
    const canonical = `${method} ${path.replace(/\{[^}]+\}/g, '{}')}`;
    assert(!normalized.has(canonical), `Ambiguous route: ${key}`);
    normalized.add(canonical);
    assert(['B', 'C', 'D'].includes(op['x-owner']), `Missing owner: ${key}`);
    assert(typeof op['x-access'] === 'string', `Missing access policy: ${key}`);
    assert(op.responses && Object.keys(op.responses).some(code => /^2\d\d$/.test(code)), `Missing success response: ${key}`);
    assert(op.responses?.default, `Missing error response: ${key}`);
    for (const name of [...path.matchAll(/\{([^}]+)\}/g)].map(m => m[1])) {
      assert(op.parameters?.some(p => p.in === 'path' && p.name === name && p.required), `Missing path parameter: ${key}: ${name}`);
    }
    const publicOperation = (op.security || []).some(s => !Object.keys(s).length) || op.security?.length === 0;
    if (method !== 'get' && !['/auth/wechat-login', '/admin/auth/login'].includes(path)) {
      assert(!publicOperation, `Unauthenticated write: ${key}`);
    }
    if (path.startsWith('/admin/') && path !== '/admin/auth/login') {
      assert(!publicOperation && op['x-access'] === 'admin' && op['x-owner'] === 'D', `Unprotected admin route: ${key}`);
    }
    if (path.includes('/ai/') || path.includes('/match-jobs')) {
      assert(!publicOperation && op['x-owner'] === 'C', `Unprotected/wrong-owner task route: ${key}`);
    }
  }
}

// Compare every method/path row in the Chinese API guide with the contract.
const documented = new Set();
for (const match of read('docs/04-api-contracts.md').matchAll(/^\| (GET|POST|PUT|PATCH|DELETE)((?:、(?:GET|POST|PUT|PATCH|DELETE))*) \| `([^`]+)` \|/gm)) {
  for (const method of (match[1] + match[2]).split('、')) documented.add(`${method} ${match[3]}`);
}
for (const key of documented) assert(operations.has(key), `Documented route missing from contract: ${key}`);
for (const key of operations.keys()) assert(documented.has(key), `Contract route missing from guide: ${key}`);

// Check our documented examples against the schema features actually used here.
// This deliberately does not claim to implement the entire OpenAPI/JSON Schema standard.
const exampleErrors = (value, source, path = '$') => {
  const schema = source.$ref ? spec.components.schemas[source.$ref.split('/').at(-1)] : source;
  if (value === null) return schema.nullable ? [] : [`${path}: unexpected null`];
  const found = [];
  if (schema.enum && !schema.enum.includes(value)) found.push(`${path}: not in enum`);
  if (schema.type === 'object') {
    if (typeof value !== 'object' || Array.isArray(value)) return [`${path}: expected object`];
    for (const name of schema.required || []) if (!(name in value)) found.push(`${path}: missing ${name}`);
    for (const [name, child] of Object.entries(value)) {
      if (schema.properties?.[name]) found.push(...exampleErrors(child, schema.properties[name], `${path}.${name}`));
      else if (schema.additionalProperties === false) found.push(`${path}: unknown ${name}`);
    }
  } else if (schema.type === 'array') {
    if (!Array.isArray(value)) return [`${path}: expected array`];
    if (schema.maxItems !== undefined && value.length > schema.maxItems) found.push(`${path}: too many items`);
    value.forEach((child, i) => found.push(...exampleErrors(child, schema.items, `${path}[${i}]`)));
  } else if (schema.type === 'string') {
    if (typeof value !== 'string') return [`${path}: expected string`];
    const length = [...value].length;
    if (schema.minLength !== undefined && length < schema.minLength) found.push(`${path}: too short`);
    if (schema.maxLength !== undefined && length > schema.maxLength) found.push(`${path}: too long`);
    if (schema.pattern && !new RegExp(schema.pattern).test(value)) found.push(`${path}: pattern mismatch`);
  } else if (schema.type === 'integer') {
    if (!Number.isInteger(value)) found.push(`${path}: expected integer`);
    if (schema.minimum !== undefined && value < schema.minimum) found.push(`${path}: below minimum`);
    if (schema.maximum !== undefined && value > schema.maximum) found.push(`${path}: above maximum`);
  } else if (schema.type === 'boolean' && typeof value !== 'boolean') found.push(`${path}: expected boolean`);
  return found;
};
for (const match of read('docs/04-api-contracts.md').matchAll(/```json\s*\r?\n([\s\S]*?)\r?\n```/g)) {
  const value = JSON.parse(match[1]);
  const name = value.jobId ? 'ExtractionJob' : value.proofText ? 'ClaimCreate' : value.type === 'LOST' ? 'CreatePost' : value.code === 'OK' ? 'PostCardPageResponse' : 'ApiError';
  for (const message of exampleErrors(value, spec.components.schemas[name])) errors.push(`API example ${name}: ${message}`);
}

const collectProperties = (schema, seen = new Set()) => {
  if (!schema || typeof schema !== 'object') return new Set();
  if (schema.$ref) {
    const name = schema.$ref.split('/').at(-1);
    if (seen.has(name)) return new Set();
    return collectProperties(spec.components.schemas[name], new Set([...seen, name]));
  }
  const result = new Set(Object.keys(schema.properties || {}));
  for (const child of Object.values(schema.properties || {})) {
    for (const name of collectProperties(child, seen)) result.add(name);
  }
  for (const name of collectProperties(schema.items, seen)) result.add(name);
  return result;
};
const privateFields = ['openid', 'session_key', 'password', 'password_hash', 'token_hash', 'proofText', 'proofImages', 'applicantContact', 'finderContact'];
for (const name of ['PostCard', 'PostDetail', 'Matches', 'Notification', 'AdminPost', 'PublicUser']) {
  const properties = collectProperties(spec.components.schemas[name]);
  for (const field of privateFields) assert(!properties.has(field), `Private property in public/summary schema ${name}: ${field}`);
}
assert(!('type' in spec.components.schemas.UpdatePost.properties), 'Update must not change post type');
for (const action of ['accept', 'reject', 'cancel', 'complete']) {
  const schemaRef = spec.paths[`/claims/{id}/${action}`].post.requestBody.content['application/json'].schema.$ref;
  const schema = spec.components.schemas[schemaRef.split('/').at(-1)];
  assert(schema.required.includes('clientRequestId'), `Missing action idempotency: ${action}`);
}

// Validate a directed service graph, not only the three coarse directory groups.
const visiting = new Set();
const visited = new Set();
const visit = (name, chain = []) => {
  if (visiting.has(name)) { errors.push(`Service cycle: ${[...chain, name].join(' -> ')}`); return; }
  if (visited.has(name)) return;
  const node = graph.services[name];
  if (!node) { errors.push(`Unknown service: ${name}`); return; }
  assert(['B', 'C', 'D'].includes(node.owner), `Bad service owner: ${name}`);
  visiting.add(name);
  for (const dependency of node.depends) {
    if (dependency.endsWith('Repository')) {
      assert(graph.services[dependency]?.owner === node.owner, `Cross-owner direct repository: ${name} -> ${dependency}`);
    }
    visit(dependency, [...chain, name]);
  }
  visiting.delete(name);
  visited.add(name);
};
for (const name of Object.keys(graph.services)) visit(name);
for (const directory of Object.keys(graph.directoryOwners)) assert(existsSync(join(root, directory)), `Missing owned directory: ${directory}`);
const groups = { business: ['post', 'recovery', 'notification'], intelligence: ['ai', 'matching', 'job'], platform: ['identity', 'asset', 'moderation'] };
const base = 'backend/src/main/java/com/campus/lostfound/modules';
for (const [group, modules] of Object.entries(groups)) {
  for (const module of modules) {
    assert(!existsSync(join(root, base, module)), `Obsolete flat module: ${module}`);
    for (const layer of ['api', 'application', 'domain', 'infrastructure']) {
      assert(existsSync(join(root, base, group, module, layer)), `Missing ${group}/${module}/${layer}`);
    }
  }
}
const cases = [...read('docs/07-testing.md').matchAll(/^\| (AT-\d+) \|.*\| ([ABCD]) \|\r?$/gm)].map(m => m[1]);
assert(new Set(cases).size === cases.length, 'Duplicate acceptance case ID');
assert(cases.includes('AT-34'), 'New concurrency/recovery regressions are missing');

console.log(`Checked ${files.filter(f => f.endsWith('.md')).length} Markdown files, ${jsonExamples} JSON examples.`);
console.log(`Checked ${operations.size} HTTP operations, ${Object.keys(spec.components.schemas).length} schemas, ${Object.keys(graph.services).length} service nodes.`);
console.log(`Checked 9 grouped modules, 36 layer directories, ${cases.length} acceptance case definitions.`);
if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
} else {
  console.log('PASS: design structure and contract consistency. Runtime behavior is NOT verified.');
}
