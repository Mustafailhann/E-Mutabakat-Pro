# -*- coding: utf-8 -*-
"""
XML Kebir Parser - CACHE formatındaki XML kebir dosyalarını parse eder
"""

import xml.etree.ElementTree as ET
from typing import Dict, Tuple, Optional


def parse_xml_kebir(file_path: str) -> Tuple[Dict, str]:
    """
    XML Kebir dosyasını parse et
    
    Args:
        file_path: XML kebir dosyası yolu
        
    Returns:
        (ledger_map, company_name) tuple'ı
        ledger_map = {belge_no: {'Lines': [{'Acc': hesap_kodu, 'Amt': tutar, 'DC': 'D/C', 'Desc': açıklama}]}}
    """
    ledger_map = {}
    company_name = ""
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Şirket adını bul
        company_elem = root.find('.//CompanyName') or root.find('.//Unvan') or root.find('.//FirmaAdi')
        if company_elem is not None:
            company_name = company_elem.text or ""
        
        # Yevmiye kayıtlarını bul
        # Farklı XML formatlarına uyum sağla
        records = (
            root.findall('.//Record') or 
            root.findall('.//Kayit') or 
            root.findall('.//YevmiyeKaydi') or
            root.findall('.//JournalEntry') or
            root.findall('.//Fis') or
            root.findall('.//Row')  # CACHE format
        )
        
        for record in records:
            # Belge numarası
            doc_no = (
                _get_text(record, 'DocNo') or
                _get_text(record, 'BelgeNo') or
                _get_text(record, 'FisNo') or
                _get_text(record, 'ID') or
                str(len(ledger_map) + 1)
            )
            
            if doc_no not in ledger_map:
                ledger_map[doc_no] = {'Lines': [], 'Desc': ''}
            
            # CACHE format için satırları işle
            lines = record.findall('.//Line') or record.findall('.//Satir') or [record]
            
            for line in lines:
                acc_code = (
                    _get_text(line, 'AccountCode') or
                    _get_text(line, 'HesapKodu') or
                    _get_text(line, 'Acc') or
                    _get_text(line, 'HESAPKODU') or
                    ""
                )
                
                if not acc_code:
                    continue
                
                # Tutar
                debit = float(_get_text(line, 'Debit') or _get_text(line, 'Borc') or _get_text(line, 'BORC') or 0)
                credit = float(_get_text(line, 'Credit') or _get_text(line, 'Alacak') or _get_text(line, 'ALACAK') or 0)
                
                amount = debit if debit > 0 else credit
                dc = 'D' if debit > 0 else 'C'
                
                # Açıklama
                desc = (
                    _get_text(line, 'Description') or
                    _get_text(line, 'Aciklama') or
                    _get_text(line, 'ACIKLAMA') or
                    _get_text(line, 'Desc') or
                    ""
                )
                
                ledger_map[doc_no]['Lines'].append({
                    'Acc': acc_code,
                    'Amt': amount,
                    'DC': dc,
                    'Desc': desc
                })
                
                if not ledger_map[doc_no]['Desc'] and desc:
                    ledger_map[doc_no]['Desc'] = desc
        
        print(f"XML Kebir: {len(ledger_map)} belge yüklendi")
        
    except Exception as e:
        print(f"XML Kebir parse hatası: {e}")
    
    return ledger_map, company_name


def _get_text(elem, tag: str) -> Optional[str]:
    """Element içinden tag'i bul ve text'ini döndür"""
    child = elem.find(f'.//{tag}')
    if child is not None and child.text:
        return child.text.strip()
    # Attribute olarak da kontrol et
    return elem.get(tag)


if __name__ == "__main__":
    print("XML Kebir Parser modülü yüklendi.")
