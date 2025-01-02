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
    // Kullanıcıya onay penceresi gösteriyoruz
    var userChoice = confirm("Modemi yeniden başlatmaya emin misiniz?");
    
    if (userChoice) {
        // Evet'e tıkladığında formu gönderiyoruz
        document.getElementById('restartForm').submit();
    } else {
        // Cancel'a tıkladığında hiçbir şey yapmıyoruz
        return false; 
    }
}

// Dosyaları getirip açıp kapar
function toggleFiles() {
    const fileList = document.getElementById('file-list');
    const toggleIcon = document.getElementById('toggle-icon');

    if (fileList.style.display === 'none' || fileList.style.display === '') {
        fileList.style.display = 'block'; // Göster
        toggleIcon.style.transform = 'rotate(0deg)'; 
    } else {
        fileList.style.display = 'none'; // Gizle
        toggleIcon.style.transform = 'rotate(180deg)'; 
    }
}
