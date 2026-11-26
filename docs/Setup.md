# First-time setup on the server

Crossdoku lives at https://games.secretagents.com/crossdoku/ and its code at /opt/games/crossdoku.
The client uses relative API paths, so it also works at a domain root if that ever changes.

1. DNS: add an A record for games.secretagents.com pointing at the server's IP address.

2. Clone and configure (as root, which has the GitHub SSH key):

	cd /opt/games
	git clone git@github.com:zenmanenergy/crossdoku.git crossdoku
	cd /opt/games/crossdoku/Server
	cp .env.example .env
	nano .env            # set APP_PASSWORD, ANTHROPIC_API_KEY, SECRET_KEY
	chown root:www-data .env
	chmod 640 .env

   For SECRET_KEY: python3 -c "import secrets; print(secrets.token_hex(32))"

3. Service:

	cp /opt/games/crossdoku/docs/crossdoku.service /etc/systemd/system/
	systemctl daemon-reload
	systemctl enable crossdoku

4. nginx and HTTPS (once DNS has updated: ping games.secretagents.com should show your server's IP):

	cp /opt/games/crossdoku/docs/nginx-games.conf /etc/nginx/sites-available/games
	ln -s /etc/nginx/sites-available/games /etc/nginx/sites-enabled/
	nginx -t
	systemctl reload nginx
	certbot --nginx -d games.secretagents.com

5. Deploy:

	cd /opt/games/crossdoku
	bash deploy.sh

After that, every update is: push from your laptop, then bash deploy.sh on the server.

## Trying it on your laptop (Windows)

	cd Server
	py -m venv venv
	venv\Scripts\pip install -r requirements.txt
	copy .env.example .env      (then edit it)
	venv\Scripts\python app.py

Open http://localhost:9010. Running app.py directly also serves the Client folder, so nginx isn't needed locally.
