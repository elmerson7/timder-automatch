from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

def get_data(tabla):
    conn = sqlite3.connect('timder.db')
    c = conn.cursor()
    c.execute(f"SELECT * FROM {tabla}")
    data = c.fetchall()
    conn.close()
    return data

@app.route('/')
def index():
    swipes = get_data('swipes')
    logs = get_data('logs')
    return render_template('index.html', swipes=swipes, logs=logs)

if __name__ == '__main__':
    app.run(debug=True)
