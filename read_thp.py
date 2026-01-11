"""
Tekdüzen Hesap Planı PDF okuyucu - dosyaya kaydet
"""
import pdfplumber

pdf = pdfplumber.open(r'tekduzhesapplani.pdf')
print(f'TEKDUZEN HESAP PLANI - {len(pdf.pages)} sayfa')

full_text = []
for i in range(len(pdf.pages)):
    text = pdf.pages[i].extract_text()
    if text:
        full_text.append(f'\n--- Sayfa {i+1} ---\n{text}')

# Dosyaya kaydet
with open('tekduzen_hesap_plani_icerik.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(full_text))

print(f'Icerik {len(pdf.pages)} sayfa olarak tekduzen_hesap_plani_icerik.txt dosyasina kaydedildi.')
