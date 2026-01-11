# -*- coding: utf-8 -*-
"""
Tüm faturalar için GİB HTML dosyalarını oluştur
Agent FF klasöründeki tüm ZIP dosyalarından
"""

import os
import sys
import zipfile
import io
import re

BASE_DIR = r"c:\Users\Asus\Desktop\agent ff"
os.chdir(BASE_DIR)

from gib_viewer import transform_invoice_to_html

OUTPUT_DIR = os.path.join(BASE_DIR, "gib_html")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def find_all_zips(base_dir):
    """Tüm ZIP dosyalarını bul"""
    zips = []
    for root, dirs, files in os.walk(base_dir):
        # Bazı klasörleri atla
        if '.git' in root or 'node_modules' in root:
            continue
        for f in files:
            if f.lower().endswith('.zip'):
                zips.append(os.path.join(root, f))
    return zips

def extract_invoice_no(xml_content):
    """XML içinden fatura numarasını çıkar"""
    # Çeşitli formatları dene
    patterns = [
        r'<[^>]*:ID[^>]*>([A-Z]{3}\d{13,16})</[^>]*:ID>',  # AAA, YGE, etc.
        r'<ID>([A-Z]{3}\d{13,16})</ID>',
        r'<cbc:ID>([A-Z]{3}\d{13,16})</cbc:ID>',
    ]
    for pattern in patterns:
        match = re.search(pattern, xml_content)
        if match:
            return match.group(1)
    return None

def process_zip(zip_path):
    """ZIP dosyasındaki tüm faturaları işle"""
    count = 0
    errors = 0
    skipped = 0
    
    if not os.path.exists(zip_path):
        return 0, 0, 0
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            for name in z.namelist():
                # Nested ZIP'leri de işle
                if name.lower().endswith('.zip'):
                    try:
                        nested_data = z.read(name)
                        with zipfile.ZipFile(io.BytesIO(nested_data), 'r') as nested_z:
                            for nested_name in nested_z.namelist():
                                if nested_name.lower().endswith('.xml'):
                                    try:
                                        content = nested_z.read(nested_name)
                                        c, e, s = process_xml(content, nested_name)
                                        count += c
                                        errors += e
                                        skipped += s
                                    except:
                                        errors += 1
                    except:
                        pass
                
                # Doğrudan XML dosyaları
                elif name.lower().endswith('.xml'):
                    try:
                        content = z.read(name)
                        c, e, s = process_xml(content, name)
                        count += c
                        errors += e
                        skipped += s
                    except:
                        errors += 1
                        
    except Exception as e:
        print(f"  HATA: {e}")
    
    return count, errors, skipped

def process_xml(content, name):
    """Tek bir XML'i işle"""
    try:
        xml_text = content.decode('utf-8', errors='ignore')
        
        # Fatura numarasını bul
        inv_no = extract_invoice_no(xml_text)
        if not inv_no:
            return 0, 0, 0
        
        # HTML dosyası zaten var mı?
        html_path = os.path.join(OUTPUT_DIR, f"{inv_no}.html")
        if os.path.exists(html_path):
            return 0, 0, 1  # Atla
        
        # XSLT dönüşümü
        try:
            html = transform_invoice_to_html(xml_text)
            if html:
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                return 1, 0, 0
            else:
                return 0, 1, 0
        except:
            return 0, 1, 0
            
    except:
        return 0, 1, 0

print("=" * 50)
print("GIB HTML Olusturucu - Agent FF")
print("=" * 50)

# Tüm ZIP'leri bul
print(f"\nZIP dosyaları aranıyor: {BASE_DIR}")
zip_files = find_all_zips(BASE_DIR)
print(f"Bulunan ZIP sayısı: {len(zip_files)}")

total_count = 0
total_errors = 0
total_skipped = 0

for i, zip_path in enumerate(zip_files):
    rel_path = os.path.relpath(zip_path, BASE_DIR)
    print(f"\n[{i+1}/{len(zip_files)}] {rel_path}")
    count, errors, skipped = process_zip(zip_path)
    if count > 0 or errors > 0:
        print(f"  Yeni: {count}, Hata: {errors}, Atlandı: {skipped}")
    total_count += count
    total_errors += errors
    total_skipped += skipped

print("\n" + "=" * 50)
print(f"TOPLAM: {total_count} yeni GIB HTML oluşturuldu")
print(f"Atlandı (zaten var): {total_skipped}")
print(f"Hata: {total_errors}")
print(f"Dizin: {OUTPUT_DIR}")
print("=" * 50)
