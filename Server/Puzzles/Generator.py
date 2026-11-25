"""Builds a Crossdoku puzzle from a 9-letter set and a word list with clues.

A puzzle is a 9x9 letter sudoku. Some row and column runs are crossword answers.
The generator guarantees:
	- exactly one solution once the crossword answers are known
	- that solution can be reached with singles logic only (no guessing)
	- the givens alone are NOT enough, so the clues always matter
"""
import random
import time

GEN_NODES = 20000  # per-solve step budget for uniqueness checks
PLACE_NODES = 1500  # quick "can this still be filled?" check while placing words

LEVELS = {
	# name: (across words, down words, extra givens added after the minimum)
	"Easy": (3, 3, 10),
	"Medium": (4, 4, 4),
	"Hard": (4, 4, 0),
}


def BoxOf(r, c):
	return (r // 3) * 3 + c // 3


UNITS = [[r * 9 + c for c in range(9)] for r in range(9)] \
	+ [[r * 9 + c for r in range(9)] for c in range(9)] \
	+ [[(b // 3 * 3 + k // 3) * 9 + b % 3 * 3 + k % 3 for k in range(9)] for b in range(9)]
PEERS = [set() for _ in range(81)]
for _unit in UNITS:
	for _i in _unit:
		PEERS[_i] |= set(_unit)
for _i in range(81):
	PEERS[_i].discard(_i)


def UsableWords(letters, clues):
	"""Keep only 4-5 letter words made of distinct letters from the set."""
	letterSet = set(letters)
	out = {}
	for word, clue in clues.items():
		w = "".join(ch for ch in word.upper() if ch.isalpha())
		if 4 <= len(w) <= 5 and len(set(w)) == len(w) and set(w) <= letterSet and clue:
			out[w] = str(clue).strip()
	return out


class _Budget(Exception):
	pass


def Solve(grid, letters, limit=2, rnd=None, deadline=None, maxNodes=200000):
	"""Backtracking solver. Returns up to `limit` solutions, or None if it gave up
	after `maxNodes` steps (some hopeless partial grids would otherwise take minutes)."""
	g = grid[:]
	rows = [set() for _ in range(9)]
	cols = [set() for _ in range(9)]
	boxes = [set() for _ in range(9)]
	for i, v in enumerate(g):
		if v:
			r, c = divmod(i, 9)
			if v in rows[r] or v in cols[c] or v in boxes[BoxOf(r, c)]:
				return []
			rows[r].add(v)
			cols[c].add(v)
			boxes[BoxOf(r, c)].add(v)
	sols = []
	nodes = [0]

	def Rec():
		if len(sols) >= limit:
			return
		nodes[0] += 1
		if nodes[0] > maxNodes:
			raise _Budget()
		if deadline and time.time() > deadline:
			raise TimeoutError()
		best = None
		bestCand = None
		for i in range(81):
			if not g[i]:
				r, c = divmod(i, 9)
				cand = [L for L in letters if L not in rows[r] and L not in cols[c] and L not in boxes[BoxOf(r, c)]]
				if best is None or len(cand) < len(bestCand):
					best = i
					bestCand = cand
					if len(cand) <= 1:
						break
		if best is None:
			sols.append(g[:])
			return
		if rnd:
			rnd.shuffle(bestCand)
		r, c = divmod(best, 9)
		b = BoxOf(r, c)
		for L in bestCand:
			g[best] = L
			rows[r].add(L)
			cols[c].add(L)
			boxes[b].add(L)
			Rec()
			g[best] = ""
			rows[r].discard(L)
			cols[c].discard(L)
			boxes[b].discard(L)
			if len(sols) >= limit:
				return

	try:
		Rec()
	except _Budget:
		return None
	return sols


def Unique(grid, letters, deadline):
	sols = Solve(grid, letters, 2, deadline=deadline, maxNodes=GEN_NODES)
	return sols is not None and len(sols) == 1


def Ambiguous(grid, letters, deadline):
	sols = Solve(grid, letters, 2, deadline=deadline, maxNodes=GEN_NODES)
	return sols is not None and len(sols) == 2


def SolvableBySingles(grid, letters):
	"""True if naked and hidden singles alone fill the grid."""
	g = grid[:]
	while True:
		changed = False
		cand = {}
		for i in range(81):
			if not g[i]:
				cand[i] = set(letters) - {g[j] for j in PEERS[i] if g[j]}
				if not cand[i]:
					return False
				if len(cand[i]) == 1:
					g[i] = cand[i].pop()
					changed = True
		if not changed:
			for unit in UNITS:
				present = {g[i] for i in unit}
				for L in letters:
					if L in present:
						continue
					spots = [i for i in unit if not g[i] and L in cand.get(i, ())]
					if len(spots) == 1:
						g[spots[0]] = L
						changed = True
		if not changed:
			break
	return all(g)


def EndCells(d, cells):
	"""The cells just before the start and just after the end of a word, if on the board."""
	out = []
	if d == "A":
		if cells[0] % 9 > 0:
			out.append(cells[0] - 1)
		if cells[-1] % 9 < 8:
			out.append(cells[-1] + 1)
	else:
		if cells[0] >= 9:
			out.append(cells[0] - 9)
		if cells[-1] < 72:
			out.append(cells[-1] + 9)
	return out


def ClearEnds(d, cells, shaded):
	"""True if no shaded cell touches either end, so every answer's length is visible."""
	return not any(x in shaded for x in EndCells(d, cells))


def Consistent(grid, cells, word):
	"""Cheap check: the word agrees with letters already there and repeats nothing in a row, column or box."""
	trial = grid[:]
	for x, ch in zip(cells, word):
		if trial[x] and trial[x] != ch:
			return None
		trial[x] = ch
	for x in cells:
		ch = trial[x]
		for p in PEERS[x]:
			if trial[p] == ch:
				return None
	return trial


def Candidates(d, words, entries, cellsUsed):
	"""Every placement of every unused word in direction d that passes the layout rules."""
	used = {e["word"] for e in entries}
	takenLines = {(e["cells"][0] // 9 if d == "A" else e["cells"][0] % 9) for e in entries if e["dir"] == d}
	out = []
	for w in words:
		if any(w in u or u in w for u in used):  # no LOAN and LOANS in one puzzle
			continue
		L = len(w)
		for line in range(9):
			if line in takenLines:
				continue
			for start in range(10 - L):
				cells = [line * 9 + start + k for k in range(L)] if d == "A" else [(start + k) * 9 + line for k in range(L)]
				cross = sum(1 for x in cells if x in cellsUsed)
				if cross > 2 or (d == "D" and cross == 0):
					continue
				if not ClearEnds(d, cells, cellsUsed):
					continue
				if any(not ClearEnds(e["dir"], e["cells"], set(cells)) for e in entries):
					continue
				out.append((w, cells))
	return out


def PlaceWords(rnd, letters, words, nAcross, nDown, deadline):
	grid = [""] * 81
	entries = []
	cellsUsed = set()
	for d, n in (("A", nAcross), ("D", nDown)):
		for _ in range(n):
			if time.time() > deadline:
				raise TimeoutError()
			cands = Candidates(d, words, entries, cellsUsed)
			rnd.shuffle(cands)
			placedOne = False
			tested = 0
			for w, cells in cands:
				trial = Consistent(grid, cells, w)
				if trial is None:
					continue
				tested += 1
				if tested > 25:
					break
				if not Solve(trial, letters, 1, deadline=deadline, maxNodes=PLACE_NODES):
					continue
				grid = trial
				cellsUsed |= set(cells)
				entries.append({"dir": d, "word": w, "cells": cells})
				placedOne = True
				break
			if not placedOne:
				return None
	return grid, entries, cellsUsed


def MakePuzzle(letters, clues, level="Medium", seed=None, timeLimit=25):
	"""Returns a puzzle dict, or raises ValueError / TimeoutError."""
	letters = "".join(dict.fromkeys(ch for ch in letters.upper() if ch.isalpha()))
	if len(letters) != 9:
		raise ValueError("Need exactly 9 distinct letters")
	words = UsableWords(letters, clues)
	if len(words) < 12:
		raise ValueError(f"Only {len(words)} usable words; need at least 12")
	nAcross, nDown, extra = LEVELS.get(level, LEVELS["Medium"])
	rnd = random.Random(seed)
	deadline = time.time() + timeLimit

	while True:
		if time.time() > deadline:
			raise TimeoutError()
		placed = PlaceWords(rnd, letters, words, nAcross, nDown, deadline)
		if not placed:
			continue
		grid, entries, wordCells = placed
		sol = Solve(grid, letters, 1, rnd, deadline, maxNodes=GEN_NODES)
		if not sol:
			continue
		sol = sol[0]

		# Start with every non-word cell given, then remove while still unique.
		candidates = [i for i in range(81) if i not in wordCells]
		rnd.shuffle(candidates)
		givens = set(candidates)
		for i in candidates:
			givens.discard(i)
			p = [sol[j] if (j in givens or j in wordCells) else "" for j in range(81)]
			if not Unique(p, letters, deadline):
				givens.add(i)

		# Add givens back until a human can finish it with singles logic.
		rest = [i for i in range(81) if i not in givens and i not in wordCells]
		rnd.shuffle(rest)
		while rest and not SolvableBySingles([sol[j] if (j in givens or j in wordCells) else "" for j in range(81)], letters):
			givens.add(rest.pop())
		for i in rest[:extra]:
			givens.add(i)

		# The clues must matter: givens alone must not pin down the answer.
		p = [sol[j] if j in givens else "" for j in range(81)]
		if not Ambiguous(p, letters, deadline):
			continue

		starts = sorted(set(e["cells"][0] for e in entries))
		num = {s: k + 1 for k, s in enumerate(starts)}
		for e in entries:
			e["num"] = num[e["cells"][0]]
			e["clue"] = words[e["word"]]
		entries.sort(key=lambda e: (e["dir"], e["num"]))
		return {
			"letters": letters,
			"solution": "".join(sol),
			"givens": sorted(givens),
			"entries": entries,
			"level": level,
		}
