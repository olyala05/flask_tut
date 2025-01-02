from flask import Flask, render_template, request, redirect, url_for
import os
import paramiko
import pymysql.cursors
import logging
logging.basicConfig(level=logging.DEBUG)
from pymodbus.client import ModbusTcpClient
from pymodbus.client import ModbusSerialClient

app = Flask(__name__)

# SSH ve Veritabanı bilgileri
SSH_HOST = os.getenv("SSH_HOST", "localhost")
SSH_USER = os.getenv("SSH_USER", "root")
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "123")

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
        
        # Veriler (eğer varsa) ekleniyor
        for line in lines[1:]:
            rows.append(line.split("\t"))
        
        return rows
    except Exception as e:
        return [[f"Hata: {str(e)}"]]

def modem_files(ip):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username=SSH_USER, password=SSH_PASSWORD)

        # Modem dosyalarını listeleme komutu
        command = "ls"
        stdin, stdout, stderr = ssh.exec_command(command)

        output = stdout.read().decode("utf-8")
        error_output = stderr.read().decode("utf-8")
        ssh.close()

        if error_output:
            print(f"Hata: {error_output}")
            raise Exception(f"Komut hatası: {error_output}")

        files = output.splitlines()
        return files
    except Exception as e:
        print(f"Hata: {str(e)}")
        return [[f"Hata: {str(e)}"]]
    
def modbus_scan(ip, port=502, start_address=0, end_address=100):
    """Modbus cihazında belirtilen adres aralığını tarar."""
    try:
        client = ModbusTcpClient(host=ip, port=port)
        # client = ModbusTcpClient(ip, port)
        if not client.connect():
            return {"status": "error", "message": "Modbus cihazına bağlanılamadı."}
        
        results = []
        for address in range(start_address, end_address):
            try:
                response = client.read_holding_registers(address, 1, unit=1)
                if not response.isError():
                    results.append({"address": address, "value": response.registers[0]})
            except Exception as e:
                continue  # Hatalı adresleri atla demek 
        
        client.close()
        return {"status": "success", "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
    """Fetch equipment data from the IoT database."""
    try:
        connection = pymysql.connect(
            host=ip,
            user=SSH_USER,
            password=SSH_PASSWORD,
            database="iot",
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM equipments")
            result = cursor.fetchall()
            return result
    except Exception as e:
        logging.error(f"Error fetching equipments data: {str(e)}")
        logging.debug(f"Connecting to database on IP: {ip}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    devices = get_connected_devices()
    fetched_data = None
    databases = None
    tables = None
    modem_files_result = None 

    selected_ip = request.form.get("selected_ip")
    selected_db = request.form.get("selected_db")
    selected_table = request.form.get("selected_table")

    # Check for button presses
    if request.method == "POST":
        if "restart_modem" in request.form:
            # Call modem restart logic
            restart_modem(selected_ip)
        elif "fetch_equipment_data" in request.form:
            # Call function to fetch data from the IoT database
            fetched_data = fetch_equipment_data(selected_ip)

    if selected_ip:
        # Seçilen IP için veritabanlarını al
        databases = fetch_databases(selected_ip)
        modem_files_result = modem_files(selected_ip)  # Call the function here
    if selected_db:
        # Seçilen veritabanı için tabloları al
        tables = fetch_tables(selected_ip, selected_db)
    if selected_table:
        # Seçilen tabloyu getir
        fetched_data = fetch_data_from_table(selected_ip, selected_db, selected_table)

    return render_template(
        "home_page.html", 
        devices=devices, 
        fetched_data=fetched_data, 
        databases=databases, 
        tables=tables, 
        selected_ip=selected_ip, 
        selected_db=selected_db, 
        selected_table=selected_table,
        modem_files=modem_files_result  # Use the renamed variable
    )

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
      
@app.route("/delete-row", methods=["POST"])
def delete_row():
    try:
        data = request.get_json()
        row_id = data.get('row_id')
        ip = request.args.get("ip")
        db_name = request.args.get("db_name")
        table_name = request.args.get("table_name")

        if not row_id:
            return {"success": False, "message": "Satır ID'si sağlanmadı"}, 400

        # Silme komutunu oluştur
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

        return {"success": True}, 200
    except Exception as e:
        return {"success": False, "message": str(e)}, 500

@app.route("/modbus-scan", methods=["POST"])
def modbus_scan_route():
    ip = request.form.get("ip")
    start_address = int(request.form.get("start_address", 0))
    end_address = int(request.form.get("end_address", 100))

    result = modbus_scan(ip, start_address=start_address, end_address=end_address)
    return render_template("modbus_scan.html", result=result)

@app.context_processor
def utility_processor():
    return dict(zip=zip)

if __name__ == "__main__":
    app.run(debug=True, port=8080)

