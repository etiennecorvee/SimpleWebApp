bash -c "export USERNAME=$(/usr/bin/cat /etc/ecodata/username.txt) && \
    export PASSWORD=$(/usr/bin/cat /etc/ecodata/password.txt) && \
    /home/ubuntu/SimpleWebApp/venv/bin/gunicorn --workers 1 \
    --certfile=/etc/ecodata/ecovision_localhost.crt \
    --keyfile=/etc/ecodata/ecovision_localhost.key \
    --bind 127.0.0.1:5001 \
    wsgi:app"