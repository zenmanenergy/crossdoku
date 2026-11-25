"""Run from Server/: python -m pytest Tests"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Puzzles.Generator import MakePuzzle, Solve, SolvableBySingles, UsableWords, ClearEnds  # noqa: E402

LETTERS = "AEILNORST"
CLUES = {
	"SALON": "Hair stylist's shop", "TRAIN": "Railway vehicle", "STONE": "Pebble's bigger cousin",
	"LATER": "Not now", "RATIO": "3:1, for example", "INLET": "Small coastal bay", "NOISE": "Din",
	"RAISE": "Lift up", "ALERT": "On guard", "STOLE": "Took without asking", "TRIAL": "Court proceeding",
	"SOLAR": "Sun-powered", "RINSE": "Wash lightly", "SAINT": "Canonized person", "TENOR": "Male voice",
	"SEAL": "Barking ocean mammal", "TOIL": "Hard work", "RAIN": "Wet weather", "NEST": "Bird's home",
	"LION": "King of the jungle", "SOIL": "Garden dirt", "RIOT": "Uprising", "TALE": "Story",
	"NOTE": "Memo", "ROSE": "Thorny flower", "LIAR": "Fibber", "SALT": "Shaker contents",
	"IRON": "Element Fe", "LOAN": "Money borrowed", "TONE": "Sound quality", "STAR": "The Sun, for one",
	"TRIO": "Group of three", "LENS": "Camera part", "RENT": "Housing payment", "NAIL": "Hammer target",
	# bad entries that must be filtered out
	"TATTOO": "Repeats letters", "BLAST": "Uses B", "AT": "Too short", "SALONS": "Too long",
}


def Check(p):
	letters = p["letters"]
	wordCells = {c for e in p["entries"] for c in e["cells"]}
	known = [p["solution"][i] if (i in p["givens"] or i in wordCells) else "" for i in range(81)]
	assert len(Solve(known, letters, 2)) == 1, "unique with answers known"
	assert SolvableBySingles(known, letters), "no guessing needed"
	givensOnly = [p["solution"][i] if i in p["givens"] else "" for i in range(81)]
	assert len(Solve(givensOnly, letters, 2)) == 2, "clues must matter"
	for e in p["entries"]:
		assert "".join(p["solution"][c] for c in e["cells"]) == e["word"]
		assert e["clue"]
		assert ClearEnds(e["dir"], e["cells"], wordCells), "answer runs into another shaded cell"


def test_usable_words_filters_bad_entries():
	u = UsableWords(LETTERS, CLUES)
	for bad in ("TATTOO", "BLAST", "AT", "SALONS"):
		assert bad not in u
	assert "SALON" in u


def test_each_level():
	for level in ("Easy", "Medium", "Hard"):
		Check(MakePuzzle(LETTERS, CLUES, level, seed=42))


def test_rejects_bad_letter_sets():
	for letters in ("ABC", "AAEILNORS"):
		try:
			MakePuzzle(letters, CLUES)
			assert False, "should have raised"
		except ValueError:
			pass


def test_built_in_puzzles_are_valid():
	path = os.path.join(os.path.dirname(__file__), "..", "..", "Client", "js", "puzzles.js")
	text = open(path, encoding="utf-8").read()
	for p in json.loads(text[text.index("["):text.rindex("]") + 1]):
		Check(p)
