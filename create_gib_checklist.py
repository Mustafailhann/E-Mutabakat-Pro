# -*- coding: utf-8 -*-
"""
KAYITSIZ faturaların GİB kontrol listesi
"""
import os
import csv

os.chdir(r"c:\Users\Asus\Desktop\agent ff")

kayitsiz = []
with open("Detayli_Karsilastirma_Raporu.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if "KAYITSIZ" in row.get("Durum", ""):
            kayitsiz.append({
                "no": row.get("Fatura_No", ""),
                "tarih": row.get("Tarih", ""),
                "tutar": row.get("Tutar_TL_Hesaplanan", ""),
                "ettn": row.get("ETTN", "")
            })

# CSV olarak kaydet
with open("kayitsiz_gib_kontrol.csv", "w", encoding="utf-8-sig", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Fatura No", "Tarih", "Tutar TL", "ETTN", "GİB Portal Link"])
    for inv in kayitsiz:
        ettn = inv['ettn']
        # GİB e-Fatura sorgulama linki (portal üzerinden manuel kontrol için)
        gib_link = f"https://portal.efatura.gov.tr/efatura/efatura-sorgu" if ettn else ""
        writer.writerow([inv['no'], inv['tarih'], inv['tutar'], ettn, gib_link])

print(f"Toplam {len(kayitsiz)} KAYITSIZ fatura")
print(f"\nListe kaydedildi: kayitsiz_gib_kontrol.csv")
print(f"\nGİB Portal'dan kontrol için: https://portal.efatura.gov.tr")
print(f"ETTN ile fatura durumu sorgulanabilir.")
