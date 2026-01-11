import os
import zipfile
from io import BytesIO

def s(p, target):
    if not os.path.exists(p): return
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            if n.endswith('.zip'):
                with z.open(n) as f:
                    try:
                        with zipfile.ZipFile(BytesIO(f.read())) as sz:
                            for sn in sz.namelist():
                                if sn.endswith('.xml'):
                                    content = sz.read(sn).decode('utf-8','ignore')
                                    if target in content:
                                        print(f'FOUND: {p} -> {n} -> {sn}')
                                        return
                    except: pass
            elif n.endswith('.xml'):
                content = z.read(n).decode('utf-8','ignore')
                if target in content:
                    print(f'FOUND: {p} -> {n}')
                    return

if __name__ == "__main__":
    target = 'ZGM2025000001473'
    for zp in ['Gelen e-Fatura.zip', 'Giden e-Fatura.zip', 'e-Arsiv.zip']:
        s(zp, target)
