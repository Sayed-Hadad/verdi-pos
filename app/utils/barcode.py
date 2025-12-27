import os
import random
import time
import base64
from io import BytesIO
from barcode import Code128
from barcode.writer import SVGWriter


def generate_unique_code(existing_set=None):
    existing_set = existing_set or set()
    while True:
        code = str(int(time.time())) + str(random.randint(1000, 9999))
        if code not in existing_set:
            return code[:12]


def generate_barcode_image(code, output_dir):
    """Generate barcode SVG (without PIL dependency)"""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{code}.svg")
    try:
        with open(file_path, "wb") as f:
            Code128(code, writer=SVGWriter()).write(f)
    except Exception:
        # Fallback: create simple text representation
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f'<svg><text>{code}</text></svg>')
    return file_path


def barcode_svg_base64(code):
    """Generate barcode as base64-encoded SVG data URI (no PIL needed)."""
    try:
        buffer = BytesIO()
        Code128(code, writer=SVGWriter()).write(buffer)
        buffer.seek(0)
        svg_content = buffer.getvalue().decode("utf-8")
        svg_base64 = base64.b64encode(svg_content.encode()).decode()
        return f"data:image/svg+xml;base64,{svg_base64}"
    except Exception:
        return ""
