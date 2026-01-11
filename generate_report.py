import csv
import os
import json
from datetime import datetime
import base64
import zipfile
import io

# Import GIB viewer for XSLT transformation
try:
    from gib_viewer import transform_invoice_to_html
    GIB_VIEWER_AVAILABLE = True
except ImportError:
    GIB_VIEWER_AVAILABLE = False
    print("Warning: gib_viewer module not available. GIB rendering disabled.")


# Default for standalone execution
DEFAULT_WORK_DIR = r"c:\Users\Asus\Desktop\agent ff"

# Invoice ZIP files for GIB rendering
INVOICE_ZIPS = [
    os.path.join(DEFAULT_WORK_DIR, "ESKI_Gelen_eFatura.zip"),
    os.path.join(DEFAULT_WORK_DIR, "ESKI_Giden_eFatura.zip"),
    os.path.join(DEFAULT_WORK_DIR, "e-Arsiv.zip"),
    os.path.join(DEFAULT_WORK_DIR, "yeşilbaşak 11, ay", "kasım 2025 faturalar", "kasım 2025 alış fat", "Gelen e-Fatura.zip"),
    os.path.join(DEFAULT_WORK_DIR, "yeşilbaşak 11, ay", "kasım 2025 faturalar", "kasım 2025 satış fat", "Giden e-Fatura.zip"),
]


def discover_all_zips(base_dir: str) -> list:
    """
    Recursively discover all ZIP files in the base directory.
    Returns list of absolute paths to ZIP files.
    """
    zip_files = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith('.zip'):
                zip_files.append(os.path.join(root, f))
    return zip_files


def get_existing_gib_html(invoice_no: str, output_dir: str) -> str:
    """
    Check if GIB HTML already exists for this invoice in gib_html folder.
    Returns filename (relative path) or None.
    """
    gib_dir = os.path.join(output_dir, "gib_html")
    if not os.path.exists(gib_dir):
        return None
    
    # Direct match: {invoice_no}.html
    direct_file = os.path.join(gib_dir, f"{invoice_no}.html")
    if os.path.exists(direct_file):
        return f"gib_html/{invoice_no}.html"
    
    # Search for any file containing the invoice number
    for fname in os.listdir(gib_dir):
        if invoice_no in fname and fname.endswith('.html'):
            return f"gib_html/{fname}"
    
    return None


def find_invoice_xml_in_zips(invoice_no: str, zip_paths: list = None, base_dir: str = None) -> str:
    """
    Search for an invoice XML by invoice number across multiple ZIP files.
    Handles nested ZIPs and individual invoice ZIPs.
    Returns: XML content as string, or None if not found.
    """
    if zip_paths is None:
        if base_dir:
            zip_paths = discover_all_zips(base_dir)
        else:
            zip_paths = INVOICE_ZIPS
    
    for zip_path in zip_paths:
        if not os.path.exists(zip_path):
            continue
        result = _search_zip_recursive(zip_path, invoice_no)
        if result:
            return result
    return None


def _search_zip_recursive(zip_source, invoice_no: str) -> str:
    """Recursively search for invoice XML in ZIP (handles nested ZIPs and single-invoice ZIPs)."""
    try:
        if isinstance(zip_source, str):
            z = zipfile.ZipFile(zip_source, 'r')
            zip_filename = os.path.basename(zip_source)
        else:
            z = zipfile.ZipFile(io.BytesIO(zip_source), 'r')
            zip_filename = ""
        
        # First: Check if the ZIP filename itself contains the invoice number
        # (for individual invoice ZIPs like in yeşilbaşak folder)
        if invoice_no in zip_filename:
            for name in z.namelist():
                if name.endswith('.xml'):
                    xml_content = z.read(name).decode('utf-8')
                    z.close()
                    return xml_content
        
        for name in z.namelist():
            # Check if this XML matches the invoice number
            if name.endswith('.xml') and invoice_no in name:
                xml_content = z.read(name).decode('utf-8')
                z.close()
                return xml_content
            
            # Also check XML content for invoice number (slower but more reliable)
            if name.endswith('.xml'):
                try:
                    xml_content = z.read(name).decode('utf-8')
                    if f'>{invoice_no}<' in xml_content or f'ID>{invoice_no}' in xml_content:
                        z.close()
                        return xml_content
                except:
                    pass
            
            # Nested ZIP - check if invoice_no is in the ZIP filename
            if name.lower().endswith('.zip'):
                # Check filename match
                if invoice_no in name:
                    nested_content = z.read(name)
                    inner = zipfile.ZipFile(io.BytesIO(nested_content), 'r')
                    for inner_name in inner.namelist():
                        if inner_name.endswith('.xml'):
                            xml_content = inner.read(inner_name).decode('utf-8')
                            inner.close()
                            z.close()
                            return xml_content
                    inner.close()
        
        z.close()
    except Exception as e:
        pass
    return None


