# -*- coding: utf-8 -*-
"""Tek faturayı detaylı incele"""

import os
os.chdir(r"c:\Users\Asus\Desktop\agent ff")

import html_kebir_parser

kebir_path = r"c:\Users\Asus\Desktop\RAD EYLÜL EKİM\Yeni klasör\10 2025 Dönem Kebir.HTM"

# Detaylı parse
entries, summary = html_kebir_parser.parse_html_kebir_detailed(kebir_path)

# AOF2025000001976 faturasını bul
target = "AOF2025000001976"
print(f"=== {target} icin tum kayitlar ===\n")

found = []
for e in entries:
    if target in e.get('fatura_no', '') or target in e.get('aciklama', ''):
        found.append(e)
        print(f"Hesap: {e.get('hesap_kodu', '?')} - {e.get('hesap', '?')}")
        print(f"  Tarih: {e.get('tarih', '?')}")
        print(f"  Fis No: {e.get('fis_no', '?')}")
        print(f"  Borc: {e.get('borc', 0):.2f}")
        print(f"  Alacak: {e.get('alacak', 0):.2f}")
        print(f"  DC: {e.get('dc', '?')}")
        print(f"  Aciklama: {e.get('aciklama', '?')[:80]}...")
        print()

print(f"Toplam {len(found)} kayit bulundu")

# Toplamları hesapla
total_borc = sum(e.get('borc', 0) for e in found)
total_alacak = sum(e.get('alacak', 0) for e in found)
print(f"\nToplam Borc: {total_borc:.2f}")
print(f"Toplam Alacak: {total_alacak:.2f}")
