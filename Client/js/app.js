// Crossdoku client. Plain JavaScript, no build step.
const APP_NAME = "Crossdoku"; // change here to rename the app everywhere on screen

const $ = id => document.getElementById(id);
const store = {
	get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } },
	set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } },
	del(k) { try { localStorage.removeItem(k); } catch (e) { /* storage unavailable */ } },
};

// ---------- puzzle list ----------
// SHARED_PUZZLES come from the server (made on the admin page); BUILT_IN_PUZZLES ship with the client.
let SHARED_PUZZLES = [];
function AllPuzzles() { return [...SHARED_PUZZLES, ...BUILT_IN_PUZZLES]; }
function PuzzleName(p) {
	if (p.name) return p.name;
	const d = new Date((p.created || 0) * 1000);
	const when = d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
	return `${p.level}${p.theme ? " · " + p.theme : ""} · ${when}`;
}

// ---------- game state ----------
let P = null, entries = [], givens = new Set(), state = [], notes = [], hinted = new Set();
let sel = -1, dir = "A", notesMode = false, showClashes = store.get("crossdoku-clashes") === true;
let startTime = 0, confirmAction = null;

function BoxOf(i) { const r = Math.floor(i / 9), c = i % 9; return Math.floor(r / 3) * 3 + Math.floor(c / 3); }
const PEERS = Array.from({ length: 81 }, (_, i) => {
	const r = Math.floor(i / 9), c = i % 9, b = BoxOf(i), out = [];
	for (let j = 0; j < 81; j++) if (j !== i && (Math.floor(j / 9) === r || j % 9 === c || BoxOf(j) === b)) out.push(j);
	return out;
});

function BuildPicker() {
	const s = $("puzzleSelect");
	s.innerHTML = "";
	const solved = store.get("crossdoku-solved") || {};
	const groups = [["New puzzles", SHARED_PUZZLES], ["Starter puzzles", BUILT_IN_PUZZLES]];
	for (const [label, list] of groups) {
		if (!list.length) continue;
		const g = document.createElement("optgroup");
		g.label = label;
		list.forEach(p => {
			const o = document.createElement("option");
			o.value = p.id;
			o.textContent = PuzzleName(p) + (solved[p.id] ? "  ✓" : "");
			g.appendChild(o);
		});
		s.appendChild(g);
	}
	if (P) s.value = P.id;
}

function NextPuzzle() {
	// The next puzzle in the list that isn't solved yet (wraps around).
	const all = AllPuzzles(), solved = store.get("crossdoku-solved") || {};
	const k = all.findIndex(p => p.id === P.id);
	for (let step = 1; step <= all.length; step++) {
		const p = all[(k + step) % all.length];
		if (!solved[p.id]) return Load(p.id);
	}
	Load(all[(k + 1) % all.length].id);
}

function Load(id) {
	const all = AllPuzzles();
	P = all.find(p => p.id === id) || all[0];
	store.set("crossdoku-last", P.id);
	entries = P.entries;
	givens = new Set(P.givens);
	state = Array(81).fill("");
	notes = Array.from({ length: 81 }, () => new Set());
	hinted = new Set();
	givens.forEach(g => state[g] = P.solution[g]);
	const saved = store.get("crossdoku-" + P.id);
	if (saved) {
		saved.state.forEach((v, j) => { if (!givens.has(j)) state[j] = v; });
		(saved.notes || []).forEach((n, j) => notes[j] = new Set(n));
		hinted = new Set(saved.hinted || []);
	}
	startTime = Date.now();
	sel = -1;
	$("status").textContent = "";
	$("letterSet").textContent = P.letters;
	$("printTitle").textContent = `${APP_NAME} · ${PuzzleName(P)}`;
	BuildPicker(); BuildBoard(); BuildClues(); BuildKeys(); Render();
	$("clueText").textContent = "Tap a shaded cell or a clue to start.";
	$("clueText").className = "muted";
}

function Save() { store.set("crossdoku-" + P.id, { state, notes: notes.map(s => [...s]), hinted: [...hinted] }); }
function EntryAt(i, d) { return entries.find(e => e.dir === d && e.cells.includes(i)); }

function BuildBoard() {
	const bd = $("board");
	bd.innerHTML = "";
	for (let i = 0; i < 81; i++) {
		const d = document.createElement("div");
		d.className = "cell";
		d.onclick = () => Tap(i);
		bd.appendChild(d);
	}
}
function BuildClues() {
	for (const d of ["A", "D"]) {
		const ol = $(d === "A" ? "across" : "down");
		ol.innerHTML = "";
		entries.filter(e => e.dir === d).forEach(e => {
			const li = document.createElement("li");
			li.innerHTML = `<span class="n"></span><span class="t"></span><span class="len"></span>`;
			li.querySelector(".n").textContent = e.num;
			li.querySelector(".t").textContent = e.clue; // textContent: clues come from Claude, never trust as HTML
			li.querySelector(".len").textContent = `(${e.word.length})`;
			li.onclick = () => { dir = d; sel = e.cells.find(c => !state[c]) ?? e.cells[0]; Render(); BringBoardIntoView(); };
			e.li = li;
			ol.appendChild(li);
		});
	}
}
function BuildKeys() {
	const k = $("keys");
	k.innerHTML = "";
	[...P.letters].forEach(L => {
		const b = document.createElement("button");
		b.textContent = L;
		b.dataset.l = L;
		b.onclick = () => Input(L);
		k.appendChild(b);
	});
}

