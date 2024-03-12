import re
from flask import Flask, render_template, request, redirect, url_for, session
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from spellchecker import SpellChecker

app = Flask(__name__)
connect = MongoClient("mongodb+srv://nevasarac:p8VUTFzTom0ANOxC@atlascluster.gh1liqu.mongodb.net/?retryWrites=true&w=majority&appName=AtlasCluster")
database = connect["SearchResults"]
app.secret_key = 'bu_gizli_anahtar_cok_guvenli_olmali'

class MedlineScraper:
    def __init__(self):
        self.base_url = "https://scholar.google.com/scholar?hl=tr&as_sdt=0%2C5&q="


def create_search_collection(search):

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

def spell_check(text):
    spell = SpellChecker()

    # Metni kelimelere ayır
    words = text.split()

    corrected_text = ""
    for word in words:
        # Eğer kelime doğru yazılmışsa, aynı şekilde bırak
        if spell.correction(word) == word:
            corrected_text += word + " "
        else:
            # Eğer kelime yanlış yazılmışsa, doğru halini kullan
            corrected_text += spell.correction(word) + " "

    return corrected_text.strip()  # Baştaki ve sondaki gereksiz boşlukları kaldır

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

@app.route('/search', methods=['GET'])
def filtrele():
    arama = session.get('user_id')
    arama_kelimesi = arama.replace("+", " ")
    order_by = request.args.get('order_by')  # Sıralama kriteri
    ascending = int(request.args.get('ascending', 1))  # Artan veya azalan sıralama

    if arama_kelimesi is None or arama_kelimesi == '':
        # Arama ifadesi belirtilmediğinde veya boş bir ifade geldiğinde
        return "Arama ifadesi belirtilmedi veya boş."

    # Veritabanından arama sonuçlarını al
    collection = database[arama_kelimesi]  # Arama kelimesini koleksiyon adı olarak kullan
    results = list(collection.find({}))

    # Sıralama yap
    if order_by == 'yayin_tarihi_once':
        results.sort(key=lambda x: int(x.get('pdf yayımlanma tarihi', 0)), reverse=(ascending == 1))
    elif order_by == 'yayin_tarihi_sonra':
        results.sort(key=lambda x: int(x.get('pdf yayımlanma tarihi', 0)), reverse=(ascending == 0))
    elif order_by == 'alinti_sayisi_artan':
        results.sort(key=lambda x: int(x.get('pdf alinti sayisi', 0)), reverse=False)
    elif order_by == 'alinti_sayisi_azalan':
        results.sort(key=lambda x: int(x.get('pdf alinti sayisi', 0)), reverse=True)

    return render_template('search_results.html', results=results)

@app.route('/', methods=['GET', 'POST'])
def hello_world():
    if request.method == 'POST':
        search = request.form['search']
        session['user_id'] = spell_check(search)
        search = spell_check(search)
        return redirect(url_for('search_yap', search=search))
    else:
        return render_template('main.html')


if __name__ == '__main__':
    app.run()