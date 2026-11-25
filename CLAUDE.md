# Crossdoku

Read docs/DesignSpec.md first.

- Client is plain static HTML/CSS/JS (no build). All API calls go through SuperFetch.
- Server is Flask: thin route files (Auth/Auth.py, Puzzles/Puzzles.py) call function files. Errors go through _Lib/Debugger.py.
- Tabs for indentation. GET by default; POST only for the password.
- Never show the player whether a letter is right or wrong (see "No-feedback rule" in DesignSpec.md).
- Clue text comes from Claude: always insert it with textContent, never innerHTML.
- Run tests from Server/: python -m pytest Tests
- Deploy with deploy.sh on the server. Never commit Server/.env.
