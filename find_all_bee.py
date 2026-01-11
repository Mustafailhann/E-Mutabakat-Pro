# -*- coding: utf-8 -*-
"""Tum entries icinde BEE ara"""

import os
import json
os.chdir(r"c:\Users\Asus\Desktop\agent ff")

import html_kebir_parser

kebir_path = r"c:\Users\Asus\Desktop\RAD EYLÜL EKİM\Yeni klasör\10 2025 Dönem Kebir.HTM"

entries, _ = html_kebir_parser.parse_html_kebir_detailed(kebir_path)

target = "BEE2025000002020"

# Tum entries'de ara (fatura_no veya aciklama)
all_found = []
for i, e in enumerate(entries):
    fn = e.get('fatura_no', '') or ''
    ac = e.get('aciklama', '') or ''
    if target in fn or target in ac:
        all_found.append({
            "index": i,
            "hesap": e.get('hesap_kodu', '?'),
            "fatura_no": fn,
            "borc": e.get('borc', 0),
            "alacak": e.get('alacak', 0)
        })

with open("all_bee_entries.json", "w", encoding="utf-8") as f:
    json.dump(all_found, f, ensure_ascii=False, indent=2)

print(f"Toplam entries: {len(entries)}")
print(f"BEE iceren entries: {len(all_found)}")
for f in all_found:
    print(f"  Hesap: {f['hesap']} Borc: {f['borc']} Alacak: {f['alacak']}")
