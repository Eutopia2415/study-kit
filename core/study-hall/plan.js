// Shared by index.html (full page) and widget.html (floating HUD): date helpers and the planner.
const DAY = 864e5, BLOCK_MIN = 70;
let S = null, P = null;   // server snapshot, computed plan
const skillStatus = k => k.gateStatus || k.status;   // the mastery gate (learning records) wins over the SKILLS.md column

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const dOf = s => new Date(s.slice(0, 10) + 'T00:00:00');
const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const addDays = (s, n) => { const d = dOf(s); d.setDate(d.getDate() + n); return iso(d); };
const days = (a, b) => Math.round((dOf(b) - dOf(a)) / DAY);
const fmt = (s, o = { weekday: 'short', month: 'short', day: 'numeric' }) => dOf(s).toLocaleDateString('en-US', o);
const inDays = n => n === 0 ? 'today' : n === 1 ? 'tomorrow' : `in ${n} days`;
const weekStart = s => { const d = dOf(s); d.setDate(d.getDate() - (d.getDay() + 6) % 7); return iso(d); };
const minutesOf = hm => { const [h, m] = hm.split(':').map(Number); return h * 60 + m; };
const clock = hm => { const m = minutesOf(hm); return `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`; };   // 24-hour
// Tonight's block times after pauses: a pause pushes back the end of the block it was in, and the
// start and end of every block after it, by however long it lasted (so far, if still paused).
// A tutor can also extend the running block (kind "extend": the same push, but counted as class
// time, so ext grows the block's length), shorten it (kind "shorten": its end comes in by min, never
// before now) or end it now (kind "end"). Finishing early earns a longer break: of the time cut from
// a block, half (5 to 10 minutes, never more than was cut) becomes extra rest, and the rest pulls later
// blocks back up, never earlier than their planned times (it only undoes earlier pushes).
const pauses = () => S.pause?.pauses || [];
const pausedNow = () => pauses().some(p => p.min == null && !p.kind);
const hhmm = m => `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(Math.round(m) % 60).padStart(2, '0')}`;
function shift(list) {
  const t = list.map(s => ({ a: minutesOf(s.start), b: minutesOf(s.end), ext: 0 }));
  t.forEach(x => { x.a0 = x.a; x.b0 = x.b; });
  for (const p of pauses()) {
    if (p.kind === 'end' || p.kind === 'shorten') {
      const run = t.find(x => x.a <= p.from && p.from < x.b);
      if (!run) continue;
      const b = p.kind === 'end' ? p.from : Math.max(p.from, run.b - p.min), all = run.b - b;
      // Shortening first takes back minutes this block was extended by: later blocks return in full, no rest.
      const undo = p.kind === 'shorten' ? Math.max(0, Math.min(all, run.ext)) : 0, cut = all - undo;
      if (p.kind === 'shorten') run.ext -= all;
      run.b = b;
      if (undo) for (const x of t) if (x.a0 >= run.b0) { x.a -= undo; x.b -= undo; }
      if (!cut) continue;
      run.cut = (run.cut || 0) + cut;
      const rest = Math.min(run.cut, Math.max(5, Math.min(10, run.cut / 2))), more = rest - (run.rest || 0);
      run.rest = rest;
      for (const x of t) if (x.a0 >= run.b0) { const pull = Math.max(0, Math.min(cut - more, x.a - x.a0)); x.a -= pull; x.b -= pull; }
      continue;
    }
    const len = p.min ?? (Date.now() - p.at) / 60e3;
    for (const x of t) {
      if (p.kind === 'extend' && x.a <= p.from && p.from < x.b) x.ext += len;
      if (x.a >= p.from) x.a += len; if (x.b > p.from) x.b += len;
    }
  }
  return t;
}
const subjName = id => (S.subjects.find(s => s.id === id) || {}).short || id;
const subjColor = id => (S.subjects.find(s => s.id === id) || {}).color || 'var(--seg-on)';

const GRADE_PTS = { 'A+': 0, 'A': 0, 'A-': 1, 'B+': 2, 'B': 3, 'B-': 4, 'C+': 5, 'C': 6, 'C-': 7, 'D+': 8, 'D': 9, 'F': 10 };
const gradeColor = l => !l ? 'var(--text-3)' : l[0] === 'A' ? 'var(--green)' : l[0] === 'B' ? 'var(--yellow)' : 'var(--red)';

