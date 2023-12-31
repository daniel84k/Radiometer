from flask import Flask, jsonify, render_template
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)

CAPTURE_DIR = '/home/pi/radiometer_data/'

def get_filenames():
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    return [f"{CAPTURE_DIR}R{yesterday.strftime('%Y%m%d')}.csv", 
            f"{CAPTURE_DIR}R{today.strftime('%Y%m%d')}.csv"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    file_names = get_filenames()
    dfs = []
    for file_name in file_names:
        try:
            temp_df = pd.read_csv(
                file_name,
                sep=" ",  # Separator w pliku CSV
                names=["Date", "Time", "Lux", "Visible", "IR", "Gain", "IntTime", "Temp", "Humidity", "Pressure", "DewPoint", "CloudTemp"],
                parse_dates={"DateTime": ["Date", "Time"]},  # Połącz datę i godzinę w jedną kolumnę "DateTime"
                date_format="%Y/%m/%d %H:%M:%S.%f",  # Format daty i godziny
                on_bad_lines='warn'  # Wypisuj ostrzeżenia o błędnych liniach
            )

            dfs.append(temp_df)
        except FileNotFoundError:
            print(f"Nie znaleziono pliku: {file_name}")
        except pd.errors.ParserError as e:
            print(f"Błąd podczas parsowania pliku {file_name}: {e}")

    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    
    # Konwersja danych na format JSON
    json_data = df.to_dict(orient='records')
    formatted_json = [
    {
        "DateTime": row["DateTime"],  # Bezpośrednio przypisz wartość, jeśli jest to już string
        "DewPoint": row["DewPoint"],
        "Gain": row["Gain"],
        "Humidity": row["Humidity"],
        "IR": row["IR"],
        "IntTime": row["IntTime"],
        "Lux": row["Lux"],
        "Pressure": row["Pressure"],
        "Temp": row["Temp"],
        "Visible": row["Visible"],
        "CloudTemp": row["CloudTemp"]
    }
    for row in json_data
]
    
    return jsonify(formatted_json)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7777)
