"""Crossdoku API. nginx serves Client/ as static files and proxies /api/ here."""
from flask import Flask, jsonify
from _Lib.Env import LoadEnv

LoadEnv()

from Auth.Auth import Auth  # noqa: E402
from Puzzles.Puzzles import Puzzles  # noqa: E402
from Scores.Scores import Scores  # noqa: E402

app = Flask(__name__)
app.register_blueprint(Auth)
app.register_blueprint(Puzzles)
app.register_blueprint(Scores)


@app.route("/api/health", methods=["GET"])
def Health():
	return jsonify({"ok": True, "app": "crossdoku"})


if __name__ == "__main__":
	# Local testing only: python app.py, then open http://localhost:9010 (admin page: /admin/)
	import os
	from flask import send_from_directory
	clientDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Client")

	@app.route("/")
	@app.route("/<path:path>")
	def Static(path=""):
		if path == "" or path.endswith("/"):
			path += "index.html"
		elif os.path.isdir(os.path.join(clientDir, path)):
			from flask import redirect
			return redirect("/" + path + "/")
		return send_from_directory(clientDir, path)

	app.run(port=9010, debug=True)
