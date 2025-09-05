
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime

def generate_xml(df: pd.DataFrame, month: str, output_path: str) -> str:
    root = ET.Element("TransactionsReport", attrib={
        "month": month,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    })

    for _, row in df.iterrows():
        tx = ET.SubElement(root, "Transaction", attrib={"id": row["id"]})
        ET.SubElement(tx, "Status").text = row["status"]
        ET.SubElement(tx, "Date").text = row["date"].strftime("%Y-%m-%d")
        amt = ET.SubElement(tx, "Amount", attrib={"currency": row["currency"]})
        amt.text = f"{row['amount']:.2f}"
        ET.SubElement(tx, "Type").text = row["type"]
        ET.SubElement(tx, "MerchantId").text = str(row["merchant_id"])
        ET.SubElement(tx, "Network").text = str(row["network"])
        ET.SubElement(tx, "Category").text = row["category"]

    tree = ET.ElementTree(root)
    xml_file = f"{output_path}/report.xml"
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)
    return xml_file
