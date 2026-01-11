# -*- coding: utf-8 -*-
"""
KDV 2 (2 No'lu KDV) Beyanname Parser
Sorumlu sıfatıyla verilen KDV beyannamesi için
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class KDV2Beyanname:
    """KDV 2 Beyanname verileri"""
    donem: str = ""
    vergi_no: str = ""
    unvan: str = ""
    
    # Matrah bilgileri
    sorumlu_matrah: float = 0.0  # Sorumlu sıfatıyla ödenen KDV matrahı
    
    # KDV tutarları
    hesaplanan_kdv: float = 0.0  # Hesaplanan KDV
    indirilecek_kdv: float = 0.0  # İndirilebilir KDV
    odenecek_kdv: float = 0.0  # Ödenecek KDV
    
    # Detaylar
    yurt_disi_hizmet: float = 0.0  # Yurt dışından alınan hizmetler
    dagitim_net: float = 0.0  # Dağıtım net tutarı


def parse_kdv2_beyanname_pdf(pdf_path: str) -> Optional[KDV2Beyanname]:
    """
    KDV 2 beyanname PDF'ini parse et
    
    Args:
        pdf_path: PDF dosya yolu
        
    Returns:
        KDV2Beyanname objesi veya None
    """
    try:
        import pdfplumber
        
        beyanname = KDV2Beyanname()
        
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + "\n"
            
            # Dönem
            donem_match = re.search(r'(\d{2})/(\d{4})', full_text)
            if donem_match:
                beyanname.donem = f"{donem_match.group(1)}/{donem_match.group(2)}"
            
            # VKN/TCKN
            vkn_match = re.search(r'(\d{10,11})', full_text)
            if vkn_match:
                beyanname.vergi_no = vkn_match.group(1)
            
            # Matrah değerleri
            # Sorumlu sıfatıyla beyan
            sorumlu_patterns = [
                r'[Ss]orumlu.*?[Mm]atrah.*?([\d.,]+)',
                r'[Tt]evkifat.*?[Mm]atrah.*?([\d.,]+)',
                r'[Hh]izmet.*?[Mm]atrah.*?([\d.,]+)',
            ]
            
            for pattern in sorumlu_patterns:
                match = re.search(pattern, full_text)
                if match:
                    beyanname.sorumlu_matrah = _parse_amount(match.group(1))
                    break
            
            # Hesaplanan KDV
            kdv_patterns = [
                r'[Hh]esaplanan.*?KDV.*?([\d.,]+)',
                r'KDV.*?[Tt]utar.*?([\d.,]+)',
            ]
            
            for pattern in kdv_patterns:
                match = re.search(pattern, full_text)
                if match:
                    beyanname.hesaplanan_kdv = _parse_amount(match.group(1))
                    break
            
            # Ödenecek KDV
            odenecek_match = re.search(r'[Öö]denecek.*?KDV.*?([\d.,]+)', full_text)
            if odenecek_match:
                beyanname.odenecek_kdv = _parse_amount(odenecek_match.group(1))
        
        return beyanname
        
    except ImportError:
        print("pdfplumber modülü yüklü değil")
        return None
    except Exception as e:
        print(f"KDV 2 parse hatası: {e}")
        return None


def _parse_amount(text: str) -> float:
    """Metin tutarı float'a çevir"""
    if not text:
        return 0.0
    try:
        # Türkçe format: 1.234,56 -> 1234.56
        cleaned = text.replace('.', '').replace(',', '.')
        return float(cleaned)
    except:
        return 0.0


if __name__ == "__main__":
    print("KDV 2 Beyanname Parser modülü yüklendi.")
