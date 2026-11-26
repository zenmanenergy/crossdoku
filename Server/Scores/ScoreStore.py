"""Leaderboards: one small JSON file per puzzle in DATA_DIR/scores. No database.

Ranking: solve time plus a penalty for each hint, lowest first.
Each name keeps only its best score on a puzzle.
"""
import json
import os
import re
import threading
import time
from _Lib.Env import Setting
from Puzzles.PuzzleStore import PuzzleDir, ID_PATTERN

HINT_PENALTY = 60        # seconds added per hint
MAX_PER_BOARD = 50       # keep the best 50 on each puzzle
MIN_SECONDS = 20         # nobody solves a full grid faster than this
MAX_SECONDS = 7 * 24 * 3600
NAME_MAX = 20

BOARD_ID = re.compile(r"^[A-Z0-9]{1,12}$")  # G + 10 hex for shared puzzles, E1/M2/H3 for starters
_lock = threading.Lock()  # gunicorn runs 1 worker with threads, so one lock covers every write
_builtIn = {"mtime": None, "puzzles": {}}


def ScoreDir():
	base = Setting("DATA_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
	path = os.path.join(base, "scores")
	os.makedirs(path, exist_ok=True)
	return path


def _Path(puzzleId):
	# The id goes into a file name, so only accept plain ids.
	if not BOARD_ID.match(str(puzzleId)):
		raise ValueError("Bad puzzle id")
	return os.path.join(ScoreDir(), puzzleId + ".json")


def _ClientDir():
	return Setting("CLIENT_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Client")


def _BuiltInPuzzles():
	# The starter puzzles live in Client/js/puzzles.js as "const BUILT_IN_PUZZLES = [...];"
	path = os.path.join(_ClientDir(), "js", "puzzles.js")
	try:
		mtime = os.path.getmtime(path)
	except OSError:
		return {}
	if mtime != _builtIn["mtime"]:
		with open(path, encoding="utf-8") as f:
			text = f.read()
		data = json.loads(text[text.index("["):text.rindex("]") + 1])
		_builtIn["puzzles"] = {p["id"]: p for p in data}
		_builtIn["mtime"] = mtime
	return _builtIn["puzzles"]


def FindSolution(puzzleId):
	"""The 81-letter solution for a shared or starter puzzle, or None if there is no such puzzle."""
	puzzleId = str(puzzleId)
	if ID_PATTERN.match(puzzleId):
		path = os.path.join(PuzzleDir(), puzzleId + ".json")
		if not os.path.exists(path):
			return None
		with open(path, encoding="utf-8") as f:
			return json.load(f).get("solution")
	p = _BuiltInPuzzles().get(puzzleId)
	return p["solution"] if p else None


def CleanName(name):
	name = " ".join(str(name or "").split())  # collapse spaces and newlines
	name = "".join(ch for ch in name if ch.isprintable())
	return name[:NAME_MAX].strip()


def Score(seconds, hints):
	return int(seconds) + HINT_PENALTY * int(hints)


def _Load(puzzleId):
	path = _Path(puzzleId)
	if not os.path.exists(path):
		return []
	try:
		with open(path, encoding="utf-8") as f:
			return json.load(f)
	except (OSError, ValueError):
		return []  # a damaged file starts a fresh board rather than breaking the game


def _Save(puzzleId, rows):
	path = _Path(puzzleId)
	tmp = path + ".tmp"
	with open(tmp, "w", encoding="utf-8") as f:
		json.dump(rows, f)
	os.replace(tmp, path)  # atomic


def _Sort(rows):
	rows.sort(key=lambda r: (r["score"], r["when"]))
	return rows


def ListScores(puzzleId):
	return _Sort(_Load(puzzleId))


def AddScore(puzzleId, name, seconds, hints):
	"""Adds or improves this name's score. Returns (rows, rank of this name or None, improved?)."""
	row = {"name": name, "seconds": int(seconds), "hints": int(hints), "score": Score(seconds, hints), "when": int(time.time())}
	key = name.lower()
	with _lock:
		rows = _Load(puzzleId)
		old = next((r for r in rows if r["name"].lower() == key), None)
		improved = old is None or row["score"] < old["score"]
		if improved:
			rows = [r for r in rows if r["name"].lower() != key] + [row]
		rows = _Sort(rows)[:MAX_PER_BOARD]
		_Save(puzzleId, rows)
	rank = next((k + 1 for k, r in enumerate(rows) if r["name"].lower() == key), None)
	return rows, rank, improved


def DeleteScore(puzzleId, name):
	key = str(name).lower()
	with _lock:
		rows = _Load(puzzleId)
		left = [r for r in rows if r["name"].lower() != key]
		if len(left) == len(rows):
			return False
		_Save(puzzleId, left)
	return True


def DeleteBoard(puzzleId):
	with _lock:
		path = _Path(puzzleId)
		if os.path.exists(path):
			os.remove(path)


def AllBoards():
	out = {}
	for name in sorted(os.listdir(ScoreDir())):
		if name.endswith(".json") and BOARD_ID.match(name[:-5]):
			rows = ListScores(name[:-5])
			if rows:
				out[name[:-5]] = rows
	return out
