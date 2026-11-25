"""Puzzle routes."""
from flask import Blueprint, request, jsonify
from _Lib.Debugger import Debugger
from Auth.Session import LoginRequired
from Puzzles.GeneratePuzzle import GeneratePuzzle, OverHourlyLimit

Puzzles = Blueprint("Puzzles", __name__)


@Puzzles.route("/api/puzzles/generate", methods=["GET"])
@LoginRequired
def Generate():
	try:
		if OverHourlyLimit():
			return jsonify({"ok": False, "error": "Hourly puzzle limit reached. Try again later."}), 429
		level = request.args.get("level", "Medium")
		theme = request.args.get("theme", "").strip()[:60]
		puzzle = GeneratePuzzle(level, theme)
		return jsonify({"ok": True, "puzzle": puzzle})
	except Exception as e:
		return Debugger(e, message="Couldn't make a puzzle this time. Please try again.")
