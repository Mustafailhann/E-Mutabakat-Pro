"""
Satış Fatura Listesi Web Raporu Oluşturucu
İnteraktif düzenleme, GIB önizleme ve Excel export özellikli HTML rapor.
"""

import json
import os
from datetime import datetime

def generate_satis_web_report(invoices, output_path):
    """
    Satış fatura listesi için interaktif web raporu oluştur.
    """
    
    invoice_data = json.dumps(invoices, ensure_ascii=False, indent=2)
    
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Satış Fatura Listesi - Düzenleyici</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }}
        
        .header {{
            background: linear-gradient(135deg, #27ae60, #1e8449);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header h1 {{ font-size: 24px; }}
        .header-buttons {{ display: flex; gap: 10px; }}
        
        .btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .btn-primary {{ background: #3498db; color: white; }}
        .btn-primary:hover {{ background: #2980b9; }}
        .btn-danger {{ background: #dc3545; color: white; }}
        .btn-danger:hover {{ background: #c82333; }}
        .btn-info {{ background: #17a2b8; color: white; }}
        .btn-info:hover {{ background: #138496; }}
        .btn-secondary {{ background: #6c757d; color: white; }}
        .btn-secondary:hover {{ background: #5a6268; }}
        
        .container {{ padding: 20px 30px; }}
        
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            flex: 1;
        }}
        .stat-card h3 {{ color: #666; font-size: 12px; margin-bottom: 5px; }}
        .stat-card .value {{ font-size: 28px; font-weight: bold; color: #27ae60; }}
        
        .table-container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        th {{
            background: #27ae60;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 10px 8px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{ background: #f8f9fa; }}
        
        .editable {{
            cursor: pointer;
            min-width: 60px;
            padding: 4px;
            border-radius: 3px;
        }}
        .editable:hover {{ background: #e8f6e9; }}
        .editable:focus {{
            outline: 2px solid #27ae60;
            background: white;
        }}
        
        .actions {{ display: flex; gap: 5px; }}
        .btn-sm {{
            padding: 5px 10px;
            font-size: 11px;
            border-radius: 3px;
        }}
        
        .num {{ text-align: right; font-family: 'Consolas', monospace; }}
        
        .modal {{
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .modal.show {{ display: flex; }}
        .modal-content {{
            background: white;
            border-radius: 10px;
            max-width: 900px;
            max-height: 90vh;
            overflow: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        .modal-header {{
            background: #27ae60;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-body {{ padding: 20px; }}
        .close {{ font-size: 24px; cursor: pointer; }}
        
        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .search-box {{
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            width: 300px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Satış Fatura Listesi (Hesaplanan KDV)</h1>
        <div class="header-buttons">
            <button class="btn btn-secondary" onclick="undoDelete()">↩️ Geri Al</button>
            <button class="btn btn-primary" onclick="exportToExcel()">📥 Excel'e Aktar</button>
        </div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <h3>TOPLAM FATURA</h3>
                <div class="value" id="totalCount">0</div>
            </div>
            <div class="stat-card">
                <h3>TOPLAM KDV HARİÇ</h3>
                <div class="value" id="totalTaxExcl">0,00 ₺</div>
            </div>
            <div class="stat-card">
                <h3>TOPLAM HESAPLANAN KDV</h3>
                <div class="value" id="totalTax">0,00 ₺</div>
            </div>
        </div>
        
        <div class="toolbar">
            <input type="text" class="search-box" placeholder="🔍 Ara (alıcı adı, fatura no...)" oninput="filterTable(this.value)">
            <div>
                <span id="selectedCount">0</span> satır seçili
                <button class="btn btn-danger btn-sm" onclick="deleteSelected()">🗑️ Seçilenleri Sil</button>
            </div>
        </div>
        
        <div class="table-container">
            <table id="satisTable">
                <thead>
                    <tr>
                        <th><input type="checkbox" id="selectAll" onclick="toggleSelectAll()"></th>
                        <th>Sıra</th>
                        <th>Tarih</th>
                        <th>Seri</th>
                        <th>Fatura No</th>
                        <th>Alıcı Ünvanı</th>
                        <th>VKN/TCKN</th>
                        <th>Mal/Hizmet Cinsi</th>
                        <th class="num">KDV Hariç</th>
                        <th class="num">KDV %</th>
                        <th class="num">Hesaplanan KDV</th>
                        <th>Dönem</th>
                        <th>İşlemler</th>
                    </tr>
                </thead>
                <tbody id="tableBody">
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Invoice Preview Modal -->
    <div class="modal" id="invoiceModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Fatura Önizleme</h3>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <div class="modal-body" id="invoicePreview">
            </div>
        </div>
    </div>

    <script>
        let invoices = {invoice_data};
        let deletedRows = [];
        let selectedRows = new Set();
        
        document.addEventListener('DOMContentLoaded', function() {{
            renderTable();
            updateStats();
        }});
        
        function renderTable() {{
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            invoices.forEach((inv, idx) => {{
                if (inv._deleted) return;
                
                const tr = document.createElement('tr');
                tr.dataset.idx = idx;
                
                tr.innerHTML = `
                    <td><input type="checkbox" class="row-select" onchange="updateSelection()"></td>
                    <td>${{idx + 1}}</td>
                    <td contenteditable="true" class="editable">${{inv.tarih || ''}}</td>
                    <td></td>
                    <td contenteditable="true" class="editable">${{(inv.seri || '') + (inv.sira_no || '')}}</td>
                    <td contenteditable="true" class="editable">${{inv.alici_unvan || ''}}</td>
                    <td contenteditable="true" class="editable">${{inv.alici_vkn || ''}}</td>
                    <td contenteditable="true" class="editable" title="${{inv.mal_cinsi || ''}}">${{truncate(inv.mal_cinsi, 30)}}</td>
                    <td contenteditable="true" class="editable num">${{formatNumber(inv.kdv_haric_tutar)}}</td>
                    <td class="num">%${{inv.kdv_orani || 20}}</td>
                    <td contenteditable="true" class="editable num">${{formatNumber(inv.kdv)}}</td>
                    <td contenteditable="true" class="editable">${{inv.kdv_donemi || ''}}</td>
                    <td class="actions">
                        <button class="btn btn-info btn-sm" onclick="showInvoice(${{idx}})">Fatura</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteRow(${{idx}})">Sil</button>
                    </td>
                `;
                
                tbody.appendChild(tr);
            }});
        }}
        
        function truncate(str, len) {{
            if (!str) return '';
            return str.length > len ? str.substring(0, len) + '...' : str;
        }}
        
        function formatNumber(num) {{
            if (num === undefined || num === null) return '0,00';
            return parseFloat(num).toLocaleString('tr-TR', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
        }}
        
        function updateStats() {{
            const active = invoices.filter(i => !i._deleted);
            document.getElementById('totalCount').textContent = active.length;
            document.getElementById('totalTaxExcl').textContent = formatNumber(active.reduce((s, i) => s + (parseFloat(i.kdv_haric_tutar) || 0), 0)) + ' ₺';
            document.getElementById('totalTax').textContent = formatNumber(active.reduce((s, i) => s + (parseFloat(i.kdv) || 0), 0)) + ' ₺';
        }}
        
        function deleteRow(idx) {{
            invoices[idx]._deleted = true;
            deletedRows.push(idx);
            renderTable();
            updateStats();
        }}
        
        function undoDelete() {{
            if (deletedRows.length > 0) {{
                const idx = deletedRows.pop();
                invoices[idx]._deleted = false;
                renderTable();
                updateStats();
            }}
        }}
        
        function toggleSelectAll() {{
            const checked = document.getElementById('selectAll').checked;
            document.querySelectorAll('.row-select').forEach(cb => cb.checked = checked);
            updateSelection();
        }}
        
        function updateSelection() {{
            selectedRows.clear();
            document.querySelectorAll('.row-select:checked').forEach(cb => {{
                selectedRows.add(parseInt(cb.closest('tr').dataset.idx));
            }});
            document.getElementById('selectedCount').textContent = selectedRows.size;
        }}
        
        function deleteSelected() {{
            if (selectedRows.size === 0) return;
            if (!confirm(selectedRows.size + ' fatura silinecek. Emin misiniz?')) return;
            
            selectedRows.forEach(idx => {{
                invoices[idx]._deleted = true;
                deletedRows.push(idx);
            }});
            selectedRows.clear();
            renderTable();
            updateStats();
        }}
        
        function filterTable(query) {{
            query = query.toLowerCase();
            document.querySelectorAll('#tableBody tr').forEach(tr => {{
                const text = tr.textContent.toLowerCase();
                tr.style.display = text.includes(query) ? '' : 'none';
            }});
        }}
        
        function showInvoice(idx) {{
            const inv = invoices[idx];
            
            if (inv.gib_html_path) {{
                window.open(inv.gib_html_path, '_blank');
                return;
            }}
            
            const preview = document.getElementById('invoicePreview');
            const total = (parseFloat(inv.kdv_haric_tutar) || 0) + (parseFloat(inv.kdv) || 0);
            
            preview.innerHTML = `
                <div style="font-family: 'Times New Roman', serif; max-width: 800px; margin: 0 auto; background: white;">
                    <div style="background: linear-gradient(135deg, #1e8449, #27ae60); color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 24px; font-weight: bold;">e-Belge</div>
                            <div style="font-size: 12px; opacity: 0.9;">Satış Faturası</div>
                        </div>
                    </div>
                    
                    <div style="background: #27ae60; color: white; text-align: center; padding: 10px; font-size: 18px; font-weight: bold;">
                        SATIŞ FATURASI
                    </div>
                    
                    <div style="padding: 20px; border: 1px solid #ddd;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #27ae60;">
                            <div style="flex: 1; text-align: center;">
                                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                                    <div style="font-size: 11px; color: #666;">FATURA NO</div>
                                    <div style="font-size: 16px; font-weight: bold; color: #2c3e50;">${{inv.seri}}${{inv.sira_no}}</div>
                                    <div style="font-size: 11px; color: #666; margin-top: 5px;">TARİH</div>
                                    <div style="font-size: 14px; font-weight: bold;">${{inv.tarih}}</div>
                                </div>
                            </div>
                        </div>
                        
                        <div style="margin-bottom: 20px;">
                            <div style="border: 1px solid #27ae60; border-radius: 5px; overflow: hidden;">
                                <div style="background: #27ae60; color: white; padding: 8px 12px; font-weight: bold; font-size: 12px;">
                                    ALICI
                                </div>
                                <div style="padding: 12px;">
                                    <div style="font-weight: bold; font-size: 14px; margin-bottom: 8px;">${{inv.alici_unvan || '-'}}</div>
                                    <table style="font-size: 12px; width: 100%;">
                                        <tr><td style="color: #666; width: 80px;">VKN/TCKN:</td><td style="font-weight: bold;">${{inv.alici_vkn || '-'}}</td></tr>
                                    </table>
                                </div>
                            </div>
                        </div>
                        
                        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px;">
                            <thead>
                                <tr style="background: #34495e; color: white;">
                                    <th style="padding: 10px; text-align: left; border: 1px solid #2c3e50;">Mal/Hizmet</th>
                                    <th style="padding: 10px; text-align: right; border: 1px solid #2c3e50;">KDV Hariç</th>
                                    <th style="padding: 10px; text-align: right; border: 1px solid #2c3e50;">KDV %</th>
                                    <th style="padding: 10px; text-align: right; border: 1px solid #2c3e50;">KDV Tutarı</th>
                                    <th style="padding: 10px; text-align: right; border: 1px solid #2c3e50;">Toplam</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td style="padding: 10px; border: 1px solid #ddd;">${{inv.mal_cinsi || '-'}}</td>
                                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">${{formatNumber(inv.kdv_haric_tutar)}}</td>
                                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">%${{inv.kdv_orani || 20}}</td>
                                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">${{formatNumber(inv.kdv)}}</td>
                                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right; font-weight: bold;">${{formatNumber(total)}}</td>
                                </tr>
                            </tbody>
                        </table>
                        
                        <div style="display: flex; justify-content: flex-end;">
                            <table style="width: 300px; border-collapse: collapse; font-size: 13px;">
                                <tr style="background: #f8f9fa;">
                                    <td style="padding: 8px 12px; border: 1px solid #ddd;">KDV Hariç Toplam</td>
                                    <td style="padding: 8px 12px; border: 1px solid #ddd; text-align: right; font-weight: bold;">${{formatNumber(inv.kdv_haric_tutar)}} ₺</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 12px; border: 1px solid #ddd;">Hesaplanan KDV</td>
                                    <td style="padding: 8px 12px; border: 1px solid #ddd; text-align: right;">${{formatNumber(inv.kdv)}} ₺</td>
                                </tr>
                                <tr style="background: #27ae60; color: white;">
                                    <td style="padding: 10px 12px; border: 1px solid #1e8449; font-weight: bold;">TOPLAM</td>
                                    <td style="padding: 10px 12px; border: 1px solid #1e8449; text-align: right; font-weight: bold; font-size: 16px;">${{formatNumber(total)}} ₺</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                </div>
            `;
            
            document.getElementById('invoiceModal').classList.add('show');
        }}
        
        function closeModal() {{
            document.getElementById('invoiceModal').classList.remove('show');
        }}
        
        function exportToExcel() {{
            const active = invoices.filter(i => !i._deleted);
            
            if (active.length === 0) {{
                alert('Dışa aktarılacak fatura yok!');
                return;
            }}
            
            const headers = [
                'Sıra No', 'Satış Faturasının Tarihi', 'Satış Faturasının Serisi',
                "Satış Faturasının Sıra No'su", 'Alıcının Adı-Soyadı / Ünvanı',
                'Alıcının VKN/TCKN', 'Satılan Mal ve/veya Hizmetin Cinsi',
                'Satılan Mal ve/veya Hizmetin Miktarı', 'KDV Hariç Tutarı',
                'KDV Oranı %', 'Hesaplanan KDV', 'KDV Dönemi'
            ];
            
            const rows = active.map((inv, idx) => [
                idx + 1,
                inv.tarih,
                '',  // Seri boş
                (inv.seri || '') + (inv.sira_no || ''),
                inv.alici_unvan,
                inv.alici_vkn,
                inv.mal_cinsi,
                inv.miktar,
                parseFloat(inv.kdv_haric_tutar) || 0,
                inv.kdv_orani || 20,
                parseFloat(inv.kdv) || 0,
                inv.kdv_donemi
            ]);
            
            rows.push([
                '', '', '', '', '', '', 'TOPLAM', '',
                active.reduce((s, i) => s + (parseFloat(i.kdv_haric_tutar) || 0), 0),
                '',
                active.reduce((s, i) => s + (parseFloat(i.kdv) || 0), 0),
                ''
            ]);
            
            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
            
            ws['!cols'] = [
                {{wch: 8}}, {{wch: 15}}, {{wch: 10}}, {{wch: 20}}, {{wch: 40}},
                {{wch: 15}}, {{wch: 50}}, {{wch: 20}}, {{wch: 18}}, {{wch: 10}},
                {{wch: 18}}, {{wch: 12}}
            ];
            
            XLSX.utils.book_append_sheet(wb, ws, 'Satış Fatura Listesi');
            XLSX.writeFile(wb, 'Satis_Fatura_Listesi.xlsx');
        }}
        
        window.onclick = function(e) {{
            if (e.target.classList.contains('modal')) {{
                e.target.classList.remove('show');
            }}
        }};
    </script>
</body>
</html>
'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_path
