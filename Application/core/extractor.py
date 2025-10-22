# core/extractor.py
"""
Extractor module:
- try_odfpy_extract: uses odfpy if available
- extract_text_from_odt_by_unzip: fallback that unzips content.xml and collects text:p
Both return a plain-text string or None.
"""

from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

# Optional odfpy
try:
    from odf.opendocument import load as odf_load
    from odf import text as odf_text
    ODFPY_AVAILABLE = True
except Exception:
    ODFPY_AVAILABLE = False

def try_odfpy_extract(odt_path: str):
    if not ODFPY_AVAILABLE:
        return None
    try:
        doc = odf_load(str(odt_path))
        paragraphs = []
        for p in doc.getElementsByType(odf_text.P):
            text_content = ""
            for n in p.childNodes:
                try:
                    # best-effort extraction of text nodes
                    if getattr(n, "data", None):
                        text_content += str(n.data)
                    else:
                        text_content += str(n)
                except Exception:
                    try:
                        text_content += str(n)
                    except Exception:
                        pass
            if text_content.strip():
                paragraphs.append(text_content.strip())
        if paragraphs:
            return "\n\n".join(paragraphs)
    except Exception:
        return None
    return None

def extract_text_from_odt_by_unzip(odt_path: str):
    """
    Fallback extractor: unzip the .odt and parse content.xml with ElementTree,
    collecting text:p contents. Returns the extracted plain text or None.
    """
    try:
        p = Path(odt_path)
        with zipfile.ZipFile(str(p), 'r') as z:
            if 'content.xml' not in z.namelist():
                return None
            with z.open('content.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
                paragraphs = []
                for pnode in root.findall('.//text:p', ns):
                    parts = []
                    if pnode.text and pnode.text.strip():
                        parts.append(pnode.text)
                    for node in pnode:
                        if node.text and node.text.strip():
                            parts.append(node.text)
                        if node.tail and node.tail.strip():
                            parts.append(node.tail)
                    paragraph = ''.join(parts).strip()
                    if paragraph:
                        paragraphs.append(paragraph)
                if paragraphs:
                    return '\n\n'.join(paragraphs)
    except Exception:
        return None
    return None

def extract_text_from_odt(odt_path: str):
    """
    Orchestrator: tries odfpy then fallback.
    """
    res = try_odfpy_extract(odt_path)
    if res:
        return res
    return extract_text_from_odt_by_unzip(odt_path)