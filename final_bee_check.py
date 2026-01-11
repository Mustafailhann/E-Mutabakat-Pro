# -*- coding: utf-8 -*-
"""BEE faturasinin tam karsilastirmasi"""

import os
import json
os.chdir(r"c:\Users\Asus\Desktop\agent ff")

import html_kebir_parser

kebir_path = r"c:\Users\Asus\Desktop\RAD EYLÜL EKİM\Yeni klasör\10 2025 Dönem Kebir.HTM"

entries, _ = html_kebir_parser.parse_html_kebir_detailed(kebir_path)
ledger, _ = html_kebir_parser.parse_html_kebir(kebir_path)

target = "BEE2025000002020"

# Tum entries
all_found = []
for e in entries:
    fn = e.get('fatura_no', '') or ''
    ac = e.get('aciklama', '') or ''
    if target in fn or target in ac:
        all_found.append({
            "hesap": e.get('hesap_kodu', '?'),
            "borc": e.get('borc', 0),
            "alacak": e.get('alacak', 0)
        })

print(f"Entries ({len(all_found)}):")
for f in all_found:
    print(f"  Hesap: {f['hesap']} | Borc: {f['borc']} | Alacak: {f['alacak']}")

print(f"\nLedger:")
if target in ledger:
    doc = ledger[target]
    print(f"  TotalDebit: {doc.get('TotalDebit', 0)}")
    print(f"  TaxTotal: {doc.get('TaxTotal', 0)}")
    print(f"  Accounts: {doc.get('Accounts', set())}")
