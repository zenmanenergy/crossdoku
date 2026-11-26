# Crossdoku Design Spec

A 9x9 letter sudoku where some row and column runs are crossword answers. Solve clues to place letters, then finish with sudoku logic.

## Structure

- Client/ - static files served by nginx. Plain HTML, CSS and JavaScript, no build step.
  - index.html, css/app.css, js/app.js (game), js/SuperFetch.js (all API calls), js/puzzles.js (9 starter puzzles)
  - APP_NAME at the top of js/app.js renames the app on screen.
- Server/ - small Flask API behind gunicorn, proxied by nginx at /api/.
  - app.py registers the routes.
  - Auth/Auth.py (routes) and Auth/Session.py (password check, signed cookie, login throttle)
  - Puzzles/Puzzles.py (route), Puzzles/GeneratePuzzle.py (Claude prompt), Puzzles/Generator.py (grid builder)
  - _Lib/Env.py (.env loader), _Lib/Claude.py (Messages API via the standard library), _Lib/Debugger.py
  - Tests/ - generator and route tests (Claude is faked in tests)
- deploy.sh - pull, install, test, restart, health check.

Hosted at https://games.secretagents.com/crossdoku/ (code in /opt/games/crossdoku). nginx (docs/nginx-games.conf) serves Client/ at /crossdoku/ and proxies /crossdoku/api/ to gunicorn on port 9010. Client API paths are relative so the path prefix needs no code changes.

No database. Generated puzzles and progress live in each browser's localStorage.

## API

| Method | Path | Notes |
| --- | --- | --- |
| POST | /api/login | body {"password"}; sets HttpOnly signed cookie (30 days). POST because it carries the password. 10 failures per IP in 15 min locks out for 15 min. |
| GET | /api/session | {"loggedIn": true/false} |
| GET | /api/logout | clears the cookie |
| GET | /api/puzzles/generate?level=Easy/Medium/Hard&theme=... | login required; capped at GENERATE_PER_HOUR |
| GET | /api/health | for deploy.sh |

## Security level

Deliberately light: one shared password from Server/.env, a cookie signed with SECRET_KEY, a login throttle and an hourly generation cap. The goal is only to stop strangers spending the Claude API budget. The static Client files themselves are public (the login screen just hides them); the API is what is protected. The Claude API key never leaves the server.

## Puzzle generation

1. Claude picks 9 distinct letters (theme-flavored if given) and about 45 words of 4 to 5 letters with clues. Reply is JSON.
2. The server throws out any word that is the wrong length, repeats a letter, or uses a letter outside the set.
3. Generator.py places the words (Easy 3 across + 3 down, Medium and Hard 4 + 4). Every down answer crosses an across answer, no answer touches another shaded cell at either end (so lengths are clear on paper), and no answer is part of another (no LOAN with LOANS). It fills the grid, then picks givens so that:
   - with the answers known there is exactly one solution,
   - that solution needs only singles logic (no guessing),
   - the givens alone are not enough, so the clues always matter.
   Easy adds 10 extra givens, Medium 4, Hard none.
4. If the word list is too thin, it asks Claude once more for a different letter set.

So Claude can write a bad clue, but it cannot produce an unsolvable grid.

## No-feedback rule

The game never says a letter is wrong:
- no Check button, and clues are not struck through when correct (only dimmed when every cell is filled)
- Hint only fills an empty cell, never corrects one
- Clashes (off by default) only compares the player's own letters against sudoku rules, never against the answer
- The one exception: when every cell is filled and the grid is not the solution, it says "Every cell is filled, but the grid isn't solved yet."

## Open questions

- Final name (Crossdoku is the working name; change APP_NAME and the title in index.html)
