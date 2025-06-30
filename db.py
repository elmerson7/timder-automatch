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
    # Procesar logs para asociar swipes y contarlos
    logs_info = []
    for i, log in enumerate(logs):
        log_id = log[0]
        inicio = log[1]
        fin = logs[i+1][1] if i+1 < len(logs) else None
        # Filtrar swipes en el rango de este log
        swipes_log = []
        for s in swipes:
            ts = s[1]
            if fin:
                if ts >= inicio and ts < fin:
                    swipes_log.append(s)
            else:
                if ts >= inicio:
                    swipes_log.append(s)
        n_like = sum(1 for s in swipes_log if s[2] == 'like')
        n_nope = sum(1 for s in swipes_log if s[2] == 'nope')
        total = len(swipes_log)
        logs_info.append({
            'id': log_id,
            'inicio': inicio,
            'n_like': n_like,
            'n_nope': n_nope,
            'total': total,
            'swipes': swipes_log
        })
    return render_template('index.html', swipes=swipes, logs=logs, logs_info=logs_info)

if __name__ == '__main__':
    app.run(debug=True)
