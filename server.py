from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import paramiko
import pymysql.cursors
import logging
from pymodbus.client import ModbusTcpClient
from pymodbus.client import ModbusSerialClient
from flask import jsonify
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# SSH ve Veritabanı bilgileri
SSH_HOST = os.getenv("SSH_HOST", "localhost")
SSH_USER = os.getenv("SSH_USER", "root")
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "123")

def ssh_connect(ip, username, password):
    """SSH ile IP'ye bağlanır ve doğrular."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=username, password=password)
        client.close()
        return True
    except Exception as e:
        return f"SSH Hatası: {str(e)}"
    
def get_connected_devices():
    """Wi-Fi'ye bağlı cihazların IP adreslerini ve MAC adreslerini listele"""
    result = os.popen("arp -a").read()
    devices = []

    for line in result.splitlines():
        if "dynamic" in line or "static" in line:
            parts = line.split()
            if len(parts) >= 3:
                ip_address = parts[0]
                mac_address = parts[1]

                if mac_address.startswith("02") or mac_address.startswith("12"):
                    devices.append(ip_address)

    return devices

def fetch_databases(ip):
    """SSH ile bağlanıp uzak cihazda bulunan veritabanlarını getirmek için metod"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username=SSH_USER, password=SSH_PASSWORD)

        # Uzak MySQL veritabanlarını listeleme komutu
        command = 'mysql -u root -p{} -e "SHOW DATABASES;"'.format(SSH_PASSWORD)
        stdin, stdout, stderr = ssh.exec_command(command)

        output = stdout.read().decode()
        ssh.close()

        databases = output.splitlines()
        return databases[1:]  # İlk satır başlıktır, onu atlıyoruz
    except Exception as e:
        return [[f"Hata: {str(e)}"]]

def fetch_tables(ip, db_name):
    """Seçilen veritabanındaki tabloları getir"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username=SSH_USER, password=SSH_PASSWORD)

        # Seçilen veritabanındaki tabloları listeleme komutu
        command = 'mysql -u root -p{} -D {} -e "SHOW TABLES;"'.format(SSH_PASSWORD, db_name)
        stdin, stdout, stderr = ssh.exec_command(command)

        output = stdout.read().decode()
        ssh.close()

        tables = output.splitlines()
        return tables[1:]  # İlk satır başlıktır, onu atlıyoruz
    except Exception as e:
        return [[f"Hata: {str(e)}"]]

def fetch_data_from_table(ip, db_name, table_name):
    """Seçilen tablodan verileri getir"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username=SSH_USER, password=SSH_PASSWORD)

        # Seçilen tablodan veri alma komutu
        command = 'mysql -u root -p{} -D {} -e "SELECT * FROM {};"'.format(SSH_PASSWORD, db_name, table_name)
        stdin, stdout, stderr = ssh.exec_command(command)

        output = stdout.read().decode()
        ssh.close()

        # Satırlara ayır ve başlıkları dahil et
        rows = []
        lines = output.splitlines()
        
        if len(lines) > 0:
            # İlk satır başlıkları (sütun adlarını) içeriyor
            rows.append(lines[0].split("\t"))
            if len(lines) == 1:
                # Tablo sadece başlıklardan oluşuyorsa (veri yoksa)
                return {"is_empty": True, "data": rows}
        
        # Veriler ekleniyor
        for line in lines[1:]:
            rows.append(line.split("\t"))
        
        return {"is_empty": False, "data": rows}
    except Exception as e:
        return {"is_empty": False, "data": [[f"Hata: {str(e)}"]]}
    
def restart_modem(ip):
    """Restart the modem via SSH."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username=SSH_USER, password=SSH_PASSWORD)

        # Restart modem command (modify as needed)
        command = "reboot"  # or the specific command to restart the modem
        ssh.exec_command(command)
        ssh.close()

        logging.info(f"Modem restarted at IP: {ip}")
    except Exception as e:
        logging.error(f"Error restarting modem: {str(e)}")
        
