# models.py
import numpy as np
import pandas as pd
from datetime import timedelta
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score
from math import sqrt

# Define available models
models = {
    'svr': SVR(kernel='rbf', C=1e3, gamma=0.1),
    'linear regression': LinearRegression(),
    'random forest': RandomForestRegressor(n_estimators=100, random_state=42),
    'decision tree': DecisionTreeRegressor(random_state=42)
}

def train_and_predict(model_name, df_json, future_months=None):
    """
    Trains the selected model and returns predictions, evaluation metrics,
    and optionally forecasts future prices.
    """
    #############################
    from io import StringIO
    df = pd.read_json(StringIO(df_json), orient="split")
    #############################
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[['Close']])

    n = len(scaled)
    split = int(n * 0.8)
    X_train, y_train = np.arange(split).reshape(-1,1), scaled[:split].flatten()
    X_test,  y_test  = np.arange(split, n).reshape(-1,1), scaled[split:].flatten()

    m = models[model_name]
    m.fit(X_train, y_train)

    # Predict test data
    pred_scaled = m.predict(X_test)
    preds   = scaler.inverse_transform(pred_scaled.reshape(-1,1)).flatten()
    actuals = scaler.inverse_transform(y_test.reshape(-1,1)).flatten()

    rmse = sqrt(mean_squared_error(actuals, preds))
    if len(actuals) < 2:
        r2 = None
    else:
        r2 = r2_score(actuals, preds)


    # Future forecast
    fut_dates, fut_preds = None, None
    if future_months:
        X_fut = np.arange(n, n + future_months).reshape(-1,1)
        f_scaled = m.predict(X_fut)
        fut_preds = scaler.inverse_transform(f_scaled.reshape(-1,1)).flatten()
        last_date = df.index[-1]
        fut_dates = [(last_date + timedelta(days=30*(i+1))).strftime('%Y-%m-%d') for i in range(future_months)]

    print(fut_preds,fut_dates)##############################
    return {
        'preds': preds.tolist(),
        'actuals': actuals.tolist(),
        'rmse': round(rmse, 2),
        'r2': round(r2, 2) if r2 is not None else "N/A",
        'future_dates': fut_dates,
        'future_preds': fut_preds.tolist() if fut_preds is not None else None
    }
