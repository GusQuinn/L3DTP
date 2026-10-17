from flask import Flask, render_template, url_for, redirect, request
import sqlite3

app = Flask(__name__)

#Connect to the database
def get_db():
    conn = sqlite3.connect('PC.db')
    conn.row_factory = sqlite3.Row
    return conn

def parse_price(val):
    """Safely convert database price values (including text strings with commas) to float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    # Strip out dollar signs, spaces, and commas
    clean = str(val).replace('$', '').replace(',', '').strip()
    try:
        return float(clean)
    except ValueError:
        return 0.0

#Main page
@app.route('/', methods=['GET'])
def index():
    raw_budget = request.args.get('budget', '').strip()
    use = request.args.get('use', default='gaming', type=str)
    
    budget = None
    error_message = None
    selected_build = None

    if raw_budget:
        try:
            budget = float(raw_budget)
            if budget < 500:
                error_message = "Minimum recommended budget for a full build is $500."
                budget = None
        except ValueError:
            error_message = "Invalid budget amount entered. Please enter a valid number."
            budget = None


    if budget:
        try:
            conn = get_db()

            # Retrieve candidate components from all 6 tables
            cpus = conn.execute("SELECT * FROM CPU").fetchall()
            mbs = conn.execute("SELECT * FROM Motherboard").fetchall()
            gpus = conn.execute("SELECT * FROM GPU").fetchall()
            rams = conn.execute("SELECT * FROM RAM").fetchall()
            ssds = conn.execute("SELECT * FROM SSD").fetchall()
            psus = conn.execute("SELECT * FROM PSU").fetchall()
            conn.close()

            compatible_builds = []

            # Perform in-memory relational matching across tables
            for c in cpus:
                c_socket = str(c['Socket']).strip() if c['Socket'] else ''
                c_price = parse_price(c['Price'])

                for m in mbs:
                    m_socket = str(m['Socket']).strip() if m['Socket'] else ''
                    # Socket compatibility check
                    if c_socket.lower() != m_socket.lower():
                        continue

                    m_ram = str(m['RAM_Type']).strip() if m['RAM_Type'] else ''
                    m_price = parse_price(m['Price'])
                    mb_name = m['Motherboard Name'] if 'Motherboard Name' in m.keys() else m['Chipset']

                    for r in rams:
                        r_slot = str(r['DIMM _Slot']).strip() if 'DIMM _Slot' in r.keys() else str(r['RAM_Model'])
                        # RAM standard compatibility check
                        if m_ram.lower() not in r_slot.lower() and r_slot.lower() not in m_ram.lower():
                            continue

                        r_price = parse_price(r['Price'])

                        for g in gpus:
                            g_price = parse_price(g['Price'])

                            for s in ssds:
                                s_price = parse_price(s['Price'])

                                for p in psus:
                                    p_price = parse_price(p['Price'])
                                    total_price = c_price + m_price + r_price + g_price + s_price + p_price

                                    compatible_builds.append({
                                        'CPU_Model': c['CPU_Model'],
                                        'CPU_Socket': c_socket,
                                        'CPU_Price': f"{c_price:.2f}",
                                        'Chipset': mb_name,
                                        'RAM_Type': m_ram,
                                        'MB_Price': f"{m_price:.2f}",
                                        'GPU_Model': g['GPU_Model'],
                                        'GPU_Price': f"{g_price:.2f}",
                                        'RAM_Model': r['RAM_Model'],
                                        'RAM_Price': f"{r_price:.2f}",
                                        'SSD_Name': s['SSD_Name'],
                                        'SSD_Price': f"{s_price:.2f}",
                                        'PSU_Model': p['PSU_Model'],
                                        'PSU_Price': f"{p_price:.2f}",
                                        'Total_Build_Price_Num': total_price,
                                        'Total_Build_Price': f"{total_price:.2f}"
                                    })

            if compatible_builds:
                # Sort builds by price descending
                compatible_builds.sort(key=lambda x: x['Total_Build_Price_Num'], reverse=True)
                
                # Find the best build within the user's budget
                for build in compatible_builds:
                    if build['Total_Build_Price_Num'] <= budget:
                        selected_build = build
                        break

                # If budget is lower than the cheapest compatible build
                if not selected_build:
                    cheapest = min(compatible_builds, key=lambda x: x['Total_Build_Price_Num'])
                    min_p = cheapest['Total_Build_Price_Num']
                    error_message = f"Your budget of ${budget:.2f} is too low. The cheapest compatible build costs ${min_p:.2f}."
            else:
                error_message = "No compatible component combinations found in database."

        except Exception as e:
            error_message = f"System Error: {str(e)}"

    return render_template(
        'index.html', 
        budget=raw_budget, 
        selected_use=use,
        selected_build=selected_build,
        error_message=error_message
    )

#Add review submissions
@app.route('/review', methods=['POST'])
def add_review():
    name = request.form.get('reviewer_name', 'Anonymous').strip()
    rating = request.form.get('rating', type=int, default=5)
    comment = request.form.get('comments', '').strip()

    # Input validation: Ensure comments are provided
    if not comment:
        return redirect(url_for('index'))

    try:
        conn = get_db()
        # SQL INSERT query
        insert_query = """
            INSERT INTO Review (Name, Rating, Comment)
            VALUES (?, ?, ?)
        """
        conn.execute(insert_query, [name, rating, comment])
        conn.commit()  # Save changes to PC.db
        conn.close()
    except sqlite3.Error as e:
        print(f"Database insertion failed: {e}")

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)