// On a phone the clue list sits below the grid; after tapping a clue, scroll back up to the grid.
function BringBoardIntoView() {
	const r = $("board").getBoundingClientRect();
	if (r.top < 0 || r.bottom > window.innerHeight) $("board").scrollIntoView({ behavior: "smooth", block: "start" });
}

function Tap(i) {
	const other = dir === "A" ? "D" : "A";
	if (i === sel) { if (EntryAt(i, other)) dir = other; }
	else { sel = i; if (!EntryAt(i, dir) && EntryAt(i, other)) dir = other; }
	Render();
}
function Locked(i) { return givens.has(i) || hinted.has(i); }

function Input(L) {
	if (sel < 0 || Locked(sel)) return;
	if (notesMode) {
		const n = notes[sel];
		n.has(L) ? n.delete(L) : n.add(L);
		state[sel] = "";
	} else {
		state[sel] = L;
		notes[sel].clear();
		PEERS[sel].forEach(j => notes[j].delete(L));
		Advance();
	}
	Save(); Render(); CheckDone();
}
function Advance() {
	const e = EntryAt(sel, dir);
	if (!e) return;
	const k = e.cells.indexOf(sel);
	for (let m = k + 1; m < e.cells.length; m++) if (!state[e.cells[m]]) { sel = e.cells[m]; return; }
}
function Erase() {
	if (sel < 0) return;
	if (!state[sel] && !notes[sel].size) {
		const e = EntryAt(sel, dir);
		if (e) { const k = e.cells.indexOf(sel); if (k > 0) sel = e.cells[k - 1]; }
	}
	if (!Locked(sel)) { state[sel] = ""; notes[sel].clear(); }
	Save(); Render();
}

function Clashes() {
	const bad = new Set();
	if (!showClashes) return bad;
	for (let i = 0; i < 81; i++) {
		if (!state[i]) continue;
		for (const j of PEERS[i]) if (state[j] === state[i]) { bad.add(i); break; }
	}
	return bad;
}

function Render() {
	const wc = new Set(entries.flatMap(e => e.cells));
	const bad = Clashes();
	const cur = sel >= 0 ? EntryAt(sel, dir) : null;
	const curCells = new Set(cur ? cur.cells : []);
	const starts = {};
	entries.forEach(e => starts[e.cells[0]] = e.num);
	const cells = $("board").children;
	for (let i = 0; i < 81; i++) {
		const d = cells[i], c = i % 9, r = Math.floor(i / 9);
		let cls = "cell";
		if (c === 2 || c === 5) cls += " bR";
		if (r === 2 || r === 5) cls += " bB";
		if (wc.has(i)) cls += " word";
		if (curCells.has(i)) cls += " inword";
		if (i === sel) cls += " sel";
		if (givens.has(i)) cls += " given";
		else if (hinted.has(i)) cls += " hinted";
		if (bad.has(i) && !givens.has(i)) cls += " clash";
		d.className = cls;
		let html = starts[i] !== undefined ? `<span class="num">${starts[i]}</span>` : "";
		if (state[i]) html += state[i];
		else if (notes[i].size) html += '<div class="notes">' + [...P.letters].map(L => `<span>${notes[i].has(L) ? L : ""}</span>`).join("") + "</div>";
		d.innerHTML = html;
	}
	// "filled" only means every cell has a letter. It never says whether they are right.
	entries.forEach(e => {
		e.li.classList.toggle("on", e === cur);
		e.li.classList.toggle("filled", e.cells.every(c => state[c]));
	});
	const ct = $("clueText");
	if (cur) {
		ct.className = "";
		ct.innerHTML = "<b></b> ";
		ct.firstChild.textContent = `${cur.num} ${cur.dir === "A" ? "Across" : "Down"}`;
		ct.appendChild(document.createTextNode(`${cur.clue} (${cur.word.length})`));
	} else if (sel >= 0) {
		ct.className = "muted";
		ct.textContent = "Sudoku cell: use row, column and box logic.";
	}
	const counts = {};
	state.forEach(v => { if (v) counts[v] = (counts[v] || 0) + 1; });
	[...$("keys").children].forEach(b => b.classList.toggle("used", counts[b.dataset.l] >= 9));
	$("notesBtn").classList.toggle("on", notesMode);
	$("notesBtn").textContent = notesMode ? "Notes: on" : "Notes";
	$("clashBtn").classList.toggle("on", showClashes);
}

