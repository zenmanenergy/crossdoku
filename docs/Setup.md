# First-time setup on the server

1. Point a subdomain (for example crossdoku.secretagents.com) at the server in DNS.
2. On the server:

	sudo git clone <your repo url> /opt/crossdoku
	cd /opt/crossdoku/Server
	sudo cp .env.example .env
	sudo nano .env            # set APP_PASSWORD, ANTHROPIC_API_KEY, SECRET_KEY
	sudo chown root:www-data .env && sudo chmod 640 .env

   For SECRET_KEY, any long random string works: python3 -c "import secrets; print(secrets.token_hex(32))"

3. Install the service and the nginx site:

	sudo cp /opt/crossdoku/docs/crossdoku.service /etc/systemd/system/
	sudo systemctl daemon-reload && sudo systemctl enable crossdoku
	sudo cp /opt/crossdoku/docs/nginx-crossdoku.conf /etc/nginx/sites-available/crossdoku
	sudo nano /etc/nginx/sites-available/crossdoku     # set server_name
	sudo ln -s /etc/nginx/sites-available/crossdoku /etc/nginx/sites-enabled/
	sudo nginx -t && sudo systemctl reload nginx
	sudo certbot --nginx -d crossdoku.secretagents.com

4. Run ./deploy.sh from /opt/crossdoku. It builds the venv, runs the tests, starts the service and checks /api/health.

After that, every update is: push from your laptop, then ./deploy.sh on the server.

## Trying it on your laptop (Windows)

	cd Server
	py -m venv venv
	venv\Scripts\pip install -r requirements.txt
	copy .env.example .env      (then edit it)
	venv\Scripts\python app.py

Open http://localhost:9010. Running app.py directly also serves the Client folder, so nginx isn't needed locally.