function sizeTask(text) {
  const t = text.toLowerCase();
  const explicit = t.match(/(\d+)-minute/);
  if (/retriev|cold|retest/.test(t)) return 15;
  if (explicit) return +explicit[1];
  if (/closed book|from memory/.test(t)) return 15;
  if (/one sitting|finish .*diagnostic/.test(t)) return 50;
  if (/tutorial|attacks/.test(t)) return 40;
  if (/\bwrite\b|paper|essay|build/.test(t)) return 35;
  if (/\bread\b/.test(t)) return 30;
  if (/score|grade/.test(t)) return 25;
  return 30;
}

/* ---------- planner ---------- */
// The school's A-D rotation (from PowerSchool's matrix view): which letter a school day is.
function rotationLetter(day) {
  const r = S.rotation, wd = dOf(day).getDay();
  if (!r || wd === 0 || wd === 6) return null;
  const cyc = r.cycle || ['A', 'B', 'C', 'D'];
  let n = 0, d = r.anchor;
  const step = day >= r.anchor ? 1 : -1;
  while (d !== day) { d = addDays(d, step); const w = dOf(d).getDay(); if (w !== 0 && w !== 6) n += step; }
  return cyc[((cyc.indexOf(r.letter) + n) % cyc.length + cyc.length) % cyc.length];
}
// A logged session counts as a study block only if it was one: not a review sweep, not a short
// "light" session (a 10-minute vocab check shouldn't fill tonight's first block).
const isBlock = r => !/sweep|light/i.test(r.slot) && !(r.minutes != null && r.minutes < 30);   // a 0-minute Done row is not a block
const nextSchoolDay = day => { let d = addDays(day, 1); while ([0, 6].includes(dOf(d).getDay())) d = addDays(d, 1); return d; };
// Each weekday has its own blocks (S.week, keyed 0 = Sunday), and a date can replace them (S.dates;
// an empty list there means no study that day). Blocks are numbered by start time; reviews aren't.
function blocksOn(day) {
  const list = S.dates?.[day] ?? S.week?.[dOf(day).getDay()] ?? [];
  let n = 0;
  return [...list].sort((a, b) => a.start.localeCompare(b.start))
    .map(b => ({ ...b, label: b.kind === 'sweep' ? 'Review' : `Block ${++n}` }));
}
const deepIds = blocks => blocks.filter(s => s.kind !== 'sweep').map(s => s.id);
const sweepIds = blocks => blocks.filter(s => s.kind === 'sweep').map(s => s.id);
// Open homework for one subject, soonest first (added on the settings page).
const homeworkOf = sid => (S.school.homework || []).filter(h => h.subject === sid && !h.done)
  .sort((a, b) => (a.due || '9').localeCompare(b.due || '9'));
// What the HUD calls a deadline: an in-class essay isn't a test.
const testWord = t => /essay/i.test(t.label || '') ? 'Essay' : 'Test';
// Tests are sat in class, so one dated today is behind you once school is out.
const SCHOOL_OUT = 16 * 60;
const upcoming = t => t.date > S.today || (t.date === S.today && new Date().getHours() * 60 + new Date().getMinutes() < SCHOOL_OUT);
function allTests() {
  const seen = new Set(), out = [];
  const add = (t, src) => {
    const key = t.subject + t.date;
    if (seen.has(key) || !S.subjects.some(s => s.id === t.subject)) return;
    seen.add(key); out.push({ ...t, src });
  };
  (S.school.tests || []).forEach(t => add(t, 'Classroom'));
  S.subjects.forEach(s => (s.deadlines || []).forEach(d => add({ subject: s.id, date: d.date, label: d.label }, 'manual')));
  return out.sort((a, b) => a.date.localeCompare(b.date));
}


