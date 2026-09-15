// Regenerates src/safelist.js from the component class names in src/input.css.
// Run: node src/tools/gen-safelist.js && npm run build
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..', '..');
const css = fs.readFileSync(path.join(root, 'src/input.css'), 'utf8');
const layer = css.slice(css.indexOf('@layer components'));
const names = new Set();
for (const m of layer.matchAll(/\.([a-zA-Z][\w-]*)/g)) names.add(m[1]);
const list = [...names].sort();
const out = [
  '// Generated from the class names in src/input.css (@layer components).',
  '// Regenerate: node src/tools/gen-safelist.js  (see .context/notes-frontend.md)',
  '// Tailwind purges @layer components classes that no scanned file uses; the JS',
  '// rewrite emits these from templates, so keep them all available.',
  'module.exports = ' + JSON.stringify(list, null, 2) + ';',
  '',
].join('\n');
fs.writeFileSync(path.join(root, 'src/safelist.js'), out);
console.log(list.length + ' classes safelisted');
