# -*- coding: utf-8 -*-
"""Fatura numaralarını karşılaştır"""

import zipfile
import os
import re
import html_kebir_parser
import xml.etree.ElementTree as ET

# ZIP'teki fatura numaralarını al
zip_path = r"c:\Users\Asus\Desktop\RAD EYLÜL EKİM\Yeni klasör\10 2025 Dönem Alış Faturaları XML E-Finans.zip"
kebir_path = r"c:\Users\Asus\Desktop\RAD EYLÜL EKİM\Yeni klasör\10 2025 Dönem Kebir.HTM"

print("=== Fatura Numarası Analizi ===\n")

# ZIP'ten ilk 5 fatura numarasını al
zip_invoice_nos = []
with zipfile.ZipFile(zip_path, 'r') as z:
    for name in z.namelist()[:10]:
        if name.lower().endswith('.xml'):
            try:
                content = z.read(name)
                text = content.decode('utf-8', errors='ignore')
                # Fatura numarasını bul - <cbc:ID> içinde
                match = re.search(r'<[^>]*:ID[^>]*>([A-Z]{3}\d{13})</[^>]*:ID>', text)
                if match:
                    zip_invoice_nos.append(match.group(1))
            except:
                pass

print(f"ZIP'teki fatura numaralarından örnekler ({len(zip_invoice_nos)}):")
for no in zip_invoice_nos[:10]:
    print(f"  {no}")

# Kebir'deki fatura numaralarını al
print("\n" + "-" * 40)
ledger, _ = html_kebir_parser.parse_html_kebir(kebir_path)

kebir_invoice_nos = list(ledger.keys())[:20]
print(f"\nKebir'deki belge numaralarından örnekler ({len(ledger)}):")
for no in kebir_invoice_nos:
    print(f"  {no}")

# Eşleşme kontrolü
print("\n" + "-" * 40)
print("\nEşleşme kontrolü:")
matches = set(zip_invoice_nos) & set(ledger.keys())
print(f"Direkt eşleşen: {len(matches)}")

if matches:
    print("Eşleşen örnekler:")
    for m in list(matches)[:5]:
        print(f"  {m}")