function MoveClue(step) {
	const order = [...entries.filter(e => e.dir === "A"), ...entries.filter(e => e.dir === "D")];
	const cur = sel >= 0 ? EntryAt(sel, dir) : null;
	let k = cur ? order.indexOf(cur) : -1;
	k = (k + step + order.length) % order.length;
	const e = order[k];
	dir = e.dir;
	sel = e.cells.find(c => !state[c]) ?? e.cells[0];
	Render();
}

// Hint fills an EMPTY cell only, so it can never reveal that a letter is wrong.
function Hint() {
	let i = sel;
	if (i < 0 || state[i]) {
		const empty = [...Array(81).keys()].filter(j => !state[j]);
		if (!empty.length) { $("status").textContent = "No empty cells left for a hint."; return; }
		i = empty[Math.floor(Math.random() * empty.length)];
		sel = i;
	}
	state[i] = P.solution[i];
	notes[i].clear();
	hinted.add(i);
	Save(); Render(); CheckDone();
}

function CheckDone() {
	if (state.some(v => !v)) { $("status").textContent = ""; return; }
	if (state.some((v, i) => v !== P.solution[i])) {
		$("status").textContent = "Every cell is filled, but the grid isn't solved yet.";
		return;
	}
	const solved = store.get("crossdoku-solved") || {};
	solved[P.id] = true;
	store.set("crossdoku-solved", solved);
	const mins = Math.max(1, Math.round((Date.now() - startTime) / 60000));
	$("winText").textContent = `${PuzzleName(P)} complete` + (hinted.size ? ` with ${hinted.size} hint${hinted.size > 1 ? "s" : ""}.` : ", no hints!") + ` About ${mins} min this session.`;
	$("win").classList.add("show");
	BuildPicker();
}

function Confirm(text, action) {
	$("confirmText").textContent = text;
	confirmAction = action;
	$("confirm").classList.add("show");
}

// ---------- start ----------
async function Start() {
	document.title = APP_NAME;
	document.querySelectorAll(".appName").forEach(h => h.textContent = APP_NAME);
	try {
		SHARED_PUZZLES = (await SuperFetch("api/puzzles")).puzzles || [];
	} catch (e) {
		SHARED_PUZZLES = []; // server down: the starter puzzles still work
	}
	$("loading").classList.add("hidden");
	$("gameScreen").classList.remove("hidden");
	// ../#G123... from the admin page opens that puzzle directly.
	const wanted = decodeURIComponent(location.hash.slice(1));
	Load(AllPuzzles().some(p => p.id === wanted) ? wanted : store.get("crossdoku-last"));
}

$("printBtn").onclick = () => window.print();
$("puzzleSelect").onchange = ev => Load(ev.target.value);
$("nextBtn").onclick = NextPuzzle;
$("notesBtn").onclick = () => { notesMode = !notesMode; Render(); };
$("eraseBtn").onclick = Erase;
$("hintBtn").onclick = Hint;
$("clashBtn").onclick = () => { showClashes = !showClashes; store.set("crossdoku-clashes", showClashes); Render(); };
$("resetBtn").onclick = () => Confirm("Clear this puzzle?", () => { store.del("crossdoku-" + P.id); Load(P.id); });
$("confirmYes").onclick = () => { $("confirm").classList.remove("show"); if (confirmAction) confirmAction(); confirmAction = null; };
$("confirmNo").onclick = () => { $("confirm").classList.remove("show"); confirmAction = null; };
$("prevClue").onclick = () => MoveClue(-1);
$("nextClue").onclick = () => MoveClue(1);
$("winClose").onclick = () => $("win").classList.remove("show");
$("winNext").onclick = () => { $("win").classList.remove("show"); NextPuzzle(); };

document.addEventListener("keydown", ev => {
	if (!P || $("gameScreen").classList.contains("hidden")) return;
	if (ev.target.tagName === "INPUT" || ev.target.tagName === "SELECT") return;
	// Leave browser shortcuts alone (Ctrl+Shift+R, Ctrl+F, Alt+Left, ...).
	if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
	const k = ev.key.toUpperCase();
	if (k.length === 1 && P.letters.includes(k)) { Input(k); ev.preventDefault(); return; }
	if (ev.key === "Backspace" || ev.key === "Delete") { Erase(); ev.preventDefault(); return; }
	if (ev.key === " ") { if (sel >= 0) Tap(sel); ev.preventDefault(); return; }
	if (ev.key === "Tab") { MoveClue(ev.shiftKey ? -1 : 1); ev.preventDefault(); return; }
	const mv = { ArrowUp: -9, ArrowDown: 9, ArrowLeft: -1, ArrowRight: 1 }[ev.key];
	if (mv === undefined) return;
	ev.preventDefault();
	if (sel < 0) sel = 0;
	else {
		const r = Math.floor(sel / 9), c = sel % 9;
		if (mv === -1 && c > 0) sel--;
		if (mv === 1 && c < 8) sel++;
		if (mv === -9 && r > 0) sel -= 9;
		if (mv === 9 && r < 8) sel += 9;
		if (Math.abs(mv) === 1) { if (EntryAt(sel, "A")) dir = "A"; } else if (EntryAt(sel, "D")) dir = "D";
	}
	Render();
});

Start();
