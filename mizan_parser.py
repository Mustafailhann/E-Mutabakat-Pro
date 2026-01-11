# -*- coding: utf-8 -*-
"""
Excel Mizan Parser - YMM Denetim için
"""
import pandas as pd
from typing import Dict, Tuple
from ymm_audit import MizanData, AccountBalance


def parse_excel_mizan(file_path: str) -> MizanData:
    """
    Excel mizan dosyasını parse et
    
    RAD Format:
    Row 1: "İki Tarih Arası Mizan" (başlık - skip)
    Row 2: Headers (Hesap Kodu, Hesap Adı, Borç, Alacak, ...)
    """
    mizan = MizanData()
    
    # Excel oku - başlık satırını atla
    df = pd.read_excel(file_path, header=1)  # 2. satır header
    
    # İlk 5 kolonu kullan: Hesap Kodu, Hesap Adı, Borç, Alacak, Bakiye Borç
    # Column indices: 0=Kod, 1=Ad, 2=Borç, 3=Alacak
    
    for idx, row in df.iterrows():
        # Hesap kodu (1. kolon)
        code = str(row.iloc[0]).strip()
        if not code or code == 'nan' or code == 'None':
            continue
        
        # Sadece numerik hesap kodlarını al
        if not code[0].isdigit():
            continue
        
        # Hesap adı (2. kolon)
        name = str(row.iloc[1])[:50] if len(row) > 1 else code
        
        # Borç (3. kolon - C)
        debit = 0.0
        try:
            debit_val = row.iloc[2] if len(row) > 2 else 0
            if pd.notna(debit_val):
                debit = float(debit_val)
        except:
            pass
        
        # Alacak (4. kolon - D)
        credit = 0.0
        try:
            credit_val = row.iloc[3] if len(row) > 3 else 0
            if pd.notna(credit_val):
                credit = float(credit_val)
        except:
            pass
        
        mizan.accounts[code] = AccountBalance(
            code=code,
            name=name,
            debit=debit,
            credit=credit
        )
    
    return mizan


def parse_txt_mizan(file_path: str) -> MizanData:
    """
    TXT mizan dosyasını parse et (Tab-separated)
    """
    mizan = MizanData()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        parts = line.strip().split('\t')
        if len(parts) < 3:
            continue
        
        code = parts[0].strip()
        if not code or not code[0].isdigit():
            continue
        
        name = parts[1].strip() if len(parts) > 1 else code
        
        debit = 0.0
        credit = 0.0
        
        try:
            if len(parts) > 2:
                debit = float(parts[2].replace('.', '').replace(',', '.') or 0)
            if len(parts) > 3:
                credit = float(parts[3].replace('.', '').replace(',', '.') or 0)
        except:
            pass
        
        mizan.accounts[code] = AccountBalance(
            code=code,
            name=name[:50],
            debit=debit,
            credit=credit
        )
    
    return mizan


if __name__ == "__main__":
    # Test
    import os
    os.chdir(r"c:\Users\Asus\Desktop\agent ff")
    
    test_file = r"c:\Users\Asus\Desktop\agent ff\rad veri\10 2025 Dönem Mizan.XLSX"
    
    print(f"Parsing: {test_file}")
    mizan = parse_excel_mizan(test_file)
    print(f"Toplam hesap: {len(mizan.accounts)}")
    
    # İlk 10 hesabı göster
    for i, (code, acc) in enumerate(sorted(mizan.accounts.items())[:10]):
        print(f"{code}: {acc.name} - B:{acc.debit:,.2f} A:{acc.credit:,.2f} = {acc.balance:,.2f}")
