"""Leaderboard routes. Viewing and posting are public; removing a score needs the admin login."""
import time
from flask import Blueprint, request, jsonify
from _Lib.Debugger import Debugger
from Auth.Session import LoginRequired
from Scores.ScoreStore import (FindSolution, CleanName, AddScore, ListScores, DeleteScore, AllBoards,
	MIN_SECONDS, MAX_SECONDS, BOARD_ID)

Scores = Blueprint("Scores", __name__)
POSTS_PER_HOUR = 30
_posts = {}  # ip -> [timestamps], in memory


def _TooMany(ip):
	now = time.time()
	recent = [t for t in _posts.get(ip, []) if now - t < 3600]
	_posts[ip] = recent
	if len(recent) >= POSTS_PER_HOUR:
		return True
	recent.append(now)
	return False


def _Bad(message, status=400):
	return jsonify({"ok": False, "error": message}), status


@Scores.route("/api/scores/<puzzleId>", methods=["GET"])
def List(puzzleId):
	try:
		if not BOARD_ID.match(puzzleId):
			return _Bad("Bad puzzle id.")
		return jsonify({"ok": True, "scores": ListScores(puzzleId)})
	except Exception as e:
		return Debugger(e, message="Couldn't load the leaderboard.")


# POST: adds to what everyone sees.
@Scores.route("/api/scores", methods=["POST"])
def Post():
	try:
		ip = request.headers.get("X-Real-IP") or request.remote_addr or "?"
		data = request.get_json(silent=True) or {}
		puzzleId = str(data.get("puzzle", ""))
		name = CleanName(data.get("name"))
		if not BOARD_ID.match(puzzleId):
			return _Bad("Bad puzzle id.")
		if not name:
			return _Bad("Please enter a name.")
		try:
			seconds, hints = int(data.get("seconds")), int(data.get("hints", 0))
		except (TypeError, ValueError):
			return _Bad("Bad time.")
		if not MIN_SECONDS <= seconds <= MAX_SECONDS or not 0 <= hints <= 81:
			return _Bad("That time doesn't look right.")
		solution = FindSolution(puzzleId)
		if not solution:
			return _Bad("Puzzle not found.", 404)
		# The client only offers to post after a correct solve, so this just stops made-up posts.
		if str(data.get("grid", "")) != solution:
			return _Bad("Only solved puzzles can be posted.")
		if _TooMany(ip):
			return _Bad("Too many scores posted. Try again later.", 429)
		rows, rank, improved = AddScore(puzzleId, name, seconds, hints)
		return jsonify({"ok": True, "scores": rows, "rank": rank, "improved": improved, "name": name})
	except Exception as e:
		return Debugger(e, message="Couldn't save your score.")


@Scores.route("/api/scores-all", methods=["GET"])
@LoginRequired
def All():
	try:
		return jsonify({"ok": True, "boards": AllBoards()})
	except Exception as e:
		return Debugger(e)


@Scores.route("/api/scores/delete", methods=["POST"])
@LoginRequired
def Delete():
	try:
		data = request.get_json(silent=True) or {}
		try:
			found = DeleteScore(data.get("puzzle", ""), data.get("name", ""))
		except ValueError:
			return _Bad("Bad puzzle id.")
		if not found:
			return _Bad("Score not found.", 404)
		return jsonify({"ok": True})
	except Exception as e:
		return Debugger(e)
