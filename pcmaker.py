from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)


app.config['TEMPLATES_AUTO_RELOAD'] = True

def get_db():
    conn = sqlite3.connect('PC.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/', methods=['GET'])
def index():
    
    budget = request.args.get('budget', type=float)
    use = request.args.get('use', default='all', type=str)

    conn = get_db()
    
    
    query = 'SELECT * FROM CPU WHERE 1=1'
    params = []

    if budget is not None:
        query += ' AND Price <= ?'
        params.append(budget)

    query += ' ORDER BY Price DESC'

    cpus = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "index.html", 
        cpus=cpus, 
        budget=budget, 
        selected_use=use
    )

if __name__ == '__main__':
    app.run(debug=True)