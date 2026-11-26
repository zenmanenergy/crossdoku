"""Shared puzzle storage: one JSON file per puzzle in DATA_DIR/puzzles. No database."""
import json
import os
import re
from _Lib.Env import Setting

ID_PATTERN = re.compile(r"^G[0-9A-F]{10}$")


def PuzzleDir():
	base = Setting("DATA_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
	path = os.path.join(base, "puzzles")
	os.makedirs(path, exist_ok=True)
	return path


def _Path(puzzleId):
	# The id goes into a file name, so only accept ids this app made.
	if not ID_PATTERN.match(str(puzzleId)):
		raise ValueError("Bad puzzle id")
	return os.path.join(PuzzleDir(), puzzleId + ".json")


def SavePuzzle(puzzle):
	path = _Path(puzzle["id"])
	tmp = path + ".tmp"
	with open(tmp, "w", encoding="utf-8") as f:
		json.dump(puzzle, f)
	os.replace(tmp, path)  # atomic, so a reader never sees half a file


def ListPuzzles():
	out = []
	folder = PuzzleDir()
	for name in os.listdir(folder):
		if not name.endswith(".json"):
			continue
		try:
			with open(os.path.join(folder, name), encoding="utf-8") as f:
				out.append(json.load(f))
		except (OSError, ValueError):
			continue  # skip a damaged file rather than break the whole list
	out.sort(key=lambda p: p.get("created", 0), reverse=True)
	return out


def DeletePuzzle(puzzleId):
	path = _Path(puzzleId)
	if os.path.exists(path):
		os.remove(path)
		return True
	return False
