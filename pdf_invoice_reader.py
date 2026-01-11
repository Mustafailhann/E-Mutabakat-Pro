"""
PDF Fatura Okuyucu
PDF formatındaki faturaları okuyup KDV listesi için veri çıkarır.
QR kod okuma desteği ile E-Arşiv faturalardan otomatik veri çıkarır.
"""

import os
import re
from datetime import datetime

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pyzbar.pyzbar import decode as decode_qr, ZBarSymbol
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    ZBarSymbol = None


try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# QR modülünü import et
try:
    from qr_invoice_reader import parse_e_arsiv_qr_json
    QR_MODULE_AVAILABLE = True
except ImportError:
    QR_MODULE_AVAILABLE = False


def extract_invoice_from_pdf(pdf_path):
    """
    PDF faturasından KDV listesi için gerekli verileri çıkar.
    
    Returns:
        dict: Fatura verileri veya None
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber kütüphanesi gerekli: pip install pdfplumber")
    
    if not os.path.exists(pdf_path):
        print(f"PDF dosyası bulunamadı: {pdf_path}")
        return None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Tüm sayfaların metnini birleştir
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            if not full_text:
                print(f"PDF'den metin çıkarılamadı: {pdf_path}")
                return None
            
            # Fatura verilerini çıkar
            invoice_data = parse_invoice_text(full_text, pdf_path)
            return invoice_data
            
    except Exception as e:
        print(f"PDF okuma hatası ({pdf_path}): {e}")
        return None


def parse_invoice_text(text, pdf_path):
    """
    Fatura metninden verileri çıkar.
    Farklı fatura formatlarını destekler.
    """
    data = {
        'tarih': '',
        'seri': '',
        'sira_no': '',
        'satici_unvan': '',
        'satici_vkn': '',
        'mal_cinsi': '',
        'miktar': '',
        'kdv_haric_tutar': 0.0,
        'kdv': 0.0,
        'tevkifat_kdv': 0.0,
        'iki_nolu_kdv': 0.0,
        'toplam_indirilen_kdv': 0.0,
        'ggb_tescil_no': '',
        'kdv_donemi': '',
        'source_type': 'PDF',
        'source_path': pdf_path
    }
    
    # Fatura No patterns
    inv_patterns = [
        r'Fatura\s*No\s*[:\s]*([A-Z]{2,4}\d{10,})',
        r'FATURA\s*NO\s*[:\s]*([A-Z]{2,4}\d{10,})',
        r'Belge\s*No\s*[:\s]*([A-Z]{2,4}\d{10,})',
        r'e-Fatura\s*No\s*[:\s]*([A-Z]{2,4}\d{10,})',
        r'([A-Z]{3}\d{13,16})',  # ZGM2025000001473 formatı
    ]
    
    for pattern in inv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            inv_no = match.group(1)
            # Seri ve sıra no ayır
            seri_match = re.match(r'^([A-Za-z]+)(.+)$', inv_no)
            if seri_match:
                data['seri'] = seri_match.group(1).upper()
                data['sira_no'] = seri_match.group(2)
            else:
                data['sira_no'] = inv_no
            break
    
    # Tarih patterns
    date_patterns = [
        r'Fatura\s*Tarihi\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})',
        r'Tarih\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})',
        r'(\d{2}[./]\d{2}[./]\d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1).replace('/', '.')
            data['tarih'] = date_str
            # KDV dönemi
            try:
                dt = datetime.strptime(date_str, '%d.%m.%Y')
                data['kdv_donemi'] = dt.strftime('%Y/%m')
            except:
                pass
            break
    
    # VKN patterns (10 haneli)
    vkn_patterns = [
        r'VKN\s*[:\s]*(\d{10})',
        r'Vergi\s*Kimlik\s*No\s*[:\s]*(\d{10})',
        r'V\.K\.N\.\s*[:\s]*(\d{10})',
        r'(\d{10})',  # Fallback - ilk 10 haneli sayı
    ]
    
    for pattern in vkn_patterns:
        match = re.search(pattern, text)
        if match:
            vkn = match.group(1)
            # Telefon numarası olmamasını kontrol et
            if not vkn.startswith('05') and not vkn.startswith('00'):
                data['satici_vkn'] = vkn
                break
    
    # Firma adı - genellikle VKN'den önce veya sonra
    unvan_patterns = [
        r'Satıcı\s*[:\s]*([A-ZÇĞİÖŞÜa-zçğıöşü\s\.]+(?:LTD|A\.Ş\.|ŞTİ|SAN\.|TİC\.)[\w\s\.]*)',
        r'Ünvanı?\s*[:\s]*([A-ZÇĞİÖŞÜa-zçğıöşü\s\.]+(?:LTD|A\.Ş\.|ŞTİ|SAN\.|TİC\.)[\w\s\.]*)',
        r'([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü\s\.]+(?:LTD|A\.Ş\.|ŞTİ|SAN\.|TİC\.)[\w\s\.]*)',
    ]
    
    for pattern in unvan_patterns:
        match = re.search(pattern, text)
        if match:
            unvan = match.group(1).strip()
            if len(unvan) > 5:  # En az 5 karakter
                data['satici_unvan'] = unvan[:100]  # Max 100 karakter
                break
    
    # Tutar patterns
    # KDV Hariç / Matrah
    matrah_patterns = [
        r'Matrah\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
        r'KDV\s*Hariç\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
        r'Ara\s*Toplam\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
    ]
    
    for pattern in matrah_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = parse_amount(match.group(1))
            if amount > 0:
                data['kdv_haric_tutar'] = amount
                break
    
    # KDV Tutarı
    kdv_patterns = [
        r'KDV\s*Tutarı\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
        r'Hesaplanan\s*KDV\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
        r'KDV\s*%\s*\d+\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
        r'Toplam\s*KDV\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
    ]
    
    for pattern in kdv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = parse_amount(match.group(1))
            if amount > 0:
                data['kdv'] = amount
                data['toplam_indirilen_kdv'] = amount
                break
    
    # Genel Toplam (fallback hesaplama için)
    if data['kdv_haric_tutar'] == 0 and data['kdv'] == 0:
        toplam_patterns = [
            r'Genel\s*Toplam\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
            r'Toplam\s*Tutar\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
            r'Ödenecek\s*Tutar\s*[:\s]*([\d.,]+)\s*(?:TL|₺)?',
        ]
        
        for pattern in toplam_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                total = parse_amount(match.group(1))
                if total > 0:
                    # Varsayılan %20 KDV ile hesapla
                    data['kdv_haric_tutar'] = round(total / 1.20, 2)
                    data['kdv'] = round(total - data['kdv_haric_tutar'], 2)
                    data['toplam_indirilen_kdv'] = data['kdv']
                    break
    
    # Mal/Hizmet cinsi - ilk ürün satırını bul
    # Genellikle tablo formatında olur
    lines = text.split('\n')
    for line in lines:
        # Ürün satırı genellikle miktar ve fiyat içerir
        if re.search(r'\d+\s*(AD|KG|LT|MT|M2|KWH|TON)', line, re.IGNORECASE):
            # İlk kelime muhtemelen ürün adı
            words = line.split()
            if words:
                data['mal_cinsi'] = ' '.join(words[:5])[:100]  # İlk 5 kelime max 100 karakter
                # Miktarı bul
                qty_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(AD|KG|LT|MT|M2|KWH|TON)', line, re.IGNORECASE)
                if qty_match:
                    data['miktar'] = f"{qty_match.group(1)}{qty_match.group(2).upper()}"
                break
    
    # Varsayılan değerler
    if not data['mal_cinsi']:
        data['mal_cinsi'] = 'MAL/HİZMET'
    if not data['miktar']:
        data['miktar'] = '1AD'
    
    return data


def parse_amount(amount_str):
    """
    Tutar string'ini float'a çevir.
    '1.234,56' veya '1,234.56' formatlarını destekler.
    """
    if not amount_str:
        return 0.0
    
    # Temizle
    amount_str = amount_str.strip()
    
    # Türkçe format: 1.234,56
    if ',' in amount_str and '.' in amount_str:
        if amount_str.index('.') < amount_str.index(','):
            # Türkçe format
            amount_str = amount_str.replace('.', '').replace(',', '.')
        else:
            # İngilizce format
            amount_str = amount_str.replace(',', '')
    elif ',' in amount_str:
        # Sadece virgül var - ondalık ayracı
        amount_str = amount_str.replace(',', '.')
    elif '.' in amount_str:
        # Kontrol et - binlik mi ondalık mı
        parts = amount_str.split('.')
        if len(parts[-1]) == 3:
            # Muhtemelen binlik ayraç
            amount_str = amount_str.replace('.', '')
    
    try:
        return float(amount_str)
    except:
        return 0.0


def load_invoices_from_pdf_folder(folder_path):
    """
    Klasördeki tüm PDF faturalarını yükle.
    """
    invoices = []
    
    if not os.path.exists(folder_path):
        print(f"Klasör bulunamadı: {folder_path}")
        return invoices
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(folder_path, filename)
            inv_data = extract_invoice_from_pdf(pdf_path)
            if inv_data:
                invoices.append(inv_data)
    
    return invoices


def extract_invoices_from_bulk_pdf(pdf_path, progress_callback=None):
    """
    Çok sayfalı PDF dosyasından faturaları çıkar.
    Her sayfa veya sayfa grubu ayrı bir fatura olarak işlenir.
    
    Args:
        pdf_path: PDF dosya yolu
        progress_callback: İlerleme callback fonksiyonu (current, total)
    
    Returns:
        list: Fatura verileri listesi
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber kütüphanesi gerekli: pip install pdfplumber")
    
    if not os.path.exists(pdf_path):
        print(f"PDF dosyası bulunamadı: {pdf_path}")
        return []
    
    invoices = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Toplam sayfa: {total_pages}")
            
            current_invoice_text = ""
            current_invoice_start_page = 1
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                
                # İlerleme bildirimi
                if progress_callback:
                    progress_callback(page_num, total_pages)
                
                # Yeni fatura başlangıcı kontrolü
                is_new_invoice = False
                
                # Fatura başlangıç işaretleri
                new_invoice_patterns = [
                    r'Fatura\s*No\s*[:\s]*[A-Z]{2,4}\d{10,}',
                    r'e-Fatura\s*No',
                    r'FATURA\s*NO',
                    r'Belge\s*No\s*[:\s]*[A-Z]{2,4}\d{10,}',
                    r'[A-Z]{3}20\d{2}\d{10,}',  # ZGM2025... formatı
                ]
                
                for pattern in new_invoice_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        is_new_invoice = True
                        break
                
                if is_new_invoice and current_invoice_text:
                    # Önceki faturayı işle
                    inv_data = parse_invoice_text(current_invoice_text, f"{pdf_path}#page{current_invoice_start_page}")
                    if inv_data and (inv_data.get('sira_no') or inv_data.get('kdv', 0) > 0):
                        invoices.append(inv_data)
                    
                    # Yeni fatura başlat
                    current_invoice_text = text + "\n"
                    current_invoice_start_page = page_num
                else:
                    current_invoice_text += text + "\n"
                
                # Her 20 sayfada bir log
                if page_num % 20 == 0:
                    print(f"  İşleniyor: {page_num}/{total_pages} sayfa, {len(invoices)} fatura bulundu")
            
            # Son faturayı işle
            if current_invoice_text:
                inv_data = parse_invoice_text(current_invoice_text, f"{pdf_path}#page{current_invoice_start_page}")
                if inv_data and (inv_data.get('sira_no') or inv_data.get('kdv', 0) > 0):
                    invoices.append(inv_data)
            
            print(f"Toplam {len(invoices)} fatura bulundu")
    
    except Exception as e:
        print(f"PDF okuma hatası ({pdf_path}): {e}")
    
    return invoices


