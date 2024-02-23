from flask import Flask, render_template

app = Flask(__name__)

class MedlineScraper:
    def __init__(self):
        self.base_url = "https://scholar.google.com/scholar?hl=tr&as_sdt=0%2C5&q="

@app.route('/')
def hello_world():
    return render_template('main.html')


# main driver function
if __name__ == '__main__':
    app.run( )