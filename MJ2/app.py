# app.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import train_and_predict, models
from utils import load_stock_data, create_chart_data
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ——— Database setup ———
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import the single db instance and both user models
from auth_models import db, UserAuth, UserProfile
db.init_app(app)

# ——— Flask-Login setup ———
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return UserAuth.query.get(int(user_id))

# ——— Landing Route ———
@app.route('/')
def landing():
    # If no users exist, force signup first
    if UserAuth.query.count() == 0:
        return redirect(url_for('signup'))
    return redirect(url_for('login'))

# ——— Sign Up ———
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name     = request.form['name']
        age      = request.form['age']
        sex      = request.form['sex']
        email    = request.form['email']

        # Prevent duplicate usernames
        if UserAuth.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('signup'))

        # 1) Create and commit the credential record
        user = UserAuth(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()    # new_user.id is now assigned

        # 2) Create and commit the profile record, linking to user.id
        profile = UserProfile(
            user_id=user.id,
            name=name,
            age=int(age),
            sex=sex,
            email=email
        )
        db.session.add(profile)
        db.session.commit()

        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

# ——— Login ———
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = UserAuth.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('chat'))

        flash('Invalid credentials.', 'error')
    return render_template('login.html')

# ——— Logout ———
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ——— Chat Interface ———
@app.route('/chat')
@login_required
def chat():
    # Initialize chat state if needed
    if 'history' not in session:
        session['history'] = [
            ('bot', 'Which stock(s) are you looking for? For example: AAPL, TSLA, MSFT.')
        ]
        session['stage'] = 'ask_ticker'
    return render_template('index.html', user=current_user)

@app.route('/chat', methods=['POST'])
@login_required
def chat_post():
    msg    = request.json.get("message")
    history = session.get("history", [])
    store   = session.get("store", {})
    stage   = session.get("stage", "ask_ticker")

    def bot_response(text):
        history.append(("bot", text))

    def user_response(text):
        history.append(("you", text))

    user_response(msg)

    if stage == "ask_ticker":
        ticker = msg.strip().upper()
        store['ticker'] = ticker
        bot_response(f"Got it – looking at **{ticker}**. Now enter date range: e.g. 2023-01-01 to 2024-12-31")
        stage = "ask_dates"

    elif stage == "ask_dates":
        try:
            start, end = [d.strip() for d in msg.split("to")]
            store['start'], store['end'] = start, end
            df = load_stock_data(store['ticker'], start, end)
            if df.empty:
                bot_response("No data found for that ticker and date range.")
            else:
                store['df'] = df.to_json(orient="split")
                bot_response("Data loaded! Choose model(s): SVR, Linear Regression, Random Forest, Decision Tree—or type ALL.")
                stage = "ask_model"
        except:
            bot_response("Sorry, please use YYYY-MM-DD to YYYY-MM-DD format.")

    elif stage == "ask_model":
        choice = msg.lower()
        available = list(models.keys())

        if choice == "all":
            sel = available
        else:
            sel = [m for m in available if m in choice]

        if not sel:
            bot_response("Please pick from: " + ", ".join(available) + " or ALL.")
        else:
            store['models'] = sel
            results = {}
            for model_name in sel:
                res = train_and_predict(model_name, store['df'])  # No forecast yet
                results[model_name] = res
                bot_response(f"**{model_name.upper()}** → RMSE: {res['rmse']}, R²: {res['r2']}")
            store['results'] = results
            bot_response("Would you like to see raw data, charts, or future forecast?")
            stage = "ask_output"

    elif stage == "ask_output":
        text = msg.lower()
        from io import StringIO
        df = pd.read_json(StringIO(store['df']), orient="split")

        if isinstance(df.columns[0], tuple):
            df.columns = pd.MultiIndex.from_tuples(df.columns)

        res = store.get('results', {})

        if "raw" in text:
            bot_response("Here’s your data head:")
            bot_response(df.head().to_string())
            bot_response("Anything else? Charts or forecast?")
        elif "chart" in text:
            bot_response("Generating charts for your data. Check the chart area below!")
            bot_response("Want a future forecast?")
        elif "future" in text:
            bot_response("How many months ahead?")
            stage = "ask_horizon"
        else:
            bot_response("I can show you ‘raw data’, ‘charts’, or ‘future forecast’.")

    elif stage == "ask_horizon":
        try:
            months = int(msg)
            bot_response(f"Predicting next {months} months…")

            df_json = store['df']
            results = {}

            for model_name in store['models']:
                res = train_and_predict(model_name, df_json, future_months=months)
                results[model_name] = res

                forecast_msg = f"**{model_name.upper()} Forecast**:\n" + "\n".join(
                    [f"{date}: ${price:.2f}" for date, price in zip(res['future_dates'], res['future_preds'])]
                )
                bot_response(forecast_msg)
            # ─── store the forecasts so /chart_data can see them ─────────────────
            store['results'] = results
            session['store'] = store

            # ─── tell the front‐end to fetch & draw the chart ────────────────────
            bot_response("Generating charts for your forecast. Check the chart area below!")


            # 🔥 Store the updated results with forecasts
            store['results'] = results
            bot_response("All done! Anything else?")
            stage = "ask_output"

        except:
            bot_response("Please enter a valid number of months (e.g., 6).")

    else:
        bot_response("Oops, something went wrong. Let’s start over. Which stock are you interested in?")
        stage = "ask_ticker"

    # Update session state
    session["history"] = history
    session["store"]   = store
    session["stage"]   = stage

    return jsonify({"history": history})

# ——— Chart Data Endpoint ———
@app.route('/chart_data')
@login_required
def chart_data():
    if "store" not in session or "results" not in session["store"]:
        return jsonify({"error": "No chart data available"})

    from io import StringIO
    df = pd.read_json(StringIO(session["store"]["df"]), orient="split")

    # Flatten MultiIndex columns if needed
    if isinstance(df.columns, pd.MultiIndex):
        ticker = df.columns.get_level_values(1)[0]
        flat = pd.DataFrame()
        for col_type in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if (col_type, ticker) in df.columns:
                flat[col_type] = df[(col_type, ticker)]
        df = flat

    chart_data = create_chart_data(df, session["store"]["results"])
    return jsonify(chart_data)

# ——— App Entry Point ———
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
