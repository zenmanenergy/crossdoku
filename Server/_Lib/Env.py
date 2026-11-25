"""Loads Server/.env into os.environ (no extra packages needed)."""
import os


def LoadEnv(path=None):
	path = path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
	if not os.path.exists(path):
		return
	with open(path, encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line or line.startswith("#") or "=" not in line:
				continue
			key, value = line.split("=", 1)
			value = value.strip().strip('"').strip("'")
			os.environ.setdefault(key.strip(), value)


def Setting(name, default=""):
	return os.environ.get(name, default)
