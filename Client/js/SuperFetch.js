// All client-server requests go through SuperFetch.
// URLs are relative (api/...), so the app works at a domain root or under a path like /crossdoku/.
// Returns the parsed JSON on success; throws an Error with the server's message otherwise.
async function SuperFetch(url, options = {}) {
	const opts = { credentials: "same-origin", ...options };
	if (opts.body && typeof opts.body !== "string") {
		opts.body = JSON.stringify(opts.body);
		opts.headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
	}
	let resp;
	try {
		resp = await fetch(url, opts);
	} catch (e) {
		throw new Error("Can't reach the server.");
	}
	let data = {};
	try { data = await resp.json(); } catch (e) { /* non-JSON reply */ }
	if (!resp.ok || data.ok === false) {
		const err = new Error(data.error || `Server error ${resp.status}`);
		err.status = resp.status;
		throw err;
	}
	return data;
}
