# SimpleWebApp

## Install

https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04

> mkdir myproject
or
git clone https://github.com/etiennecorvee/SimpleWebApp.git
> cd myproject/
or
cd SimpleWebApp
> python3 -m venv venv
> source venv/bin/activate
> python3 -m pip install --upgrade pip
> pip install gunicorn flask requests opencv-python

> vi myproject.py
    from flask import Flask
    app = Flask(__name__)
    @app.route("/")
    def hello():
        return "<h1 style='color:blue'>Hello There!</h1>"
    if __name__ == "__main__":
        app.run(host='0.0.0.0')

> sudo ufw allow 5000
> python myproject.py

test from outside http://127.0.0.1:5000/

> vi wsgi.py
    from myproject import app
    if __name__ == "__main__":
        app.run()

> gunicorn --bind 0.0.0.0:5000 wsgi:app
> deactivate

test from outside http://127.0.0.1:5000/

> sudo nano /etc/systemd/system/myproject.service

or

> sudo cp myproject.service /etc/systemd/system/
    
[Unit]
Description=Gunicorn instance to serve myproject
After=network.target
[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/myproject
Environment="PATH=/home/ubuntu/myproject/venv/bin"
ExecStart=/home/ubuntu/myproject/venv/bin/gunicorn --workers 1 --bind 0.0.0.0:5001 wsgi:app
[Install]
WantedBy=multi-user.target  150  sudo systemctl start myproject

> sudo systemctl enable myproject
> sudo systemctl start myproject
(sudo systemctl daemon-reload)
test from outside http://127.0.0.1:5001/

this works from any cloud VM such as OVH

## Test

### 

> cd /home/ubuntu/EcoVision/STAND_ALONE_ECO3D/platform/prog
> bash manager.sh

### simulation
simulate with one existing fall detection availbale results:
chute_d-2023-11-01T13:04:39.014000-nbp1-colour.mm

curl -X POST http://localhost:5002/process/chute_d-2023-11-01T13:04:39.014000-nbp1-colour.png