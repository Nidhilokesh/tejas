# utils.py
import yfinance as yf
import pandas as pd

def load_stock_data(ticker, start, end):
    """
    Downloads and resamples stock data from Yahoo Finance.
    Returns a DataFrame resampled to monthly frequency.
    """
    try:
        df = yf.download(ticker, start=start, end=end)
        if df.empty:
            raise ValueError("No data found for this ticker.")
        # Flatten the DataFrame columns 
        if ticker in df.columns:
            df.columns = df.columns.droplevel(0)
        df_monthly = df.resample('ME').last()
        return df_monthly
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def create_chart_data(df, results):
    """
    Prepares chart data for frontend rendering
    """
    # Base historical data
    dates = [d.strftime('%Y-%m-%d') for d in df.index.tolist()]
        
    # Look at the actual column structure to determine access method
    close_values = None
    
    # Check more explicitly for MultiIndex or tuple columns
    if isinstance(df.columns, pd.MultiIndex):
        # Get the first ticker in the column
        ticker = df.columns.get_level_values(1)[0]
        close_values = df[('Close', ticker)].tolist()
    elif isinstance(df.columns[0], tuple):
        # Handle case where columns are tuples but not a proper MultiIndex
        close_col = next((col for col in df.columns if col[0] == 'Close'), None)
        if close_col:
            close_values = df[close_col].tolist()
        else:
            raise ValueError(f"Could not find 'Close' in columns: {df.columns}")
    else:
        # Regular single-level columns
        close_values = df['Close'].tolist()
    
    historical_data = {
        'dates': dates,
        'close': close_values,
    }
    
    # Model predictions
    model_data = {}
    for model_name, result in results.items():
        # Get the test set predictions (last 20% of data)
        split_idx = int(len(df) * 0.8)
        test_dates = dates[split_idx:]
        model_data[model_name] = {
            'dates': test_dates,
            'predictions': result['preds'],
            'actuals': result['actuals'],
            'metrics': {
                'rmse': result['rmse'],
                'r2': result['r2']
            }
        }

        print(f"Model {model_name}: Future dates: {result.get('future_dates')}, Future preds: {result.get('future_preds')}")##########
        # Add future predictions if available
        if result.get('future_dates') and result.get('future_preds'):
            model_data[model_name]['future_dates'] = result['future_dates']
            model_data[model_name]['future_preds'] = result['future_preds']
    
    return {
        'historical': historical_data,
        'models': model_data
    }