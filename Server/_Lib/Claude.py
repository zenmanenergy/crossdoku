"""Minimal Claude Messages API call using only the standard library."""
import json
import urllib.request
import urllib.error
from _Lib.Env import Setting

API_URL = "https://api.anthropic.com/v1/messages"


def AskClaude(system, prompt, maxTokens=4000, timeout=90):
	key = Setting("ANTHROPIC_API_KEY")
	if not key:
		raise RuntimeError("ANTHROPIC_API_KEY is not set in Server/.env")
	body = json.dumps({
		"model": Setting("CLAUDE_MODEL", "claude-sonnet-5-5"),
		"max_tokens": maxTokens,
		"system": system,
		"messages": [{"role": "user", "content": prompt}],
	}).encode("utf-8")
	req = urllib.request.Request(API_URL, data=body, method="POST", headers={
		"x-api-key": key,
		"anthropic-version": "2023-06-01",
		"content-type": "application/json",
	})
	try:
		with urllib.request.urlopen(req, timeout=timeout) as resp:
			data = json.loads(resp.read().decode("utf-8"))
	except urllib.error.HTTPError as e:
		detail = e.read().decode("utf-8", "replace")[:500]
		raise RuntimeError(f"Claude API error {e.code}: {detail}")
	return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")


def ExtractJson(text):
	"""Pulls the first {...} object out of a reply, ignoring any code fences."""
	start = text.find("{")
	end = text.rfind("}")
	if start < 0 or end <= start:
		raise ValueError("No JSON object in Claude's reply")
	return json.loads(text[start:end + 1])
