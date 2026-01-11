/**
 * e-Mutabakat Pro - Web Uygulaması JavaScript
 */

// ================== GLOBALS ==================
let currentAction = null;

// ================== FILE UPLOAD ==================

document.addEventListener('DOMContentLoaded', function () {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');

    // Drag & Drop Events
    uploadZone.addEventListener('dragover', function (e) {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', function (e) {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', function (e) {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    });

    // File Input Change
    fileInput.addEventListener('change', function (e) {
        if (e.target.files.length > 0) {
            uploadFiles(e.target.files);
        }
    });

    // Click to open file dialog
    uploadZone.addEventListener('click', function (e) {
        // Ignore clicks on the file input itself or the label (label already triggers input)
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'LABEL' || e.target.closest('label')) {
            return;
        }
        fileInput.click();
    });

    // Load existing files
    refreshFileList();
});


function uploadFiles(files) {
    const formData = new FormData();

    for (let i = 0; i < files.length; i++) {
        formData.append('files[]', files[i]);
    }

    showLoading();

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();

            if (data.success) {
                addLog(`✅ ${data.files.length} dosya yüklendi`);
                refreshFileList();
            } else {
                addLog(`❌ Yükleme hatası: ${data.error}`, 'error');
            }
        })
        .catch(error => {
            hideLoading();
            addLog(`❌ Hata: ${error.message}`, 'error');
        });
}


function refreshFileList() {
    fetch('/get-files')
        .then(response => response.json())
        .then(data => {
            const fileList = document.getElementById('file-list');
            const fileCount = document.getElementById('file-count');
            const fileActions = document.getElementById('file-actions');

            fileCount.textContent = `${data.files.length} dosya`;

            if (data.files.length === 0) {
                fileList.innerHTML = '';
                fileActions.style.display = 'none';
                return;
            }

            fileActions.style.display = 'flex';

            fileList.innerHTML = data.files.map(file => `
            <div class="file-item">
                <span class="file-name">
                    📄 ${file.name}
                </span>
                <span class="file-size">${formatFileSize(file.size)}</span>
            </div>
        `).join('');
        });
}


function clearFiles() {
    if (!confirm('Tüm dosyalar silinecek. Emin misiniz?')) {
        return;
    }

    showLoading();

    fetch('/clear-files', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            hideLoading();

            if (data.success) {
                addLog('🗑️ Dosya listesi temizlendi');
                refreshFileList();
            }
        });
}


function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}


// ================== KDV OPERATIONS ==================

function generateKdvExcel() {
    showLoading();

    fetch('/generate-kdv-excel', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            hideLoading();

            if (data.logs) {
                data.logs.forEach(log => addLog(log));
            }

            if (data.success) {
                addLog(`\n📊 Excel dosyası hazır: ${data.invoice_count} fatura`);

                // Download file
                const link = document.createElement('a');
                link.href = data.file;
                link.download = data.filename;
                link.click();
            } else {
                addLog(`❌ Hata: ${data.error}`, 'error');
            }
        })
        .catch(error => {
            hideLoading();
            addLog(`❌ Hata: ${error.message}`, 'error');
        });
}


function showVknModal(action) {
    currentAction = action;
    const modal = document.getElementById('vkn-modal');
    const title = document.getElementById('modal-title');
    const desc = document.getElementById('modal-description');

    if (action === 'kdv') {
        title.textContent = 'Mükellef VKN (Opsiyonel)';
        desc.textContent = 'Satış faturalarını hariç tutmak için kendi VKN/TCKN\'nizi girin:';
    } else if (action === 'satis') {
        title.textContent = 'Mükellef VKN (Zorunlu)';
        desc.textContent = 'Satış faturalarınızı bulmak için kendi VKN/TCKN\'nizi girin:';
    }

    document.getElementById('vkn-input').value = '';
    modal.classList.add('active');
}


function closeVknModal() {
    document.getElementById('vkn-modal').classList.remove('active');
    currentAction = null;
}


function submitVkn() {
    const vkn = document.getElementById('vkn-input').value.trim();

    // Save currentAction before closing modal (closeVknModal sets it to null)
    const action = currentAction;

    if (action === 'satis' && !vkn) {
        alert('Satış fatura listesi için VKN zorunludur!');
        return;
    }

    closeVknModal();

    if (action === 'kdv') {
        generateKdvWeb(vkn);
    } else if (action === 'satis') {
        generateSatisWeb(vkn);
    }
}


function generateKdvWeb(vkn) {
    showLoading();

    // Popup blocker bypass: Kullanıcı etkileşimi sırasında pencereyi önceden aç
    const newWindow = window.open('about:blank', '_blank');
    if (newWindow) {
        newWindow.document.write('<html><head><title>KDV Listesi Yükleniyor...</title></head><body style="font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f7fa;"><div style="text-align: center;"><h2>⏳ İşleniyor...</h2><p>Lütfen bekleyin, faturalar yükleniyor...</p></div></body></html>');
    }

    fetch('/generate-kdv-web', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vkn: vkn || '' })
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();

            if (data.logs) {
                data.logs.forEach(log => addLog(log));
            }

            if (data.success) {
                addLog(`\n🌐 Web düzenleyici açılıyor...`);
                if (newWindow) {
                    newWindow.location.href = data.url;
                } else {
                    // Fallback: eğer popup engellenmiş ise sayfa içinde yönlendir
                    window.location.href = data.url;
                }
            } else {
                addLog(`❌ Hata: ${data.error}`, 'error');
                if (newWindow) newWindow.close();
            }
        })
        .catch(error => {
            hideLoading();
            addLog(`❌ Hata: ${error.message}`, 'error');
            if (newWindow) newWindow.close();
        });
}


function generateSatisWeb(vkn) {
    showLoading();

    // Popup blocker bypass: Kullanıcı etkileşimi sırasında pencereyi önceden aç
    const newWindow = window.open('about:blank', '_blank');
    if (newWindow) {
        newWindow.document.write('<html><head><title>Satış Listesi Yükleniyor...</title></head><body style="font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f7fa;"><div style="text-align: center;"><h2>⏳ İşleniyor...</h2><p>Lütfen bekleyin, satış faturaları yükleniyor...</p></div></body></html>');
    }

    fetch('/generate-satis-web', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vkn: vkn })
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();

            if (data.logs) {
                data.logs.forEach(log => addLog(log));
            }

            if (data.success) {
                addLog(`\n💰 Satış listesi açılıyor...`);
                if (newWindow) {
                    newWindow.location.href = data.url;
                } else {
                    window.location.href = data.url;
                }
            } else {
                addLog(`❌ Hata: ${data.error}`, 'error');
                if (newWindow) newWindow.close();
            }
        })
        .catch(error => {
            hideLoading();
            addLog(`❌ Hata: ${error.message}`, 'error');
            if (newWindow) newWindow.close();
        });
}


// ================== LOGGING ==================

function addLog(message, type = 'info') {
    const container = document.getElementById('log-container');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = message;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
}


function clearLogs() {
    const container = document.getElementById('log-container');
    container.innerHTML = '<div class="log-entry">✨ Log temizlendi</div>';
}


// ================== UI HELPERS ==================

function showLoading() {
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}