// Making way for a test: the night before one, its subject's block gets 45 more minutes; two or three
// nights out, 20. The time comes evenly from the evening's other blocks (none below 30 minutes) and the
// review (down to 15); what they can't give runs the evening up to 15 minutes later. Breaks keep their
// length, a block already logged gives nothing, and one block per subject grows (100 minutes at most).
const MAKE_WAY = n => n <= 1 ? 45 : n <= 3 ? 20 : 0;
function makeWay(blocks, slots, tests, day) {
  const len = b => minutesOf(b.end) - minutesOf(b.start), grow = {}, seen = new Set();
  for (const b of blocks) {
    const x = slots[b.id];
    if (!x || !x.sid || x.logged || b.kind === 'sweep' || seen.has(x.sid)) continue;
    const t = tests.find(t => t.subject === x.sid && days(day, t.date) >= 1 && days(day, t.date) <= 3);
    const m = t ? Math.max(0, Math.min(MAKE_WAY(days(day, t.date)), 100 - len(b))) : 0;
    if (m) { grow[b.id] = { t, m }; seen.add(x.sid); }
  }
  let need = Object.values(grow).reduce((a, g) => a + g.m, 0);
  if (!need) return;
  const give = {}, spare = b => len(b) - (give[b.id] || 0) - (b.kind === 'sweep' ? 15 : 30);
  const donors = blocks.filter(b => !grow[b.id] && !slots[b.id]?.logged);
  for (let taken = true; need > 0 && taken;) {   // five minutes at a time, round the donors, so the cut is even
    taken = false;
    for (const b of donors) if (need > 0 && spare(b) >= 5) { give[b.id] = (give[b.id] || 0) + 5; need -= 5; taken = true; }
  }
  const late = Math.min(15, need);
  need -= late;
  if (need > 0) for (const g of Object.values(grow).reverse()) { const cut = Math.min(g.m, need); g.m -= cut; need -= cut; }
  let at = minutesOf(blocks[0].start);
  blocks.forEach((b, k) => {
    if (k) at += minutesOf(b.start) - minutesOf(blocks[k - 1].was?.end ?? blocks[k - 1].end);
    const d = len(b) + (grow[b.id]?.m || 0) - (give[b.id] || 0);
    b.was = { start: b.start, end: b.end };
    b.start = hhmm(at); b.end = hhmm(at + d); at += d;
  });
  for (const [id, g] of Object.entries(grow)) {
    if (!g.m) continue;
    const from = blocks.filter(b => give[b.id]).map(b => b.kind === 'sweep' ? 'the review' : slotName(slots[b.id]));
    slots[id].why = `${g.t.label} is ${inDays(days(day, g.t.date))}: ${g.m} more minutes`
      + (from.length ? `, from ${from.join(', ').replace(/, ([^,]*)$/, ' and $1')}` : '') + (late ? `, ending ${late} minutes later` : '');
  }
}

