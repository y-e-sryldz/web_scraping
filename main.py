from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

app = Flask(__name__)


class MedlineScraper:
    def __init__(self):
        self.base_url = "https://scholar.google.com/scholar?hl=tr&as_sdt=0%2C5&q="


def create_search_collection(search):
    connect = MongoClient(
        "mongodb+srv://nevasarac:p8VUTFzTom0ANOxC@atlascluster.gh1liqu.mongodb.net/?retryWrites=true&w=majority&appName=AtlasCluster")
    database = connect["Deneme"]
    search = search.replace("+", " ")
    if "search" not in database.list_collection_names():
        collection = database[search]
        return collection
    else:
        return database[search]


def save_search_results(results,search):
    collection = create_search_collection(search)
    for result in results:
        collection.insert_one(result)


@app.route('/search-yap/<string:search>')
def search_yap(search):
    scraper = MedlineScraper()
    search = search.replace(" ", "+")
    search_url = scraper.base_url + search
    response = requests.get(search_url)
    print(search_url)
    if response.status_code == 200:
        source = BeautifulSoup(response.content, "html.parser")
        results = source.find_all('div', {'class': 'gs_ri'})
        pdf = source.find_all('div', {'class': 'gs_or_ggsm'})

        search_results = []
        if results and pdf:
            for result, pdf_item in zip(results, pdf):
                link = result.find('a', href=True)
                link_text = link.text.strip()
                link_url = link['href']
                pdf_link = pdf_item.find('a', href=True)
                pdf_link_text = pdf_link.text.strip()
                pdf_link_url = pdf_link['href']
                search_results.append({'link_text': link_text, 'link_url': link_url, 'pdf_link_text': pdf_link_text,
                                       'pdf_link_url': pdf_link_url})

            save_search_results(search_results,search)  # Search sonuçlarını MongoDB'ye kaydet
            return render_template('search_results.html', results=search_results)
        else:
            return render_template('search_results.html', results=None)
    else:
        return render_template('search_results.html', results=None)


@app.route('/', methods=['GET', 'POST'])
def hello_world():
    if request.method == 'POST':
        search = request.form['search']
        return redirect(url_for('search_yap', search=search))
    else:
        return render_template('main.html')


if __name__ == '__main__':
    app.run()
