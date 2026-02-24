from flask import Flask, render_template, request, redirect, jsonify
import serial
import serial.tools.list_ports
import threading
import csv
from datetime import datetime
import os
import tkinter as tk
from tkinter import filedialog
import time
import webbrowser

app = Flask(__name__)

ser = None
latest_temp = "--"
data_log = []
serial_lines = []
log_file_path = None
logging_enabled = False
connection_status = "Not Connected"

# -------- Get Available COM Ports --------
def get_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

# -------- Serial Reader Thread --------
def read_serial():
    global latest_temp, ser, data_log, serial_lines
    global log_file_path, logging_enabled, connection_status

    while True:
        if ser and ser.is_open:
            try:
                line = ser.readline().decode(errors="ignore").strip()

                if line:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    serial_lines.append(f"[{timestamp}] {line}")
                    if len(serial_lines) > 300:
                        serial_lines.pop(0)

                    if "Temperature:" in line:
                        temp = float(line.split(":")[1].strip())
                        latest_temp = temp

                        data_log.append({"time": timestamp, "temp": temp})
                        if len(data_log) > 200:
                            data_log.pop(0)

                        if logging_enabled and log_file_path:
                            file_exists = os.path.isfile(log_file_path)

                            with open(log_file_path, "a", newline="") as f:
                                writer = csv.writer(f)

                                if not file_exists:
                                    writer.writerow(["Date & Time", "Temperature (°C)"])

                                writer.writerow([timestamp, temp])

            except Exception as e:
                print("Serial Error:", e)
                try:
                    ser.close()
                except:
                    pass
                connection_status = "Not Connected"

        else:
            connection_status = "Not Connected"

        time.sleep(0.5)

# Start thread
thread = threading.Thread(target=read_serial)
thread.daemon = True
thread.start()

# -------- Home --------
@app.route("/", methods=["GET", "POST"])
def home():
    global ser, connection_status

    if request.method == "POST":
        selected_port = request.form.get("port")
        try:
            if ser and ser.is_open:
                ser.close()

            ser = serial.Serial(selected_port, 115200, timeout=1)
            connection_status = "Connected"

        except Exception as e:
            print("Serial Error:", e)
            connection_status = "Not Connected"

        return redirect("/")

    ports = get_ports()

    return render_template("index.html",
                           ports=ports,
                           temp=latest_temp,
                           status=connection_status)

# -------- Status API --------
@app.route("/status")
def get_status():
    return jsonify({"status": connection_status})

# -------- Disconnect --------
@app.route("/disconnect")
def disconnect():
    global ser, connection_status
    try:
        if ser and ser.is_open:
            ser.close()
    except:
        pass
    connection_status = "Not Connected"
    return redirect("/")

# -------- Data API --------
@app.route("/data")
def get_data():
    return jsonify(data_log)

@app.route("/serial_data")
def get_serial_data():
    return jsonify(serial_lines)

# -------- Start Logging --------
@app.route("/start_logging")
def start_logging():
    global log_file_path, logging_enabled

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder = filedialog.askdirectory()
    root.destroy()

    if not folder:
        return redirect("/")

    log_file_path = os.path.join(folder, "motor_data.csv")
    logging_enabled = True

    return redirect("/")

# -------- Stop Logging --------
@app.route("/stop_logging")
def stop_logging():
    global logging_enabled
    logging_enabled = False
    return redirect("/")

# -------- Run App --------
if __name__ == "__main__":
    # Auto open browser
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)