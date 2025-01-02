from flask import Flask, render_template, request
from pymodbus.client import ModbusSerialClient
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

class ModbusHandler:
    def __init__(self, port, baudrate=9600, parity='N', stopbits=1, bytesize=8):
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize
        )
        if not self.client.connect():
            logging.error("Modbus bağlantısı kurulamadı.")
            raise ConnectionError("Modbus bağlantısı kurulamadı.")

    def scan_devices(self, start_id=1, end_id=247):
        """Cihazları belirli bir ID aralığında tarar."""
        found_devices = []
        for unit_id in range(start_id, end_id + 1):
            try:
                result = self.client.read_holding_registers(0, 1, unit=unit_id)
                if not result.isError():
                    found_devices.append(unit_id)
            except Exception as e:
                logging.debug(f"Unit ID {unit_id} hata: {e}")
        return found_devices

    def close(self):
        self.client.close()

@app.route("/", methods=["GET", "POST"])
def index():
    modbus_devices = None

    if request.method == "POST":
        modbus_port = request.form.get("modbus_port")

        if modbus_port:
            try:
                modbus_handler = ModbusHandler(port=modbus_port)
                modbus_devices = modbus_handler.scan_devices()
                modbus_handler.close()
            except Exception as e:
                logging.error(f"Modbus tarama hatası: {e}")
                modbus_devices = None

    return render_template("modbus_scan.html", modbus_devices=modbus_devices)

if __name__ == "__main__":
    app.run(debug=True, port=8080)
