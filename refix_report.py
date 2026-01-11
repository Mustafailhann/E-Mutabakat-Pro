
path = 'generate_report.py'
try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_line = 'if r["Fatura_No"] == "SFM2025000000817" and js_invoice_db[row_id]["Tax"] == 0:'
    new_line = 'if "SFM2025000000817" in r["Fatura_No"]:' # Simplified condition

    if old_line in content:
        print("Found strict match substring. Replacing with loose match...")
        new_content = content.replace(old_line, new_line)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Replaced successfully.")
    else:
        print("Block NOT found!")
except Exception as e:
    print(f"Error: {e}")
