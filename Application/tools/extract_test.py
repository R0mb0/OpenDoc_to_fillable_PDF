#!/usr/bin/env python3
# tools/extract_test.py
# Usage:
#   python tools/extract_test.py path/to/file.odt
#   python tools/extract_test.py path/to/content.xml

import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def extract_from_content_xml(path):
    ns = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
    tree = ET.parse(path)
    root = tree.getroot()
    paragraphs = []
    for p in root.findall('.//text:p', ns):
        parts = []
        if p.text and p.text.strip():
            parts.append(p.text)
        for node in p:
            if node.text and node.text.strip():
                parts.append(node.text)
            if node.tail and node.tail.strip():
                parts.append(node.tail)
        paragraph = ''.join(parts).strip()
        if paragraph:
            paragraphs.append(paragraph)
    return '\n\n'.join(paragraphs)

def extract_from_odt_by_unzip(odt_path):
    with zipfile.ZipFile(str(odt_path), 'r') as z:
        if 'content.xml' not in z.namelist():
            raise RuntimeError("content.xml not found in odt archive")
        with z.open('content.xml') as f:
            # write to a temp file-like object parsed by ET
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
            paragraphs = []
            for p in root.findall('.//text:p', ns):
                parts = []
                if p.text and p.text.strip():
                    parts.append(p.text)
                for node in p:
                    if node.text and node.text.strip():
                        parts.append(node.text)
                    if node.tail and node.tail.strip():
                        parts.append(node.tail)
                paragraph = ''.join(parts).strip()
                if paragraph:
                    paragraphs.append(paragraph)
            return '\n\n'.join(paragraphs)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/extract_test.py path/to/file.odt|content.xml")
        sys.exit(1)
    p = Path(sys.argv[1])
    if not p.exists():
        print("File not found:", p)
        sys.exit(2)
    if p.suffix.lower() == ".odt":
        try:
            text = extract_from_odt_by_unzip(p)
            print("=== Extracted text (from odt) ===\n")
            print(text if text else "<NO TEXT EXTRACTED>")
        except Exception as e:
            print("Error extracting from odt:", e)
            raise
    elif p.name.lower() == "content.xml" or p.suffix.lower() == ".xml":
        try:
            text = extract_from_content_xml(p)
            print("=== Extracted text (from content.xml) ===\n")
            print(text if text else "<NO TEXT EXTRACTED>")
        except Exception as e:
            print("Error extracting from content.xml:", e)
            raise
    else:
        print("Unsupported file type:", p.suffix)