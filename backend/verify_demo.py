"""Produce a real edited PDF and render evidence; run after make_samples.py."""
from pathlib import Path
from app import pdf_engine as pdf

root=Path(__file__).resolve().parents[1]
data=(root/'samples'/'demo.pdf').read_bytes()
for query,replacement in [('welcom','welcome'),('ตอนรับ','ต้อนรับ')]:
    data,warnings=pdf.apply(data,{'kind':'replace','query':query,'text':replacement,'all':True})
output=root/'samples'/'edited-demo.pdf'; output.write_bytes(data)
with pdf.open_pdf(data) as doc:
    text='\n'.join(p.get_text() for p in doc)
    assert 'A warm welcome to Northstar' in text
    assert 'บริษัทมีความยินดีต้อนรับลูกค้า' in text
    assert len(doc)==2
    doc[0].get_pixmap(matrix=pdf.fitz.Matrix(1.5,1.5)).save(root/'docs'/'edited-document.png')
with pdf.open_pdf((root/'samples'/'demo.pdf').read_bytes()) as doc:
    doc[0].get_pixmap(matrix=pdf.fitz.Matrix(1.5,1.5)).save(root/'docs'/'original-document.png')
print('Verified: two pages, corrected English and Thai, valid reopened PDF; PNG evidence is document output, not app screenshots.')
