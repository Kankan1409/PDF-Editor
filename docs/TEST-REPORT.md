# รายงานทดสอบ — 14 ตุลาคม 2026

> อัปเดต 15 ตุลาคม 2026: UI เปลี่ยนเป็นดับเบิลคลิกแก้บนหน้าโดยตรง ไม่มีหน้าต่างเปรียบเทียบ ผลล่าสุด Backend 27 tests และ Frontend 8 tests ผ่าน พร้อม build ดู [INLINE-EDIT.md](INLINE-EDIT.md) รายละเอียดด้านล่างเป็นผลและ workflow ของรุ่นก่อนหน้า

## ผลที่ยืนยันแล้ว

- `npm run build`: ผ่าน TypeScript strict และ Vite production build
- `npm audit`: หลังปรับ dependencies พบ 0 vulnerabilities ในผลที่เรียกครั้งนี้; production-only audit รอบท้ายพบ 0 เช่นกัน (ไม่ใช่การรับรองความปลอดภัยทุกด้าน)
- `python -m pytest -q`: **16 passed**, 1 deprecation warning ของ Starlette TestClient/httpx; ไม่ใช่ functional failure
- PyMuPDF ที่ใช้ทดสอบสุดท้าย: **1.28.2**, Python **3.12**, Node **24.19.0** ใน runtime ที่มีอยู่
- มีไฟล์ PDF ส่งออกจริง `samples/edited-demo.pdf` ที่แก้ `welcom → welcome` และ `ตอนรับ → ต้อนรับ`; เปิดอ่านกลับและ render ด้วย PyMuPDF แล้วได้ 2 หน้า
- ตรวจภาพ render ของเอกสารตัวอย่างด้วยสายตา; ไฟล์ `original-document.png`/`edited-document.png` เป็นภาพเอกสารจริง ไม่ใช่ screenshot ของแอป

## รายการ automated tests ที่ผ่าน

| กรณี | ขอบเขตที่ตรวจจริง |
|---|---|
| อัปโหลด PDF 2 หน้า | API คืนข้อมูลและ text lines ทุกหน้า |
| แยกเซสชัน | client ที่ไม่มี cookie อ่านไฟล์ของอีก client ไม่ได้ |
| แก้ข้อความอังกฤษ | Preview ไม่เปลี่ยน current ก่อน commit; PDF อ่านกลับมีข้อความใหม่ |
| ยกเลิก Preview / Undo / Redo | current bytes คืนตรงต้นฉบับ และ redo คืนข้อความแก้แล้ว |
| แก้คำผิดไทย | ค้นหาเจอ แทนที่ได้ ไม่มีคำผิดเก่าในข้อความที่อ่านกลับ |
| รักษากรอบ/เส้น | จำนวน vector drawings และขนาดหน้าคงเดิมใน sample |
| พิกเซลนอกบริเวณแก้ | เปรียบเทียบ render ก่อน/หลังนอก bbox + 2px antialias margin แล้วเหมือนกันใน sample |
| เพิ่มและลบข้อความ | เพิ่มในพื้นที่ว่างแล้วค้นคืนได้ ลบแล้วไม่มีข้อความนั้น |
| เพิ่ม/ลบ/เรียง/หมุนหน้า | จำนวนหน้า ตำแหน่งเนื้อหา และ rotation ตรงตามคำสั่ง |
| รวม/แยก/ส่งออก | รวมเป็น 4 หน้า แยกเลือก 2 หน้า เปิดและ render หน้าออกได้ |
| ชื่อไฟล์อันตราย | sanitize ชื่อดาวน์โหลด ไม่ใช้เป็น path ของไฟล์บน server |
| ไฟล์เสียหาย/เข้ารหัส | ปฏิเสธด้วย error ที่กำหนด |
| ภาพสแกน | ระบุชนิด scan, ไม่มี real text, OCR request ไม่เปลี่ยน bytes ของ PDF |
| ฟอนต์ฝังและ fallback | นำ embedded Latin font กลับมาใช้; Thai fallback พร้อม warning และอ่านกลับได้ |
| วรรณยุกต์/สระไทย | ทดสอบ `ที่`, `ขั้น`, `น้ำ`, `ผู้ใช้`, `กุ้ง` โดย normalize NFKC |
| ข้อความซ้อน/ยาวเกิน | ปฏิเสธการเปลี่ยนที่เสี่ยงหรือไม่พอดี |
| สิทธิ์/ลายเซ็น | ปิดแก้ไข PDF ที่จำกัดสิทธิ์และมีฟิลด์ลายเซ็น (ไม่ใช่ทดสอบตรวจ cryptographic signature จริง) |
| Preview เก่า / Origin ผิด | ปฏิเสธ revision ไม่ตรงและ cross-origin mutation |
| เซสชันหมดอายุ | cleanup แล้วเอกสารอ่านต่อไม่ได้ |
| แทนที่ตำแหน่งเดียว/ไม่พบ | แทนที่ได้ตาม hit index และคืนผลว่างเมื่อไม่พบ |
| Frontend/API contract | TestClient เสิร์ฟ built HTML, JS/CSS, PDF sample แล้ว upload→preview→commit→download ผ่าน origin เดียวกัน |