def fetch_equipment_data(ip):
    """IoT veritabanındaki 'equipments' tablosunu getir."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username=SSH_USER, password=SSH_PASSWORD)

        command = 'mysql -u root -p{} -D iot -e "SELECT * FROM equipments;"'.format(SSH_PASSWORD)
        stdin, stdout, stderr = ssh.exec_command(command)

        output = stdout.read().decode()
        ssh.close()

        lines = output.splitlines()
        rows = []
        
        if len(lines) > 0:
            rows.append(lines[0].split("\t"))
        
        if len(lines) > 1:
            for line in lines[1:]:
                rows.append(line.split("\t"))
            return {"is_empty": False, "data": rows}
        else:
            return {"is_empty": True, "data": None}
    except Exception as e:
        return {"is_empty": False, "data": [[f"Hata: {str(e)}"]]}

def fetch_modems_data(ip):
    """Fetch the 'modems' table data from the deiot database."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username=SSH_USER, password=SSH_PASSWORD)

        command = 'mysql -u root -p{} -D iot -e "SELECT * FROM modems;"'.format(SSH_PASSWORD)
        stdin, stdout, stderr = ssh.exec_command(command)

        output = stdout.read().decode()
        ssh.close()

        lines = output.splitlines()
        rows = []

        if len(lines) > 0:
            rows.append(lines[0].split("\t"))
        
        if len(lines) > 1:
            for line in lines[1:]:
                rows.append(line.split("\t"))
            return {"is_empty": False, "data": rows}
        else:
            return {"is_empty": True, "data": None}
    except Exception as e:
        return {"is_empty": False, "data": [[f"Error: {str(e)}"]]}

def read_modbus_data(device_port, slave_id, register_address, baudrate, count=1, stopbits=1):
    """Modbus cihazından veri okur."""
    try:
        client = ModbusSerialClient(
            method='rtu',
            port=device_port,
            baudrate=baudrate, 
            stopbits=stopbits, 
            bytesize=8,
            parity='N',
            timeout=1
        )
        
        if not client.connect():
            raise Exception(f"Modbus cihazına bağlanılamadı: {device_port}")
        
        response = client.read_holding_registers(address=register_address, count=count, unit=slave_id)
        
        if response.isError():
            raise Exception(f"Modbus hatası: {response}")
        
        # Kontrol ekleyin: response.registers None olabilir
        if response.registers is None:
            raise Exception(f"Veri alınamadı, response.registers None.")
        
        client.close()
        return response.registers  # Kayıt değerleri
    except Exception as e:
        return f"Hata: {str(e)}"

def scan_modbus_devices(device_port, slave_id=1, start_address=1, end_address=20):
    data = {}
    for address in range(start_address, end_address + 1):
        try:
            value = read_modbus_data(device_port, slave_id, address)
            data[address] = value if "Hata" not in value else None
        except Exception as e:
            data[address] = f"Hata: {str(e)}"
    return data

@app.route("/", methods=["GET", "POST"])
def index():
    modbus_data = None
    device_port = request.form.get("device_port")
    start_address = int(request.form.get("start_address", 0))
    end_address = int(request.form.get("end_address", 10))
    slave_id = int(request.form.get("slave_id", 1))

    devices = get_connected_devices()
    fetched_data = None
    databases = None
    tables = None
    is_empty = None

    selected_ip = request.form.get("selected_ip")
    selected_db = request.form.get("selected_db")
    selected_table = request.form.get("selected_table")

    # Check for button presses
    if request.method == "POST":
        if "restart_modem" in request.form:
            # Call modem restart logic
            restart_modem(selected_ip)
        elif "fetch_equipment_data" in request.form:
            # Fetch equipment data
            equipment_data = fetch_equipment_data(selected_ip)
            fetched_data = equipment_data["data"]
            is_empty = equipment_data["is_empty"]
        elif "fetch_modems_data" in request.form:
            # Fetch modems data
            modems_data = fetch_modems_data(selected_ip)
            fetched_data = modems_data["data"]
            is_empty = modems_data["is_empty"]
            
    if selected_table:
        # Seçilen tabloyu getir
        table_data = fetch_data_from_table(selected_ip, selected_db, selected_table)
        fetched_data = table_data["data"]
        is_empty = table_data["is_empty"]

    if request.method == "POST" and device_port:
        modbus_data = scan_modbus_devices(device_port, start_address, end_address)


    if request.method == 'POST':
        selected_ip = request.form.get("selected_ip")

        if not selected_ip:
            return jsonify({"error": "Lütfen bir IP seçin!"}), 400

        if request.form.get("action") == "modbus":
            ssh_result = ssh_connect(selected_ip, SSH_USER, SSH_PASSWORD)
            if ssh_result is not True:
                return jsonify({"error": ssh_result}), 400

            # Modbus bilgilerini al
            modbus_params = {
                "port": request.form.get("device_port"),
                "baudrate": int(request.form.get("baudrate")),
                "parity": request.form.get("parity"),
                "stopbits": int(request.form.get("stopbits")),
                "start_address": int(request.form.get("start_address")),
                "end_address": int(request.form.get("end_address")),
                "slave_id": int(request.form.get("slave_id"))
            }

            try:
                client = ModbusTcpClient(selected_ip)
                client.connect()
                response = client.read_holding_registers(
                    address=modbus_params["start_address"],
                    count=modbus_params["end_address"] - modbus_params["start_address"] + 1,
                    unit=modbus_params["slave_id"]
                )
                client.close()

                modbus_data = {
                    i + modbus_params["start_address"]: reg
                    for i, reg in enumerate(response.registers)
                }

            except Exception as e:
                modbus_data = f"Modbus Hatası: {str(e)}"

    # Sayfayı her durumda render et
    return render_template(
        "home_page.html",
        devices=devices,
        fetched_data=fetched_data,
        databases=databases,
        tables=tables,
        selected_ip=selected_ip,
        selected_db=selected_db,
        selected_table=selected_table,
        is_empty=is_empty,
        modbus_data=modbus_data
    )

