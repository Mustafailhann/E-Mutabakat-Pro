"""
QR Kod Fatura Okuyucu
E-Arşiv faturalardaki QR kodlardan veri çıkarır.
"""

import json
import re
from datetime import datetime

try:
    from pyzbar.pyzbar import decode
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def clean_qr_json(qr_data: str) -> str:
    """
    Bozuk QR JSON verisini temizle.
    E-Arşiv PDF'lerindeki QR'lar bazen fazladan boşluk, tırnak veya virgül içerir.
    """
    # Whitespace'leri normalleştir
    cleaned = ' '.join(qr_data.split())
    
    # Fazladan tırnak işaretlerini düzelt: "value"" -> "value"
    cleaned = re.sub(r'"\s*"([,}])', r'"\1', cleaned)
    
    # Fazladan virgülleri düzelt: ,, -> ,
    cleaned = re.sub(r',\s*,', ',', cleaned)
    
    # Sondaki fazla virgülü kaldır: ,} -> }
    cleaned = re.sub(r',\s*}', '}', cleaned)
    
    # Başlangıçta fazla boşluk/newline
    cleaned = cleaned.strip()
    
    return cleaned


def parse_e_arsiv_qr_json(qr_data: str) -> dict:
    """
    E-Arşiv QR JSON verisini parse edip fatura dict'ine dönüştür.
    
    QR JSON formatı örneği:
    {
        "vkntckn": "1234567890",
        "avkntckn": "0987654321",
        "tarih": "2025-09-15",
        "no": "ZGM2025000001234",
        "ettn": "550e8400-e29b-41d4-a716-446655440000",
        "tip": "SATIS",
        "senaryo": "TEMEL",
        "malhizmettoplam": 10000.00,
        "kdvmatrah(20)": 10000.00,
        "hesaplanankdv(20)": 2000.00
    }
    """
    # Önce JSON'ı temizle
    cleaned_data = clean_qr_json(qr_data)
    
    try:
        data = json.loads(cleaned_data)
    except json.JSONDecodeError:
        # JSON değilse URL olabilir, parse etmeye çalış
        data = parse_qr_url(qr_data)
        if not data:
            return None

    
    # Fatura numarasını ayrıştır
    fatura_no = data.get('no', '')
    seri_match = re.match(r'^([A-Za-z]+)(.+)$', fatura_no)
    seri = seri_match.group(1).upper() if seri_match else ''
    sira_no = seri_match.group(2) if seri_match else fatura_no
    
    # Tarihi dönüştür (YYYY-MM-DD -> DD.MM.YYYY)
    tarih_raw = data.get('tarih', '')
    if '-' in tarih_raw:
        parts = tarih_raw.split('-')
        if len(parts) == 3:
            tarih = f"{parts[2]}.{parts[1]}.{parts[0]}"
        else:
            tarih = tarih_raw
    else:
        tarih = tarih_raw
    
    # KDV dönemini hesapla
    kdv_donemi = ''
    try:
        if '-' in tarih_raw:
            dt = datetime.strptime(tarih_raw, '%Y-%m-%d')
        else:
            dt = datetime.strptime(tarih, '%d.%m.%Y')
        kdv_donemi = dt.strftime('%Y/%m')
    except:
        pass
    
    # Tutarları parse et
    def parse_amount(val):
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # Türkçe format: 1.234,56
            val = val.replace(' ', '').replace('₺', '').replace('TL', '')
            if ',' in val and '.' in val:
                val = val.replace('.', '').replace(',', '.')
            elif ',' in val:
                val = val.replace(',', '.')
            try:
                return float(val)
            except:
                return 0.0
        return 0.0
    
    # Farklı KDV oranları için matrah ve KDV
    kdv_matrah = 0.0
    kdv_tutar = 0.0
    
    # %20 KDV
    kdv_matrah += parse_amount(data.get('kdvmatrah(20)', 0))
    kdv_tutar += parse_amount(data.get('hesaplanankdv(20)', 0))
    
    # %10 KDV
    kdv_matrah += parse_amount(data.get('kdvmatrah(10)', 0))
    kdv_tutar += parse_amount(data.get('hesaplanankdv(10)', 0))
    
    # %1 KDV
    kdv_matrah += parse_amount(data.get('kdvmatrah(1)', 0))
    kdv_tutar += parse_amount(data.get('hesaplanankdv(1)', 0))
    
    # Fallback: genel matrah
    if kdv_matrah == 0:
        kdv_matrah = parse_amount(data.get('malhizmettoplam', 0))
    
    # Fatura tipi
    fatura_tipi = data.get('tip', '')
    senaryo = data.get('senaryo', '')
    
    # Satıcı VKN - boşlukları temizle
    satici_vkn = str(data.get('vkntckn', '')).strip()
    alici_vkn = str(data.get('avkntckn', '')).strip()
    
    return {
        'tarih': tarih,
        'seri': seri,
        'sira_no': sira_no,
        'satici_vkn': satici_vkn,
        'alici_vkn': alici_vkn,
        'satici_unvan': '',  # QR'da ünvan yok, boş bırak
        'mal_cinsi': '',  # QR'da mal cinsi yok, boş bırak
        'miktar': '',  # QR'da miktar yok, boş bırak
        'kdv_haric_tutar': kdv_matrah,
        'kdv': kdv_tutar,
        'tevkifat_kdv': 0.0,
        'iki_nolu_kdv': 0.0,
        'toplam_indirilen_kdv': kdv_tutar,
        'ggb_tescil_no': '',
        'kdv_donemi': kdv_donemi,
        'ettn': data.get('ettn', ''),
        'fatura_tipi': fatura_tipi,
        'senaryo': senaryo,
        'source_type': 'QR',
        'source_path': ''
    }


