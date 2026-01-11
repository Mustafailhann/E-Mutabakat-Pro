# -*- coding: utf-8 -*-
"""
GİB JAR dosyalarındaki URL'leri çıkar
"""
import os
import re
import json

base_path = r"c:\Users\Asus\Desktop\agent ff\gib_jars\extracted"

urls_found = set()

for root, dirs, files in os.walk(base_path):
    for fname in files:
        if fname.endswith('.class'):
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'rb') as f:
                    content = f.read()
                    text = content.decode('utf-8', errors='ignore')
                    matches = re.findall(r'https?://[a-zA-Z0-9./\-_:]+', text)
                    for m in matches:
                        urls_found.add(m)
            except:
                pass

result = {"urls": sorted(list(urls_found))}
with open("gib_urls.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Toplam {len(urls_found)} URL bulundu. Kaydedildi: gib_urls.json")