def extract_qr_from_pdf_page(page, resolution=200):
    """
    PDF sayfasından QR kod oku ve fatura verisine dönüştür.
    Birden fazla çözünürlük dener.
    
    Args:
        page: pdfplumber page nesnesi
        resolution: Başlangıç görüntü çözünürlüğü (dpi)
        
    Returns:
        dict: Fatura verisi veya None
    """
    if not PYZBAR_AVAILABLE or not PIL_AVAILABLE:
        return None
    
    if not QR_MODULE_AVAILABLE:
        return None
    
    # Farklı çözünürlükleri dene
    resolutions = [150, 200, 300]
    
    for res in resolutions:
        try:
            # Sayfayı görüntüye çevir
            page_image = page.to_image(resolution=res)
            pil_image = page_image.original
            
            # QR kodları bul (sadece QR kod, barcode değil)
            if ZBarSymbol:
                qr_codes = decode_qr(pil_image, symbols=[ZBarSymbol.QRCODE])
            else:
                qr_codes = decode_qr(pil_image)
            
            for qr in qr_codes:
                try:
                    qr_data = qr.data.decode('utf-8').strip()
                    # JSON olup olmadığını kontrol et
                    if qr_data.startswith('{') or '{' in qr_data:
                        # { karakterini bul ve oradan başla
                        start_idx = qr_data.find('{')
                        if start_idx >= 0:
                            json_data = qr_data[start_idx:]
                            invoice = parse_e_arsiv_qr_json(json_data)
                            if invoice:
                                return invoice
                except:
                    pass
        except Exception as e:
            pass
    
    return None


