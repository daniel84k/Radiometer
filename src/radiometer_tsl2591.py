import argparse
import datetime
import os
import signal
import time
import numpy as np
import board
import busio
from adafruit_extended_bus import ExtendedI2C as I2C
import adafruit_tsl2591
import adafruit_mlx90614
import adafruit_bme280
from adafruit_bme280 import basic as adafruit_bme280

DATA_DIR = os.path.expanduser('~/radiometer_data/')
GUARD_TIME = 2  # Czas oczekiwania po zmianie wzmocnienia sensora
DEFAULT_I2C_ADDRESS = adafruit_tsl2591._TSL2591_ADDR  # Domyślny adres I2C dla sensora TSL2591

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

class RadiometerDataLogger:
    def __init__(self, name=""):
        self.name = name
        if name:
            self.name = "_" + name + "_"
        os.makedirs(DATA_DIR, exist_ok=True)
        self.filename = "R" + self.name + datetime.datetime.now().strftime("%Y%m%d") + ".csv"

    def log_data(self, obs_time, lux_value, vis_level, ir_level, again, atime, temp, humidity, pressure, dew_point, mlx_temp):
        try:
            filename = "R" + self.name + obs_time.strftime("%Y%m%d") + ".csv"
            if filename != self.filename:
                self.filename = filename

            with open(DATA_DIR + self.filename, "a") as file:
                out_string = '{0:s} {1:.9f} {2:1f} {3:1f} {4:.1f} {5:.1f} {6:.2f} {7:.2f} {8:.2f} {9:.2f} {10:.2f}\n'.format(
                    obs_time.strftime("%Y/%m/%d %H:%M:%S.%f")[:-3], lux_value, vis_level, ir_level, again, atime, temp, humidity, pressure, dew_point, mlx_temp)
                file.write(out_string)

        except Exception as e:
            print("Błąd podczas zapisu danych: ", e)

class adafruit_tsl2591_extended(adafruit_tsl2591.TSL2591):
    def adjust_gain(self):
        channel_0, _ = self.raw_luminosity
        current_gain = self.gain

        if channel_0 > 30000:  # Zbliżanie się do wysycenia
            if current_gain == adafruit_tsl2591.GAIN_MAX:
#                new_gain = adafruit_tsl2591.GAIN_HIGH
#            elif current_gain == adafruit_tsl2591.GAIN_HIGH:
                new_gain = adafruit_tsl2591.GAIN_MED
            elif current_gain == adafruit_tsl2591.GAIN_MED:
                new_gain = adafruit_tsl2591.GAIN_LOW
            else:
                new_gain = current_gain  # Pozostaw bez zmian
        elif channel_0 < 1000:  # Zaciemnianie
            if current_gain == adafruit_tsl2591.GAIN_LOW:
                new_gain = adafruit_tsl2591.GAIN_MED
            elif current_gain == adafruit_tsl2591.GAIN_MED:
#               new_gain = adafruit_tsl2591.GAIN_HIGH
#            elif current_gain == adafruit_tsl2591.GAIN_HIGH:
                new_gain = adafruit_tsl2591.GAIN_MAX
            else:
                new_gain = current_gain  # Pozostaw bez zmian
        else:
            new_gain = current_gain  # Pozostaw bez zmian

        if new_gain != current_gain:
            self.gain = new_gain
            time.sleep(GUARD_TIME)  # Odczekaj po zmianie wzmocnienia

    def get_light_levels(self, disable_exception=False):
        self.adjust_gain()
        time.sleep(GUARD_TIME)
        channel_0, channel_1 = self.raw_luminosity
        atime = 100.0 * self._integration_time + 100.0
        if self._integration_time == adafruit_tsl2591.INTEGRATIONTIME_100MS:
            max_counts = adafruit_tsl2591._TSL2591_MAX_COUNT_100MS
        else:
            max_counts = adafruit_tsl2591._TSL2591_MAX_COUNT

        if channel_0 >= max_counts or channel_1 >= max_counts:
            message = "Overflow reading light channels!"
            if not disable_exception:
                raise RuntimeError(message)

        again = 1.0  # Domyślne wzmocnienie dla GAIN_LOW
        if self._gain == adafruit_tsl2591.GAIN_LOW:
            again = 1.0
        elif self._gain == adafruit_tsl2591.GAIN_MED:
            again = 25.0
