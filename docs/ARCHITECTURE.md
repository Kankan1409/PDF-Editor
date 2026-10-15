# การตัดสินใจเชิงเทคนิค

React/TypeScript/Vite ตรงตามเทคโนโลยีที่ร้องขอ ใช้ Tailwind 4 + CSS components ที่เขียนเองและ Lucide icons แทน shadcn เพื่อให้ dependency/UI บางและแก้ต่อได้ง่าย Viewer ใช้ PDF.js โดยตรง มี canvas ของจริงและชั้นปุ่มสำหรับเลือก bbox ของข้อความ; กล่อง HTML ใช้เลือกและพิมพ์ร่างข้อความบนหน้า ไฟล์ส่งออกสร้างจาก PyMuPDF บน backend

PDF ไม่มี document layout model เหมือน Word จึงแก้ข้อความแบบบรรทัดที่มี style สม่ำเสมอ ใช้ text redaction ที่ไม่แตะภาพ/เส้น แล้ว insert text ที่ baseline เดิมถ้าเป็น simple Latin หรือ Story shaping สำหรับไทย ขอบเขตการแทรกคือ bbox เดิม รักษาขนาดเดิมและมี collision guard

Flow: upload → inspect → ดับเบิลคลิก/พิมพ์ร่าง → Enter → POST /api/apply พร้อม revision → apply บนสำเนา bytes → read-back validation → append history ภายใต้ lock → PDF.js renders current → export ส่วน /preview และ /commit คงไว้สำหรับ compatibility และ merge แต่ UI ไม่มีหน้าต่างเปรียบเทียบ

ไม่พยายามเปลี่ยน byte strings ใน content stream โดยเดา encoding/TJ advances/ToUnicode เพราะเสี่ยงทำข้อมูลผิด วัตถุภาพและเส้นคงไว้โดย redaction options; ไม่รับประกัน content-stream byte-for-byte fidelity

ฟอนต์ต้นฉบับที่ฝัง: ตรวจ TTF/OTF rights bits และ cmap แล้วเก็บ font bytes ก่อน redaction การรองรับ rights bits เป็น technical check ไม่ใช่การพิสูจน์ใบอนุญาตทางกฎหมายของไฟล์ผู้ใช้ ฟอนต์ subset ที่มี glyph ไม่ครบจะค้นหาฟอนต์ชื่อเดียวกันในเครื่องหรือ PDF_FONT_DIR ถ้าไม่พบจะปฏิเสธการแก้ ไม่ใช้ฟอนต์อื่นแทน

Story สร้าง GSUB alternate glyph โดยบาง glyph ไม่มี ToUnicode ใน output จึงซ่อม mapping เฉพาะฟอนต์ Noto Thai ที่ระบบสร้างใหม่จาก glyph names ที่ทราบ (ไม่แตะต้นฉบับผู้ใช้) ตรวจการอ่านกลับโดย normalize NFKC เพื่อรองรับสระอำแบบ decomposition ผลที่อ่านกลับไม่ตรงจะถูกปฏิเสธ

OCR เรียก PyMuPDF/Tesseract ที่รันในเครื่องเดียวกัน ใช้ผลอ่านข้อความเท่านั้น ไม่ตีความว่า OCR text กลายเป็นข้อความจริงในสแกน การแปลงเฉพาะบริเวณจะเป็นงานถัดไปและต้องมีการอนุมัติภาพ Preview

ความคืบหน้ารายงานเป็นสถานะกำลังทำงาน ไม่ใช่เปอร์เซ็นต์เทียม การแก้ไขไม่ทำทุก keystroke แต่ทำเมื่อกด Enter หรือปุ่มบันทึกบนหน้า เพื่อลดการประมวลผล PDF ซ้ำ

ข้อจำกัด coordinate: text extraction ใช้ unrotated page coordinates จึงปิดเลือก/แก้ข้อความเมื่อ page rotation ไม่เป็น 0 แทนการใช้พิกัดที่ไม่ตรง หน้าเดิมที่ crop/องค์ประกอบซ้อนซับซ้อนควรทดสอบเพิ่มเติม
