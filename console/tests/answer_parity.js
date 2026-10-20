// Usage: node tests/answer_parity.js <cases.json>
// cases.json: [{run: <published run JSON>, question, expected}] produced by run_tests.py from the Python engine.
const fs = require('fs');
const { builtin } = require('../web/answer.js');
const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
let bad = 0;
for (const c of cases) {
  const got = builtin(c.question, c.run.result.harvester, c.run.result.profiler);
  if (got.answer !== c.expected.answer || JSON.stringify(got.sources) !== JSON.stringify(c.expected.sources)) {
    bad++;
    console.log('MISMATCH: ' + c.question + '\n--- python\n' + c.expected.answer + '\n--- js\n' + got.answer);
  }
}
console.log(`${cases.length - bad}/${cases.length} answers identical`);
process.exit(bad ? 1 : 0);