#        elif self._gain == adafruit_tsl2591.GAIN_HIGH:
#            again = 428.0  # lub inna odpowiednia wartość dla GAIN_HIGH
        elif self._gain == adafruit_tsl2591.GAIN_MAX:
            again = 9876.0  # lub inna odpowiednia wartość dla GAIN_MAX

        cpl = (atime * again) / adafruit_tsl2591._TSL2591_LUX_DF
        lux1 = (channel_0 - (adafruit_tsl2591._TSL2591_LUX_COEFB * channel_1)) / cpl
        lux2 = ((adafruit_tsl2591._TSL2591_LUX_COEFC * channel_0) - (adafruit_tsl2591._TSL2591_LUX_COEFD * channel_1)) / cpl
        lux = max(lux1, lux2)

        # Przeliczanie wartości widzialnego światła (vis) i podczerwieni (ir) uwzględniając wzmocnienie
        vis_level = channel_0
        ir_level = channel_1

        return lux, vis_level, ir_level, again, atime


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='Acquire light levels')
    ap.add_argument("-a", "--address", type=lambda x: int(x, 0), default=DEFAULT_I2C_ADDRESS, help="Set the light sensor's i2c address. Default is " + hex(DEFAULT_I2C_ADDRESS))
    ap.add_argument("-b", "--bus", type=int, default=1, help="Specify the i2c bus used for connecting the sensor. Default is bus 1")
    gain_choices = ["max", "high", "med", "low", "auto"]
    ap.add_argument("-g", "--gain", choices=gain_choices, type=str, default="auto", help="Gain level for the light sensor. Default is auto")
    ap.add_argument("-m", "--multiplexer", type=int, default=None, help="Connect to the i2c sensor via an adafruit TCA9548A multiplexer using the number of the multiplexer channel e.g. 0-7")
    ap.add_argument("-n", "--name", type=str, default="", help="Optional name of the sensor for the output file name. Default is no name")
    ap.add_argument("-s", "--sqm", action='store_true', help="Take hourly SQM measurements")
    ap.add_argument("-v", "--verbose", action='store_true', help="Verbose output to terminal")
    args = vars(ap.parse_args())

    signal.signal(signal.SIGINT, signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)


    i2c = I2C(args['bus'])
    mlx = adafruit_mlx90614.MLX90614(i2c)
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

    if args['multiplexer'] is not None:
        import adafruit_tca9548a
        tca = adafruit_tca9548a.TCA9548A(i2c)
        sensor = adafruit_tsl2591_extended(tca[args['multiplexer']])
    else:
        sensor = adafruit_tsl2591_extended(i2c, address=args['address'])

    radiometer_data_logger = RadiometerDataLogger(name=args['name'])

    while True:
        try:
            time_stamp = datetime.datetime.now()
            lux, vis_level, ir_level, again, atime = sensor.get_light_levels()
            temp, wilgotnosc, cisnienie, punkt_rosy = read_bme280_data(bme280)
            mlx_temp = mlx.object_temperature
            radiometer_data_logger.log_data(time_stamp, lux, vis_level, ir_level, again, atime, temp, wilgotnosc, cisnienie, punkt_rosy, mlx_temp)
            if args['verbose']:
                print(f"Log: {time_stamp}, Lux: {lux}, Temp: {temp}, Gain: {again}")

        except RuntimeError as e:
            print("Błąd sensora: ", e)
        except Exception as e:
            print("Nieoczekiwany błąd: ", e)

        time.sleep(58)  # Odczekaj 30 sekund przed rozpoczęciem kolejnej iteracji
