# -*- coding: utf-8 -*-
"""
Beyanname Parser Modülü - KDV ve Muhtasar Beyannamelerini PDF'den Parse Eder

GİB'den indirilen beyanname PDF'lerini okuyarak yapılandırılmış veri çıkarır.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
import re
import os

# PDF okuma için pdfplumber kullanılacak
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Uyarı: pdfplumber yüklü değil. PDF parse edilemeyecek.")


@dataclass
class KDVBeyanname:
    """KDV Beyannamesi Verileri"""
    donem: str = ""  # "Kasım 2025" veya "2025/11"
    vkn: str = ""  # Vergi Kimlik No
    unvan: str = ""  # Mükellef Unvanı
    
    # Matrah ve Vergiler
    teslim_hizmet_toplami: float = 0.0  # Mal teslimi ve hizmet toplamı
    hesaplanan_kdv: float = 0.0  # 391 hesabı karşılığı
    
    # İndirimler
    indirilecek_kdv_toplami: float = 0.0  # 191 hesabı karşılığı
    onceki_donem_devreden: float = 0.0  # Önceki dönemden devreden KDV
    
    # Sonuç
    odenecek_kdv: float = 0.0  # Ödenecek KDV
    sonraki_doneme_devreden: float = 0.0  # 190 hesabı karşılığı
    
    # Detaylar (opsiyonel)
    kdv_oranlari: Dict[int, float] = field(default_factory=dict)  # %20: tutar, %10: tutar


@dataclass
class MuhtasarBeyanname:
    """Muhtasar Beyannamesi Verileri"""
    donem: str = ""
    vkn: str = ""
    unvan: str = ""
    
    # Stopaj Türleri
    ucret_stopaji: float = 0.0  # Ücretlere ait Gelir Vergisi stopajı (360.01)
    serbest_meslek_stopaji: float = 0.0  # Serbest meslek ödemeleri (360.02)
    yillara_sari_insaat: float = 0.0  # Yıllara sari inşaat (360.03)
    kira_stopaji: float = 0.0  # Kira ödemeleri stopajı (360.04)
    diger_stopaj: float = 0.0  # Diğer stopajlar
    
    # Toplam
    toplam_stopaj: float = 0.0
    
    # Damga Vergisi
    damga_vergisi: float = 0.0
    
    # Çalışan Listesi (PDF'den çekilen isimler)
    employees: List[str] = field(default_factory=list)


def parse_kdv_beyanname_pdf(pdf_path: str) -> Optional[KDVBeyanname]:
    """
    KDV Beyannamesi PDF'ini parse et.
    
    Args:
        pdf_path: PDF dosya yolu
        
    Returns:
        KDVBeyanname objesi veya None (parse edilemezse)
    """
    if not PDF_AVAILABLE:
        print("pdfplumber yüklü değil. Lütfen: pip install pdfplumber")
        return None
    
    if not os.path.exists(pdf_path):
        print(f"Dosya bulunamadı: {pdf_path}")
        return None
    
    beyanname = KDVBeyanname()
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            # Dönem çıkar (örn: "Yıl 2025" + "Ay Ekim")
            yil_match = re.search(r'Yıl\s+(\d{4})', full_text)
            ay_match = re.search(r'Ay\s+(\w+)', full_text)
            if yil_match and ay_match:
                beyanname.donem = f"{ay_match.group(1)} {yil_match.group(1)}"
            
            # VKN çıkar
            vkn_match = re.search(r'Vergi Kimlik Numarası\s+(\d{10,11})', full_text)
            if vkn_match:
                beyanname.vkn = vkn_match.group(1)
            
            # Unvan çıkar
            unvan_match = re.search(r'Soyadı \(Unvanı\)\s+(.+?)(?:\n|Adı)', full_text)
            if unvan_match:
                beyanname.unvan = unvan_match.group(1).strip()
            
            # Hesaplanan KDV (Toplam Katma Değer Vergisi veya Hesaplanan Katma Değer Vergisi)
            patterns_hesaplanan = [
                r'Hesaplanan Katma Değer Vergisi\s+([\d.,]+)',
                r'Toplam Katma Değer Vergisi\s+([\d.,]+)',
            ]
            for pattern in patterns_hesaplanan:
                match = re.search(pattern, full_text)
                if match:
                    beyanname.hesaplanan_kdv = _parse_turkish_number(match.group(1))
                    break
            
            # İndirimler Toplamı
            indirim_match = re.search(r'İndirimler Toplamı\s+([\d.,]+)', full_text)
            if indirim_match:
                beyanname.indirilecek_kdv_toplami = _parse_turkish_number(indirim_match.group(1))
            
            # Önceki Dönemden Devreden
            devreden_match = re.search(r'Önceki Dönemden Devreden.*?([\d.,]+)', full_text, re.DOTALL)
            if devreden_match:
                beyanname.onceki_donem_devreden = _parse_turkish_number(devreden_match.group(1))
            
            # Ödenecek KDV
            odenecek_match = re.search(r'(?:Bu Dönemde )?Ödenmesi Gereken Katma Değer Vergisi\s+([\d.,]+)', full_text)
            if odenecek_match:
                beyanname.odenecek_kdv = _parse_turkish_number(odenecek_match.group(1))
            
            # Sonraki Döneme Devreden
            sonraki_match = re.search(r'Sonraki Döneme Devreden Katma Değer Vergisi\s+([\d.,]+)', full_text)
            if sonraki_match:
                beyanname.sonraki_doneme_devreden = _parse_turkish_number(sonraki_match.group(1))
            
            # Matrah toplamı
            matrah_match = re.search(r'Matrah Toplamı\s+([\d.,]+)', full_text)
            if matrah_match:
                beyanname.teslim_hizmet_toplami = _parse_turkish_number(matrah_match.group(1))
            
            return beyanname
            
    except Exception as e:
        print(f"KDV beyanname parse hatası: {e}")
        return None


def parse_muhtasar_beyanname_pdf(pdf_path: str) -> Optional[MuhtasarBeyanname]:
    """
    Muhtasar Beyannamesi PDF'ini parse et.
    """
    if not PDF_AVAILABLE:
        print("pdfplumber yüklü değil.")
        return None
    
    if not os.path.exists(pdf_path):
        print(f"Dosya bulunamadı: {pdf_path}")
        return None
    
    beyanname = MuhtasarBeyanname()
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            # Dönem
            donem_match = re.search(r'Dönem[:\s]*(\d{4}[/\-]\d{1,2})', full_text)
            if donem_match:
                beyanname.donem = donem_match.group(1)
            
            # Ücret stopajı (Gelir Vergisi Kesintisi - Ücret)
            ucret_match = re.search(r'Ücret[^0-9]*([0-9.,]+)', full_text, re.IGNORECASE)
            if ucret_match:
                beyanname.ucret_stopaji = _parse_turkish_number(ucret_match.group(1))
            
            # Serbest meslek stopajı
            serbest_match = re.search(r'Serbest Meslek[^0-9]*([0-9.,]+)', full_text, re.IGNORECASE)
            if serbest_match:
                beyanname.serbest_meslek_stopaji = _parse_turkish_number(serbest_match.group(1))
            
            # Kira stopajı
            kira_match = re.search(r'Kira[^0-9]*([0-9.,]+)', full_text, re.IGNORECASE)
            if kira_match:
                beyanname.kira_stopaji = _parse_turkish_number(kira_match.group(1))
            
            # Toplam
            toplam_match = re.search(r'Toplam Vergi[\s:]*([0-9.,]+)', full_text, re.IGNORECASE)
            if toplam_match:
                beyanname.toplam_stopaj = _parse_turkish_number(toplam_match.group(1))
            
            # Damga Vergisi
            damga_match = re.search(r'Damga Vergisi[\s:]*([0-9.,]+)', full_text, re.IGNORECASE)
            if damga_match:
                beyanname.damga_vergisi = _parse_turkish_number(damga_match.group(1))
            
            # Çalışan isimlerini çek (Muhtasar listesinden)
            # TC Kimlik No + Ad Soyad formatı aranıyor
            # Örnek: "12345678901 AHMET YILMAZ"
            employee_patterns = [
                r'(\d{11})\s+([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü]+)',  # TC + Ad Soyad
                r'([A-ZÇĞİÖŞÜ]{2,})\s+([A-ZÇĞİÖŞÜ]{2,})\s+\d{11}',  # Ad Soyad + TC
            ]
            
            employees_found = set()
            for pattern in employee_patterns:
                matches = re.findall(pattern, full_text)
                for match in matches:
                    if isinstance(match, tuple):
                        # TC + Ad formatı
                        if match[0].isdigit():
                            name = match[1].strip()
                        else:
                            name = f"{match[0]} {match[1]}".strip()
                        if name and len(name) > 4:
                            employees_found.add(name.upper())
            
            # PDF tablolarından da dene
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if row:
                                for cell in row:
                                    if cell and isinstance(cell, str):
                                        # Sadece harf içeren ve 2+ kelime olan hücreleri al
                                        words = cell.strip().split()
                                        if len(words) >= 2 and all(w.isalpha() or w in 'ÇĞİÖŞÜçğıöşü' for w in ''.join(words)):
                                            name = ' '.join(words).upper()
                                            if 6 < len(name) < 50:
                                                employees_found.add(name)
            
            beyanname.employees = list(employees_found)
            print(f"Muhtasardan {len(beyanname.employees)} çalışan bulundu")
            
            return beyanname
            
    except Exception as e:
        print(f"Muhtasar parse hatası: {e}")
        return None


def _parse_turkish_number(text: str) -> float:
    """
    Türkçe sayı formatını parse et.
    "1.234.567,89" -> 1234567.89
    """
    if not text:
        return 0.0
    
    # Boşlukları temizle
    text = text.strip()
    
    # Binlik ayracı (nokta) kaldır, ondalık ayracı (virgül) noktaya çevir
    text = text.replace('.', '').replace(',', '.')
    
    try:
        return float(text)
    except ValueError:
        return 0.0


def create_kdv_beyanname_manual(
    donem: str,
    hesaplanan_kdv: float,
    indirilecek_kdv: float,
    onceki_donem_devreden: float = 0.0
) -> KDVBeyanname:
    """
    Manuel veri girişi ile KDV beyanname oluştur.
    """
    beyanname = KDVBeyanname(
        donem=donem,
        hesaplanan_kdv=hesaplanan_kdv,
        indirilecek_kdv_toplami=indirilecek_kdv,
        onceki_donem_devreden=onceki_donem_devreden
    )
    
    # Ödenecek veya devreden hesapla
    net = hesaplanan_kdv - indirilecek_kdv - onceki_donem_devreden
    if net > 0:
        beyanname.odenecek_kdv = net
    else:
        beyanname.sonraki_doneme_devreden = abs(net)
    
    return beyanname


def create_muhtasar_beyanname_manual(
    donem: str,
    ucret_stopaji: float = 0.0,
    serbest_meslek: float = 0.0,
    kira_stopaji: float = 0.0,
    diger: float = 0.0
) -> MuhtasarBeyanname:
    """
    Manuel veri girişi ile Muhtasar beyanname oluştur.
    """
    beyanname = MuhtasarBeyanname(
        donem=donem,
        ucret_stopaji=ucret_stopaji,
        serbest_meslek_stopaji=serbest_meslek,
        kira_stopaji=kira_stopaji,
        diger_stopaj=diger,
        toplam_stopaj=ucret_stopaji + serbest_meslek + kira_stopaji + diger
    )
    return beyanname


if __name__ == "__main__":
    # Test
    print("Beyanname Parser Modülü")
    print("========================")
    
    # Manuel test
    kdv = create_kdv_beyanname_manual(
        donem="2025/11",
        hesaplanan_kdv=150000,
        indirilecek_kdv=120000,
        onceki_donem_devreden=5000
    )
    print(f"\nKDV Beyanname (Manuel):")
    print(f"  Dönem: {kdv.donem}")
    print(f"  Hesaplanan KDV: {kdv.hesaplanan_kdv:,.2f} TL")
    print(f"  İndirilecek KDV: {kdv.indirilecek_kdv_toplami:,.2f} TL")
    print(f"  Önceki Dönem Devreden: {kdv.onceki_donem_devreden:,.2f} TL")
    print(f"  Ödenecek KDV: {kdv.odenecek_kdv:,.2f} TL")
    print(f"  Sonraki Döneme Devreden: {kdv.sonraki_doneme_devreden:,.2f} TL")
