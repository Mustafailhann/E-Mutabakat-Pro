"""
PDF Fatura Tarama Sunucusu
PDF dosyalarını yükleyip fatura verisi çıkarmak için Flask sunucusu.
Fatura görüntüleme özelliği ile.
"""

import os
import json
import webbrowser
import base64
import io
from flask import Flask, request, jsonify, send_from_directory, render_template_string, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# PDF okuyucuyu import et
from pdf_invoice_reader import extract_invoices_from_bulk_pdf_with_qr, PDFPLUMBER_AVAILABLE, PYZBAR_AVAILABLE

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

app = Flask(__name__)
CORS(app)

# Konfigürasyon
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
PAGE_IMAGES_FOLDER = os.path.join(os.path.dirname(__file__), 'page_images')
ALLOWED_EXTENSIONS = {'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PAGE_IMAGES_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PAGE_IMAGES_FOLDER'] = PAGE_IMAGES_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max

# Global: Son taranan PDF yolu
last_scanned_pdf = None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Ana sayfa - PDF Fatura Tarayıcı arayüzü"""
    return render_template_string('''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📄 E-Arşiv PDF Fatura Tarayıcı</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 25px 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .header h1 { color: #2c3e50; font-size: 28px; margin-bottom: 10px; }
        .header p { color: #7f8c8d; font-size: 14px; }
        .status-bar { display: flex; gap: 15px; margin-top: 15px; }
        .status-item { padding: 8px 15px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .status-ok { background: #d4edda; color: #155724; }
        .status-warn { background: #fff3cd; color: #856404; }
        
        .upload-section {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 40px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .upload-area {
            border: 3px dashed #bdc3c7;
            border-radius: 15px;
            padding: 60px 40px;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 20px;
        }
        .upload-area:hover { border-color: #667eea; background: #f8f9ff; }
        .upload-area.dragover { border-color: #764ba2; background: #f0e6ff; }
        .upload-icon { font-size: 64px; margin-bottom: 15px; }
        .upload-text { font-size: 18px; color: #2c3e50; margin-bottom: 10px; }
        .upload-hint { font-size: 13px; color: #95a5a6; }
        
        #fileInput { display: none; }
        
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-primary { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }
        .btn-success { background: linear-gradient(135deg, #11998e, #38ef7d); color: white; }
        .btn-success:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(17, 153, 142, 0.4); }
        .btn-info { background: #17a2b8; color: white; padding: 6px 12px; font-size: 12px; }
        .btn-info:hover { background: #138496; }
        
        .progress-container { display: none; margin-top: 20px; }
        .progress-bar { height: 8px; background: #ecf0f1; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); width: 0%; transition: width 0.3s; }
        .progress-text { margin-top: 10px; font-size: 13px; color: #7f8c8d; }
        
        .results-section {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            display: none;
        }
        .results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 15px; }
        .results-header h2 { color: #2c3e50; font-size: 20px; }
        .results-stats { display: flex; gap: 20px; flex-wrap: wrap; }
        .stat-box { text-align: center; padding: 15px 25px; background: #f8f9fa; border-radius: 10px; }
        .stat-value { font-size: 28px; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 12px; color: #95a5a6; margin-top: 5px; }
        
        .invoice-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 15px; }
        .invoice-table th { background: #667eea; color: white; padding: 12px 10px; text-align: left; font-weight: 600; position: sticky; top: 0; }
        .invoice-table td { padding: 10px; border-bottom: 1px solid #ecf0f1; }
        .invoice-table tr:hover { background: #f8f9fa; }
        .invoice-table .num { text-align: right; font-family: 'Consolas', monospace; }
        
        .source-badge { padding: 3px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; }
        .source-qr { background: #d4edda; color: #155724; }
        .source-text { background: #cce5ff; color: #004085; }
        
        .actions-bar { margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end; flex-wrap: wrap; }
        
        /* Modal */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; justify-content: center; align-items: center; }
        .modal.show { display: flex; }
        .modal-content { background: white; border-radius: 15px; max-width: 90vw; max-height: 90vh; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
        .modal-header { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .modal-header h3 { font-size: 18px; }
        .modal-close { font-size: 28px; cursor: pointer; opacity: 0.8; }
        .modal-close:hover { opacity: 1; }
        .modal-body { padding: 0; max-height: calc(90vh - 60px); overflow: auto; background: #2c3e50; }
        .modal-body img { max-width: 100%; display: block; margin: 0 auto; }
        .modal-loading { padding: 60px; text-align: center; color: white; }
        .modal-error { padding: 40px; text-align: center; color: #e74c3c; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 E-Arşiv PDF Fatura Tarayıcı</h1>
            <p>PDF formatındaki e-Arşiv faturalarınızı yükleyin, QR kodları ve metin analizi ile otomatik veri çıkarın.</p>
            <div class="status-bar">
                <span class="status-item {{ 'status-ok' if pdfplumber else 'status-warn' }}">
                    PDF Okuyucu: {{ '✓ Aktif' if pdfplumber else '✗ Yok' }}
                </span>
                <span class="status-item {{ 'status-ok' if pyzbar else 'status-warn' }}">
                    QR Okuyucu: {{ '✓ Aktif' if pyzbar else '✗ Yok' }}
                </span>
            </div>
        </div>
        
        <div class="upload-section">
            <div class="upload-area" id="dropZone" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📁</div>
                <div class="upload-text">PDF dosyasını sürükleyip bırakın veya tıklayın</div>
                <div class="upload-hint">Maksimum dosya boyutu: 50 MB</div>
            </div>
            <input type="file" id="fileInput" accept=".pdf" onchange="handleFileSelect(this)">
            
            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="progress-text" id="progressText">Hazırlanıyor...</div>
            </div>
        </div>
        
        <div class="results-section" id="resultsSection">
            <div class="results-header">
                <h2>📋 Taranan Faturalar</h2>
                <div class="results-stats">
                    <div class="stat-box">
                        <div class="stat-value" id="totalInvoices">0</div>
                        <div class="stat-label">Toplam Fatura</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="qrCount">0</div>
                        <div class="stat-label">QR'dan</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="textCount">0</div>
                        <div class="stat-label">Metinden</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="totalKDV">0 ₺</div>
                        <div class="stat-label">Toplam KDV</div>
                    </div>
                </div>
            </div>
            
            <div style="max-height: 500px; overflow: auto;">
                <table class="invoice-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Kaynak</th>
                            <th>Fatura No</th>
                            <th>Tarih</th>
                            <th>VKN</th>
                            <th class="num">KDV Hariç</th>
                            <th class="num">KDV</th>
                            <th>Görüntü</th>
                        </tr>
                    </thead>
                    <tbody id="invoiceTableBody">
                    </tbody>
                </table>
            </div>
            
            <div class="actions-bar">
                <button class="btn btn-primary" onclick="copyToClipboard()">📋 JSON Kopyala</button>
                <button class="btn btn-success" onclick="downloadCSV()">📥 CSV İndir</button>
                <button class="btn btn-success" onclick="openInEditor()">🔗 Editörde Aç</button>
            </div>
        </div>
    </div>
    
    <!-- Invoice Preview Modal -->
    <div class="modal" id="invoiceModal">
        <div class="modal-content" style="width: 800px;">
            <div class="modal-header">
                <h3 id="modalTitle">📄 Fatura Görüntüsü</h3>
                <span class="modal-close" onclick="closeModal()">&times;</span>
            </div>
            <div class="modal-body" id="modalBody">
                <div class="modal-loading">Yükleniyor...</div>
            </div>
        </div>
    </div>
    
    <script>
        let scannedInvoices = [];
        let currentPdfFile = null;
        
        const dropZone = document.getElementById('dropZone');
        
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].name.toLowerCase().endsWith('.pdf')) {
                uploadFile(files[0]);
            }
        });
        
        function handleFileSelect(input) {
            if (input.files.length > 0) uploadFile(input.files[0]);
        }
        
        async function uploadFile(file) {
            const progressContainer = document.getElementById('progressContainer');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            
            currentPdfFile = file.name;
            progressContainer.style.display = 'block';
            progressFill.style.width = '10%';
            progressText.textContent = 'Dosya yükleniyor...';
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                progressFill.style.width = '30%';
                progressText.textContent = 'PDF taranıyor (bu birkaç dakika sürebilir)...';
                
                const response = await fetch('/scan', { method: 'POST', body: formData });
                
                progressFill.style.width = '90%';
                progressText.textContent = 'Sonuçlar işleniyor...';
                
                const data = await response.json();
                
                if (data.success) {
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Tamamlandı!';
                    scannedInvoices = data.invoices;
                    displayResults(data);
                    setTimeout(() => { progressContainer.style.display = 'none'; }, 1000);
                } else {
                    progressText.textContent = 'Hata: ' + data.error;
                    progressFill.style.background = '#e74c3c';
                }
            } catch (error) {
                progressText.textContent = 'Hata: ' + error.message;
                progressFill.style.background = '#e74c3c';
            }
        }
        
        function displayResults(data) {
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('totalInvoices').textContent = data.invoices.length;
            document.getElementById('qrCount').textContent = data.qr_count;
            document.getElementById('textCount').textContent = data.text_count;
            
            let totalKDV = 0;
            data.invoices.forEach(inv => totalKDV += (inv.kdv || 0));
            document.getElementById('totalKDV').textContent = formatNumber(totalKDV) + ' ₺';
            
            const tbody = document.getElementById('invoiceTableBody');
            tbody.innerHTML = '';
            
            data.invoices.forEach((inv, idx) => {
                const tr = document.createElement('tr');
                const sourceClass = inv.source_type === 'QR' ? 'source-qr' : 'source-text';
                const pageNum = extractPageNum(inv.source_path);
                
                tr.innerHTML = `
                    <td>${idx + 1}</td>
                    <td><span class="source-badge ${sourceClass}">${inv.source_type || 'PDF'}</span></td>
                    <td><strong>${inv.seri || ''}${inv.sira_no || ''}</strong></td>
                    <td>${inv.tarih || '-'}</td>
                    <td>${inv.satici_vkn || '-'}</td>
                    <td class="num">${formatNumber(inv.kdv_haric_tutar || 0)}</td>
                    <td class="num">${formatNumber(inv.kdv || 0)}</td>
                    <td><button class="btn btn-info" onclick="showInvoice(${pageNum}, '${inv.seri || ''}${inv.sira_no || ''}')">👁 Görüntüle</button></td>
                `;
                tbody.appendChild(tr);
            });
        }
        
        function extractPageNum(sourcePath) {
            if (!sourcePath) return 1;
            const match = sourcePath.match(/#page(\\d+)/);
            return match ? parseInt(match[1]) : 1;
        }
        
        function showInvoice(pageNum, invoiceNo) {
            const modal = document.getElementById('invoiceModal');
            const modalBody = document.getElementById('modalBody');
            const modalTitle = document.getElementById('modalTitle');
            
            modalTitle.textContent = '📄 Fatura: ' + invoiceNo + ' (Sayfa ' + pageNum + ')';
            modalBody.innerHTML = '<div class="modal-loading">⏳ Sayfa görüntüsü yükleniyor...</div>';
            modal.classList.add('show');
            
            // Sayfa görüntüsünü yükle
            fetch('/page-image/' + pageNum)
                .then(response => {
                    if (response.ok) return response.blob();
                    throw new Error('Sayfa yüklenemedi');
                })
                .then(blob => {
                    const url = URL.createObjectURL(blob);
                    modalBody.innerHTML = '<img src="' + url + '" alt="Fatura Sayfa ' + pageNum + '" style="width: 100%;">';
                })
                .catch(error => {
                    modalBody.innerHTML = '<div class="modal-error">❌ ' + error.message + '</div>';
                });
        }
        
        function closeModal() {
            document.getElementById('invoiceModal').classList.remove('show');
        }
        
        // ESC tuşu ile modal'ı kapat
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
        
        function formatNumber(num) {
            return parseFloat(num || 0).toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        function copyToClipboard() {
            navigator.clipboard.writeText(JSON.stringify(scannedInvoices, null, 2));
            alert('JSON panoya kopyalandı!');
        }
        
        function downloadCSV() {
            if (scannedInvoices.length === 0) return;
            const headers = ['Tarih', 'Fatura No', 'VKN', 'Ünvan', 'KDV Hariç', 'KDV', 'Kaynak'];
            let csv = headers.join(';') + '\\n';
            scannedInvoices.forEach(inv => {
                csv += [
                    inv.tarih || '',
                    (inv.seri || '') + (inv.sira_no || ''),
                    inv.satici_vkn || '',
                    (inv.satici_unvan || '').replace(/;/g, ','),
                    inv.kdv_haric_tutar || 0,
                    inv.kdv || 0,
                    inv.source_type || 'PDF'
                ].join(';') + '\\n';
            });
            const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'faturalar.csv';
            link.click();
        }
        
        function openInEditor() {
            localStorage.setItem('scannedInvoices', JSON.stringify(scannedInvoices));
            window.open('/editor', '_blank');
        }
    </script>
</body>
</html>
    ''', pdfplumber=PDFPLUMBER_AVAILABLE, pyzbar=PYZBAR_AVAILABLE)


@app.route('/scan', methods=['POST'])
def scan_pdf():
    """PDF dosyasını tara ve fatura verilerini döndür"""
    global last_scanned_pdf
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Dosya bulunamadı'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Dosya seçilmedi'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Sadece PDF dosyaları kabul edilir'})
    
    try:
        # Dosyayı kaydet (silmeyeceğiz, sayfa görüntüsü için lazım)
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Son taranan PDF'i sakla
        last_scanned_pdf = filepath
        
        # PDF'i tara
        invoices = extract_invoices_from_bulk_pdf_with_qr(filepath, use_qr=True)
        
        # QR ve metin sayılarını hesapla
        qr_count = sum(1 for inv in invoices if inv.get('source_type') == 'QR')
        text_count = len(invoices) - qr_count
        
        return jsonify({
            'success': True,
            'invoices': invoices,
            'total_count': len(invoices),
            'qr_count': qr_count,
            'text_count': text_count
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/page-image/<int:page_num>')
def page_image(page_num):
    """PDF sayfasının görüntüsünü döndür"""
    global last_scanned_pdf
    
    if not last_scanned_pdf or not os.path.exists(last_scanned_pdf):
        return jsonify({'error': 'PDF dosyası bulunamadı'}), 404
    
    if not pdfplumber:
        return jsonify({'error': 'pdfplumber yüklü değil'}), 500
    
    try:
        with pdfplumber.open(last_scanned_pdf) as pdf:
            if page_num < 1 or page_num > len(pdf.pages):
                return jsonify({'error': 'Geçersiz sayfa numarası'}), 400
            
            page = pdf.pages[page_num - 1]  # 0-indexed
            
            # Sayfayı görüntüye çevir
            page_image = page.to_image(resolution=150)
            
            # PNG olarak byte array'e çevir
            img_byte_arr = io.BytesIO()
            page_image.original.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            return send_file(img_byte_arr, mimetype='image/png')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/editor')
def editor():
    """KDV Listesi Editörüne yönlendir"""
    return send_from_directory('.', 'KDV_Listesi_Editor.html')


@app.route('/api/status')
def status():
    """Sunucu durumunu döndür"""
    return jsonify({
        'status': 'running',
        'pdfplumber': PDFPLUMBER_AVAILABLE,
        'pyzbar': PYZBAR_AVAILABLE,
        'last_pdf': last_scanned_pdf
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("📄 E-Arşiv PDF Fatura Tarayıcı Sunucusu")
    print("="*60)
    print(f"PDF Okuyucu: {'✓ Aktif' if PDFPLUMBER_AVAILABLE else '✗ Yok'}")
    print(f"QR Okuyucu: {'✓ Aktif' if PYZBAR_AVAILABLE else '✗ Yok'}")
    print()
    print("Sunucu başlatılıyor: http://localhost:5000")
    print("Kapatmak için Ctrl+C")
    print("="*60 + "\n")
    
    # Tarayıcıda aç
    webbrowser.open('http://localhost:5000')
    
    # Sunucuyu başlat
    app.run(host='0.0.0.0', port=5000, debug=False)

