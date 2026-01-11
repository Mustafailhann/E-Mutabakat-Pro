import csv

print("FATURA KDV KONTROLU")
print("-" * 60)

kayitsiz_count = 0
kayitsiz_kdv_ok = 0
kayitsiz_kdv_zero = 0

with open('Detayli_Karsilastirma_Raporu.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if "KAYITSIZ" in row['Durum']:
            kayitsiz_count += 1
            kdv = float(row.get('Fatura_KDV', 0))
            if kdv > 0:
                kayitsiz_kdv_ok += 1
            else:
                kayitsiz_kdv_zero += 1
                print(f"KDV=0: {row['Fatura_No']}")

print("-" * 60)
print(f"KAYITSIZ fatura sayisi: {kayitsiz_count}")
print(f"KDV > 0 olan: {kayitsiz_kdv_ok}")
print(f"KDV = 0 olan: {kayitsiz_kdv_zero}")
print("-" * 60)

# SFM kontrolu
with open('Detayli_Karsilastirma_Raporu.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'SFM2025000000817' in row['Fatura_No']:
            print(f"\nSFM2025000000817 KONTROLU:")
            print(f"  KDV: {row['Fatura_KDV']}")
            print(f"  Beklenen: 275.0")
            kdv = float(row['Fatura_KDV'])
            if abs(kdv - 275.0) < 1:
                print("  SONUC: BASARILI!")
            else:
                print("  SONUC: HATALI!")
