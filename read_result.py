# -*- coding: utf-8 -*-
import json

with open("integration_test_result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 50)
print("MUTABAKAT TEST SONUCLARI")
print("=" * 50)

print("\nDosya Kontrolleri:")
for k, v in data.get("dosya_kontrolleri", {}).items():
    print(f"  {k}: {'OK' if v else 'YOK'}")

print("\nAnaliz Sonuclari:")
for k, v in data.get("sonuclar", {}).items():
    print(f"  {k}: {v}")

print(f"\nCSV Rapor: {data.get('csv_path', 'N/A')}")
print(f"Log Sayisi: {data.get('log_count', 0)}")
