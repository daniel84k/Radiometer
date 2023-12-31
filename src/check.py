import pandas as pd

# Wczytaj plik CSV
df = pd.read_csv('/home/pi/radiometer_data/R20231221.csv', delimiter=' ') # Zmień delimiter jeśli potrzeba

# Wyświetl podstawowe informacje o danych
print(df.info())

# Sprawdź pierwsze kilka wierszy danych
print(df.head())

# Sprawdź, czy są jakieś brakujące wartości
print(df.isnull().sum())

# Opcjonalnie, sprawdź statystyki dla danych liczbowych
print(df.describe())
