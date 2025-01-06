// home_page.js
function toggleSelectAll() {
    var selectAll = document.getElementById("select-all");
    var checkboxes = document.getElementsByName("selected_rows");
    for (var i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = selectAll.checked;
    }
}

function deleteRow(rowId) {
    if (confirm("Bu satırı silmek istediğinizden emin misiniz?")) {
        $.ajax({
            url: "/delete-row",  // Silme işlemi yapılacak rota
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ "row_id": rowId }),
            success: function(response) {
                if (response.success) {
                    alert("Silme işlemi başarılı");
                    location.reload();  // Sayfayı yenileyerek güncellemeleri göster
                } else {
                    alert("Silme işlemi başarısız");
                }
            },
            error: function(xhr, status, error) {
                alert("Silme işlemi sırasında hata oluştu: " + error);
            }
        });
    }
}

// Restart Etmek istediğine Eminmisiniz Seçenegini sunar
function confirmRestart() {
        // Seçilen IP adresini al
    var selectedIp = document.getElementById("selected_ip").value;

    // Eğer IP seçilmemişse uyarı göster
    if (!selectedIp) {
        alert("Lütfen bir cihazın IP'sini seçin.");
        return false;
    }

    // Eğer IP seçilmişse, kullanıcıya onay sorusu göster
    var userChoice = confirm("Modemi yeniden başlatmak istediğinize emin misiniz?");
        
    // Evet'e tıkladığında formu gönderiyoruz, aksi halde hiçbir şey yapmıyoruz
    return userChoice;
}


 // Modbus 
 document.getElementById('modbusButton').addEventListener('click', function (e) {
    e.preventDefault(); // Sayfa yenilenmesini önler
    const selectedIP = document.getElementById('selected_ip').value;

    if (!selectedIP) {
        alert('Lütfen bir cihaz seçiniz!');
        return;
    }

    // Modbus formunu göster
    document.getElementById('modbusForm').style.display = 'block';

    // Seçilen IP'yi bir gizli input alanında sakla
    const modbusFormContent = document.getElementById('modbusFormContent');
    let hiddenIPField = document.getElementById('hidden_ip_field');
    if (!hiddenIPField) {
        hiddenIPField = document.createElement('input');
        hiddenIPField.type = 'hidden';
        hiddenIPField.name = 'device_ip';
        hiddenIPField.id = 'hidden_ip_field';
        modbusFormContent.appendChild(hiddenIPField);
    }
    hiddenIPField.value = selectedIP;
});

// Modems Tablosunu ve Equipmants uttonuna tıkladığında eğer ip adresini seçmediysa uyarı vermek için yazdığım js kodu
document.getElementById('device-form').addEventListener('submit', function (e) {
    const selectedIP = document.getElementById('selected_ip').value;

    if (!selectedIP) {
        alert('Lütfen bir cihaz IP\'si seçiniz!');
        e.preventDefault(); 
    }
});

