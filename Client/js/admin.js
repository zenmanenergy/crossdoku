// Crossdoku admin page: log in, make puzzles, delete puzzles.
// Lives at /crossdoku/admin/, so API paths start with ../
const $ = id => document.getElementById(id);
let level = "Medium", pendingDelete = null;

function Show(id) {
	["loading", "loginScreen", "adminScreen"].forEach(s => $(s).classList.toggle("hidden", s !== id));
}

function Describe(p) {
	const d = new Date((p.created || 0) * 1000);
	const when = d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
	return `${p.level}${p.theme ? " · " + p.theme : ""} · ${when}`;
}

async function LoadList() {
	const list = $("list");
	try {
		const puzzles = (await SuperFetch("../api/puzzles")).puzzles || [];
		$("count").textContent = `(${puzzles.length})`;
		list.innerHTML = "";
		if (!puzzles.length) {
			list.innerHTML = '<li class="muted">None yet. Make one above.</li>';
			return;
		}
		puzzles.forEach(p => {
			const li = document.createElement("li");
			li.className = "card";
			li.innerHTML = `<div class="info"><b class="name"></b><span class="words muted"></span></div>
				<div class="actions"><a class="play" href="">Play</a><button class="small del">Delete</button></div>`;
			li.querySelector(".name").textContent = Describe(p);
			li.querySelector(".words").textContent = `Letters ${p.letters} · ${p.entries.map(e => e.word).join(", ")}`;
			li.querySelector(".play").href = "../#" + encodeURIComponent(p.id);
			const del = li.querySelector(".del");
			del.onclick = () => ConfirmDelete(p, del);
			list.appendChild(li);
		});
	} catch (e) {
		list.innerHTML = "";
		const li = document.createElement("li");
		li.className = "error";
		li.textContent = e.message;
		list.appendChild(li);
	}
}

// Two taps to delete: the first turns the button into "Really delete?".
async function ConfirmDelete(p, btn) {
	if (pendingDelete !== p.id) {
		pendingDelete = p.id;
		btn.textContent = "Really delete?";
		btn.classList.add("danger");
		setTimeout(() => { if (pendingDelete === p.id) { pendingDelete = null; btn.textContent = "Delete"; btn.classList.remove("danger"); } }, 4000);
		return;
	}
	pendingDelete = null;
	btn.disabled = true;
	try {
		await SuperFetch("../api/puzzles/delete", { method: "POST", body: { id: p.id } });
		LoadList();
	} catch (e) {
		if (e.status === 401) return Show("loginScreen");
		btn.disabled = false;
		btn.textContent = e.message;
	}
}

async function Generate() {
	const btn = $("generateBtn");
	btn.disabled = true;
	$("genStatus").textContent = "Claude is picking letters and writing clues, then the server builds the grid. This takes about 30 to 60 seconds.";
	try {
		const data = await SuperFetch("../api/puzzles/generate", { method: "POST", body: { level, theme: $("theme").value.trim() } });
		const p = data.puzzle;
		$("genStatus").innerHTML = 'Done: <b></b>. <a href="">Play it</a>';
		$("genStatus").querySelector("b").textContent = Describe(p);
		$("genStatus").querySelector("a").href = "../#" + encodeURIComponent(p.id);
		$("theme").value = "";
		LoadList();
	} catch (e) {
		if (e.status === 401) return Show("loginScreen");
		$("genStatus").textContent = e.message;
	} finally {
		btn.disabled = false;
	}
}

async function Start() {
	try {
		const data = await SuperFetch("../api/session");
		if (data.loggedIn) { Show("adminScreen"); LoadList(); } else Show("loginScreen");
	} catch (e) {
		$("loading").textContent = e.message;
	}
}

$("loginForm").onsubmit = async ev => {
	ev.preventDefault();
	$("loginError").textContent = "";
	try {
		await SuperFetch("../api/login", { method: "POST", body: { password: $("password").value } });
		$("password").value = "";
		Show("adminScreen");
		LoadList();
	} catch (e) {
		$("loginError").textContent = e.message;
	}
};
$("logoutBtn").onclick = async () => { try { await SuperFetch("../api/logout"); } catch (e) { /* ignore */ } Show("loginScreen"); };
$("generateBtn").onclick = Generate;
$("levelSeg").onclick = ev => {
	const b = ev.target.closest("button");
	if (!b) return;
	level = b.dataset.level;
	[...$("levelSeg").children].forEach(x => x.classList.toggle("on", x === b));
};

Start();