def extract_invoices_from_bulk_pdf_with_qr(pdf_path, progress_callback=None, use_qr=True):
    """
    Çok sayfalı PDF dosyasından faturaları çıkar.
    QR kod varsa QR'dan, yoksa metin analizinden veri çıkarır.
    
    Args:
        pdf_path: PDF dosya yolu
        progress_callback: İlerleme callback fonksiyonu (current, total)
        use_qr: QR kod okuma aktif mi
        
    Returns:
        list: Fatura verileri listesi
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber kütüphanesi gerekli: pip install pdfplumber")
    
    if not os.path.exists(pdf_path):
        print(f"PDF dosyası bulunamadı: {pdf_path}")
        return []
    
    invoices = []
    qr_success_count = 0
    text_success_count = 0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Toplam sayfa: {total_pages}")
            print(f"QR okuma: {'Aktif' if use_qr and PYZBAR_AVAILABLE else 'Pasif'}")
            
            current_invoice_text = ""
            current_invoice_start_page = 1
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                
                # İlerleme bildirimi
                if progress_callback:
                    progress_callback(page_num, total_pages)
                
                # Önce QR koddan okumayı dene
                qr_invoice = None
                if use_qr and PYZBAR_AVAILABLE:
                    qr_invoice = extract_qr_from_pdf_page(page)
                    if qr_invoice:
                        qr_invoice['source_path'] = f"{pdf_path}#page{page_num}"
                        invoices.append(qr_invoice)
                        qr_success_count += 1
                        continue  # QR başarılı, metne gerek yok
                
                # QR yoksa veya okunamazsa metin analizi
                # Yeni fatura başlangıcı kontrolü
                is_new_invoice = False
                
                new_invoice_patterns = [
                    r'Fatura\s*No\s*[:\s]*[A-Z]{2,4}\d{10,}',
                    r'e-Fatura\s*No',
                    r'FATURA\s*NO',
                    r'e-Arşiv\s*Fatura',
                    r'Belge\s*No\s*[:\s]*[A-Z]{2,4}\d{10,}',
                    r'[A-Z]{3}20\d{2}\d{10,}',
                ]
                
                for pattern in new_invoice_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        is_new_invoice = True
                        break
                
                if is_new_invoice and current_invoice_text:
                    # Önceki faturayı işle
                    inv_data = parse_invoice_text(current_invoice_text, f"{pdf_path}#page{current_invoice_start_page}")
                    if inv_data and (inv_data.get('sira_no') or inv_data.get('kdv', 0) > 0):
                        invoices.append(inv_data)
                        text_success_count += 1
                    
                    current_invoice_text = text + "\n"
                    current_invoice_start_page = page_num
                else:
                    current_invoice_text += text + "\n"
                
                # Her 20 sayfada bir log
                if page_num % 20 == 0:
                    print(f"  İşleniyor: {page_num}/{total_pages} sayfa, {len(invoices)} fatura (QR: {qr_success_count}, Metin: {text_success_count})")
            
            # Son faturayı işle
            if current_invoice_text:
                inv_data = parse_invoice_text(current_invoice_text, f"{pdf_path}#page{current_invoice_start_page}")
                if inv_data and (inv_data.get('sira_no') or inv_data.get('kdv', 0) > 0):
                    invoices.append(inv_data)
                    text_success_count += 1
            
            print(f"\n=== Sonuç ===")
            print(f"Toplam fatura: {len(invoices)}")
            print(f"  QR'dan okunan: {qr_success_count}")
            print(f"  Metinden okunan: {text_success_count}")
    
    except Exception as e:
        print(f"PDF okuma hatası ({pdf_path}): {e}")
        import traceback
        traceback.print_exc()
    
    return invoices


def extract_invoices_from_image_pdf(pdf_path, progress_callback=None):
    """
    Görüntü tabanlı PDF dosyasından QR kodları tarayarak faturaları çıkar.
    E-Arşiv fatura PDF'leri için (metin içermeyen, sadece görüntü).
    Tüm sayfalardaki QR kodları tarar.
    
    Args:
        pdf_path: PDF dosya yolu
        progress_callback: İlerleme callback fonksiyonu (current, total)
        
    Returns:
        list: Fatura verileri listesi
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber kütüphanesi gerekli: pip install pdfplumber")
    
    if not PYZBAR_AVAILABLE:
        raise ImportError("pyzbar kütüphanesi gerekli: pip install pyzbar")
    
    if not os.path.exists(pdf_path):
        print(f"PDF dosyası bulunamadı: {pdf_path}")
        return []
    
    invoices = []
    seen_invoice_nos = set()  # Tekrar eden faturaları önle
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Görüntü PDF tarama başladı: {total_pages} sayfa")
            
            for page_num, page in enumerate(pdf.pages, 1):
                # İlerleme bildirimi
                if progress_callback:
                    progress_callback(page_num, total_pages)
                
                # Sayfayı görüntüye çevir ve QR tara
                qr_invoice = extract_qr_from_pdf_page(page, resolution=200)
                
                if qr_invoice:
                    # Sayfa numarasını ekle
                    qr_invoice['source_path'] = f"{pdf_path}#page{page_num}"
                    qr_invoice['page_num'] = page_num
                    invoices.append(qr_invoice)
                    inv_no = f"{qr_invoice.get('seri', '')}{qr_invoice.get('sira_no', '')}"
                    print(f"  Sayfa {page_num}: Fatura {inv_no} bulundu")
                else:
                    # QR okunamayan sayfalar için placeholder ekle
                    placeholder = {
                        'tarih': '',
                        'seri': '',
                        'sira_no': f'SAYFA {page_num} - OKUNAMADI',
                        'satici_vkn': '',
                        'satici_unvan': 'QR Kod Okunamadı',
                        'mal_cinsi': 'PDF sayfasını görüntülemek için Fatura butonuna tıklayın',
                        'miktar': '',
                        'kdv_haric_tutar': 0.0,
                        'kdv': 0.0,
                        'tevkifat_kdv': 0.0,
                        'iki_nolu_kdv': 0.0,
                        'toplam_indirilen_kdv': 0.0,
                        'ggb_tescil_no': '',
                        'kdv_donemi': '',
                        'source_type': 'PDF-OKUNAMADI',
                        'source_path': f"{pdf_path}#page{page_num}",
                        'page_num': page_num
                    }
                    invoices.append(placeholder)
                    print(f"  Sayfa {page_num}: QR okunamadı - placeholder eklendi")
                
                # Her 5 sayfada bir log
                if page_num % 5 == 0:
                    print(f"  İşleniyor: {page_num}/{total_pages} sayfa, {len(invoices)} fatura bulundu")
            
            print(f"\n=== Sonuç ===")
            print(f"Toplam fatura: {len(invoices)}")
    
    except Exception as e:
        print(f"PDF okuma hatası ({pdf_path}): {e}")
        import traceback
        traceback.print_exc()
    
    return invoices


