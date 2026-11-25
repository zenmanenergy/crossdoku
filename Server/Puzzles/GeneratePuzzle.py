"""Asks Claude for a letter set plus clued words, then builds the puzzle locally.

Claude only supplies letters, words and clues. The code checks every word and
builds the grid itself, so a bad reply can never produce an unsolvable puzzle.
"""
import time
import uuid
from _Lib.Claude import AskClaude, ExtractJson
from _Lib.Env import Setting
from Puzzles.Generator import MakePuzzle, UsableWords, LEVELS

_recent = []  # timestamps of generations, for the hourly cap

SYSTEM = "You write word lists and crossword clues for a letter-sudoku puzzle game. Reply with JSON only."


def BuildPrompt(theme, avoid):
	themeLine = f'Theme: "{theme}". Lean the letter set, words and clue flavor toward this theme where you can, but valid words matter more than the theme.' if theme else "No theme: pick any lively letter set."
	avoidLine = f"Do not use this exact letter set: {avoid}." if avoid else ""
	return f"""Pick 9 DIFFERENT uppercase letters that combine into many common English words. Include at least 3 vowels.
{themeLine}
{avoidLine}

Then list 45 common English words that:
- are 4 or 5 letters long
- use ONLY those 9 letters
- never repeat a letter within the word (SALON is fine, TATTOO is not)
- are not proper nouns, abbreviations or plurals made only by adding S (unless the plural is a common word in its own right)

For each word write a short crossword-style clue (under 40 characters) that does not contain the answer. Keep it family friendly and fair for a smart adult.

Reply with only this JSON:
{{"letters": "ABCDEFGHI", "words": [{{"word": "WORD", "clue": "Clue text"}}]}}"""


def OverHourlyLimit():
	limit = int(Setting("GENERATE_PER_HOUR", "30") or 30)
	now = time.time()
	_recent[:] = [t for t in _recent if now - t < 3600]
	return len(_recent) >= limit


def GeneratePuzzle(level, theme):
	if level not in LEVELS:
		level = "Medium"
	_recent.append(time.time())
	lastError = None
	avoid = ""
	for attempt in range(2):
		reply = ExtractJson(AskClaude(SYSTEM, BuildPrompt(theme, avoid)))
		letters = str(reply.get("letters", "")).upper()
		clues = {str(w.get("word", "")): str(w.get("clue", "")) for w in reply.get("words", []) if isinstance(w, dict)}
		usable = UsableWords(letters, clues)
		try:
			puzzle = MakePuzzle(letters, usable, level)
		except (ValueError, TimeoutError) as e:
			lastError = e
			avoid = letters
			continue
		puzzle["id"] = "G" + uuid.uuid4().hex[:10].upper()
		puzzle["theme"] = theme
		puzzle["created"] = int(time.time())
		return puzzle
	raise RuntimeError(f"Generation failed twice: {lastError}")
