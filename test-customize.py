from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    dummy_product = {
        'id': 1,
        'name': 'Test Product',
        'category': 't-shirts',
        'colors': ['White', 'Black', 'Red'],
        'sizes': ['S', 'M', 'L'],
        'price': 19.99
    }
    return render_template('customize.html', product=dummy_product, size='M')

if __name__ == '__main__':
    app.run(debug=True, port=5001)