def smart_extract_invoices_from_pdf(pdf_path, progress_callback=None):
    """
    PDF tipini otomatik algılayıp uygun yöntemi kullanır.
    - Metin içeriyorsa: metin + QR analizi
    - Sadece görüntüyse: QR tarama
    
    Args:
        pdf_path: PDF dosya yolu
        progress_callback: İlerleme callback fonksiyonu
        
    Returns:
        list: Fatura verileri listesi
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber kütüphanesi gerekli")
    
    if not os.path.exists(pdf_path):
        print(f"PDF dosyası bulunamadı: {pdf_path}")
        return []
    
    # İlk birkaç sayfadan metin çıkarmayı dene
    has_text = False
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:3]:
                text = page.extract_text()
                if text and len(text.strip()) > 50:
                    has_text = True
                    break
    except:
        pass
    
    if has_text:
        print("Metin tabanlı PDF algılandı - Hibrit tarama (metin + QR)")
        return extract_invoices_from_bulk_pdf_with_qr(pdf_path, progress_callback, use_qr=True)
    else:
        print("Görüntü tabanlı PDF algılandı - QR tarama")
        return extract_invoices_from_image_pdf(pdf_path, progress_callback)


# Test
if __name__ == "__main__":
    # Test dizini
    test_dir = r"c:\Users\Asus\Desktop\agent ff"
    
    # QR modülü kontrolü
    print(f"pdfplumber: {'✓' if PDFPLUMBER_AVAILABLE else '✗'}")
    print(f"pyzbar (QR): {'✓' if PYZBAR_AVAILABLE else '✗'}")
    print(f"PIL: {'✓' if PIL_AVAILABLE else '✗'}")
    print(f"QR modülü: {'✓' if QR_MODULE_AVAILABLE else '✗'}")
    print()
    
    # PDF dosyası ara
    for f in os.listdir(test_dir):
        if f.lower().endswith('.pdf') and 'fatura' in f.lower():
            print(f"\n{'='*60}")
            print(f"Test: {f}")
            print('='*60)
            
            pdf_path = os.path.join(test_dir, f)
            
            # QR destekli bulk okuma
            invoices = extract_invoices_from_bulk_pdf_with_qr(pdf_path, use_qr=True)
            
            if invoices:
                print(f"\nİlk 3 fatura:")
                for i, inv in enumerate(invoices[:3], 1):
                    print(f"\n  {i}. Fatura:")
                    print(f"     No: {inv.get('seri', '')}{inv.get('sira_no', '')}")
                    print(f"     Tarih: {inv.get('tarih', '')}")
                    print(f"     VKN: {inv.get('satici_vkn', '')}")
                    print(f"     KDV Hariç: {inv.get('kdv_haric_tutar', 0):.2f} ₺")
                    print(f"     KDV: {inv.get('kdv', 0):.2f} ₺")
                    print(f"     Kaynak: {inv.get('source_type', 'Metin')}")
            break
