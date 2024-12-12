from flask import Flask, render_template, request, redirect, url_for
import os
import json
import csv
import requests
from elasticsearch import Elasticsearch

# import requests  # Don't forget to import requests

app = Flask(__name__)

es = Elasticsearch(["http://localhost:9200"])

LOGS_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..', 'logstash', 'logs')

if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)


# Define Kibana URL and visualization ID
KIBANA_URL = "https://l.facebook.com/l.php?u=https%3A%2F%2Fsupreme-potato-7v596rxg7wrqcx7gg-5601.app.github.dev%2F%3Ffbclid%3DIwZXh0bgNhZW0CMTAAAR1UWvjdbPPd5eU_hF0PEMHqAwmn5ruzofO5qASkpEq4M4cW4qd1OlWUs5w_aem_6SjC9jAZyT5CDczAf4QuFg&h=AT0n15qr6LYrwil_TMD6UwZYocMe3aQo3Uy8M_U7r7ae3c9mpkaWvmYChQVTELRK7rK0oYm2yZknnapa1DZgZFCwKFoWeTIXr9VSID-UG_eo90VHQg7zGmVerBpXewpmLtYzcQ"
# /  # URL complète de votre instance Kibana
#VISUALIZATION_ID = "a2cbb630-b0ea-11ef-bffc-c7786914d8da"

ALLOWED_EXTENSIONS = {'json', 'csv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    error_message = request.args.get('error_message')
    return render_template('index.html', error_message=error_message)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index', error_message="Aucun fichier sélectionné"))

    file = request.files['file']

    if file.filename == '':
        return redirect(url_for('index', error_message="Aucun fichier sélectionné"))

    if file and allowed_file(file.filename):
        filename = os.path.join(LOGS_DIR, file.filename)
        file.save(filename)

        try:
            if filename.endswith('.json'):
                process_json(filename)
            elif filename.endswith('.csv'):
                process_csv(filename)
        except Exception as e:
            return redirect(url_for('index', error_message=f"Erreur lors du traitement du fichier: {str(e)}"))

        return redirect(url_for('index'))

    return redirect(url_for('index', error_message="Fichier non autorisé, uniquement JSON ou CSV."))


@app.route('/dashboard')
def show_visualization():
    return render_template('dashboard.html')
@app.route('/dashboard2')
def show_visualization2():
    return render_template('dashboard2.html')

def process_json(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
        print(f"Fichier JSON traité: {filename}")

        # Indexer le fichier JSON dans Elasticsearch
        es.index(index="json2-2024-12-12", body=data)
        
        # Rafraîchir l'index pour que les données soient immédiatement disponibles
        es.indices.refresh(index="logs-json-index")
        print("Index rafraîchi dans Elasticsearch.")


# Traiter le fichier CSV


# def process_csv(filename):
#     with open(filename, 'r') as file:
#         reader = csv.reader(file)
#         for row in reader:
#             print(f"Ligne CSV: {row}")

def process_csv(filename):
    with open(filename, 'r') as file:
        # Utilisation de DictReader pour lire le CSV en tant que dictionnaire
        reader = csv.DictReader(file)
        for row in reader:
            try:
                # Indexer chaque ligne dans Elasticsearch
                es.index(index="logs-csv-index", body=row)
            except Exception as e:
                print(f"Erreur lors de l'indexation dans Elasticsearch : {e}")
        print(f"Fichier CSV importé dans Elasticsearch : {filename}")

    # Rafraîchir l'index pour que les données soient immédiatement disponibles
    es.indices.refresh(index="csv2-2024.12.12")
    print("Index rafraîchi dans Elasticsearch.")


@app.route('/search', methods=['GET', 'POST'])
def search_logs():
    results = []
    query = ""
    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            # Elasticsearch search query
            es_query = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["LineId", "Label", "Timestamp", "Date", "User", "Month", "Day", "Time", "Location", "Component", "PID", "Content", "EventId", "EventTemplate"]
                    }
                }
            }
            response = es.search(index="csv2-2024.12.12", body=es_query)
            results = response.get('hits', {}).get('hits', [])

            # Remove duplicates based on 'LineId'
            results = {result['_source']['LineId'] : result for result in results}.values()

    return render_template('search.html', results=results, query=query)

@app.route('/search2', methods=['GET', 'POST'])
def search_logs2():
    results = []
    query = ""
    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            # Elasticsearch search query
            es_query = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["log.level", "Message"]
                    }
                }
            }
            response = es.search(index="json2-2024.12.12", body=es_query)
            results = response.get('hits', {}).get('hits', [])

            # Remove duplicates based on 'Timestamp' (or any unique field if needed)
            #results = {result['_source']['Timestamp']: result for result in results}.values()

    return render_template('search2.html', results=results, query=query)



if __name__ == '__main__':
    app.run(debug=True)