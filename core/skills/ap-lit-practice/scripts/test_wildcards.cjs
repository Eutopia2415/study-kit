const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const page = fs.readFileSync(process.argv[2], 'utf8');
const start = page.indexOf('    let bank = ');
const end = page.indexOf('    function hexToRgb(hex)', start);
assert(start >= 0 && end > start);
const interactionStart = page.indexOf('    function startNewAttempt()', start);
assert(interactionStart > start && interactionStart < end);
const scoreStart = page.indexOf('    function rawPoemScore()');
const scoreEnd = page.indexOf('    function renderPassage(', scoreStart);
assert(scoreStart > end && scoreEnd > scoreStart);
const storage = new Map();
const localStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value)
};
const result = vm.runInNewContext(page.slice(start, interactionStart) + page.slice(scoreStart, scoreEnd) + `
  const first = state;
  let previous = null;
  const counts = new Set();
  const categoriesSeen = new Set();
  const combinations = new Set();
  for (let run = 0; run < 3000; run++) {
    const attempt = newState(previous);
    applySequence(attempt);
    const count = attempt.bonusOrder.length;
    counts.add(count);
    if (count < 3 || count > 5 || attempt.answers.length !== CORE_COUNT + count || TOTAL_COUNT !== CORE_COUNT + count) throw new Error('Wrong attempt size');
    const easyCount = attempt.bonusOrder.filter(id => bonusBank.questions[id].tier === 'easy').length;
    const categories = attempt.bonusOrder.map(id => bonusBank.questions[id].category);
    categories.forEach(category => categoriesSeen.add(category));
    combinations.add([...new Set(categories)].sort().join(','));
    if (easyCount !== 1 || new Set(categories).size < 3 || count - easyCount < 2 || attempt.scoringVersion !== 3) throw new Error('Wrong wildcard mix');
    if (attempt.bonusAfter.some(slot => slot < 2 || slot >= CORE_COUNT)) throw new Error('Wildcard in first two positions');
    if (new Set(attempt.bonusAfter).size !== count || new Set(attempt.bonusColors).size !== count) throw new Error('Repeated slot or color');
    if (bank.questions[0].kind !== 'core' || bank.questions[1].kind !== 'core') throw new Error('Wildcard starts too early');
    for (let i = 1; i < bank.questions.length; i++) {
      if (bank.questions[i].kind === 'bonus' && bank.questions[i - 1].kind === 'bonus') throw new Error('Consecutive wildcards');
    }
    if (previous) {
      if (attempt.bonusAfter.join(',') === previous.bonusAfter.join(',')) throw new Error('Same positions as last attempt');
      if (attempt.bonusOrder.some(id => previous.bonusOrder.includes(id))) throw new Error('Repeated wildcard from last attempt');
    }
    previous = attempt;
  }
  const legacy = {
    answers: Array(20).fill(null), eliminated: Array.from({length:20},()=>Array(5).fill(false)),
    flags: Array(20).fill(false), confidence: Array(20).fill(null),
    bonusAfter: [2,4,6,8,10], bonusOrder: [0,1,2,3,4],
    index: 3, maxStepSeen: 3, view: 'question', submitted: false, notes: ''
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(legacy));
  const restored = loadState();
  applySequence(restored);
  if (restored.answers.length !== 20 || restored.index !== 3 || new Set(restored.bonusColors).size !== 5) throw new Error('Saved attempt lost');
  state = restored;
  state.answers = bank.questions.map((question, index) => question.kind === 'core' ? bank.key[index] : null);
  if (score() !== 15) throw new Error('Legacy attempt was retroactively penalized');
  state = previous;
  applySequence(state);
  state.answers = bank.questions.map((question, index) => question.kind === 'core' ? bank.key[index] : null);
  if (rawPoemScore() !== 15 || bonusScore() !== 0 || score() !== 0 || totalScore() !== 0) throw new Error('Unanswered wildcards must eliminate points');
  const bonusIndices = bank.questions.map((question, index) => question.kind === 'bonus' ? index : -1).filter(index => index >= 0);
  bonusIndices.forEach(index => { state.answers[index] = bank.key[index]; });
  if (score() !== 15 || totalScore() !== 15 + bonusIndices.length || pointsEliminated()) throw new Error('All correct wildcards must keep points');
  state.answers[bonusIndices[0]] = null;
  if (score() !== 15 || totalScore() !== 14 + bonusIndices.length || pointsEliminated()) throw new Error('One missed wildcard must keep points');
  state.answers[bonusIndices[1]] = LETTERS.replace(bank.key[bonusIndices[1]], '')[0];
  if (score() !== 0 || totalScore() !== 0 || !pointsEliminated() || wildcardMisses() !== 2) throw new Error('Two missed wildcards must eliminate all points');
  state.scoringVersion = 2;
  bonusIndices.forEach(index => { state.answers[index] = null; });
  if (score() !== 0 || totalScore() !== 0) throw new Error('Saved v2 scoring changed');
  state.answers[bonusIndices[0]] = bank.key[bonusIndices[0]];
  if (score() !== 15 || totalScore() !== 16) throw new Error('Saved v2 scoring changed');
  localStorage.setItem(STORAGE_KEY, JSON.stringify(previous));
  const reloaded = loadState();
  if (JSON.stringify(reloaded.bonusAfter) !== JSON.stringify(previous.bonusAfter) ||
      JSON.stringify(reloaded.bonusOrder) !== JSON.stringify(previous.bonusOrder) ||
      JSON.stringify(reloaded.bonusColors) !== JSON.stringify(previous.bonusColors)) throw new Error('Reload changed the attempt');
  ({ counts: [...counts].sort(), bankSize: bonusBank.questions.length, categoriesSeen: [...categoriesSeen].sort(),
     combinationCount: combinations.size, savedAttemptPreserved: true });
`, { localStorage });
assert.deepStrictEqual(Array.from(result.counts), [3, 4, 5]);
assert.equal(result.bankSize, 23);
assert.deepStrictEqual(Array.from(result.categoriesSeen), ['capital city', 'flags', 'iGEM', 'math', 'people faces']);
assert(result.combinationCount >= 10);
console.log('Passed 3000 varied generations across five categories, previous-attempt exclusion, two-miss scoring, reload, and legacy attempts.');
