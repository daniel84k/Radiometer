import argparse
import datetime
import os
import signal
import threading
import time
import numpy as np
import syslog
import board
import busio
from adafruit_extended_bus import ExtendedI2C as I2C
import adafruit_tsl2591
import adafruit_bme280
from adafruit_bme280 import basic as adafruit_bme280

DATA_DIR = os.path.expanduser('~/radiometer_data/')
GUARD_TIME = 30
DEFAULT_I2C_ADDRESS = adafruit_tsl2591._TSL2591_ADDR

def signalHandler(signum, frame):
    os._exit(0)

def read_bme280_data(sensor):
    temperatura = sensor.temperature
    wilgotnosc = sensor.humidity
    cisnienie = sensor.pressure
    punkt_rosy = calculate_dew_point(temperatura, wilgotnosc)
    return temperatura, wilgotnosc, cisnienie, punkt_rosy

def calculate_dew_point(temperatura, wilgotnosc):
    b = 17.62
    c = 243.12
    gamma = (b * temperatura) / (c + temperatura) + np.log(wilgotnosc / 100.0)
    punkt_rosy = (c * gamma) / (b - gamma)
    return punkt_rosy

class adafruit_tsl2591_extended(adafruit_tsl2591.TSL2591):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dostosowane wartości progowe
        self.min_counts_threshold = 1
        self.max_counts_threshold = 40000  # Możesz dostosować tę wartość do swoich warunków
        self.auto_gain = True

    def adjust_gain(self):
        raw_luminosity = self.raw_luminosity
        if raw_luminosity is None:
            print("Błąd odczytu surowej luminancji")
            return False

        channel_0, channel_1 = raw_luminosity
        print(f"Surowa luminancja - Kanał 0: {channel_0}, Kanał 1: {channel_1}")
        if channel_0 >= self.max_counts_threshold or channel_1 >= self.max_counts_threshold:
            return False  # Nie zmieniaj gain w tym przypadku
        elif channel_0 < self.min_counts_threshold and channel_1 < self.min_counts_threshold:
            return False  # Nie zmieniaj gain w tym przypadku

        return True

    def get_light_levels(self):
        # Usuń ustawianie wzmocnienia (gain) w tym miejscu
        if self.auto_gain and not self.adjust_gain():
            print("Nie można dostosować Gain")
            return None

        raw_luminosity = self.raw_luminosity
        if raw_luminosity is None:
            print("Błąd odczytu surowej luminancji")
            return None

        channel_0, channel_1 = raw_luminosity
        atime = 100.0 * self._integration_time + 100.0
        cpl = (atime * self._gain) / adafruit_tsl2591._TSL2591_LUX_DF
        if cpl == 0:
            print("Dzielenie przez zero! Wartość CPL wynosi 0.")
            return None

        lux1 = (channel_0 - (adafruit_tsl2591._TSL2591_LUX_COEFB * channel_1)) / cpl
        lux2 = ((adafruit_tsl2591._TSL2591_LUX_COEFC * channel_0) - (adafruit_tsl2591._TSL2591_LUX_COEFD * channel_1)) / cpl
        return max(lux1, lux2), channel_0, channel_1, self._gain, atime

class RadiometerDataLogger:
    def __init__(self, name=""):
        self.name = name
        if name:
            self.name = "_" + name + "_"
        os.makedirs(DATA_DIR, exist_ok=True)
        self.filename = "R" + self.name + datetime.datetime.now().strftime("%Y%m%d") + ".csv"

    def log_data(self, obs_time, lux_value, vis_level, ir_level, again, atime, temp, humidity, pressure, dew_point):
        try:
            filename = "R" + self.name + obs_time.strftime("%Y%m%d") + ".csv"
            if filename != self.filename:
                self.filename = filename

            with open(DATA_DIR + self.filename, "a") as file:
                out_string = '{0:s} {1:.9f} {2:d} {3:d} {4:.1f} {5:.1f} {6:.2f} {7:.2f} {8:.2f} {9:.2f}\n'.format(
                    obs_time.strftime("%Y/%m/%d %H:%M:%S.%f")[:-3], lux_value, vis_level, ir_level, again, atime, temp, humidity, pressure, dew_point)
                file.write(out_string)

        except Exception as e:
            print("Błąd podczas zapisu danych: ", e)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='Acquire light levels')
    ap.add_argument("-a", "--address", type=lambda x: int(x, 0), default=DEFAULT_I2C_ADDRESS, help="Set the light sensor's i2c address. Default is " + hex(DEFAULT_I2C_ADDRESS))
    ap.add_argument("-b", "--bus", type=int, default=1, help="Specify the i2c bus used for connecting the sensor e.g. 3 if /dev/i2c-3 has been created using dtoverlay. Default is bus 1")
    ap.add_argument("-n", "--name", type=str, default="", help="Optional name of the sensor for the output file name. Default is no name")
    args = vars(ap.parse_args())

    signal.signal(signal.SIGINT, signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)

    i2c = I2C(args['bus'])
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
    sensor = adafruit_tsl2591_extended(i2c, address=args['address'])
    sensor.enable()
    sensor.gain = adafruit_tsl2591.GAIN_MED
    sensor.integration_time = adafruit_tsl2591.INTEGRATIONTIME_100MS

    radiometer_data_logger = RadiometerDataLogger(name=args['name'])

    while True:
        try:
            time_stamp = datetime.datetime.now()
            lux_info = sensor.get_light_levels()
            if lux_info is not None:
                lux, vis_level, ir_level, again, atime = lux_info
                temp, wilgotnosc, cisnienie, punkt_rosy = read_bme280_data(bme280)
                radiometer_data_logger.log_data(time_stamp, lux, vis_level, ir_level, again, atime, temp, wilgotnosc, cisnienie, punkt_rosy)
                print(f"Log: {time_stamp}, Lux: {lux}, Temp: {temp}, Gain: {again}")
            else:
                print("Nie można odczytać poziomu oświetlenia")

        except RuntimeError as e:
            print("Błąd sensora: ", e)
        except Exception as e:
            print("Nieoczekiwany błąd: ", e)

        time.sleep(30)
