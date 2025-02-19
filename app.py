from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import os
import boto3
import watchtower
import time

load_dotenv()  # Charge les variables d'environnement du fichier .env

app = Flask(__name__)

#"test" 2 3 4 5 6 7 8 9
# Configuration de la base de données
#DATABASE = {
#    'dbname': os.getenv('api_fraude_db'),
#    'user': os.getenv('postgres'),
#    'password': os.getenv('password'),
#    'host': os.getenv('localhost'),
#    'port': os.getenv('5432')
#}

DATABASE = {
    'dbname': os.getenv('DATABASE_NAME'),
    'user': os.getenv('DATABASE_USER'),
    'password': os.getenv('PASSWORD'),
    'host': os.getenv('HOST'),
    'port': os.getenv('PORT')
}

# Whitelist de numéros (exemple)
WHITELIST = {"+2250123456789", "+2259876543210"}

# Configuration des logs CloudWatch
client = boto3.client('logs', region_name='us-east-1')  # Remplacez par votre région AWS
LOG_GROUP = '/flask/app-logs'
LOG_STREAM = 'business-log'

# Créer un logger pour les logs métier
def log_to_cloudwatch(message, level='info'):

    # Ajouter le niveau de log au message
    formatted_message = f"[{level.upper()}] {message}"

    # Envoyer le log à CloudWatch
    client.put_log_events(
        logGroupName=LOG_GROUP,
        logStreamName=LOG_STREAM,
        logEvents=[{'timestamp': int(time.time() * 1000), 'message': formatted_message}]
    )

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = psycopg2.connect(**DATABASE)
    return conn

@app.route('/transaction', methods=['POST'])
def create_transaction():
    data = request.get_json()
    #logger.info(f"Requête reçue : {data}")
    log_to_cloudwatch(f"Requête reçue : {data}", level='info')

    client_phone = data['client_phone']
    amount = data['amount']

    # Vérifier si le numéro est dans la whitelist
    if client_phone in WHITELIST:
        #logger.info(f"Numéro {client_phone} dans la whitelist, règles de gestion ignorées.")
        log_to_cloudwatch(f"Numéro {client_phone} dans la whitelist, règles de gestion ignorées.", level='info')
        return process_transaction(data)

    # Vérifier si le numéro est blacklisté
    if is_blacklisted(client_phone):
        #logger.warning(f"Numéro {client_phone} est blacklisté.")
        log_to_cloudwatch(f"Numéro {client_phone} est blacklisté.", level='warn')
        return jsonify({"error": "Numéro blacklisté pendant 30 minutes"}), 403

    # Vérifier le nombre de requêtes dans les 5 dernières minutes
    if not check_request_limit(client_phone):
        #logger.warning(f"Numéro {client_phone} a dépassé la limite de 3 requêtes en 5 minutes.")
        log_to_cloudwatch(f"Numéro {client_phone} a dépassé la limite de 3 requêtes en 5 minutes.", level='warn')
        blacklist_number(client_phone)
        return jsonify({"error": "Limite de 3 requêtes en 5 minutes atteinte, numéro blacklisté pendant 30 minutes"}), 429

    # Appliquer les règles de gestion
    if not check_daily_limit(client_phone, amount):
        #logger.warning(f"Limite quotidienne dépassée pour le numéro {client_phone}.")
        log_to_cloudwatch(f"Limite quotidienne dépassée pour le numéro {client_phone}.", level='warn')
        return jsonify({"error": "Daily limit exceeded"}), 400

    if not check_monthly_limit(client_phone, amount):
        #logger.warning(f"Limite mensuelle dépassée pour le numéro {client_phone}.")
        log_to_cloudwatch(f"Limite mensuelle dépassée pour le numéro {client_phone}.", level='warn')
        return jsonify({"error": "Monthly limit exceeded"}), 400

    # Traiter la transaction
    return process_transaction(data)

def process_transaction(data):
    #logger.info(f"Processing transaction from {data['client_phone']}.")
    log_to_cloudwatch(f"Processing transaction from {data['client_phone']}.", level='info')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("INSERT INTO transactions (client_phone, merchant_name, amount, operation, country, origin) VALUES (%s, %s, %s, %s, %s, %s)"),
        [data['client_phone'], data['merchant_name'], data['amount'], data['operation'], data['country'], data['origin']]
    )
    conn.commit()
    cur.close()
    conn.close()
    #logger.info(f"Transaction enregistrée pour le numéro {data['client_phone']}.")
    log_to_cloudwatch(f"Transaction enregistrée pour le numéro {data['client_phone']}.", level='info')
    return jsonify({"message": "Transaction created successfully"}), 201

def check_daily_limit(client_phone, amount):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("SELECT SUM(amount) FROM transactions WHERE client_phone = %s AND transaction_time >= CURRENT_DATE"),
        [client_phone]
    )
    total_amount = cur.fetchone()[0] or 0
    cur.close()
    conn.close()
    return (total_amount + amount) <= 2000000

def check_monthly_limit(client_phone, amount):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("SELECT SUM(amount) FROM transactions WHERE client_phone = %s AND transaction_time >= date_trunc('month', CURRENT_DATE)"),
        [client_phone]
    )
    total_amount = cur.fetchone()[0] or 0
    cur.close()
    conn.close()
    return (total_amount + amount) <= 10000000

def check_time_between_transactions(client_phone):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("SELECT transaction_time FROM transactions WHERE client_phone = %s ORDER BY transaction_time DESC LIMIT 1"),
        [client_phone]
    )
    last_transaction_time = cur.fetchone()
    cur.close()
    conn.close()
    if last_transaction_time:
        last_transaction_time = last_transaction_time[0]
        if datetime.now() - last_transaction_time < timedelta(minutes=5):
            return False
    return True

def check_request_limit(client_phone):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("SELECT COUNT(*) FROM transactions WHERE client_phone = %s AND transaction_time >= %s"),
        [client_phone, datetime.now() - timedelta(minutes=5)]
    )
    request_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return request_count < 3

def is_blacklisted(client_phone):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("SELECT blacklist_time FROM blacklist WHERE client_phone = %s AND blacklist_time >= %s"),
        [client_phone, datetime.now() - timedelta(minutes=30)]
    )
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

def blacklist_number(client_phone):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("INSERT INTO blacklist (client_phone, blacklist_time) VALUES (%s, %s)"),
        [client_phone, datetime.now()]
    )
    conn.commit()
    cur.close()
    conn.close()
    #logger.warning(f"Numéro {client_phone} blacklisté pendant 30 minutes.")
    log_to_cloudwatch(f"Numéro {client_phone} blacklisté pendant 30 minutes.", level='warn')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)