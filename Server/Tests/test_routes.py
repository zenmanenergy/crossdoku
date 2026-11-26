"""Route tests with Claude faked out. Run from Server/: python -m pytest Tests"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["APP_PASSWORD"] = "narwhal"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ANTHROPIC_API_KEY"] = "fake"
os.environ["GENERATE_PER_HOUR"] = "3"
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="crossdoku-test-")  # never touch real puzzles

import app as App  # noqa: E402
import Puzzles.GeneratePuzzle as Gen  # noqa: E402
from Tests.test_generator import CLUES, Check  # noqa: E402

FAKE_REPLY = "```json\n" + json.dumps({"letters": "AEILNORST", "words": [{"word": w, "clue": c} for w, c in CLUES.items()]}) + "\n```"
Gen.AskClaude = lambda system, prompt, **kw: FAKE_REPLY


def Client():
	App.app.config["TESTING"] = True
	return App.app.test_client()


def Admin():
	c = Client()
	assert c.post("/api/login", json={"password": "narwhal"}).status_code == 200
	return c


def test_list_is_public():
	r = Client().get("/api/puzzles")
	assert r.status_code == 200 and isinstance(r.get_json()["puzzles"], list)


def test_generate_and_delete_need_login():
	c = Client()
	assert c.post("/api/puzzles/generate", json={"level": "Easy"}).status_code == 401
	assert c.post("/api/puzzles/delete", json={"id": "G0123456789"}).status_code == 401


def test_generate_is_not_a_get():
	assert Admin().get("/api/puzzles/generate").status_code == 405


def test_wrong_password():
	c = Client()
	assert c.post("/api/login", json={"password": "nope"}).status_code == 401
	assert c.get("/api/session").get_json()["loggedIn"] is False


def test_forged_cookie_rejected():
	c = Client()
	c.set_cookie("crossdoku_session", "9999999999.deadbeef")
	assert c.post("/api/puzzles/generate", json={}).status_code == 401


def test_generate_saves_for_everyone_then_delete():
	Gen._recent.clear()
	c = Admin()
	r = c.post("/api/puzzles/generate", json={"level": "Hard", "theme": "science"})
	assert r.status_code == 200, r.get_json()
	p = r.get_json()["puzzle"]
	Check(p)
	assert p["level"] == "Hard" and p["theme"] == "science"
	# A visitor with no login sees it.
	ids = [x["id"] for x in Client().get("/api/puzzles").get_json()["puzzles"]]
	assert p["id"] in ids
	assert c.post("/api/puzzles/delete", json={"id": p["id"]}).status_code == 200
	ids = [x["id"] for x in Client().get("/api/puzzles").get_json()["puzzles"]]
	assert p["id"] not in ids
	assert c.post("/api/puzzles/delete", json={"id": p["id"]}).status_code == 404


def test_delete_rejects_path_tricks():
	c = Admin()
	for bad in ("../../.env", "G123", "g0123456789", ""):
		assert c.post("/api/puzzles/delete", json={"id": bad}).status_code == 400


def test_logout():
	c = Admin()
	c.get("/api/logout")
	assert c.post("/api/puzzles/generate", json={}).status_code == 401


def test_hourly_limit():
	Gen._recent.clear()
	c = Admin()
	codes = [c.post("/api/puzzles/generate", json={"level": "Easy"}).status_code for _ in range(4)]
	assert codes == [200, 200, 200, 429]
