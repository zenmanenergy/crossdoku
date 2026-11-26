"""Leaderboard tests. Run from Server/: python -m pytest Tests"""
import Tests.test_routes as R  # sets up env, fake Claude and a temp DATA_DIR  # noqa: F401
import Scores.Scores as S
from Scores.ScoreStore import FindSolution

E1 = FindSolution("E1")  # a starter puzzle from Client/js/puzzles.js


def Post(c, **kw):
	body = {"puzzle": "E1", "name": "Steve", "seconds": 300, "hints": 0, "grid": E1}
	body.update(kw)
	return c.post("/api/scores", json=body)


def Fresh():
	S._posts.clear()
	return R.Client()


def test_starter_solution_found():
	assert E1 and len(E1) == 81


def test_post_and_list_public():
	c = Fresh()
	r = Post(c, name="Ana", seconds=400)
	assert r.status_code == 200 and r.get_json()["rank"] >= 1
	names = [x["name"] for x in c.get("/api/scores/E1").get_json()["scores"]]
	assert "Ana" in names


def test_best_score_kept_and_hint_penalty():
	c = Fresh()
	Post(c, puzzle="E2", grid=FindSolution("E2"), name="Bo", seconds=500)
	r = Post(c, puzzle="E2", grid=FindSolution("E2"), name="bo", seconds=600)  # worse, same name
	assert r.get_json()["improved"] is False
	Post(c, puzzle="E2", grid=FindSolution("E2"), name="Cy", seconds=200, hints=5)  # 200 + 300 = 500
	rows = c.get("/api/scores/E2").get_json()["scores"]
	assert [x["name"] for x in rows] == ["Bo", "Cy"]  # tie on 500: earlier post first
	assert rows[0]["seconds"] == 500


def test_rejects_unsolved_and_bad_input():
	c = Fresh()
	wrong = ("B" if E1[0] != "B" else "C") + E1[1:]
	assert Post(c, grid=wrong).status_code == 400
	assert Post(c, seconds=3).status_code == 400
	assert Post(c, name="   ").status_code == 400
	assert Post(c, puzzle="../../x").status_code == 400
	assert Post(c, puzzle="Z9").status_code == 404


def test_name_cleaned():
	c = Fresh()
	r = Post(c, name="  A\nVery   Long Name That Keeps Going  ")
	assert r.get_json()["name"] == "A Very Long Name Tha"


def test_rate_limit():
	c = Fresh()
	codes = [Post(c, name=f"P{k}").status_code for k in range(S.POSTS_PER_HOUR + 1)]
	assert codes[-1] == 429 and codes[0] == 200


def test_admin_remove_needs_login():
	c = Fresh()
	Post(c, puzzle="E3", grid=FindSolution("E3"), name="Troll")
	assert c.post("/api/scores/delete", json={"puzzle": "E3", "name": "Troll"}).status_code == 401
	assert c.get("/api/scores-all").status_code == 401
	a = R.Admin()
	assert "E3" in a.get("/api/scores-all").get_json()["boards"]
	assert a.post("/api/scores/delete", json={"puzzle": "E3", "name": "troll"}).status_code == 200
	assert c.get("/api/scores/E3").get_json()["scores"] == []


def test_deleting_puzzle_removes_its_board():
	R.Gen._recent.clear()
	a = R.Admin()
	p = a.post("/api/puzzles/generate", json={"level": "Easy"}).get_json()["puzzle"]
	S._posts.clear()
	assert Post(a, puzzle=p["id"], grid=p["solution"]).status_code == 200
	a.post("/api/puzzles/delete", json={"id": p["id"]})
	assert a.get(f"/api/scores/{p['id']}").get_json()["scores"] == []