บาง test ตรวจหลายกรณีในฟังก์ชันเดียว จึงมีรายการย่อยมากกว่า 16 แถว

## สิ่งที่ยังไม่ยืนยันและข้อจำกัดจริง

1. **ยังไม่ได้ผ่าน browser end-to-end**: สั่งเริ่ม Vite/Uvicorn ได้และเห็น startup output แต่ sandbox ปฏิเสธการเชื่อมต่อ localhost (`EACCES`/timeout) และผู้ใช้ลองแล้วเปิดไม่ได้ นโยบาย browser ปฏิเสธการใช้แท็บที่โหลดล้มเหลว จึงไม่มีภาพ Preview ของโปรแกรมที่ยืนยันการใช้งานจริงในรอบนี้
2. `frontend/e2e/editor.spec.ts` มี 2 browser tests สำหรับ upload, English/Thai edits, Undo/Redo, download และ capture screenshots แต่ **ยังไม่ได้รัน** เนื่องจากข้อจำกัดข้างต้น
3. Frontend/API contract test เป็น ASGI in-process test ไม่ได้ execute JavaScript ใน browser และไม่ใช่ network end-to-end
4. **ยังไม่ได้ทดสอบ Docker build/run**: ไม่พบ Docker CLI ใน runtime ที่ใช้งาน จัดเตรียม Dockerfile/Compose และคู่มือไว้แล้ว
5. **ยังไม่ได้ทดสอบ OCR สำเร็จด้วย tha+eng**: ทดสอบ scan detection, ข้อผิดพลาดเมื่อ OCR ไม่พร้อม และการไม่แก้ไฟล์อัตโนมัติเท่านั้น Dockerfile เตรียมชุดภาษาไว้
6. **ยังไม่ได้เปิดไฟล์ส่งออกใน Adobe Reader/Edge จริง**: เปิดและ render ด้วย PyMuPDF สำเร็จ แต่ยังไม่ถือเป็นการยืนยันข้าม reader
7. UI dark mode, tablet layout, drag-and-drop และ browser download dialog มีโค้ดแล้ว แต่ยังไม่ได้ตรวจหน้าจอจริง จึงต้องตรวจด้วย browser tests และ manual acceptance บน Windows ปกติ
8. เก็บฟอนต์เดิมได้เฉพาะกรณีที่ตรวจสอบและรองรับ ไม่รับประกัน PDF ทุกไฟล์และไม่แก้ outline text
9. เพิ่ม/ลบ/ย้ายภาพ, รูปทรง, layout controls แบบเต็ม, แก้ภาพสแกนเฉพาะบริเวณ, เขียนทับต้นฉบับ และ production authentication ยังไม่ทำใน MVP

## ขั้นตอนสาธิตบน Windows ปกติ

รัน `start.ps1 -Install` จาก root แล้วเปิด `http://127.0.0.1:8000/`:

1. กด “ลองด้วยเอกสารตัวอย่าง” → ตรวจ thumbnail 2 หน้า
2. คลิก `A warm welcom to Northstar` → แก้เป็น `A warm welcome to Northstar` → Preview → ยืนยัน
3. เลือกค้นหา → ค้น `ตอนรับ` → แทนที่ `ต้อนรับ` → ดูผลก่อน/หลัง → ยืนยัน
4. กด Undo แล้ว Redo ตรวจว่าข้อความกลับถูกขั้นตอน
5. กดส่งออก → ตั้งชื่อ → ดาวน์โหลด → เปิดใน reader ที่ใช้งานจริงและตรวจทั้งสองหน้า
6. ทดสอบด้วย PDF งานจริงที่มีฟอนต์/ตาราง/ภาพแตกต่างจาก sample ก่อนใช้งานจริง
