"""Shared error handler: logs the full traceback, returns a safe JSON error."""
import traceback
from flask import jsonify


def Debugger(e, status=500, message="Something went wrong on the server."):
	traceback.print_exc()
	return jsonify({"ok": False, "error": message}), status
