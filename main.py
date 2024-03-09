import re

from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

app = Flask(__name__)


class MedlineScraper:
    def __init__(self):
        self.base_url = "https://scholar.google.com/scholar?hl=tr&as_sdt=0%2C5&q="


def create_search_collection(search):
    connect = MongoClient("mongodb+srv://nevasarac:p8VUTFzTom0ANOxC@atlascluster.gh1liqu.mongodb.net/?retryWrites=true&w=majority&appName=AtlasCluster")
    database = connect["SearchResults"]
    search = search.replace("+", " ")
    if search not in database.list_collection_names():  # Burada search değişkeninin içeriğini kontrol ediyoruz, search string olmalı.
        collection = database[search]
        return collection
    else:
        return database[search]


def save_search_results(results, search):
    collection = create_search_collection(search)
    existing_results = collection.find({})  # Veritabanında var olan tüm sonuçları al
    existing_urls = set(result['link url'] for result in existing_results)  # Var olan sonuçların URL'lerini bir set'e al

    new_results = []
    for result in results:
        if result['link url'] not in existing_urls:  # Eğer sonuç veritabanında yoksa
            new_results.append(result)  # Yeni sonuç listesine ekle

    if new_results:  # Eğer yeni sonuçlar varsa
        collection.insert_many(new_results)  # Yeni sonuçları veritabanına ekle
    else:
        print("Tüm sonuçlar zaten veritabanında bulunuyor.")



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
                gs_a_div = result.find('div', {'class': 'gs_a'})  # GS_A classına sahip div'i bul
                if gs_a_div:  # Eğer GS_A classına sahip bir div bulunduysa
                    numbers = re.findall(r'\d+', gs_a_div.text)  # Div içindeki sadece rakamları al
                    pdf_yayin_tarihi = ''.join(numbers)  # Alınan rakamları birleştir
                else:
                    pdf_yayin_tarihi = None
                gs_fl_div = result.find('div', {'class': 'gs_fl gs_flb'})  # gs_fl gs_flb sınıfına sahip div'i bul
                if gs_fl_div:  # Eğer gs_fl gs_flb sınıfına sahip bir div bulunduysa
                    third_a = gs_fl_div.find_all('a')[2]  # 3. <a> etiketine gir
                    pdf_alinti_sayisi_match = re.search(r'\d+',
                                                        third_a.text.strip()) if third_a else None  # Eğer 3. <a> etiketi varsa, text'ini al, yoksa None olarak ata
                    pdf_alinti_sayisi = pdf_alinti_sayisi_match.group() if pdf_alinti_sayisi_match else None
                else:
                    pdf_alinti_sayisi = None

                gs_a_div = result.find('div', {'class': 'gs_a'})  # GS_A classına sahip div'i bul
                if gs_a_div:  # Eğer GS_A classına sahip bir div bulunduysa
                    text_until_dash = gs_a_div.text.split('-')[0].strip()  # Div içindeki metni - işaretine kadar al
                    pdf_yazarlar = re.sub(r'\s+', ' ', text_until_dash)  # Birden fazla boşlukları tek boşluk yap
                else:
                    pdf_yazarlar = None

                search_results.append({'yayin adi': link_text, 'link url': link_url, 'pdf link text': pdf_link_text,
                                       'pdf link url': pdf_link_url, 'pdf yayımlanma tarihi': pdf_yayin_tarihi,
                                       'pdf alinti sayisi': pdf_alinti_sayisi, 'Yazarlar': pdf_yazarlar})

            save_search_results(search_results, search)  # Search sonuçlarını MongoDB'ye kaydet
            return render_template('search_results.html', results=search_results)
        else:
            return render_template('search_results.html', results=None)
    else:
        return render_template('search_results.html', results=None)


@app.route('/search')
def search():
    order_by = request.args.get('order_by')
    ascending = request.args.get('ascending')
    search = request.args.get('search')

    if search is None:
        return "Arama ifadesi belirtilmedi."

    # Veritabanından arama sonuçlarını al
    collection = create_search_collection(search)
    results = list(collection.find({}))

    # Alıntı sayısına göre sıralama
    if order_by == 'pdf_alinti_sayisi' and ascending:
        results.sort(key=lambda x: int(x.get('pdf alinti sayisi', 0)), reverse=(ascending.lower() == 'true'))

    return render_template('search_results.html', results=results)


@app.route('/', methods=['GET', 'POST'])
def hello_world():
    if request.method == 'POST':
        search = request.form['search']
        return redirect(url_for('search_yap', search=search))
    else:
        return render_template('main.html')


if __name__ == '__main__':
    app.run()
