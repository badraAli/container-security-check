sudo yum update -y
sudo yum install -y python3 python3-pip -y
sudo yum install nginx -y
Pip install unicorn
sudo yum install git -y (optionnel)

creer l'environnement virtuel
activer l'environnement virtuel

pip install flask
pip install gunicorn


pip install -r requirements.txt


- creer un fichier .env sur le serveur pour stocker de maniere permanente les variables d'environnements
- creer un fichier gitignore pour ignorer certains fichiers

- freeze > requirements.txt (pour update les dependances du projet)

-
----------------------------------------------------------------------------------
- Autre methode de configuration des logs ccloudwatchs
pip install boto3 watchtower
# Configuration des logs CloudWatch
cloudwatch_logs = boto3.client('logs', region_name='your-region')  # Remplacez par votre région AWS

# Créer un logger pour les logs métier
business_logger = logging.getLogger('business')
business_logger.setLevel(logging.INFO)
cloudwatch_handler_business = watchtower.CloudWatchLogHandler(
    log_group='/flask/app-logs',
    stream_name='business-logs',
    boto3_client=cloudwatch_logs
)
business_logger.addHandler(cloudwatch_handler_business)

# business_logger.info(f"Numéro {client_phone} dans la whitelist, règles de gestion ignorées.")

# business_logger.warning(f"Numéro {client_phone} est blacklisté.")

IAM Role : Utiliser un rôle IAM au lieu des clés d'accès pour une meilleure sécurité.
permission CloudWatchAgentServerPolicy a attaché au role

Format des logs : Personnaliser le format des logs pour inclure plus d'informations (comme l'ID de transaction).
-
----------------------------------------------------------------------------------


- Database
----------------------------------------------------------------------------------
creation de la table transactions de la base de donnée
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    client_phone VARCHAR(20) NOT NULL,
    merchant_name VARCHAR(100) NOT NULL,
    amount NUMERIC NOT NULL,
    operation VARCHAR(50) NOT NULL,
    country CHAR(2) NOT NULL,
    origin VARCHAR(100) NOT NULL,
    transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

creation de la table blacklist de la base de données
CREATE TABLE blacklist (
    id SERIAL PRIMARY KEY,
    client_phone VARCHAR(20) NOT NULL,
    blacklist_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
----------------------------------------------------------------------------------


tester la connexion a la base de donnée
sudo yum install postgresql15
psql -h <urlbd> -U <postgres> -d <databse>


-nginx
----------------------------------------------------------------------------------
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/your/app/static/;
    }
}
----------------------------------------------------------------------------------

-security-check.service
----------------------------------------------------------------------------------
sudo nano /etc/systemd/system/security-check.service

[Unit]
Description=Gunicorn instance to serve security check api
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/security-check
EnvironmentFile=/home/ec2-user/security-check/.env
ExecStart=/home/ec2-user/security-check/fraudapi/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 app:app

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl restart security-check
----------------------------------------------------------------------------------

-github action
----------------------------------------------------------------------------------
Script de deploiement Github action
name: Deploy Flask App to Amazon Linux

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v2

    - name: Install SSH key
      uses: shimataro/ssh-key-action@v2
      with:
        key: ${{ secrets.SSH_PRIVATE_KEY }}
        known_hosts: ${{ secrets.KNOWN_HOSTS }}

    - name: Deploy to Amazon Linux
      run: |
        ssh -o StrictHostKeyChecking=no ec2-user@${{ secrets.SERVER_IP }} << 'EOF'
        cd /path/to/your/app
        git pull origin main
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        sudo cp nginx.conf /etc/nginx/conf.d/my_flask_app.conf
        sudo systemctl restart nginx
        gunicorn --bind 127.0.0.1:8000 wsgi:app
        EOF
