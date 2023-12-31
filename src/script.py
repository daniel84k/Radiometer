import psycopg2
from psycopg2 import OperationalError
import datetime
import time
import board
import adafruit_tsl2591
import math
import argparse
import os
import signal
import threading
import numpy as np
import syslog
from adafruit_bme280 import basic as adafruit_bme280
from adafruit_extended_bus import ExtendedI2C as I2C

# Constants
DATA_DIR = os.path.expanduser('~/radiometer_data/')
GUARD_TIME = 0.12
DEFAULT_I2C_ADDRESS = adafruit_tsl2591._TSL2591_ADDR

# Database connection function from the first script
def connect_to_database():
    try:
        connection = psycopg2.connect(
            database="monitoring",
            user="monitoring",
            password="18280088",
            host="127.0.0.1",
            port="5432"
        )
        return connection
    except OperationalError as e:
        print(f"The error '{e}' occurred")
# Insert sensor data function from the first script
def insert_sensor_data(temperature, humidity, pressure, light, dewpoint, sqm, nelm, infrared, visible, full_spectrum, datetime):
    # ... (same as in the first script)

# Calculate dew point function from the first script
def calculate_dew_point(temperature, humidity):
    # ... (same as in the first script)

# Read light sensor function from the first script
def read_light_sensor(sensor):
    # ... (same as in the first script)

# Functions from the second script (e.g., signalHandler, reset_sensor, measure_sky_brightness)
def signalHandler(signum, frame):
    # ... (same as in the second script)

# Class definitions from the second script
class RadiometerDataLogger():
    # ... (same as in the second script)

class adafruit_tsl2591_extended(adafruit_tsl2591.TSL2591):
    # ... (same as in the second script)

# Main program
if __name__ == "__main__":
    # Argument parsing from the second script
    ap = argparse.ArgumentParser(description='Acquire light levels')
    # ... (rest of the argument parsing code from the second script)
    args = vars(ap.parse_args())

    # Initialization from both scripts
    i2c = board.I2C()  # for BME280 and TSL2591
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
    bme280.sea_level_pressure = 1013.25

    sensor = adafruit_tsl2591.TSL2591(i2c)
    sensor.gain = adafruit_tsl2591.GAIN_MAX
    sensor.integration_time = adafruit_tsl2591.INTEGRATIONTIME_100MS

    radiometer_data_logger = RadiometerDataLogger(name=args['name'])

    # Main loop combining both scripts
    while True:
        # Read data from BME280
        temperature = round(bme280.temperature, 2)
        humidity = round(bme280.relative_humidity, 2)
        pressure = round(bme280.pressure, 2)
        dewpoint = round(calculate_dew_point(temperature, humidity), 2)

        # Read data from TSL2591
        light = read_light_sensor(sensor)
        sqm, nelm, infrared, visible, full_spectrum = 0, 0, 0, 0, 0  # Initialize to zero or appropriate default values

        # Logic for processing and storing light data (from the second script)
        # ... (add the logic for processing light data from the second script here)

        # Insert data into the database (from the first script)
        insert_sensor_data(temperature, humidity, pressure, light, dewpoint, sqm, nelm, infrared, visible, full_spectrum, datetime.datetime.now())

        # Sleep or wait logic
        time.sleep(60.0)  # Adjust the sleep time as needed

        # Additional functionality or exception handling can be added here

# Ensure to handle any exceptions and close resources where necessary
