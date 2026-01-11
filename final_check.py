import csv
import json

def check_names():
    with open('Detayli_Karsilastirma_Raporu.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 10: break
            sender = json.loads(row['Sender'])
            receiver = json.loads(row['Receiver'])
            print(f"Inv: {row['Fatura_No']}")
            print(f"  Sender: {sender.get('Name')}")
            print(f"  Receiver: {receiver.get('Name')}")
            print(f"  KDV: {row['Fatura_KDV']}")
            print("-" * 20)

if __name__ == "__main__":
    check_names()