function plan() {
  const today = S.today, subj = Object.fromEntries(S.subjects.map(s => [s.id, s]));
  const tests = allTests();
  const doneTasks = new Set(S.history.filter(h => h.kind === 'done').map(h => h.subject + '|' + h.task));
  const grade = id => S.grades.courses?.[id]?.letter;
  const vetoToday = S.history.filter(h => h.kind === 'veto' && h.date === today);
  const st = {};
  for (const s of S.subjects) {
    const rows = S.log.filter(r => r.subject === s.id).sort((a, b) => a.date.localeCompare(b.date));
    const deep = rows.filter(isBlock).map(r => r.date);
    const week = {};
    deep.forEach(d => { const w = weekStart(d); week[w] = (week[w] || 0) + 1; });
    st[s.id] = {
      // Jev reads each line's kind when it can (cold, task, note), trusted at 0.6 or above; a note is a record, not work.
      queue: s.tasks.filter(t => !doneTasks.has(s.id + '|' + t.text) && !(t.kind === 'note' && t.kindP >= 0.6)).map(t => ({ text: t.text, title: t.title, kind: t.kindP >= 0.6 ? t.kind : null, aimed: t.aimed, min: sizeTask(t.text) })),
      due: s.gaps.map(g => g.retest || today), last: deep[deep.length - 1] || null, touched: rows.length ? rows[rows.length - 1].date : null, week, prepped: new Set(),
      pretested: new Set(), reviewed: new Set(), ahead: new Set(), essayWeek: null, mcqWeek: null,
    };
  }

  // Fill one 70-minute block for a subject. Test blocks start with test-format practice
  // unless the STATE.md list is already aimed at the test.
  // The gap most overdue for a retest on that day, or null when none is due. On the same date a
  // retest the tutor wrote down beats an inferred one, which beats an undated gap; then STATE.md's
  // priority order. Planning a retest pushes that gap's next one 3 days out.
  const SURE = { set: 0, inferred: 1, undated: 2 };
  const dueGap = (id, day) => {
    const due = st[id].due, gaps = subj[id].gaps, rank = i => SURE[gaps[i].retestWhy] ?? 2;
    const k = due.map((d, i) => i).filter(i => due[i] <= day).sort((a, b) => due[a].localeCompare(due[b]) || rank(a) - rank(b) || a - b)[0];
    if (k == null) return null;
    const g = gaps[k], late = days(due[k], day);
    due[k] = addDays(day, 3);
    return { ...g, why: g.retestWhy === 'set' ? (late > 0 ? `retest was due ${fmt(g.retest)}` : 'retest due')
      : g.retestWhy === 'inferred' ? `last worked ${fmt(g.last)}${late > 0 ? `, ${late}d overdue` : ''}` : 'no date in STATE.md' };
  };
  // A STATE.md task is already test prep if it names the test, its date, or a quiz format. A bare
  // "test" doesn't count ("to test the degree" is a drill, not quiz practice).
  const aimedAt = (text, test) => {
    const d = dOf(test.date), m = d.getMonth() + 1, n = d.getDate(), mon = fmt(test.date, { month: 'short' });
    return /\b(quiz|mcqs?|multiple[- ]choice|reassess\w*|mock|practice (test|exam)|exam format)\b/i.test(text)
      || text.toLowerCase().includes(test.label.toLowerCase())
      || new RegExp(`\\b(${mon}\\w*\\.? ${n}|0?${m}[-/]0?${n})\\b`, 'i').test(text);
  };
  // A line is cold retrieval by Jev's reading when there is one, else by its wording; same for "aimed at the test".
  const isCold = t => t.kind ? t.kind === 'cold' : /retriev|cold|retest/i.test(t.text);
  const aimed = (t, test) => t.aimed != null ? t.aimed : aimedAt(t.text, test);
  const takeWork = (id, test, day, M = BLOCK_MIN) => {   // M: this block's minutes
    const s = subj[id], q = st[id].queue, picked = [];
    // Within 3 days of a test the block is a sweep of the whole test: one cold item at most, then the
    // test takes the rest of the block, every section of its study guide. Further out, up to two
    // cold-retrieval items open the block (TEACHING.md's loop starts with them) and prep follows.
    const sweep = !!test && days(day, test.date) <= 3;
    while (q.length && picked.length < (sweep ? 1 : 2) && isCold(q[0])) picked.push(q.shift());
    if (test) {
      // The tutor's own prep item in STATE.md, wherever it sits in the list, is the one to run.
      // The tutor's own prep item: a task aimed at the test beats a cold question that also names it.
      // Rank: a line that names the test or its format, then any task aimed at it, then anything aimed at it.
      let k = q.findIndex(t => aimedAt(t.text, test) && !isCold(t));
      if (k < 0) k = q.findIndex(t => aimed(t, test) && !isCold(t));
      if (k < 0) k = q.findIndex(t => aimed(t, test));
      const own = k >= 0 ? q.splice(k, 1)[0] : null;
      if (own || sweep || !picked.some(t => aimed(t, test))) {
        const again = st[id].prepped.has(test.date);
        st[id].prepped.add(test.date);
        const focus = s.gaps.slice(0, 2).map(g => g.title).join('; ');
        const left = M - picked.reduce((a, t) => a + t.min, 0);
        const scope = sweep && testWord(test) === 'Test' ? ' Whole test: one question per section of the study guide (or chapter list), in its order,'
          + ' before going deep on any one; depth only where an answer fails. At close, name in STATE.md the sections not reached.' : '';
        picked.push(own ? { ...own, kind: own.kind || 'task', title: own.title || (sweep ? `${test.label} sweep` : null), min: sweep ? left : own.min, text: own.text + scope }
          : { min: sweep ? left : s.ok ? 40 : M, kind: 'task', title: `${test.label} prep`, text: `${test.label} prep${again ? ' (continued)' : ''}: `
            + (test.format ? `practise the format (${test.format}), closed notes.` : 'practise in the test format, closed notes.')
            + (focus && !sweep ? ` Focus on: ${focus}.` : '') + scope
            + (s.ok ? '' : ` ${s.short} has no STATE.md yet, so use the class practice sets.`) });
      }
    }
    let total = picked.reduce((a, t) => a + t.min, 0);
    // A writing subject (config style "write", AP Lit) writes one timed essay a week. If this week's
    // blocks carry none yet, and this block isn't a test sweep, the essay goes in here.
    if (s.style === 'write' && !sweep) {
      const wk = weekStart(day), hasEssay = picked.some(t => /\b(essay|timed)\b/i.test(t.text));
      const hasMcq = picked.some(t => /\b(mcq|multiple[- ]choice)\b/i.test(t.text));
      if (hasMcq) st[id].mcqWeek = wk;
      if (hasEssay) st[id].essayWeek = wk;
      else if (st[id].essayWeek === wk && !hasMcq && st[id].mcqWeek !== wk && total + 30 <= M) {
        // The essay is already in this week: this block gets the timed multiple-choice set instead.
        st[id].mcqWeek = wk;
        picked.push({ min: 30, kind: 'task', title: 'Timed MCQ set', text: 'Timed MCQ set, 30 minutes: one passage set, poetry and prose fiction alternating week to week, from the CED samples or a released set '
          + '(RESOURCES.md), exam timing. Then each miss against the text: why the distractor looked right, then the wording or inference that defeats it; never a defence of an answer the passage can\'t support. Update the MCQ rows in SKILLS.md.' });
        total += 30;
      }
      else if (st[id].essayWeek !== wk && total + 40 <= M) {
        st[id].essayWeek = wk;
        picked.push({ min: M - total, kind: 'task', title: 'Timed essay', text: 'Timed essay, 40 minutes: the next Writing row in SKILLS.md that is seen or tested (Q1, Q2 or Q3), '
          + 'the released prompt in its exact wording (writing/prompts, writing/released), in a file from writing/essays/_TEMPLATE.md. Budget for the whole block: 5 claim ladder on the prompt, '
          + '40 essay with the stop time posted and called at minute 35, 10 feedback as one exchange (name the capping sentence, the learner says why it fails in their own words, then the rewrite), '
          + '10 rewrite, 5 close (retry the hardest move with no cues) protected whatever overruns. Before the clock: which decision does the character make differently because of the claim, and who pays? No answer means the claim is the work tonight, not the essay. Grade by writing/GRADING.md; the essay is independent evidence, the rewrite assisted. Log both in writing/LOG.md.' });
        total = M;
      }
    }
    // Coverage: one skill the class has reached that was never asked here (SKILLS.md "seen"), as a
    // 15-minute pretest, so untested ground gets found before an exam does. Not inside a test sweep.
    if (!sweep && total + 15 <= M && !picked.some(t => /\bessay\b/i.test(t.text))) {   // an essay night has no room for a pretest
      const sk = (s.skills || []).find(k => skillStatus(k) === 'seen' && !st[id].pretested.has(k.skill));
      const isCase = s.style === 'case';
      if (sk && (!isCase || total + 30 <= M)) {
        st[id].pretested.add(sk.skill);
        picked.push(isCase
          ? { min: 30, kind: 'task', title: `Case: ${shorten(sk.skill, 6)}`, text: `Case brief, covered in class but never asked here: ${sk.skill} (unit ${sk.unit}). `
              + 'Facts, rule, reasoning, from the assigned reading first. Then change one legally significant fact and ask whether the result flips. Mark it tested in SKILLS.md at close.' }
          : { min: 15, kind: 'task', title: `Pretest: ${shorten(sk.skill, 6)}`, text: `Pretest, seen in class but never asked here: ${sk.skill} (unit ${sk.unit}). `
              + 'One problem cold; if it fails, one or two chunks and a check. Mark it tested in SKILLS.md at close.' });
        total += isCase ? 30 : 15;
      }
    }
    // Teaching ahead: no test inside a week and the class position known from Classroom → 20 minutes
    // on what class probably does next, run as a pretest, with the file on disk to read first.
    if (!test && !sweep && total + 20 <= M) {
      const nx = (s.forecast?.next || []).find(k => !st[id].ahead.has(k.skill));
      if (nx && (s.forecast.at != null || !s.forecast.lessons28)) {   // class position known, or no class posting lessons (self-paced)
        st[id].ahead.add(nx.skill);
        picked.push({ min: 20, kind: 'task', title: `${s.forecast.sequential ? 'Ahead' : 'New'}: ${shorten(nx.skill, 6)}`,
          text: (s.forecast.sequential ? `Teaching ahead of class: ${nx.skill} (unit ${nx.unit}), probably next in class. Skip it if STATE.md's Pace says you're already ahead. `
            : `New practice to open: ${nx.skill} (${nx.unit}), never worked here. `)
          + 'One problem cold, then one or two chunks and a check.'
          + (nx.file ? ' Read first: `' + nx.file + '`.' : '') });
        total += 20;
      }
    }
    while (q.length && (picked.length === 0 || total + q[0].min <= M)) { const t = q.shift(); picked.push(t); total += t.min; }
    const g = M - total >= 15 && dueGap(id, day);
    if (g) picked.push({ kind: 'task', title: `Drill: ${g.title}`, text: `Drill gap: ${g.title} (${g.why}). New problems, closed notes.`
      + (s.style === 'deep' ? ' Fast reps: five of the same procedure in a row until it runs without thought, then one with the justification sentence written out.' : ''), min: M - total });
    // A block that carries a timed essay keeps its budget (5 cold, 40 essay, 15 feedback, 10 rewrite): the cold item is one question.
    if (s.style === 'write' && picked.some(t => /\bessay\b/i.test(t.text))) picked.filter(isCold).forEach(t => {
      // On an essay night the opener feeds the essay: a claim ladder on tonight's prompt replaces the cold item (which stays queued).
      const cut = t.min - 5; t.min = 5; t.kind = 'task'; t.title = 'Claim ladder';
      t.text = 'Claim ladder, 5 minutes, on tonight\'s prompt (writing/DRILLS.md): three theses, pick the one a reader could disagree with, one sentence why. The cold item it replaces goes back to STATE.md for the next block.';
      const essay = picked.find(t => /\bessay\b/i.test(t.text)); if (essay) essay.min += cut;
    });
    if (s.style === 'deep') picked.filter(isCold).forEach(t => {
      t.text += ' Change the representation from last time (equation, graph, table or a described situation); a success in one form is not a success in another.';
    });
    return picked;
  };

  const evenings = [];
  for (let i = 0; i <= 13; i++) {
    const day = addDays(today, i), blocks = blocksOn(day);
    if (!blocks.length) continue;
    const wk = weekStart(day);
    const logged = i === 0 ? S.log.filter(r => r.date === today) : [];
    const slots = {};
    // Whatever is already logged tonight wins over the plan.
    const deepLogs = logged.filter(isBlock);
    // A row goes to the block pinned to its subject, else to the earliest open planner-picked block.
    const logRow = r => ({ sid: r.subject, logged: r, why: 'Already logged in SCHEDULE.md' });
    const rest = deepLogs.filter(r => {
      const b = blocks.find(b => b.kind === 'fixed' && b.subject === r.subject && !slots[b.id]);
      if (b) slots[b.id] = logRow(r);
      return !b;
    });
    blocks.filter(b => b.kind !== 'sweep' && b.kind !== 'fixed').forEach((b, k) => { if (rest[k]) slots[b.id] = logRow(rest[k]); });
    const sweepLog = logged.find(r => /sweep/i.test(r.slot));


    // Blocks pinned to a subject in Schedule keep it, whatever else is going on.
    for (const sl of blocks) {
      if (sl.kind === 'fixed' && !slots[sl.id] && subj[sl.subject]) {
        const t = tests.find(t => t.subject === sl.subject && days(day, t.date) > 0 && days(day, t.date) <= 7);
        slots[sl.id] = { sid: sl.subject, test: t, why: 'Set in Schedule' };
      }
    }
    const taken = new Set(Object.values(slots).map(x => x.sid).filter(Boolean));
    const free = deepIds(blocks).filter(id => !slots[id]);
    // Test pressure: a test pulls its subject in more often as it nears. From 14 days out about every
    // third night, from 7 days every other night, inside 3 days every night, and the night before it
    // outranks everything. A subject studied more recently than that cadence keeps only a third of the pull.
    const nextTest = sid => tests.find(t => t.subject === sid && days(day, t.date) > 0 && days(day, t.date) <= 14);
    const testPull = (t, stale) => {
      if (!t) return 0;
      const n = days(day, t.date), cadence = n <= 3 ? 1 : n <= 7 ? 2 : 3;
      const base = n <= 1 ? 120 : n <= 3 ? 90 : n <= 7 ? 60 : 30;
      return stale >= cadence ? base : Math.round(base / 3);
    };
    for (const id of free) {
      const ranked = S.subjects
        .filter(s => !taken.has(s.id) && s.weekly > 0 && !(i === 0 && vetoToday.some(v => v.subject === s.id && v.slot === id)))
        .map(s => {
          const g = GRADE_PTS[grade(s.id)] ?? 2, done = st[s.id].week[wk] || 0, need = Math.max(0, s.weekly - done);
          const stale = st[s.id].last ? days(st[s.id].last, day) : 7;
          // Class weighting: more class days means more new material; the night before a class
          // is the best time to prepare for it.
          const classDays = (s.meets || []).length, tomorrow = rotationLetter(nextSchoolDay(day));
          const t = nextTest(s.id), pull = testPull(t, stale);
          // Floor: a subject behind on its week and untouched for 5 days pulls like a test a week out;
          // for 7 days, like one 3 days out. The night before a test still beats it. One pressure, the larger.
          const starve = need > 0 && stale >= 7 ? 95 : need > 0 && stale >= 5 ? 65 : 0;
          const parts = [[g * 6, grade(s.id) ? `PowerSchool grade ${grade(s.id)}` : 'no grade yet'],
                         [Math.max(pull, starve), pull >= starve ? (t ? `${t.label} is ${fmt(t.date)}, ${inDays(days(day, t.date))}` : '') : `not studied for ${stale} days`],
                         [tomorrow && (s.meets || []).includes(tomorrow) && classDays < 4 ? 8 : 0, `class tomorrow (${tomorrow} day)`],
                         [classDays * 2.5, `${classDays}/4 class days`],
                         [need * 10, need ? `${done} of ${s.weekly} blocks done this week` : ''],
                         [Math.min(stale, 7) * 3, st[s.id].last ? `last studied ${stale === 0 ? 'today' : stale + ' days ago'}` : 'no session logged yet']];
          // The strongest reason leads (a test, when one is pulling); the grade is always named.
          const other = parts.slice(1).filter(p => p[1] && p[0] > 0).sort((a, b) => b[0] - a[0])[0];
          const lead = other && other[0] > parts[0][0] ? [other[1], parts[0][1]] : [parts[0][1], other?.[1]];
          // Test prep (and the 3-day sweep) only inside a week; further out the block is ordinary work.
          return { s, test: t && days(day, t.date) <= 7 ? t : undefined, score: parts.reduce((a, p) => a + p[0], 0),
                   why: lead.filter(Boolean).join(', ') };
        })
        .sort((a, b) => b.score - a.score);
      if (!ranked.length) continue;
      taken.add(ranked[0].s.id);
      slots[id] = { sid: ranked[0].s.id, test: ranked[0].test, why: ranked[0].why.replace(/^./, c => c.toUpperCase()) };
    }
    makeWay(blocks, slots, tests, day);
    for (const id of deepIds(blocks)) {
      const x = slots[id];
      if (!x || !x.sid) continue;
      const bl = blocks.find(b => b.id === id);
      if (!x.logged) x.work = takeWork(x.sid, x.test, day, bl ? minutesOf(bl.end) - minutesOf(bl.start) : BLOCK_MIN);
      st[x.sid].last = st[x.sid].touched = day;
      if (!x.logged) st[x.sid].week[wk] = (st[x.sid].week[wk] || 0) + 1;
    }
    // Sweep: two subjects not studied tonight with a retest due or a shown skill back for review
    // (SKILLS.md Next date reached), longest untouched first. A due gap comes before a review.
    // A row is back when either SKILLS.md or the gate calls it shown: gate-shown without a Next date waits 14 days
    // from its last gate day; hand-marked shown that the gate demoted comes back on its Next date as a retest.
    const reviewOn = k => k.next || (k.gateStatus === 'shown' && k.gateLast ? addDays(k.gateLast, 14) : null);
    const reviewDue = sid => (subj[sid].skills || []).filter(k => (k.status === 'shown' || skillStatus(k) === 'shown')
      && reviewOn(k) && reviewOn(k) <= day && !st[sid].reviewed.has(k.skill));
    const sweepSubs = S.subjects.filter(s => s.ok && (st[s.id].due.some(d => d <= day) || reviewDue(s.id).length) && !taken.has(s.id))
      .sort((a, b) => (st[a.id].touched || '').localeCompare(st[b.id].touched || '')).slice(0, 2);
    sweepSubs.forEach(s => { st[s.id].touched = day; });
    // Each sweep subject gets its due gap, and a shown skill back for review when one is due too.
    const reviewOf = s => { const k = reviewDue(s.id)[0]; if (!k) return null; st[s.id].reviewed.add(k.skill);
      return { title: k.skill, review: true, why: skillStatus(k) === 'shown' ? `shown ${k.last ? fmt(k.last) : 'earlier'}, back for review`
        : `marked shown, gate ${k.gate}: retest` }; };
    const sweep = sweepIds(blocks).length ? sweepSubs.map(s => { const g = dueGap(s.id, day), r = reviewOf(s); return { s, gap: g || r, review: g ? r : null }; }) : [];
    // A "short" subject (Business) gets ten minutes of terms in the review slot every night it has no block.
    if (sweepIds(blocks).length) S.subjects.filter(s => s.style === 'short' && s.ok && !taken.has(s.id) && !sweep.some(w => w.s.id === s.id)).forEach(s => {
      const terms = (s.skills || []).filter(k => ['tested', 'seen'].includes(skillStatus(k))).map(k => k.skill);
      sweep.push({ s, gap: { title: `Terms, 10 min: five from ${terms.length} tested or seen rows, definitions in your words`, terms: true } });
    });
    sweepIds(blocks).forEach((id, k) => {
      slots[id] = k === 0 && sweepLog ? { sid: sweepLog.subject, logged: sweepLog, why: 'Already logged in SCHEDULE.md' }
        : { sweep, why: 'Retests due in subjects you skipped tonight' };
    });
    evenings.push({ day, blocks, slots, wk, testsToday: tests.filter(t => t.date === day) });
  }
  return { evenings, tests };
}