def get_gib_html_for_invoice(invoice_no: str, zip_paths: list = None, output_dir: str = None, ettn: str = None) -> str:
    """
    Get GIB-rendered HTML for an invoice.
    First checks existing gib_html folder, then searches ZIPs and generates HTML using XSLT.
    Saves generated HTML to gib_html folder for future use.
    Returns: HTML string or None.
    """
    if not output_dir:
        output_dir = DEFAULT_WORK_DIR
    
    gib_dir = os.path.join(output_dir, "gib_html")
    os.makedirs(gib_dir, exist_ok=True)
    
    # First check if HTML already exists with invoice number as filename
    direct_file = os.path.join(gib_dir, f"{invoice_no}.html")
    if os.path.exists(direct_file):
        try:
            with open(direct_file, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            pass
    
    # Search for any file containing the invoice number in its name
    try:
        for fname in os.listdir(gib_dir):
            if invoice_no in fname and fname.endswith('.html'):
                full_path = os.path.join(gib_dir, fname)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except:
                    pass
    except:
        pass
    
    # ZIP search disabled for performance - use showGibInvoice fallback
    # GIB HTML files will be looked up directly by invoice number in JavaScript
    return None


# KKEG Risk Tespit Fonksiyonu
def detect_kkeg_risk(description: str, acc_code: str = "", invoice_data: dict = None) -> tuple:
    """
    Açıklama, hesap kodu ve fatura içeriğinden KKEG riski tespit et.
    Returns: (risk_level, risk_reason) veya (None, None)
    """
    # Tüm metinleri birleştir
    texts_to_check = []
    
    # Yevmiye açıklaması
    if description:
        texts_to_check.append(description.lower())
    
    # Fatura içeriği
    if invoice_data:
        # Fatura kalemleri
        items = invoice_data.get('Items', [])
        for item in items:
            if item.get('Name'):
                texts_to_check.append(str(item.get('Name', '')).lower())
            if item.get('Description'):
                texts_to_check.append(str(item.get('Description', '')).lower())
        
        # Fatura notları
        notes = invoice_data.get('Notes', [])
        for note in notes:
            if note:
                texts_to_check.append(str(note).lower())
        
        # Gönderen ismi (bazen fatura kaynağı bilgi verir)
        sender = invoice_data.get('Sender', {})
        if sender.get('Name'):
            texts_to_check.append(str(sender.get('Name', '')).lower())
    
    combined_text = ' '.join(texts_to_check)
    
    kkeg_rules = {
        'YÜKSEK - Ceza/Tazminat': ['ceza', 'para cezası', 'trafik cez', 'vergi cez', 'sgk ceza', 'tazminat', 'gecikme zammı'],
        'YÜKSEK - Kişisel Gider': ['kişisel', 'özel', 'ev kirası', 'konut', 'şahsi', 'eş', 'çocuk'],
        'ORTA - Seyahat/Konaklama': ['otel', 'konaklama', 'uçak', 'bilet', 'thy', 'pegasus', 'taksi', 'transfer', 'hilton', 'marriott', 'wyndham'],
        'ORTA - Temsil/Ağırlama': ['yemek', 'restoran', 'lokanta', 'hediye', 'temsil', 'ağırlama', 'ikram', 'cafe', 'kahve'],
        'DÜŞÜK - Bağış': ['bağış', 'yardım', 'hayır', 'dernek', 'vakıf'],
        'DÜŞÜK - Araç Gideri': ['akaryakıt', 'benzin', 'mazot', 'otopark', 'hgs', 'ogs', 'köprü', 'shell', 'opet', 'bp', 'petrol']
    }
    
    # KKEG sadece GİDER/MALİYET hesaplarında olabilir
    # 600/601/602 = SATIŞ (HASILAT) hesapları - bunlar gider değil!
    # 620-689 = Maliyet hesapları (SMM, Üretim, Finansman, Olağandışı)
    # 7xx = Dönem giderleri (760 Pazarlama, 770 Genel Yönetim, 780 Finansman)
    
    is_expense_account = False
    if acc_code:
        if acc_code.startswith('7'):
            # Tüm 7xx hesaplar gider
            is_expense_account = True
        elif acc_code.startswith('6'):
            # 6xx'de sadece 620+ hesapları gider (600/601/602 satış - hariç)
            if not acc_code.startswith(('600', '601', '602', '603')):
                is_expense_account = True
    
    # Eğer gider/maliyet hesabı değilse KKEG riski yok
    if not is_expense_account:
        return (None, None)
    
    for risk_reason, keywords in kkeg_rules.items():
        if any(kw in combined_text for kw in keywords):
            return (risk_reason.split(' - ')[0], risk_reason.split(' - ')[1])
    
    # Gider/maliyet hesabı ama anahtar kelime yok
    if is_expense_account:
        return ('DÜŞÜK', 'Gider Hesabı')
    
    return (None, None)


def create_html_report(output_dir=DEFAULT_WORK_DIR, invoice_zip_paths=None):
    """
    Create HTML report from CSV comparison data.
    
    Args:
        output_dir: Directory for output files
        invoice_zip_paths: List of ZIP file paths containing invoices for GIB rendering
    """
    # Use provided paths or fall back to default
    if invoice_zip_paths is None:
        invoice_zip_paths = INVOICE_ZIPS
    
    csv_file = os.path.join(output_dir, "Detayli_Karsilastirma_Raporu.csv")
    html_file = os.path.join(output_dir, "Fatura_Defter_Analiz_Raporu.html")

    if not os.path.exists(csv_file):
        print(f"CSV dosyası bulunamadı: {csv_file}")
        return

    rows = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        # Clean keys (remove potential BOM artifacts if utf-8-sig didn't catch it somehow or other chars)
        rows = [{k.strip('\ufeff" '): v for k, v in row.items()} for row in reader]

    # İstatistikler
    stats = {}
    for r in rows:
        s = r["Durum"]
        stats[s] = stats.get(s, 0) + 1

    # Detay Verisi için DB (JS'e aktarılacak)
    js_details_db = {}
    js_invoice_db = {}
    gib_html_db = {}  # GIB XSLT ile render edilmiş HTML içerikleri
    
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Calibri, sans-serif; margin: 40px; font-size:14px; color:#333; }}
            h1 {{ color: #2E74B5; }}
            h2 {{ color: #1F4E78; border-bottom: 2px solid #1F4E78; padding-bottom: 5px; margin-top: 30px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; color: #333; font-weight: bold; position: sticky; top: 0; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            tr:hover {{ background-color: #f1f1f1; }}
            .danger {{ background-color: #ffe6e6 !important; color: #a00000; }}
            .warning {{ background-color: #fff4cc !important; color: #996600; }}
            .info {{ background-color: #e6f7ff !important; color: #004d99; }}
            .summary-box {{ background-color: #f8f9fa; border: 1px solid #ccc; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .num {{ text-align: right; font-family: Consolas, monospace; }}
            
            /* Button Style */
            .btn-detail {{
                background-color: #007bff; color: white; border: none; padding: 5px 10px;
                border-radius: 3px; cursor: pointer; font-size: 11px; margin: 2px;
            }}
            .btn-invoice {{
                background-color: #28a745; color: white; border: none; padding: 5px 10px;
                border-radius: 3px; cursor: pointer; font-size: 11px; margin: 2px;
            }}
            .btn-detail:hover {{ background-color: #0056b3; }}
            .btn-invoice:hover {{ background-color: #1e7e34; }}
            
            /* Modal Style */
            .modal {{
                display: none; position: fixed; z-index: 1000; left: 0; top: 0;
                width: 100%; height: 100%; overflow: auto;
                background-color: rgba(0,0,0,0.6);
            }}
            .modal-content {{
                background-color: #fefefe; margin: 5% auto; padding: 25px;
                border: 1px solid #888; width: 85%; max-width: 950px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5); border-radius: 8px;
            }}
            .close {{ color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }}
            .close:hover {{ color: black; }}
            
            .modal-header {{ border-bottom: 2px solid #2E74B5; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }}
            .modal-title {{ font-size: 18px; font-weight: bold; color: #1F4E78; }}
            
            /* Invoice Preview Styles - GİB Standard e-Fatura */
            .inv-box {{ 
                padding: 30px; 
                background: #fff; 
                font-family: Arial, sans-serif; 
                color: #000; 
                line-height: 1.4;
                border: 1px solid #ccc;
                max-width: 800px;
                margin: 0 auto;
            }}
            .inv-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 0;
                padding-bottom: 10px;
            }}
            .inv-logo-area {{ 
                display: flex;
                flex-direction: column;
            }}
            .inv-efatura-label {{
                font-size: 14px;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }}
            .inv-hr {{ 
                border: none;
                border-top: 4px solid #f47920; 
                margin: 0 0 15px 0;
            }}
            
            /* Party Boxes - GİB Style */
            .inv-info-grid {{ 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 0; 
                margin-bottom: 15px;
                border: 1px solid #999;
            }}
            .inv-party-box {{ 
                border: none;
                font-size: 11px; 
            }}
            .inv-party-box:first-child {{
                border-right: 1px solid #999;
            }}
            .inv-party-title {{ 
                font-weight: bold; 
                background: #f47920; 
                color: #fff;
                padding: 6px 10px; 
                text-transform: uppercase;
                font-size: 11px;
            }}
            .inv-party-content {{ 
                padding: 10px; 
                min-height: 90px;
                background: #fff;
            }}
            .inv-name {{ 
                font-weight: bold; 
                margin-bottom: 5px; 
                text-transform: uppercase;
                font-size: 12px;
            }}
            .inv-party-row {{
                margin: 3px 0;
            }}
            .inv-party-label {{
                font-weight: bold;
            }}
            
            /* Meta Table - GİB Style */
            .inv-meta-table {{ 
                width: 100%; 
                font-size: 11px; 
                border-collapse: collapse; 
                margin-bottom: 10px;
                border: 1px solid #999;
            }}
            .inv-meta-table td {{ 
                padding: 5px 10px; 
                border: 1px solid #ccc; 
            }}
            .inv-meta-label {{ 
                font-weight: bold; 
                background: #f5f5f5; 
                width: 25%; 
            }}
            .inv-meta-value {{
                width: 25%;
            }}
            .ettn-box {{ 
                font-size: 11px; 
                margin: 10px 0;
                padding: 5px;
                background: #f9f9f9;
                border: 1px solid #ddd;
            }}
            
            /* Items Table - GİB Style with Orange Header */
            .inv-items-table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-top: 10px; 
                font-size: 10px; 
                border: 1px solid #333; 
            }}
            .inv-items-table th {{ 
                background: #f47920; 
                color: #fff; 
                padding: 6px 4px; 
                text-align: center; 
                border: 1px solid #d66a1a;
                font-weight: bold;
                font-size: 9px;
            }}
            .inv-items-table td {{ 
                padding: 5px 4px; 
                border: 1px solid #ccc; 
                vertical-align: top;
            }}
            .inv-items-table .num {{
                text-align: right;
            }}
            
            /* Summary Tables - GİB Style */
            .inv-summary-area {{ 
                display: flex; 
                justify-content: flex-end; 
                margin-top: 15px; 
            }}
            .inv-summary-table {{ 
                width: 320px; 
                border-collapse: collapse; 
                font-size: 11px;
                border: 1px solid #999;
            }}
            .inv-summary-table td {{ 
                padding: 5px 8px; 
                border: 1px solid #ccc; 
            }}
            .inv-summary-label {{ 
                background: #f9f9f9; 
                text-align: left; 
                font-weight: normal;
            }}
            .inv-summary-value {{
                text-align: right;
                font-family: 'Consolas', monospace;
            }}
            .inv-total-row {{ 
                font-weight: bold; 
                background: #f0f0f0 !important;
            }}
            .inv-total-row td {{
                font-size: 12px;
            }}
            
            /* Logo Box */
            .inv-logo-box {{
                width: 150px;
                height: 60px;
                border: 1px dashed #ccc;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #999;
                font-size: 14px;
                margin-bottom: 5px;
                background: #fafafa;
            }}
            
            /* Notes Section */
            .inv-notes-section {{
                margin-top: 20px;
                padding: 10px;
                background: #f9f9f9;
                border: 1px solid #ddd;
                font-size: 11px;
            }}
            .inv-notes-section ul {{
                margin: 5px 0 0 20px;
                padding: 0;
            }}
            .inv-notes-section li {{
                margin: 3px 0;
            }}
            
            .inv-footer {{ 
                margin-top: 30px; 
                font-size: 9px; 
                color: #666; 
                font-style: italic; 
                border-top: 1px solid #eee; 
                padding-top: 10px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <h1>Fatura ve Defter Analiz Raporu</h1>
        <p><strong>Tarih:</strong> {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
        
        <div class="summary-box">
            <h3>Özet İstatistikler</h3>
            <ul>
    """
    
    for k, v in stats.items():
        color = "black"
        if "KAYITSIZ" in k: color = "red"
        elif "Tutar" in k: color = "#cc9900"
        html_content += f'<li style="color:{color}"><strong>{k}:</strong> {v} Adet</li>'

    html_content += """
            </ul>
        </div>

        <!-- 1. Kritik Hatalar -->
        <h2>1. Kritik Hatalar (Defterde Yok)</h2>
        <p>Defter kayıtlarında bulunamayan ancak ZIP fatura klasöründe mevcut olan faturalar.</p>
        <table>
            <thead>
                <tr>
                    <th>Fatura No</th>
                    <th>Tarih</th>
                    <th>Satıcı</th>
                    <th class="num">TL Tutar</th>
                    <th>Dosya</th>
                    <th style="text-align:center;">İşlem</th>
                </tr>
            </thead>
            <tbody>
    """
    
    row_id_counter = 0
    count_crit = 0
    for r in rows:
        if "KAYITSIZ" in r["Durum"]:
            count_crit += 1
            row_id = f"crit_{row_id_counter}"
            row_id_counter += 1
            
            # Invoice Data
            inv_data = {
                "No": r["Fatura_No"],
                "Date": r["Tarih"],
                "Currency": r.get("Para_Birimi", "TRY"),
                "Sender": json.loads(r.get("Sender", "{}")),
                "Receiver": json.loads(r.get("Receiver", "{}")),
                "Items": json.loads(r.get("Items", "[]")),
                "ETTN": r.get("ETTN", ""),
                "Scenario": r.get("Scenario", ""),
                "InvType": r.get("InvType", ""),
                "Tax": r.get("Fatura_KDV_Orj", r.get("Fatura_KDV", 0)),
                "TaxExcl": r.get("TaxExcl", 0),
                "Discount": r.get("Discount", 0),
                "Total": r.get("Tutar_Orj", 0),
                "Notes": json.loads(r.get("Notes", "[]")),
                "Despatches": json.loads(r.get("Despatches", "[]")),
                "Orders": json.loads(r.get("Orders", "[]")),
                "PaymentMeans": json.loads(r.get("PaymentMeans", "[]")),
                "ExchangeRate": r.get("ExchangeRate", 0.0)
            }
            
            # Fallback: KDV hesaplanamamışsa ama matrah ve toplam varsa, farkı al
            try:
                t_tax = float(inv_data["Tax"])
                t_total = float(inv_data["Total"])
                t_excl = float(inv_data["TaxExcl"])
                if t_tax == 0 and t_total > 0 and t_excl > 0:
                    inv_data["Tax"] = round(t_total - t_excl, 2)
            except:
                pass
            
            js_invoice_db[row_id] = inv_data
            
            # Generate GIB HTML for this invoice
            gib_html = get_gib_html_for_invoice(r['Fatura_No'], output_dir=output_dir, ettn=r.get('ETTN', ''))
            if gib_html:
                gib_html_db[row_id] = gib_html
            
            sender_name = inv_data["Sender"].get("Name", "Bilinmiyor")
            html_content += f"""
            <tr class="danger">
                <td>{r['Fatura_No']}</td>
                <td>{r['Tarih']}</td>
                <td>{sender_name}</td>
                <td class="num">{float(r.get('Tutar_TL_Hesaplanan',0)):.2f}</td>
                <td><small>{r['Dosya']}</small></td>
                <td style="text-align:center;">
                    <button class="btn-invoice" onclick="showInvoice('{row_id}')">Fatura</button>
                    <button class="btn-detail" onclick="showGibInvoice('{row_id}')" style="background:#2E74B5;">GIB</button>
                </td>
            </tr>
            """
    
    if count_crit == 0: html_content += "<tr><td colspan='6'>Kritik hata bulunmadı.</td></tr>"
    html_content += "</tbody></table>"

    # 2. Tutar Farkları
    html_content += """
        <h2>2. Tutar Farkları ve Kur Hesaplamaları</h2>
        <table>
            <thead>
                <tr>
                    <th>Fatura No</th>
                    <th>P.B.</th>
                    <th class="num">Fatura (TL)</th>
                    <th class="num">Defter (TL)</th>
                    <th class="num" style="background-color:#ffe;">Fark</th>
                    <th>Durum</th>
                    <th style="background:#ffebee;">KKEG Risk</th>
                    <th style="text-align:center;">İşlem</th>
                </tr>
            </thead>
            <tbody>
    """
    
    count_diff = 0
    for r in rows:
        st = r["Durum"]
        if "KAYITSIZ" in st or "BELGESİZ" in st: continue
        
        is_diff = abs(float(r.get('Fark', 0))) > 2.0
        is_forex = r.get('Para_Birimi') != 'TRY'
        is_kdv_err = "KDV" in st
        
        if is_diff or is_forex or is_kdv_err:
            count_diff += 1
            css_class = ""
            if "Tutar Farkı" in st: css_class = "warning"
            if "KDV" in st: css_class = "warning"
            
            row_id = f"row_{row_id_counter}"
            row_id_counter += 1
            
            # Yevmiye Details
            js_details_db[row_id] = json.loads(r.get("Yevmiye_Detay", "[]"))
            
            # Invoice Details
            js_invoice_db[row_id] = {
                "No": r["Fatura_No"],
                "Date": r["Tarih"],
                "Currency": r.get("Para_Birimi", "TRY"),
                "Sender": json.loads(r.get("Sender", "{}")),
                "Receiver": json.loads(r.get("Receiver", "{}")),
                "Items": json.loads(r.get("Items", "[]")),
                "ETTN": r.get("ETTN", ""),
                "Scenario": r.get("Scenario", ""),
                "InvType": r.get("InvType", ""),
                "Tax": r.get("Fatura_KDV_Orj", r.get("Fatura_KDV", 0)),
                "TaxExcl": r.get("TaxExcl", 0),
                "Discount": r.get("Discount", 0),
                "Total": r.get("Tutar_Orj", 0),
                "Notes": json.loads(r.get("Notes", "[]")),
                "Despatches": json.loads(r.get("Despatches", "[]")),
                "Orders": json.loads(r.get("Orders", "[]")),
                "PaymentMeans": json.loads(r.get("PaymentMeans", "[]")),
                "ExchangeRate": r.get("ExchangeRate", 0.0)
            }
            
            # Fallback
            try:
                t_tax = float(js_invoice_db[row_id]["Tax"])
                t_total = float(js_invoice_db[row_id]["Total"])
                t_excl = float(js_invoice_db[row_id]["TaxExcl"])
                if t_tax == 0 and t_total > 0 and t_excl > 0:
                     # General fallback: KDV = Toplam - Matrah
                     js_invoice_db[row_id]["Tax"] = round(t_total - t_excl, 2)
            except: pass
            
            # Generate GIB HTML for this invoice
            gib_html = get_gib_html_for_invoice(r['Fatura_No'], output_dir=output_dir, ettn=r.get('ETTN', ''))
            if gib_html:
                gib_html_db[row_id] = gib_html
            
            # KKEG risk tespiti - yevmiye hesap kodlarına göre
            # detect_kkeg_risk fonksiyonu 600/601/602 satış hesaplarını zaten hariç tutuyor
            kkeg_risk_level, kkeg_risk_reason = None, None
            yevmiye_list = js_details_db.get(row_id, [])
            invoice_info = js_invoice_db.get(row_id, {})
            for line in yevmiye_list:
                acc = str(line.get("Acc", ""))
                desc = line.get("Desc", "")
                level, reason = detect_kkeg_risk(desc, acc, invoice_info)
                if level:
                    kkeg_risk_level, kkeg_risk_reason = level, reason
                    break
            
            # KKEG risk gösterge renkleri
            if kkeg_risk_level == "YÜKSEK":
                kkeg_style = "background:#ffcdd2; color:#c62828; font-weight:bold;"
                kkeg_text = f"⚠️ {kkeg_risk_reason}"
            elif kkeg_risk_level == "ORTA":
                kkeg_style = "background:#ffe0b2; color:#e65100;"
                kkeg_text = f"⚡ {kkeg_risk_reason}"
            elif kkeg_risk_level == "DÜŞÜK":
                kkeg_style = "background:#fff9c4; color:#f57f17;"
                kkeg_text = f"📋 {kkeg_risk_reason}"
            else:
                kkeg_style = "color:#81c784;"
                kkeg_text = "✅ Yok"
            
            html_content += f"""
            <tr class="{css_class}">
                <td>{r['Fatura_No']}</td>
                <td>{r.get('Para_Birimi')}</td>
                <td class="num"><strong>{r.get('Tutar_TL_Hesaplanan')}</strong></td>
                <td class="num">{r.get('Tutar_Defter')}</td>
                <td class="num" style="background-color:#ffe;">{float(r.get('Fark',0)):.2f}</td>
                <td>{st}</td>
                <td style="{kkeg_style}">{kkeg_text}</td>
                <td style="text-align:center;">
                    <button class="btn-detail" onclick="showDetails('{row_id}', '{r["Fatura_No"]}')">Defter</button>
                    <button class="btn-invoice" onclick="showInvoice('{row_id}')">Fatura</button>
                    <button class="btn-detail" onclick="showGibInvoice('{row_id}')" style="background:#2E74B5;">GIB</button>
                    <button onclick="addToReport(this, '{row_id}', '{r["Fatura_No"]}', '{kkeg_risk_reason or "Tutar Farkı"}', {float(r.get('Tutar_TL_Hesaplanan') or 0)})" style="background:#9c27b0; color:white; border:none; padding:5px 8px; border-radius:4px; cursor:pointer; margin-left:4px;" title="Denetçi Raporuna Aktar">📥</button>
                </td>
            </tr>
            """

    if count_diff == 0: html_content += "<tr><td colspan='7'>Listelenecek kayıt yok.</td></tr>"
    html_content += "</tbody></table>"

    # 3. KDV Uyuşmazlıkları
    html_content += """
        <h2>3. KDV Uyuşmazlıkları (Özel Analiz)</h2>
        <table>
            <thead>
                <tr>
                    <th>Fatura No</th>
                    <th class="num">Fatura KDV</th>
                    <th class="num">Defter KDV</th>
                    <th class="num" style="background-color:#ffe;">Fark</th>
                    <th>Durum / Notlar</th>
                    <th style="background:#ffebee;">KKEG Risk</th>
                    <th style="text-align:center;">İşlem</th>
                </tr>
            </thead>
            <tbody>
    """
    
    count_kdv = 0
    for r in rows:
        if "KDV" in r["Durum"] or "KDV TUTAR FARKI" in r.get("Hesap_Notlari", ""):
            count_kdv += 1
            row_id = f"kdv_{row_id_counter}"
            row_id_counter += 1
            
            js_details_db[row_id] = json.loads(r.get("Yevmiye_Detay", "[]"))
            js_invoice_db[row_id] = {
                "No": r["Fatura_No"],
                "Date": r["Tarih"],
                "Currency": r.get("Para_Birimi", "TRY"),
                "Sender": json.loads(r.get("Sender", "{}")),
                "Receiver": json.loads(r.get("Receiver", "{}")),
                "Items": json.loads(r.get("Items", "[]")),
                "ETTN": r.get("ETTN", ""),
                "Scenario": r.get("Scenario", ""),
                "InvType": r.get("InvType", ""),
                "Tax": r.get("Fatura_KDV_Orj", r.get("Fatura_KDV", 0)),
                "TaxExcl": r.get("TaxExcl", 0),
                "Discount": r.get("Discount", 0),
                "Total": r.get("Tutar_Orj", 0),
                "Notes": json.loads(r.get("Notes", "[]")),
                "Despatches": json.loads(r.get("Despatches", "[]")),
                "Orders": json.loads(r.get("Orders", "[]")),
                "PaymentMeans": json.loads(r.get("PaymentMeans", "[]")),
                "ExchangeRate": r.get("ExchangeRate", 0.0)
            }
            
            # Generate GIB HTML for this invoice
            gib_html = get_gib_html_for_invoice(r['Fatura_No'], output_dir=output_dir, ettn=r.get('ETTN', ''))
            if gib_html:
                gib_html_db[row_id] = gib_html
            
            # KKEG risk tespiti - hesap kodlarına göre
            # detect_kkeg_risk 600/601/602 satış hesaplarını zaten hariç tutuyor
            kkeg_risk_level, kkeg_risk_reason = None, None
            yevmiye_list = js_details_db.get(row_id, [])
            invoice_info = js_invoice_db.get(row_id, {})
            for line in yevmiye_list:
                acc = str(line.get("Acc", ""))
                desc = line.get("Desc", "")
                level, reason = detect_kkeg_risk(desc, acc, invoice_info)
                if level:
                    kkeg_risk_level, kkeg_risk_reason = level, reason
                    break
            
            # KKEG risk gösterge renkleri
            if kkeg_risk_level == "YÜKSEK":
                kkeg_style = "background:#ffcdd2; color:#c62828; font-weight:bold;"
                kkeg_text = f"⚠️ {kkeg_risk_reason}"
            elif kkeg_risk_level == "ORTA":
                kkeg_style = "background:#ffe0b2; color:#e65100;"
                kkeg_text = f"⚡ {kkeg_risk_reason}"
            elif kkeg_risk_level == "DÜŞÜK":
                kkeg_style = "background:#fff9c4; color:#f57f17;"
                kkeg_text = f"📋 {kkeg_risk_reason}"
            else:
                kkeg_style = "color:#81c784;"
                kkeg_text = "✅ Yok"
            
            html_content += f"""
            <tr class="warning">
                <td>{r['Fatura_No']}</td>
                <td class="num">{float(r.get('Fatura_KDV',0)):.2f}</td>
                <td class="num">{float(r.get('Defter_KDV',0)):.2f}</td>
                <td class="num" style="background-color:#ffe;"><b>{float(r.get('KDV_Fark',0)):.2f}</b></td>
                <td>{r['Durum']} <br> <small>{r.get('Hesap_Notlari','')}</small></td>
                <td style="{kkeg_style}">{kkeg_text}</td>
                <td style="text-align:center;">
                    <button class="btn-detail" onclick="showDetails('{row_id}', '{r["Fatura_No"]}')">Defter</button>
                    <button class="btn-invoice" onclick="showInvoice('{row_id}')">Fatura</button>
                    <button class="btn-detail" onclick="showGibInvoice('{row_id}')" style="background:#2E74B5;">GIB</button>
                    <button onclick="addToReport(this, '{row_id}', '{r["Fatura_No"]}', '{kkeg_risk_reason or "KDV Uyuşmazlığı"}', {float(r.get('Fatura_KDV') or 0)})" style="background:#9c27b0; color:white; border:none; padding:5px 8px; border-radius:4px; cursor:pointer; margin-left:4px;" title="Denetçi Raporuna Aktar">📥</button>
                </td>
            </tr>
            """
            
    if count_kdv == 0: html_content += "<tr><td colspan='6'>KDV Hatası bulunmadı.</td></tr>"
    html_content += "</tbody></table>"

    # 4. Belgesizler
    html_content += """
        <h2>4. Belgesiz Defter Kayıtları (Faturası Bulunamayan)</h2>
        <table>
            <thead>
                <tr>
                    <th>Belge No</th>
                    <th>Tarih</th>
                    <th class="num">Tutar</th>
                    <th>Durum</th>
                    <th style="text-align:center;">İşlem</th>
                </tr>
            </thead>
            <tbody>
    """
    
    count_missing = 0
    for r in rows:
        if "BELGESİZ" in r["Durum"]:
            count_missing += 1
            row_id = f"miss_{row_id_counter}"
            row_id_counter += 1
            
            # Yevmiye Details
            yevmiye_list = json.loads(r.get("Yevmiye_Detay", "[]"))
            js_details_db[row_id] = yevmiye_list
            
            # Synthetic Invoice Data from Ledger
            partner_name = "Bilinmiyor (Defter Kaydı)"
            receiver_name = "Bilinmiyor (Defter Kaydı)"
            sender_name = "Bilinmiyor (Defter Kaydı)"
            
            # Try to guess Type/Partner from Acc Codes
            acc_list = [str(x.get("Acc","")) for x in yevmiye_list]
            is_sales = any(a.startswith("600") or a.startswith("120") or a.startswith("391") for a in acc_list)
            is_purchase = any(a.startswith("153") or a.startswith("770") or a.startswith("320") or a.startswith("191") for a in acc_list)
            
            if is_sales:
                sender_name = "ZEUGMA MERMER (SİZ / DEFTER)"
                receiver_name = "Müşteri (Belge No: " + r['Fatura_No'] + ")"
            elif is_purchase:
                sender_name = "Satıcı (Belge No: " + r['Fatura_No'] + ")"
                receiver_name = "ZEUGMA MERMER (SİZ / DEFTER)"

            js_invoice_db[row_id] = {
                "No": r["Fatura_No"],
                "Date": r["Tarih"],
                "Currency": r.get("Para_Birimi", "TRY"),
                "Sender": {"Name": sender_name, "Address": "Fatura belgesi dosyalar arasında bulunamadı.", "City": "DEFTER KAYDI"},
                "Receiver": {"Name": receiver_name, "Address": "Fatura belgesi dosyalar arasında bulunamadı.", "City": "DEFTER KAYDI"},
                "Items": [{"Description": "Defter Kaydı Detayı", "Quantity": 1, "Unit": "ADET", "Price": r['Tutar_Defter'], "VATRate": 20, "Total": r['Tutar_Defter']}],
                "ETTN": "(BELGE DOSYASI YOK)",
                "Scenario": "DEFTER_KAYDI",
                "InvType": "DEBBER_RECORD",
                "Tax": float(r.get("Defter_KDV",0)),
                "TaxExcl": float(r.get("Tutar_Defter",0)) - float(r.get("Defter_KDV",0)),
                "Discount": 0,
                "Total": r['Tutar_Defter']
            }
                
            html_content += f"""
            <tr>
                <td>{r['Fatura_No']}</td>
                <td>{r['Tarih']}</td>
                <td class="num">{r['Tutar_Defter']}</td>
                <td>{r['Durum']}</td>
                <td style="text-align:center;">
                    <button class="btn-detail" onclick="showDetails('{row_id}', '{r["Fatura_No"]}')">Defter</button>
                    <button class="btn-invoice" onclick="showInvoice('{row_id}')">Fatura</button>
                </td>
            </tr>
            """
            
    if count_missing == 0: html_content += "<tr><td colspan='5'>Belgesiz kayıt bulunmadı.</td></tr>"
    html_content += "</tbody></table><br><br>"

    # 5. KKEG İnceleme Bölümü
    html_content += """
        <h2 style="color:#d63031;">5. KKEG İnceleme (Kullanıcı Değerlendirmesi)</h2>
        <p>Aşağıdaki giderler KKEG (Kanunen Kabul Edilmeyen Gider) şüphesi taşımaktadır. 
        <strong>Fatura</strong> ve <strong>Defter</strong> butonlarına tıklayarak belgeleri inceleyin ve değerlendirme yapın.</p>
        
        <div style="background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:20px;">
            <div style="display:flex; gap:30px;">
                <div id="kkegSummary">
                    <span style="color:#27ae60; font-weight:bold;">✅ Kabul: <span id="kkegAcceptCount">0</span></span> | 
                    <span style="color:#e74c3c; font-weight:bold;">⚠️ KKEG: <span id="kkegRejectCount">0</span></span> | 
                    <span style="color:#f39c12; font-weight:bold;">❓ Bekleyen: <span id="kkegPendingCount">0</span></span>
                </div>
            </div>
        </div>
        
        <table id="kkegTable">
            <thead>
                <tr style="background:#d63031; color:white;">
                    <th>Belge No</th>
                    <th>Hesap</th>
                    <th>Açıklama</th>
                    <th class="num">Tutar</th>
                    <th>Şüphe Türü</th>
                    <th style="text-align:center;">Belgeler</th>
                    <th style="text-align:center; width:200px;">Değerlendirme</th>
                </tr>
            </thead>
            <tbody id="kkegTableBody">
    """
    
    # KKEG şüpheli kayıtları tespit et
    kkeg_keywords = {
        'seyahat': ['otel', 'konaklama', 'uçak', 'bilet', 'thy', 'pegasus', 'taksi'],
        'temsil': ['yemek', 'restoran', 'hediye', 'temsil', 'ağırlama'],
        'ceza': ['ceza', 'tazminat', 'gecikme', 'faizi'],
        'kisisel': ['kişisel', 'özel', 'ev', 'personal']
    }
    
    kkeg_items = []
    kkeg_id_counter = 0
    
    # TÜM KAYITLARDA KKEG taraması yap (Belgesiz, Eşleşen, vs.)
    for r in rows:
        try:
            yevmiye_list = json.loads(r.get("Yevmiye_Detay", "[]") or "[]")
        except (json.JSONDecodeError, TypeError):
            yevmiye_list = []
        has_invoice = "KAYITSIZ" not in r.get("Durum", "") and "BELGESİZ" not in r.get("Durum", "")
        
        for line in yevmiye_list:
            acc = str(line.get("Acc", ""))
            desc = line.get("Desc", "").lower()
            amt = float(line.get("Amt", 0) or 0)
            dc = line.get("DC", "D")
            
            # Sadece GİDER hesapları (760, 770, 689 vb.) + BORÇ kayıtları
            if acc.startswith(("760", "770", "689", "780")) and dc in ["D", "B"] and amt > 0:
                # Şüphe türünü belirle
                suspicion_type = "Genel Gider"
                for susp_type, keywords in kkeg_keywords.items():
                    if any(kw in desc for kw in keywords):
                        suspicion_type = susp_type.capitalize()
                        break
                
                kkeg_id = f"kkeg_{kkeg_id_counter}"
                kkeg_id_counter += 1
                
                # Row ID'yi bul (fatura butonu için)
                row_id_for_inv = None
                for rid, inv in js_invoice_db.items():
                    if inv.get("No") == r["Fatura_No"]:
                        row_id_for_inv = rid
                        break
                
                kkeg_items.append({
                    'id': kkeg_id,
                    'doc_no': r['Fatura_No'],
                    'acc': acc,
                    'desc': line.get("Desc", ""),
                    'amt': amt,
                    'suspicion': suspicion_type,
                    'has_invoice': has_invoice,
                    'row_id': row_id_for_inv
                })
                
                # JavaScript verisine ekle
                js_details_db[kkeg_id] = yevmiye_list
    
    if kkeg_items:
        for item in kkeg_items:
            html_content += f"""
            <tr id="kkegRow_{item['id']}" data-status="pending">
                <td>{item['doc_no']}</td>
                <td><code>{item['acc']}</code></td>
                <td>{item['desc'][:50]}...</td>
                <td class="num">{item['amt']:,.2f}</td>
                <td><span style="background:#fee; padding:2px 8px; border-radius:4px;">{item['suspicion']}</span></td>
                <td style="text-align:center;">
                    <button class="btn-detail" onclick="showDetails('{item['id']}', '{item['doc_no']}')" style="background:#1e3a5f;">📋 Defter</button>
                    {'<button class="btn-detail" onclick="showGibInvoice(' + "'" + (item['row_id'] or item['id']) + "'" + ')" style="background:#2E74B5;">📄 GIB Fatura</button>' if item['has_invoice'] else '<button disabled style="background:#ccc; color:#666; border:none; padding:5px 10px; border-radius:4px;">📄 Fatura Yok</button>'}
                </td>
                <td style="text-align:center;">
                    <button onclick="setKkegStatus('{item['id']}', 'accept')" style="background:#27ae60; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; margin:2px;">✅ Kabul</button>
                    <button onclick="setKkegStatus('{item['id']}', 'reject')" style="background:#e74c3c; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; margin:2px;">⚠️ KKEG</button>
                    <button onclick="setKkegStatus('{item['id']}', 'review')" style="background:#f39c12; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; margin:2px;">❓</button>
                </td>
            </tr>
            """
    else:
        html_content += "<tr><td colspan='7' style='text-align:center; color:#27ae60;'>✅ KKEG şüphesi taşıyan kayıt bulunamadı.</td></tr>"
    
    html_content += """
            </tbody>
        </table>
        
        <script>
        // KKEG Değerlendirme Sistemi
        var kkegEvaluations = JSON.parse(localStorage.getItem('kkegEvaluations') || '{}');
        
        function setKkegStatus(id, status) {
            kkegEvaluations[id] = status;
            localStorage.setItem('kkegEvaluations', JSON.stringify(kkegEvaluations));
            
            var row = document.getElementById('kkegRow_' + id);
            row.dataset.status = status;
            
            // Satır rengini güncelle
            if (status === 'accept') {
                row.style.background = '#d4edda';
            } else if (status === 'reject') {
                row.style.background = '#f8d7da';
            } else {
                row.style.background = '#fff3cd';
            }
            
            updateKkegSummary();
        }
        
        function updateKkegSummary() {
            var acceptCount = 0, rejectCount = 0, pendingCount = 0;
            var rows = document.querySelectorAll('#kkegTableBody tr');
            rows.forEach(function(row) {
                var status = row.dataset.status;
                if (status === 'accept') acceptCount++;
                else if (status === 'reject') rejectCount++;
                else pendingCount++;
            });
            document.getElementById('kkegAcceptCount').textContent = acceptCount;
            document.getElementById('kkegRejectCount').textContent = rejectCount;
            document.getElementById('kkegPendingCount').textContent = pendingCount;
        }
        
        // Sayfa yüklendiğinde önceki değerlendirmeleri uygula
        document.addEventListener('DOMContentLoaded', function() {
            for (var id in kkegEvaluations) {
                var status = kkegEvaluations[id];
                var row = document.getElementById('kkegRow_' + id);
                if (row) {
                    row.dataset.status = status;
                    if (status === 'accept') row.style.background = '#d4edda';
                    else if (status === 'reject') row.style.background = '#f8d7da';
                    else row.style.background = '#fff3cd';
                }
            }
            updateKkegSummary();
        });
        
        // ==========================================
        // RAPORA AKTAR - Denetçi Risk İşaretleme
        // ==========================================
        var exportedRisks = JSON.parse(localStorage.getItem('denetciRiskleri') || '[]');
        
        function addToReport(btn, rowId, invoiceNo, riskType, amount) {
            // Zaten eklendi mi kontrol et
            var exists = exportedRisks.some(function(r) { return r.invoiceNo === invoiceNo; });
            if (exists) {
                alert('Bu kayıt zaten rapora eklenmiş!\\n\\nFatura: ' + invoiceNo);
                return;
            }
            
            var risk = {
                id: rowId,
                invoiceNo: invoiceNo,
                riskType: riskType,
                amount: amount,
                date: new Date().toISOString(),
                note: ''
            };
            
            // Not iste
            var note = prompt('Bu risk için not eklemek ister misiniz? (Boş bırakabilirsiniz)', '');
            if (note !== null) {
                risk.note = note;
                exportedRisks.push(risk);
                localStorage.setItem('denetciRiskleri', JSON.stringify(exportedRisks));
                
                // Butonu işaretle
                btn.style.background = '#4caf50';
                btn.innerText = '✓';
                btn.disabled = true;
                
                updateRiskPanel();
                alert('✅ Risk rapora eklendi!\\n\\nFatura: ' + invoiceNo + '\\nRisk: ' + riskType);
            }
        }
        
        function removeFromReport(invoiceNo) {
            exportedRisks = exportedRisks.filter(r => r.invoiceNo !== invoiceNo);
            localStorage.setItem('denetciRiskleri', JSON.stringify(exportedRisks));
            updateRiskPanel();
        }
        
        function updateRiskPanel() {
            var panel = document.getElementById('riskPanel');
            var list = document.getElementById('riskList');
            var count = document.getElementById('riskCount');
            
            count.textContent = exportedRisks.length;
            
            if (exportedRisks.length === 0) {
                list.innerHTML = '<p style="color:#999;">Henüz risk işaretlenmedi.</p>';
            } else {
                var html = '<table style="width:100%; font-size:12px; border-collapse:collapse;">';
                html += '<tr style="background:#f5f5f5;"><th>Fatura</th><th>Risk</th><th>Tutar</th><th>Not</th><th></th></tr>';
                exportedRisks.forEach(function(r) {
                    html += '<tr>';
                    html += '<td style="padding:4px; border-bottom:1px solid #eee;">' + r.invoiceNo + '</td>';
                    html += '<td style="padding:4px; border-bottom:1px solid #eee;">' + r.riskType + '</td>';
                    html += '<td style="padding:4px; border-bottom:1px solid #eee;">' + r.amount.toFixed(2) + '</td>';
                    html += '<td style="padding:4px; border-bottom:1px solid #eee; max-width:150px; overflow:hidden; text-overflow:ellipsis;">' + (r.note || '-') + '</td>';
                    html += '<td style="padding:4px; border-bottom:1px solid #eee;"><button onclick="removeFromReport(\\'' + r.invoiceNo + '\\')" style="background:#e74c3c; color:white; border:none; padding:2px 6px; border-radius:3px; cursor:pointer;">×</button></td>';
                    html += '</tr>';
                });
                html += '</table>';
                list.innerHTML = html;
            }
        }
        
        function exportToAuditorReport() {
            if (exportedRisks.length === 0) {
                alert('Aktarılacak risk bulunamadı!');
                return;
            }
            
            // Denetçi Raporuna Risk Bölümü Ekle
            var riskHtml = '<div id="denetciRiskSection" style="margin-top:30px; padding:20px; background:#fff3e0; border:2px solid #ff9800; border-radius:8px;">';
            riskHtml += '<h2 style="color:#e65100; margin-top:0;">⚠️ Denetçi Risk Tespitleri</h2>';
            riskHtml += '<p>Aşağıdaki riskler denetçi tarafından Fatura-Defter Mutabakat analizi sırasında tespit edilmiştir.</p>';
            riskHtml += '<table style="width:100%; border-collapse:collapse; margin-top:15px;">';
            riskHtml += '<thead><tr style="background:#ff9800; color:white;"><th style="padding:10px; border:1px solid #e65100;">Fatura No</th><th style="padding:10px; border:1px solid #e65100;">Risk Türü</th><th style="padding:10px; border:1px solid #e65100;">Tutar</th><th style="padding:10px; border:1px solid #e65100;">Not</th></tr></thead>';
            riskHtml += '<tbody>';
            
            var totalAmount = 0;
            exportedRisks.forEach(function(r) {
                riskHtml += '<tr>';
                riskHtml += '<td style="padding:8px; border:1px solid #ddd;">' + r.invoiceNo + '</td>';
                riskHtml += '<td style="padding:8px; border:1px solid #ddd; background:#fff8e1;">' + r.riskType + '</td>';
                riskHtml += '<td style="padding:8px; border:1px solid #ddd; text-align:right;">' + r.amount.toLocaleString('tr-TR', {minimumFractionDigits:2}) + ' TL</td>';
                riskHtml += '<td style="padding:8px; border:1px solid #ddd;">' + (r.note || '-') + '</td>';
                riskHtml += '</tr>';
                totalAmount += r.amount;
            });
            
            riskHtml += '<tr style="background:#ffe0b2; font-weight:bold;">';
            riskHtml += '<td colspan="2" style="padding:10px; border:1px solid #e65100;">TOPLAM</td>';
            riskHtml += '<td style="padding:10px; border:1px solid #e65100; text-align:right;">' + totalAmount.toLocaleString('tr-TR', {minimumFractionDigits:2}) + ' TL</td>';
            riskHtml += '<td style="padding:10px; border:1px solid #e65100;">' + exportedRisks.length + ' adet risk</td>';
            riskHtml += '</tr>';
            riskHtml += '</tbody></table></div>';
            
            // localStorage'a kaydet (Denetçi raporu otomatik okuyacak)
            localStorage.setItem('denetciRiskleri', JSON.stringify(exportedRisks));
            
            alert('✅ ' + exportedRisks.length + ' adet risk kaydedildi!\\n\\nToplam Tutar: ' + totalAmount.toLocaleString('tr-TR', {minimumFractionDigits:2}) + ' TL\\n\\nDenetçi Raporunu açtığınızda bu riskler otomatik görünecektir.');
        }
        
        // Sayfa yüklendiğinde risk panelini güncelle
        document.addEventListener('DOMContentLoaded', function() {
            updateRiskPanel();
        });
        </script>
        
        <!-- Risk Özeti Paneli -->
        <div id="riskPanel" style="position:fixed; bottom:20px; right:20px; width:420px; background:white; border:2px solid #9c27b0; border-radius:8px; box-shadow:0 4px 20px rgba(0,0,0,0.2); z-index:1000; max-height:350px; overflow-y:auto;">
            <div style="background:#9c27b0; color:white; padding:10px; font-weight:bold; display:flex; justify-content:space-between; align-items:center;">
                <span>📋 Denetçi Riskleri (<span id="riskCount">0</span>)</span>
                <button onclick="exportToAuditorReport()" style="background:#ff9800; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer; font-weight:bold;">📥 Rapora Aktar</button>
            </div>
            <div id="riskList" style="padding:10px; max-height:250px; overflow-y:auto;"></div>
        </div>
    """
    
    # --- SAVE GIB HTML FILES SEPARATELY ---
    gib_files_dir = os.path.join(output_dir, "gib_html")
    os.makedirs(gib_files_dir, exist_ok=True)
    
    gib_file_paths = {}  # row_id -> filename
    for row_id, html_content_gib in gib_html_db.items():
        if html_content_gib:
            filename = f"{row_id}.html"
            filepath = os.path.join(gib_files_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as gf:
                gf.write(html_content_gib)
            gib_file_paths[row_id] = f"gib_html/{filename}"
    
    # --- MODAL & JS ---
    json_db_str = json.dumps(js_details_db, ensure_ascii=False)
    invoice_db_str = json.dumps(js_invoice_db, ensure_ascii=False)
    gib_files_str = json.dumps(gib_file_paths, ensure_ascii=False)
    
    html_content += f"""
    <!-- Defter Detay Modal -->
    <div id="detailModal" class="modal">
      <div class="modal-content">
        <div class="modal-header">
            <div class="modal-title">Yevmiye Kayıt Detayı - <span id="modalDocNo"></span></div>
            <span class="close" onclick="closeModal('detailModal')">&times;</span>
        </div>
        <div id="modalBody">
            <table id="detailTable">
                <thead>
                    <tr><th>Hesap Kodu</th><th>B/A</th><th class="num">Tutar</th><th>Açıklama</th></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
      </div>
    </div>

    <!-- Fatura Görünümü Modal -->
    <div id="invoiceModal" class="modal">
      <div class="modal-content" style="max-width:850px;">
        <div class="modal-header">
            <div class="modal-title">Fatura Önizlemesi - <span id="invNo"></span></div>
            <span class="close" onclick="closeModal('invoiceModal')">&times;</span>
        </div>
        <div class="inv-box" id="invContent" style="padding:20px; font-size:14px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:20px; border-bottom:1px solid #ddd; padding-bottom:10px;">
                <div><strong>Tarih:</strong> <span id="invDate">-</span></div>
                <div><strong>Tip:</strong> <span id="invType">-</span></div>
                <div><strong>Para Birimi:</strong> <span id="invCurrency">-</span></div>
                <div><strong>Döviz Kuru:</strong> <span id="invExchangeRate">-</span></div>
            </div>
            <div style="display:flex; gap:40px; margin-bottom:20px;">
                <div style="flex:1; border:1px solid #ddd; padding:10px; border-radius:4px;">
                    <h4 style="margin-top:0; color:#2E74B5;">Gönderen</h4>
                    <p><strong>Ad:</strong> <span id="senderName">-</span></p>
                    <p><strong>VKN/TCKN:</strong> <span id="senderVkn">-</span></p>
                    <p><strong>Vergi Dairesi:</strong> <span id="senderTaxOffice">-</span></p>
                    <p><strong>Adres:</strong> <span id="senderAddress">-</span></p>
                </div>
                <div style="flex:1; border:1px solid #ddd; padding:10px; border-radius:4px;">
                    <h4 style="margin-top:0; color:#2E74B5;">Alıcı</h4>
                    <p><strong>Ad:</strong> <span id="receiverName">-</span></p>
                    <p><strong>VKN/TCKN:</strong> <span id="receiverVkn">-</span></p>
                    <p><strong>Vergi Dairesi:</strong> <span id="receiverTaxOffice">-</span></p>
                    <p><strong>Adres:</strong> <span id="receiverAddress">-</span></p>
                </div>
            </div>
            <h4 style="color:#2E74B5;">Kalemler</h4>
            <table style="width:100%; border-collapse:collapse; margin-bottom:20px;">
                <thead style="background:#f5f5f5;">
                    <tr><th style="padding:8px; border:1px solid #ddd;">Ürün/Hizmet</th><th style="padding:8px; border:1px solid #ddd;">Miktar</th><th style="padding:8px; border:1px solid #ddd;">Birim</th><th style="padding:8px; border:1px solid #ddd;">Birim Fiyat</th><th style="padding:8px; border:1px solid #ddd;">KDV %</th><th style="padding:8px; border:1px solid #ddd;">KDV Tutarı</th><th style="padding:8px; border:1px solid #ddd;">Satır Toplamı</th></tr>
                </thead>
                <tbody id="itemsTableBody"></tbody>
            </table>
            <div style="display:flex; justify-content:flex-end; gap:30px; margin-bottom:20px; font-size:16px;">
                <div><strong>Matrah:</strong> <span id="invTaxExcl">-</span></div>
                <div><strong>KDV:</strong> <span id="invTax">-</span></div>
                <div><strong>İndirim:</strong> <span id="invDiscount">-</span></div>
                <div style="color:#2E74B5; font-weight:bold;"><strong>Toplam:</strong> <span id="invTotal">-</span></div>
            </div>
            <div style="display:flex; gap:20px;">
                <div style="flex:1;"><h5>Notlar</h5><ul id="notesList" style="margin:0; padding-left:20px;"></ul></div>
                <div style="flex:1;"><h5>İrsaliyeler</h5><ul id="despatchList" style="margin:0; padding-left:20px;"></ul></div>
                <div style="flex:1;"><h5>Siparişler</h5><ul id="orderList" style="margin:0; padding-left:20px;"></ul></div>
                <div style="flex:1;"><h5>Ödeme Bilgileri</h5><ul id="paymentList" style="margin:0; padding-left:20px;"></ul></div>
            </div>
        </div>
      </div>
    </div>

    <!-- GIB Resmi Görüntüleyici Modal -->
    <div id="gibModal" class="modal">
      <div class="modal-content" style="max-width:900px; max-height:90vh;">
        <div class="modal-header" style="background:#2E74B5;">
            <div class="modal-title" style="color:white;">GIB Resmi e-Fatura Görüntüleyici - <span id="gibInvNo"></span></div>
            <span class="close" onclick="closeModal('gibModal')" style="color:white;">&times;</span>
        </div>
        <iframe id="gibFrame" style="width:100%; height:80vh; border:none;"></iframe>
      </div>
    </div>

    <!-- JavaScript Functions (loaded first, isolated from data) -->
    <script>
        // Initialize data containers
        var detailData = {{}};
        var invoiceData = {{}};
        var gibFilePaths = {{}};
        
        function showGibInvoice(rowId) {{
            var filepath = gibFilePaths[rowId];
            if (filepath) {{
                window.open(filepath, '_blank');
            }} else {{
                // Try to find by invoice number directly
                var inv = invoiceData[rowId];
                if (inv && inv.No) {{
                    var directPath = 'gib_html/' + inv.No + '.html';
                    // Direct open - file:// protocol doesn't support fetch properly
                    var win = window.open(directPath, '_blank');
                    // If popup blocked or file doesn't exist, show message
                    setTimeout(function() {{
                        if (!win || win.closed) {{
                            alert('GİB görüntüsü bu fatura için mevcut değil veya popup engellenmiş olabilir.\\n\\nFatura No: ' + inv.No + '\\n\\nDosya: ' + directPath);
                        }}
                    }}, 500);
                }} else {{
                    alert('GİB görüntüsü bu fatura için mevcut değil.');
                }}
            }}
        }}
        
        function showDetails(rowId, docNo) {{
            document.getElementById("modalDocNo").innerText = docNo;
            var tbody = document.querySelector("#detailTable tbody");
            tbody.innerHTML = "";
            var lines = detailData[rowId];
            if (!lines) {{ alert('Defter verisi bulunamadı.'); return; }}
            var totalD = 0, totalC = 0;
            lines.forEach(function(line) {{
                var color = (line.DC === "C" || line.DC === "A") ? "color:red;" : "";
                var row = document.createElement("tr");
                row.innerHTML = '<td><b>' + line.Acc + '</b></td><td style="text-align:center; ' + color + '">' + line.DC + '</td><td class="num">' + parseFloat(line.Amt).toFixed(2) + '</td><td>' + line.Desc + '</td>';
                tbody.appendChild(row);
                if(line.DC === 'D' || line.DC === 'B') totalD += parseFloat(line.Amt); else totalC += parseFloat(line.Amt);
            }});
            var sumRow = document.createElement("tr"); sumRow.style.fontWeight = "bold"; sumRow.style.backgroundColor = "#eef";
            sumRow.innerHTML = '<td colspan="2" style="text-align:right">TOPLAM:</td><td class="num">' + totalD.toFixed(2) + ' | ' + totalC.toFixed(2) + '</td><td></td>';
            tbody.appendChild(sumRow);
            document.getElementById("detailModal").style.display = "block";
        }}
        
        function showInvoice(rowId) {{
            var inv = invoiceData[rowId];
            if (!inv) {{ alert('Fatura verisi bulunamadı.'); return; }}
            document.getElementById("invNo").innerText = inv.No;
            document.getElementById("invDate").innerText = inv.Date;
            document.getElementById("invType").innerText = inv.Type;
            document.getElementById("invCurrency").innerText = inv.Currency;
            document.getElementById("invTotal").innerText = inv.Total;
            document.getElementById("invTaxExcl").innerText = inv.TaxExcl;
            document.getElementById("invTax").innerText = inv.Tax;
            document.getElementById("invDiscount").innerText = inv.Discount;
            document.getElementById("invExchangeRate").innerText = inv.ExchangeRate || "-";
            document.getElementById("senderName").innerText = inv.Sender ? inv.Sender.Name || "-" : "-";
            document.getElementById("senderVkn").innerText = inv.Sender ? inv.Sender.VKN || "-" : "-";
            document.getElementById("senderTaxOffice").innerText = inv.Sender ? inv.Sender.TaxOffice || "-" : "-";
            document.getElementById("senderAddress").innerText = inv.Sender ? inv.Sender.Address || "-" : "-";
            document.getElementById("receiverName").innerText = inv.Receiver ? inv.Receiver.Name || "-" : "-";
            document.getElementById("receiverVkn").innerText = inv.Receiver ? inv.Receiver.VKN || "-" : "-";
            document.getElementById("receiverTaxOffice").innerText = inv.Receiver ? inv.Receiver.TaxOffice || "-" : "-";
            document.getElementById("receiverAddress").innerText = inv.Receiver ? inv.Receiver.Address || "-" : "-";
            var itemsTbody = document.getElementById("itemsTableBody");
            itemsTbody.innerHTML = "";
            if(inv.Items && inv.Items.length > 0) {{
                inv.Items.forEach(function(item) {{
                    var tr = document.createElement("tr");
                    tr.innerHTML = '<td>' + item.Name + '</td><td class="num">' + item.Quantity + '</td><td>' + item.Unit + '</td><td class="num">' + item.UnitPrice + '</td><td class="num">' + item.VATRate + '%</td><td class="num">' + item.VATAmount + '</td><td class="num">' + item.LineTotal + '</td>';
                    itemsTbody.appendChild(tr);
                }});
            }} else {{
                itemsTbody.innerHTML = "<tr><td colspan='7'>Kalem bilgisi bulunamadı.</td></tr>";
            }}
            var notesList = document.getElementById("notesList");
            notesList.innerHTML = "";
            if(inv.Notes && inv.Notes.length > 0) {{
                inv.Notes.forEach(function(note) {{
                    var li = document.createElement("li");
                    li.textContent = note;
                    notesList.appendChild(li);
                }});
            }}
            var despatchList = document.getElementById("despatchList");
            despatchList.innerHTML = "";
            if(inv.Despatches && inv.Despatches.length > 0) {{
                inv.Despatches.forEach(function(d) {{
                    var li = document.createElement("li");
                    li.textContent = d.ID + " (" + d.IssueDate + ")";
                    despatchList.appendChild(li);
                }});
            }}
            var orderList = document.getElementById("orderList");
            orderList.innerHTML = "";
            if(inv.Orders && inv.Orders.length > 0) {{
                inv.Orders.forEach(function(o) {{
                    var li = document.createElement("li");
                    li.textContent = o.ID + " (" + o.IssueDate + ")";
                    orderList.appendChild(li);
                }});
            }}
            var paymentList = document.getElementById("paymentList");
            paymentList.innerHTML = "";
            if(inv.PaymentMeans && inv.PaymentMeans.length > 0) {{
                inv.PaymentMeans.forEach(function(p) {{
                    var li = document.createElement("li");
                    li.textContent = p.Code + ": " + p.DueDate + " - " + p.Amount + " " + p.Currency;
                    paymentList.appendChild(li);
                }});
            }}
            document.getElementById("invoiceModal").style.display = "block";
        }}
        
        function closeModal(id) {{
            document.getElementById(id).style.display = "none";
        }}
        
        window.onclick = function(event) {{
            if (event.target.classList.contains("modal")) {{
                event.target.style.display = "none";
            }}
        }};
    </script>
    
    <!-- Data loaded in separate script (syntax errors won't break functions above) -->
    <script>
        try {{
            detailData = {json_db_str};
            invoiceData = {invoice_db_str};
            gibFilePaths = {gib_files_str};
            console.log("Data loaded successfully.");
        }} catch(e) {{
            console.error("Data loading error:", e);
            alert("Veri yüklenirken hata oluştu. Konsolu kontrol edin.");
        }}
    </script>

    </body>
    </html>
    """
    output_file = os.path.join(output_dir, "Fatura_Defter_Analiz_Raporu.html")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Rapor oluşturuldu: {output_file}")

if __name__ == "__main__":
    create_html_report()
