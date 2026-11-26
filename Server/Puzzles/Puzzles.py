"""Puzzle routes. Listing is public; making and deleting puzzles needs the admin login."""
from flask import Blueprint, request, jsonify
from _Lib.Debugger import Debugger
from Auth.Session import LoginRequired
from Puzzles.GeneratePuzzle import GeneratePuzzle, OverHourlyLimit
from Puzzles.PuzzleStore import SavePuzzle, ListPuzzles, DeletePuzzle

Puzzles = Blueprint("Puzzles", __name__)


@Puzzles.route("/api/puzzles", methods=["GET"])
def List():
	try:
		return jsonify({"ok": True, "puzzles": ListPuzzles()})
	except Exception as e:
		return Debugger(e, message="Couldn't load the puzzle list.")


# POST: these two change what everyone sees.
@Puzzles.route("/api/puzzles/generate", methods=["POST"])
@LoginRequired
def Generate():
	try:
		if OverHourlyLimit():
			return jsonify({"ok": False, "error": "Hourly puzzle limit reached. Try again later."}), 429
		data = request.get_json(silent=True) or {}
		level = str(data.get("level", "Medium"))
		theme = str(data.get("theme", "")).strip()[:60]
		puzzle = GeneratePuzzle(level, theme)
		SavePuzzle(puzzle)
		return jsonify({"ok": True, "puzzle": puzzle})
	except Exception as e:
		return Debugger(e, message="Couldn't make a puzzle this time. Please try again.")


@Puzzles.route("/api/puzzles/delete", methods=["POST"])
@LoginRequired
def Delete():
	try:
		data = request.get_json(silent=True) or {}
		try:
			found = DeletePuzzle(data.get("id", ""))
		except ValueError:
			return jsonify({"ok": False, "error": "Bad puzzle id."}), 400
		if not found:
			return jsonify({"ok": False, "error": "Puzzle not found."}), 404
		return jsonify({"ok": True})
	except Exception as e:
		return Debugger(e)