known_hosts 
Il s'agit d'un fichier qui stocke les clés publiques des serveurs auxquels vous vous êtes déjà connecté via SSH.
Sur votre machine locale, connectez-vous une fois à votre serveur via SSH.
La clé publique du serveur sera ajoutée à votre fichier ~/.ssh/known_hosts
Extrayez la ligne correspondant à votre serveur et ajoutez-la en tant que secret GitHub sous le nom KNOWN_HOSTS
my-server-ip ecdsa-sha2-nistp256 AAAA... (clé publique du serveur)
----------------------------------------------------------------------------------

----------------------------------------------------------------------------------
Utiliser un fichier de configuration speciale pour l'application 

Fichier de configuration Nginx (/etc/nginx/sites-available/flask-app)

server {
    listen 80;
    server_name your-domain.com;

    # Logs d'accès et d'erreurs
    access_log /var/log/nginx/flask-app-access.log;
    error_log /var/log/nginx/flask-app-error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Rediriger les erreurs 404 et 500 vers des pages personnalisées (optionnel)
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}

Activez la configuration :
sudo ln -s /etc/nginx/sites-available/flask-app /etc/nginx/sites-enabled/
sudo nginx -t  # Vérifier la syntaxe
sudo systemctl restart nginx
----------------------------------------------------------------------------------


----------------------------------------------------------------------------------
Pour utiliser l'id de l'instance comme flux de log

import logging
import watchtower
import boto3
import os

# Récupérer l'ID de l'instance
instance_id = os.popen("curl -s http://169.254.169.254/latest/meta-data/instance-id").read().strip()

# Configuration CloudWatch
cloudwatch_logs = boto3.client('logs', region_name='your-region')

# Logger pour les logs métier
business_logger = logging.getLogger('business')
business_logger.setLevel(logging.INFO)
cloudwatch_handler = watchtower.CloudWatchLogHandler(
    log_group='/flask/business-logs',
    stream_name=instance_id,
    boto3_client=cloudwatch_logs
)
business_logger.addHandler(cloudwatch_handler)

# Exemple de log métier
business_logger.info("Ceci est un log métier.")

----------------------------------------------------------------------------------


-
----------------------------------------------------------------------------------

Autres exemple d'automatisation avec gitub action

Pour cette structure de projet

flask-app/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   └── ...
├── tests/
│   └── test_app.py
├── requirements.txt
├── gunicorn.conf.py
├── nginx-flask-app.conf
└── .github/
    └── workflows/
        └── deploy.yml

Configuration du workflow GitHub Actions

name: Deploy Flask App

on:
  push:
    branches:
      - main  # Déclencher le déploiement uniquement sur la branche main

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        run: |
          python -m pytest tests/

  deploy:
    runs-on: ubuntu-latest
    needs: test  # Attendre que le job "test" soit terminé
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Install SSH key
        uses: shimataro/ssh-key-action@v2
        with:
          key: ${{ secrets.SSH_PRIVATE_KEY }}  # Clé SSH privée stockée dans les secrets GitHub
          known_hosts: ${{ secrets.KNOWN_HOSTS }}  # Known hosts pour éviter les prompts

      - name: Copy files to server
        run: |
          scp -r ./* user@your-server-ip:/path/to/flask-app

      - name: Restart services
        run: |
          ssh user@your-server-ip "sudo systemctl restart gunicorn"
          ssh user@your-server-ip "sudo systemctl restart nginx"

4. Explication du workflow
Job test :

Vérifie le code.

Configure Python.

Installe les dépendances.

Exécute les tests avec pytest.

Job deploy :

Vérifie le code.

Installe la clé SSH pour se connecter au serveur.

Copie les fichiers sur le serveur avec scp.

Redémarre Gunicorn et Nginx pour appliquer les changements.


6. Configuration du serveur
Fichier de configuration Nginx
Placez le fichier nginx-flask-app.conf sur le serveur dans /etc/nginx/sites-available/ et activez-le :

sudo ln -s /etc/nginx/sites-available/nginx-flask-app.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx