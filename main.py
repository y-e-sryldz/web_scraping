from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

class MedlineScraper:
    def __init__(self):
        self.base_url = "https://scholar.google.com/scholar?hl=tr&as_sdt=0%2C5&q="

@app.route('/search-yap/<string:search>')
def search_yap(search):
    scraper = MedlineScraper()
    search = search.replace(" ","+")
    search_url = scraper.base_url + search
    response = requests.get(search_url)  # URL'ye istekte bulunun
    if response.status_code == 200:
        source = BeautifulSoup(response.content, "html.parser")  # Yanıt içeriğini ayrıştır
        results = source.find_all('div', {'id': 'gs_res_ccl_mid'})
        print(results)
    return search_url

@app.route('/',methods=['GET','POST'])
def hello_world():
    if request.method == 'POST':
        search = request.form['search']
        return redirect(url_for('search_yap', search=search))
    else:
        return render_template('main.html')

if __name__ == '__main__':
    app.run()
