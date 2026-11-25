"""Route tests with Claude faked out. Run from Server/: python -m pytest Tests"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["APP_PASSWORD"] = "narwhal"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ANTHROPIC_API_KEY"] = "fake"
os.environ["GENERATE_PER_HOUR"] = "3"

import app as App  # noqa: E402
import Puzzles.GeneratePuzzle as Gen  # noqa: E402
from Tests.test_generator import CLUES, Check  # noqa: E402

FAKE_REPLY = "```json\n" + json.dumps({"letters": "AEILNORST", "words": [{"word": w, "clue": c} for w, c in CLUES.items()]}) + "\n```"
Gen.AskClaude = lambda system, prompt, **kw: FAKE_REPLY


def Client():
	App.app.config["TESTING"] = True
	return App.app.test_client()


def test_generate_needs_login():
	c = Client()
	r = c.get("/api/puzzles/generate")
	assert r.status_code == 401


def test_wrong_password():
	c = Client()
	r = c.post("/api/login", json={"password": "nope"})
	assert r.status_code == 401
	assert c.get("/api/session").get_json()["loggedIn"] is False


def test_forged_cookie_rejected():
	c = Client()
	c.set_cookie("crossdoku_session", "9999999999.deadbeef")
	assert c.get("/api/puzzles/generate").status_code == 401


def test_login_generate_logout():
	Gen._recent.clear()
	c = Client()
	assert c.post("/api/login", json={"password": "narwhal"}).status_code == 200
	assert c.get("/api/session").get_json()["loggedIn"] is True
	r = c.get("/api/puzzles/generate?level=Hard&theme=science")
	assert r.status_code == 200, r.get_json()
	p = r.get_json()["puzzle"]
	Check(p)
	assert p["level"] == "Hard" and p["theme"] == "science" and p["id"].startswith("G")
	c.get("/api/logout")
	assert c.get("/api/puzzles/generate").status_code == 401


def test_hourly_limit():
	Gen._recent.clear()
	c = Client()
	c.post("/api/login", json={"password": "narwhal"})
	codes = [c.get("/api/puzzles/generate?level=Easy").status_code for _ in range(4)]
	assert codes == [200, 200, 200, 429]
