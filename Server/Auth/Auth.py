"""Auth routes: one shared password, signed cookie, no database."""
from flask import Blueprint, request, jsonify
from _Lib.Debugger import Debugger
from Auth.Session import CheckPassword, MakeToken, IsLoggedIn, COOKIE_NAME, MAX_AGE, LoginBlocked, RecordFailure

Auth = Blueprint("Auth", __name__)


@Auth.route("/api/login", methods=["POST"])
def Login():
	# POST because it carries the password.
	try:
		ip = request.headers.get("X-Real-IP") or request.remote_addr or "?"
		if LoginBlocked(ip):
			return jsonify({"ok": False, "error": "Too many tries. Wait 15 minutes."}), 429
		data = request.get_json(silent=True) or {}
		if not CheckPassword(data.get("password", "")):
			RecordFailure(ip)
			return jsonify({"ok": False, "error": "Wrong password."}), 401
		resp = jsonify({"ok": True})
		secure = request.is_secure or request.headers.get("X-Forwarded-Proto") == "https"
		resp.set_cookie(COOKIE_NAME, MakeToken(), max_age=MAX_AGE, httponly=True, samesite="Strict", secure=secure)
		return resp
	except Exception as e:
		return Debugger(e)


@Auth.route("/api/session", methods=["GET"])
def Session():
	return jsonify({"ok": True, "loggedIn": IsLoggedIn()})


@Auth.route("/api/logout", methods=["GET"])
def Logout():
	resp = jsonify({"ok": True})
	resp.delete_cookie(COOKIE_NAME)
	return resp