/* ---------- short, finished phrases ---------- */
// A task's title when one exists, else its first clause cut at a natural break. Never ends in "…"
// or on a dangling word.
const STOP = /\s+(and|or|the|a|an|for|to|of|on|in|with|from|before|after|your|its|their|by|as|at)$/i;
function shorten(text, words = 8) {
  let t = String(text || '').replace(/\([^)]*\)/g, '').replace(/\s+/g, ' ').replace(/\s+([,.;:])/g, '$1').trim();
  const parts = t.split(/(?<!\bv)\.\s|:\s|;\s|\s—\s/).map(x => x.trim()).filter(Boolean);
  t = (parts[0] || '').split(' ').length <= 3 && parts[1] ? `${parts[0]}: ${parts[1]}` : (parts[0] || '');
  t = t.replace(/[.:;,]+$/, '');
  if (t.split(' ').length > words) {
    const commaCut = t.split(', ')[0];
    t = commaCut.split(' ').length >= 3 && commaCut.split(' ').length <= words ? commaCut : t.split(' ').slice(0, words).join(' ');
  }
  while (STOP.test(t)) t = t.replace(STOP, '');
  return t.replace(/[,:;]+$/, '');
}
const taskTitle = t => t.title || shorten(t.text);

/* ---------- now / next (drives the HUD) ---------- */
const slotName = x => !x ? 'Free' : x.homework ? 'Homework' : x.sweep ? 'Review' : subjName(x.sid);
const slotColor = x => !x ? '#48484a' : x.homework ? '#8e8e93' : x.sweep ? '#636366' : subjColor(x.sid);

// One short line for what a block is about.
function topicOf(x) {
  if (!x) return '';
  if (x.homework) return x.homework.length === 1 ? x.homework[0].title : `${x.homework.length} due`;
  if (x.sweep) return 'Cold questions: ' + x.sweep.map(w => w.s.short).join(', ');
  if (x.logged) return x.logged.what || 'Logged';
  const t = (x.work || [])[0];
  return t ? taskTitle(t) : '';
}

const dur = min => { min = Math.max(0, Math.round(min)); return min >= 60 ? `${Math.floor(min / 60)}h ${String(min % 60).padStart(2, '0')}m` : `${min}m`; };

async function api(url, body) {
  const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : { cache: 'no-store' });
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.status);
  return j;
}