@app.route("/fetch-modbus-data", methods=["POST"])
def fetch_modbus_data_route():
    try:
        # Formdan gelen veriler
        device_port = request.form.get("device_port")
        baudrate = int(request.form.get("baudrate", 9600))
        stopbits = int(request.form.get("stopbits", 1))
        slave_id = int(request.form.get("slave_id", 1))
        start_address = int(request.form.get("start_address", 1))
        end_address = int(request.form.get("end_address", 20))

        # Modbus verisini al
        modbus_data = scan_modbus_devices(device_port, slave_id)

        return render_template("home_page.html", modbus_data=modbus_data)

    except Exception as e:
        return f"Hata: {str(e)}"

@app.route("/update-row", methods=["GET", "POST"])
def update_row():
    if request.method == "GET":
        # URL'den parametreleri al
        ip = request.args.get("ip")
        db_name = request.args.get("db_name")
        table_name = request.args.get("table_name")
        row_data = request.args.get("row_data", "").split("|")
        columns = request.args.get("columns", "").split("|")
    
        # Güncelleme formunu render et
        return render_template(
            "update.html",
            ip=ip,
            db_name=db_name,
            table_name=table_name,
            row_data=row_data,
            columns=columns
        )
    
    if request.method == "POST":
        # POST isteği ile gelen veriyi işle
        ip = request.form.get("ip")
        db_name = request.form.get("db_name")
        table_name = request.form.get("table_name")
        row_data = request.form.getlist("row_data[]")
        columns = request.form.getlist("columns[]")

        try:
            set_clause = ", ".join([f"{col}='{val}'" for col, val in zip(columns, row_data)])
            primary_key = columns[0]  # İlk sütunun primary key olduğunu varsayıyoruz
            primary_value = row_data[0]

            command = (
                f"mysql -u root -p{SSH_PASSWORD} -D {db_name} -e "
                f"\"UPDATE {table_name} SET {set_clause} WHERE {primary_key}='{primary_value}';\""
            )

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, username=SSH_USER, password=SSH_PASSWORD)

            stdin, stdout, stderr = ssh.exec_command(command)
            ssh.close()

            # Başarıyla tamamlandıktan sonra yönlendirme
            return redirect(url_for("index"))
        except Exception as e:
            return {"success": False, "message": str(e)}, 500
        
@app.route("/delete-selected-rows", methods=["POST"])
def delete_selected_rows():
    try:
        # Formdan gelen veriyi al
        selected_rows = request.form.getlist("selected_rows")
        ip = request.args.get("ip")
        db_name = request.args.get("db_name")
        table_name = request.args.get("table_name")

        # Eğer hiçbir satır seçilmemişse hata döndür
        if not selected_rows:
            return redirect(url_for("index"))

        # Silme komutunu oluştur
        for row_id in selected_rows:
            command = (
                f"mysql -u root -p{SSH_PASSWORD} -D {db_name} -e "
                f"\"DELETE FROM {table_name} WHERE id='{row_id}';\""
            )

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, username=SSH_USER, password=SSH_PASSWORD)

            # Silme komutunu çalıştır
            ssh.exec_command(command)
            ssh.close()

        return redirect(url_for("index"))
    except Exception as e:
        return {"success": False, "message": str(e)}, 500
      
@app.context_processor
def utility_processor():
    return dict(zip=zip)

if __name__ == "__main__":
    app.run(debug=True, port=8080)

