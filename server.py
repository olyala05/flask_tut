from flask import Flask, render_template, request, redirect, url_for
import os
import paramiko
import pymysql.cursors

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


@app.route("/", methods=["GET", "POST"])
def index():
    devices = get_connected_devices()
    fetched_data = None
    databases = None
    tables = None

    selected_ip = request.form.get("selected_ip")
    selected_db = request.form.get("selected_db")
    selected_table = request.form.get("selected_table")

    if selected_ip:
        # Seçilen IP için veritabanlarını al
        databases = fetch_databases(selected_ip)
    if selected_db:
        # Seçilen veritabanı için tabloları al
        tables = fetch_tables(selected_ip, selected_db)
    if selected_table:
        # Seçilen tabloyu getir
        fetched_data = fetch_data_from_table(selected_ip, selected_db, selected_table)

    return render_template("home_page.html", devices=devices, fetched_data=fetched_data, databases=databases, tables=tables, selected_ip=selected_ip, selected_db=selected_db, selected_table=selected_table)

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

