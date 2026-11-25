"""Signed-cookie session and simple login throttling (in memory)."""
import hashlib
import hmac
import time
from functools import wraps
from flask import request, jsonify
from _Lib.Env import Setting

COOKIE_NAME = "crossdoku_session"
MAX_AGE = 60 * 60 * 24 * 30  # 30 days
_failures = {}  # ip -> [timestamps]


def _Secret():
	return (Setting("SECRET_KEY") or "change-me").encode("utf-8")


def CheckPassword(password):
	expected = Setting("APP_PASSWORD")
	if not expected:
		return False
	return hmac.compare_digest(str(password).encode("utf-8"), expected.encode("utf-8"))


def MakeToken():
	expires = str(int(time.time()) + MAX_AGE)
	sig = hmac.new(_Secret(), expires.encode(), hashlib.sha256).hexdigest()
	return f"{expires}.{sig}"


def IsLoggedIn():
	token = request.cookies.get(COOKIE_NAME, "")
	if "." not in token:
		return False
	expires, sig = token.split(".", 1)
	good = hmac.new(_Secret(), expires.encode(), hashlib.sha256).hexdigest()
	if not hmac.compare_digest(sig, good):
		return False
	return expires.isdigit() and int(expires) > time.time()


def LoginRequired(fn):
	@wraps(fn)
	def Wrapper(*args, **kwargs):
		if not IsLoggedIn():
			return jsonify({"ok": False, "error": "Please log in."}), 401
		return fn(*args, **kwargs)
	return Wrapper


def LoginBlocked(ip):
	now = time.time()
	recent = [t for t in _failures.get(ip, []) if now - t < 900]
	_failures[ip] = recent
	return len(recent) >= 10


def RecordFailure(ip):
	_failures.setdefault(ip, []).append(time.time())