def parse_qr_url(qr_data: str) -> dict:
    """
    GİB doğrulama URL'sinden fatura bilgilerini çıkar.
    Örnek: https://ebelge.gib.gov.tr/...?p=...
    """
    if not qr_data or 'gib.gov.tr' not in qr_data.lower():
        return None
    
    # URL parametrelerini parse et
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(qr_data)
        params = parse_qs(parsed.query)
        
        # p parametresi genellikle base64 encoded JSON içerir
        if 'p' in params:
            import base64
            decoded = base64.b64decode(params['p'][0]).decode('utf-8')
            return json.loads(decoded)
    except:
        pass
    
    return None


def extract_qr_from_image(image) -> list:
    """
    PIL Image'dan QR kodları çıkar.
    
    Args:
        image: PIL Image nesnesi
        
    Returns:
        list: QR kod verilerinin listesi
    """
    if not PYZBAR_AVAILABLE:
        raise ImportError("pyzbar kütüphanesi gerekli: pip install pyzbar")
    
    qr_codes = decode(image)
    results = []
    
    for qr in qr_codes:
        try:
            data = qr.data.decode('utf-8')
            results.append(data)
        except:
            pass
    
    return results


def extract_invoices_from_qr_data(qr_data_list: list) -> list:
    """
    QR veri listesinden fatura listesi oluştur.
    
    Args:
        qr_data_list: QR kod veri string'leri listesi
        
    Returns:
        list: Fatura dict'leri listesi
    """
    invoices = []
    
    for qr_data in qr_data_list:
        invoice = parse_e_arsiv_qr_json(qr_data)
        if invoice:
            invoices.append(invoice)
    
    return invoices


# Test
if __name__ == "__main__":
    # Örnek QR JSON testi
    test_qr = '''
    {
        "vkntckn": "1234567890",
        "avkntckn": "0987654321",
        "tarih": "2025-09-15",
        "no": "ZGM2025000001234",
        "ettn": "550e8400-e29b-41d4-a716-446655440000",
        "tip": "SATIS",
        "senaryo": "TEMEL",
        "malhizmettoplam": 10000.00,
        "kdvmatrah(20)": 10000.00,
        "hesaplanankdv(20)": 2000.00
    }
    '''
    
    result = parse_e_arsiv_qr_json(test_qr)
    if result:
        print("QR Parse Başarılı:")
        print(f"  Fatura No: {result['seri']}{result['sira_no']}")
        print(f"  Tarih: {result['tarih']}")
        print(f"  VKN: {result['satici_vkn']}")
        print(f"  KDV Hariç: {result['kdv_haric_tutar']:.2f}")
        print(f"  KDV: {result['kdv']:.2f}")
    else:
        print("QR Parse Hatası!")
