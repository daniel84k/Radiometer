import argparse
import glob
import os
import pandas as pd
from matplotlib import pyplot as plt
from scipy.signal import find_peaks
import numpy as np

CAPTURE_DIR = os.path.expanduser('~/radiometer_data/')
PEAK_DETECTION_LUX_LIMIT = 2.0
ADAFRUIT_TSL2591_LUX_DF = 408.0

def lux_to_magarcsec2(lux):
    return -2.5 * np.log10(lux / 108000)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='Analyse radiometer data')
    ap.add_argument("file", type=str, nargs='*', help="File or directory to analyse. Default is last 2 files in the directory " + CAPTURE_DIR)
    ap.add_argument("-n", "--night", action='store_true', help="Display with night readings range")
    ap.add_argument("-l", "--linear", action='store_true', help="Display with linear scale")
    ap.add_argument("-s", "--save", action='store_true', help="Save plot")
    ap.add_argument("-p", "--prominence", type=float, default=0, help="Peak detection prominence above background. Usually 0.005 lux. Default is no peak detection")

    args = vars(ap.parse_args())

    file_names = args['file']
    night_range = args['night']
    prominence = args['prominence']
    linear_scale = args['linear']
    save_figure = args['save']

    if len(file_names) == 0:
        file_names = sorted(glob.glob(CAPTURE_DIR + "R*.csv*"))[-2:]

    print("Graphing", file_names)

    dfs = []
    for file_name in file_names:
        temp_df = pd.read_csv(file_name, sep=" ", names=["DateTime", "Lux", "Visible", "IR", "Gain", "IntTime", "Temp", "Humidity", "Pressure", "DewPoint"], parse_dates=["DateTime"])
        dfs.append(temp_df)
    df = pd.concat(dfs, ignore_index=True)

    print("Contents in csv file:")
    print(df.head())

    peaks = []
    if prominence != 0:
        peaks, properties = find_peaks(df.Lux.clip(upper=PEAK_DETECTION_LUX_LIMIT), prominence=prominence, width=(1, 60))
        print("Peaks found:", len(peaks))
        if len(peaks) < 50:
            for peak in peaks:
                print(df.DateTime[peak], df.Lux[peak])

    # Convert Lux data to NumPy array
    lux_array = df.Lux.values
    times_array = df.DateTime.to_numpy()

    # Plot Lux data
    plt.figure(figsize=(10, 6))
    plt.plot(times_array, lux_array)
    plt.xlabel('Time')
    plt.ylabel('Lux')
    if night_range:
        plt.ylim(-0.1, 0.5)
    elif not linear_scale:
        plt.yscale("log")
    if len(peaks) > 0:
        plt.plot(times_array[peaks], lux_array[peaks], marker="o", ls="", ms=3)
    plt.title('Illuminance in Lux')
    plt.grid()
    if save_figure:
        plt.savefig(os.path.splitext(file_names[-1])[0] + '_lux.png')
    plt.show()

    # Convert Lux to mag/arcsec^2 and plot
    mag_arcsec2_array = lux_to_magarcsec2(lux_array)
    plt.figure(figsize=(10, 6))
    plt.plot(times_array, mag_arcsec2_array)
    plt.xlabel('Time')
    plt.ylabel('Mag/arcsec^2')
    plt.title('Sky Brightness in Mag/arcsec^2')
    plt.grid()
    if save_figure:
        plt.savefig(os.path.splitext(file_names[-1])[0] + '_magarcsec2.png')
    plt.show()

    # Convert Visible and IR data to NumPy arrays
    visible_array = df.Visible.values
    ir_array = df.IR.values

    # Plot Visible and IR data
    plt.figure(figsize=(10, 6))
    plt.xlabel('Time')
    plt.ylabel('Count')
    if not linear_scale:
        plt.yscale("log")
    plt.plot(times_array, visible_array, label="Visible")
    plt.plot(times_array, ir_array, label="IR")
    plt.title('Raw Sensor Values')
    plt.legend(loc='upper left')
    plt.grid()
    if save_figure:
        plt.savefig(os.path.splitext(file_names[-1])[0] + '_vis_ir.png')
    plt.show()

    # Calculate average measured times between readings
    res = np.diff(times_array).astype('timedelta64[ms]').astype(np.int64)
    if len(res) > 0:
        m = res.mean()
        print("Average measured times between readings", m, "ms")
