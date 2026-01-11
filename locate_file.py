import zipfile
import io

def search():
    with zipfile.ZipFile('Giden e-Fatura.zip') as z:
        for n in z.namelist():
            if n.endswith('.zip'):
                try:
                    with z.open(n) as f:
                        with zipfile.ZipFile(io.BytesIO(f.read())) as sz:
                            for sn in sz.namelist():
                                if '0ED93C98' in sn:
                                    print(f"PATH: {n}|{sn}")
                                    return
                except: pass
            elif '0ED93C98' in n:
                print(f"PATH: {n}")
                return

if __name__ == "__main__":
    search()
