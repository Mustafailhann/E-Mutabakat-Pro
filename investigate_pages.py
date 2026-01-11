"""
Investigate page 3 and 13 QR detection issue
"""
import pdfplumber
from pyzbar.pyzbar import decode, ZBarSymbol

pdf_path = r'c:\Users\Asus\Desktop\RAD EYLÜL EKİM\Yeni klasör\09 2025 Dönem Gelen E Arşiv Faturalar.pdf'

with pdfplumber.open(pdf_path) as pdf:
    for page_num in [3, 13]:
        print(f'\n=== Sayfa {page_num} ===')
        page = pdf.pages[page_num - 1]  # 0-indexed
        
        # Farklı çözünürlükleri dene
        for res in [100, 150, 200, 250, 300, 400]:
            img = page.to_image(resolution=res)
            
            # Tüm barcode türlerini dene
            all_codes = decode(img.original)
            qr_only = decode(img.original, symbols=[ZBarSymbol.QRCODE])
            
            if all_codes or qr_only:
                print(f'  {res} dpi: {len(all_codes)} toplam kod, {len(qr_only)} QR')
                for code in all_codes:
                    print(f'    Tip: {code.type}, Data: {code.data[:100]}...')
            else:
                print(f'  {res} dpi: Kod bulunamadi')
        
        # Metin var mı?
        text = page.extract_text()
        if text:
            print(f'  Metin var: {len(text)} karakter')
            # Fatura no ara
            import re
            matches = re.findall(r'[A-Z]{2,4}20\d{2}\d{10,}', text)
            if matches:
                print(f'  Fatura No: {matches}')
        else:
            print(f'  Metin yok (goruntu PDF)')
