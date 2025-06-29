from flask import Flask, render_template
import sqlite3
import json

app = Flask(__name__)

def get_data(tabla):
    conn = sqlite3.connect('timder.db')
    c = conn.cursor()
    c.execute(f"SELECT * FROM {tabla}")
    data = []
    for row in c.fetchall():
        row = list(row)
        if tabla == 'swipes' and len(row) > 4:
            try:
                row[4] = json.loads(row[4]) if row[4] else []
            except json.JSONDecodeError:
                row[4] = []
        data.append(row)
    conn.close()
    return data

@app.route('/')
def index():
    swipes = get_data('swipes')
    logs = get_data('logs')
    return render_template('index.html', swipes=swipes, logs=logs)

if __name__ == '__main__':
    app.run(debug=True)
