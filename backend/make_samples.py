from pathlib import Path
import shutil
import pymupdf as f
from app.pdf_engine import FONTS, repair_generated_thai_cmaps

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'samples'; OUT.mkdir(exist_ok=True)
def thai(p,rect,text,size=15):
    css=f'@font-face{{font-family:thai;src:url(NotoSansThai.ttf)}} *{{margin:0;padding:0}} div{{font-family:thai;font-size:{size}pt;line-height:1.2;color:#233c45}}'
    start=p.parent.xref_length()
    p.insert_htmlbox(rect,f'<div>{text}</div>',css=css,archive=f.Archive(str(FONTS)))
    repair_generated_thai_cmaps(p.parent,start)

doc=f.open();p=doc.new_page()
p.draw_rect((0,0,595,14),color=None,fill=(.09,.40,.34))
p.insert_text((50,66),'NORTHSTAR',fontsize=22,fontname='hebo',color=(.09,.40,.34))
p.insert_text((50,85),'CUSTOMER EXPERIENCE / BANGKOK',fontsize=8,color=(.45,.55,.51))
p.insert_text((430,65),'DOC. 2026 / 014',fontsize=9,color=(.45,.55,.51))
p.draw_line((50,108),(545,108),color=(.8,.86,.82),width=.7)
thai(p,(50,132,545,174),'จดหมายต้อนรับลูกค้า',23)
p.insert_text((50,201),'A warm welcom to Northstar',fontsize=17,fontname='helv',color=(.14,.24,.27))
thai(p,(50,231,545,263),'บริษัทมีความยินดีตอนรับลูกค้า',17)
thai(p,(50,276,545,306),'ขอบคุณที่ไว้วางใจและเลือกใช้บริการของเรา',13)
p.insert_text((50,333),'Your dedicated team is ready to help.',fontsize=12)
p.draw_rect((50,375,545,513),color=(.78,.85,.81),fill=(.95,.97,.96),width=.6)
p.insert_text((68,402),'SERVICE OVERVIEW',fontsize=10,fontname='hebo',color=(.09,.4,.34))
for y,a,b in [(438,'Reference','NS-2026-014'),(466,'Contact','support@example.com'),(494,'Status','Ready for review')]:
    p.insert_text((68,y),a,fontsize=10);p.insert_text((285,y),b,fontsize=10)
thai(p,(50,550,545,580),'ยินดีให้บริการและพร้อมดูแลคุณในทุกขั้นตอน',13)
p.draw_line((50,767),(545,767),color=(.8,.86,.82),width=.7)
p.insert_text((50,789),'NORTHSTAR / SAMPLE DOCUMENT',fontsize=8,color=(.45,.55,.51))
p.insert_text((524,789),'01',fontsize=8)
p=doc.new_page();p.insert_text((50,75),'PROJECT NOTES',fontsize=24,fontname='hebo')
thai(p,(50,110,545,145),'ข้อมูลเพิ่มเติมสำหรับทดสอบเอกสารหลายหน้า',17)
p.insert_text((50,183),'Please review every page before exporting.',fontsize=14)
p.insert_font(fontname='NotoEmbedded',fontfile=str(FONTS/'NotoSans.ttf'))
p.insert_text((50,225),'Embedded font example: Welcome customer.',fontname='NotoEmbedded',fontsize=12)
p.insert_text((50,275),'Numbers and symbols: INV-2026 / 1,250.00 + 7%',fontsize=12)
doc.save(OUT/'demo.pdf',garbage=4,deflate=True)
pix=doc[0].get_pixmap(matrix=f.Matrix(1.3,1.3))
scan=f.open();sp=scan.new_page(width=595,height=842);sp.insert_image(sp.rect,stream=pix.tobytes('png'));scan.save(OUT/'scanned.pdf')
doc.save(OUT/'encrypted.pdf',encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner-demo',user_pw='demo-password')
(OUT/'corrupt.pdf').write_bytes(b'%PDF-1.7\ncorrupt sample')
public=ROOT/'frontend'/'public'/'samples';public.mkdir(parents=True,exist_ok=True)
shutil.copy(OUT/'demo.pdf',public/'demo.pdf')
print('Created demo.pdf (2 pages, Thai + English + embedded font), scanned.pdf, encrypted.pdf and corrupt.pdf')
