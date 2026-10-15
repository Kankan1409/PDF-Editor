# Smart PDF Editor — MVP

> อัปเดตการรักษาฟอนต์: การแก้ข้อความเดิมจะไม่ fallback เป็นฟอนต์อื่นและไม่ย่อขนาดเองแล้ว ใช้ฟอนต์เดิมกับภาษาไทยได้เมื่อข้อมูลฟอนต์รองรับ ดู [รายละเอียดและผลทดสอบ 21 กรณี](docs/FONT-FIX.md) โดยข้อจำกัด fallback/auto-shrink ในบันทึก MVP ด้านล่างเป็นพฤติกรรมรุ่นก่อนหน้า ใช้แนวทางใน FONT-FIX.md แทน

เว็บแก้ไข **เนื้อหา PDF จริง** ด้วย React + TypeScript + Vite, Tailwind CSS, PDF.js และ FastAPI + PyMuPDF พร้อมเมนูภาษาไทย การแก้ข้อความบนหน้าโดยตรง และ Undo/Redo

> สถานะ: MVP ที่ผ่านการทดสอบ engine/API และ build frontend แล้ว ไม่ใช่ระบบแก้ PDF ทุกชนิดได้สมบูรณ์ 100% ดูผลและส่วนที่ยังไม่ได้ทดสอบใน [docs/TEST-REPORT.md](docs/TEST-REPORT.md) โดยเฉพาะ Preview ผ่านเบราว์เซอร์จริงซึ่งถูกจำกัดโดยสภาพแวดล้อมที่ใช้สร้างโปรเจกต์

## เปิดใช้งานบน Windows แบบรวดเร็ว

ติดตั้ง Python **3.12** พร้อม Python Launcher (`py`), Node.js **22 LTS ขึ้นไป** พร้อม npm และ VS Code จากเว็บไซต์ผู้พัฒนา เปิดโฟลเดอร์นี้ด้วย VS Code แล้วเปิด Terminal แบบ PowerShell:

```powershell
.\start.ps1 -Install
```

สคริปต์สร้าง Python environment ใน `backend/.venv`, ติดตั้ง requirements, รัน `npm ci`, build frontend แล้วเปิด FastAPI ซึ่งเสิร์ฟทั้งหน้าเว็บและ API ที่:

**http://127.0.0.1:8000/**

เปิด URL ด้วย Chrome หรือ Edge เอง เมื่อหยุดด้วย Ctrl+C เอกสารในเซสชันจะหาย หากติด Execution Policy ให้ใช้คำสั่งติดตั้งและรันแยกด้านล่างได้ ไม่จำเป็นต้องเปลี่ยนนโยบายเครื่อง

ครั้งต่อไปใช้ ` .\start.ps1 ` โดยไม่ต้อง `-Install` เมื่อต้องการ rebuild หลังแก้ frontend ให้ใช้ `-Install` อีกครั้ง หรือ `npm run build` ใน frontend

## ติดตั้งและรัน Development แยกสอง Terminal

Terminal 1 จากโฟลเดอร์โปรเจกต์:

```powershell
py -3.12 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm ci
npm run dev
```

เปิด **http://127.0.0.1:5173/** ใน development Vite จะ proxy `/api` ไป FastAPI ไม่ต้องตั้ง CORS แบบเปิดทั้งหมด หาก 5173 ถูกใช้ Vite จะแสดงพอร์ตใหม่ ให้เปิดตาม URL ที่แสดง

## Build และรันโดยไม่ใช้ Docker

```powershell
cd frontend
npm ci
npm run build
cd ../backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

เปิด http://127.0.0.1:8000 หลัง build; FastAPI จะตรวจ `frontend/dist` ตอนเริ่มโปรเซส จึงต้อง restart backend หาก build เป็นครั้งแรก

Linux ใช้ `python3 -m venv backend/.venv` และ `backend/.venv/bin/python` แทน path ของ Windows

## Docker Compose

ติดตั้ง Docker Desktop (Windows ใช้ Linux containers/WSL2) แล้ว:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose logs -f
```

เปิด **http://127.0.0.1:8080/**; หยุดด้วย `docker compose down`

Frontend เป็น nginx + static build, backend เป็น Python พร้อม Tesseract tha/eng พอร์ต backend ไม่ถูก publish สู่ host และพอร์ต frontend bind localhost เป็นค่าเริ่มต้น Dockerfile เตรียมแล้วแต่ยังไม่ได้ทดสอบ Docker build/run ในสภาพแวดล้อมที่ส่งมอบ

ดู [docs/DEPLOY.md](docs/DEPLOY.md) สำหรับ reverse proxy, HTTPS, session limits และข้อจำกัดก่อนเปิดใช้งานกับหลายผู้ใช้

## วิธีใช้งาน

1. **เปิด PDF**: กด “เลือกไฟล์ PDF” หรือ “เปิดไฟล์” หรือลากวางไฟล์ สูงสุด 25 MB / 200 หน้า; กด “ลองด้วยเอกสารตัวอย่าง” เพื่อใช้ไฟล์ที่มากับโปรเจกต์
2. **ดูเอกสาร**: คลิก thumbnail เพื่อเปลี่ยนหน้า ใช้ปุ่มซูมด้านล่าง และปุ่มหมุนใน toolbar
3. **แก้ข้อความ**: ดับเบิลคลิกบรรทัดบน PDF แล้วพิมพ์แก้บนหน้าได้เลย กด Enter หรือปุ่มบันทึกเพื่อใช้การแก้ไข กด Esc เพื่อยกเลิก ไม่มีหน้าต่างเปรียบเทียบ หากบันทึกไม่ผ่าน ข้อความที่พิมพ์ยังอยู่ให้แก้ต่อ บนแท็บเล็ตสามารถเลือกข้อความแล้วกด “แก้ข้อความบนหน้า” ได้
4. **แก้คำผิด**: เลือกไอคอนค้นหา ใส่ `ตอนรับ` และ `ต้อนรับ` กดค้นหา แล้วเลือกแทนที่ตำแหน่งเดียวหรือทั้งหมด ผลปรากฏบนหน้า PDF โดยตรง ใช้ Undo เพื่อย้อนกลับ
5. **เพิ่มข้อความ**: เลือกเครื่องมือ T ใส่ข้อความและพิกัดกล่องหน่วย PDF point (72 pt = 1 นิ้ว) ปรับขนาดและสี ถ้าทับข้อความเดิมระบบจะไม่ยอมรับ ให้ย้ายพิกัดกล่อง
6. **ลบข้อความ**: เลือกบรรทัดและกดลบ ข้อความจะถูกลบจากเนื้อหา PDF จริง ใช้ Undo เพื่อคืนข้อความ
7. **จัดหน้า**: เพิ่มหน้า ลบหน้า เลื่อนหน้าขึ้น/ลง และหมุนหน้า คำสั่งมีผลทันทีและใช้ Undo/Redo ได้ สำหรับการเลือกแก้ข้อความให้หมุนกลับ 0°
8. **รวม PDF**: เปิด “ข้อมูลและข้อจำกัดเอกสาร” แล้วกดรวม PDF อีกไฟล์ ระบบเพิ่มหน้าต่อท้าย
9. **แยก PDF**: เปิดส่งออกและใส่เลขหน้า เช่น `1,3,4` จะดาวน์โหลดเฉพาะหน้าที่ระบุ; ว่าง = ทุกหน้า
10. **Undo / Redo**: ปุ่มลูกศรบนสุด เก็บ snapshot สูงสุด 20 รายการตามขอบเขตหน่วยความจำ; โหลดหน้าเว็บใหม่ในเซสชันเดิมยังเรียกเอกสารได้ แต่ restart backend จะล้างทั้งหมด
11. **ส่งออก**: ตรวจทุกหน้าหลังแก้ก่อนกดส่งออก ตั้งชื่อไฟล์แล้วดาวน์โหลดเป็นไฟล์ใหม่ สามารถดาวน์โหลดต้นฉบับแยกได้
12. **ปิดเอกสาร**: กด “ปิดและลบเซสชัน” ในข้อมูลเอกสาร; เซสชันที่ไม่ถูกใช้จะหมดอายุใน 1 ชั่วโมง

## OCR

Dockerfile ติดตั้ง Tesseract และข้อมูลภาษาไทย/อังกฤษไว้ สำหรับ Windows ให้ติดตั้ง Tesseract และหาโฟลเดอร์ที่มีทั้ง `tha.traineddata` และ `eng.traineddata` จากนั้นตั้งก่อนรัน backend:

```powershell
$env:TESSDATA_PREFIX = 'C:/Program Files/Tesseract-OCR/tessdata'
```

กดเครื่องมือ OCR เพื่ออ่านข้อความหน้าปัจจุบัน **OCR ใน MVP เป็นการอ่านเท่านั้น** ไม่เปลี่ยนภาพสแกนเป็นข้อความแก้ไขได้ ไม่ลบตัวอักษรออกจากภาพ และยังไม่ได้ตรวจคุณภาพ OCR สำเร็จในเครื่องที่สร้างโปรเจกต์ หากไม่พบชุดภาษา จะแจ้งสถานะ 503 ที่เข้าใจได้

## ฟอนต์และการรักษารูปแบบ

- หน่วยแก้ไขเป็นบรรทัดที่มีรูปแบบเดียว ไม่ใช่ paragraph reflow ทั้งหน้า
- PyMuPDF ไม่ใช่โปรแกรม word processor: MVP ใช้ text-only redaction ที่ `fill=False`, `images=0`, `graphics=0` แล้ววางเนื้อหาใหม่ ไม่มีสี่เหลี่ยมสีขาวปิดข้อความ และไม่ปล่อยข้อความเดิมซ่อนอยู่เป็นวิธีแก้หลัก
- ตรวจฟอนต์ฝัง TTF/OTF สิทธิ์ embedding และ glyph coverage เก็บ font bytes ก่อนลบข้อความเดิม รองรับ shaping ภาษาไทยด้วยฟอนต์เดิม
- ข้อความเดิมต้องใช้ฟอนต์เดิม: ใช้ฟอนต์ฝัง หรือค้นหาฟอนต์ชื่อเดียวกันในเครื่อง/PDF_FONT_DIR หากใช้ไม่ได้จะปฏิเสธ ไม่เปลี่ยนเป็น Noto เอง ส่วนข้อความเพิ่มใหม่ใช้ Noto ที่แนบใบอนุญาต OFL
- ฟอนต์ Noto ที่แจกเป็น static instance จากต้นฉบับ variable font ของ Google Fonts; มีใบอนุญาตใน `backend/fonts`
- ซ่อม ToUnicode ของฟอนต์ที่สร้างใหม่เมื่อพิสูจน์ mapping ได้จาก cmap/GSUB และตรวจข้อความอ่านกลับ ดูรายละเอียดใน docs/CI08-FONT-FIX.md
- รักษาขนาดและ baseline เดิม ขยายพื้นที่แนวนอนเฉพาะเมื่อไม่ชนเนื้อหาข้างเคียง หากพื้นที่ไม่พอหรืออ่านกลับไม่ตรงจะยกเลิกการแก้ไข
- บรรทัดหลายรูปแบบ ข้อความแนวตั้ง/หมุน ขอบเขตบรรทัดซ้อนกัน และการแก้บนหน้าหมุนถูกปฏิเสธใน MVP ไม่รับประกัน kerning, tracking, paragraph alignment หรืออักษรสัญลักษณ์ทุกแบบ
- PDF มีลายเซ็นหรือฟิลด์ลายเซ็น: เปิดดูแต่ปิดการแก้ไข; PDF เข้ารหัสต้องใช้ซอฟต์แวร์ที่ได้รับอนุญาตปลดล็อกก่อน ไม่มีการข้ามรหัสผ่านหรือจำกัดสิทธิ์

## โครงสร้าง

```text
frontend/src/components/PdfPage.tsx   PDF.js renderer + text selection
frontend/src/services/api.ts         API client / download
frontend/src/types/index.ts          TypeScript definitions
frontend/src/App.tsx                 editor, panels, preview, export
backend/app/main.py                 upload/API/validation/OCR/export
backend/app/pdf_engine.py           extraction/font/search/text/page editing
backend/app/store.py                session/history/TTL/memory limits
backend/tests/                      engine + API + build contract tests
frontend/e2e/                       browser acceptance tests (ยังไม่รันในเครื่องนี้)
samples/                            PDF ตัวอย่างไทย/อังกฤษ/สแกน/เข้ารหัส/เสียหาย
docs/                               deployment/architecture/test report
```

## ทดสอบ

หลัง build frontend ให้รันจาก backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

สร้างตัวอย่างใหม่: `python make_samples.py` จาก backend (ไฟล์เดิมชื่อเดียวกันถูกเขียนใหม่); รหัสผ่านของ `encrypted.pdf` สำหรับการตรวจด้วย reader คือ `demo-password`

Browser acceptance tests เตรียมไว้แต่ยังไม่ได้รันสำเร็จในสภาพแวดล้อมนี้ เริ่ม backend และ frontend ด้วยคำสั่ง development ก่อน แล้วเปิด Terminal เพิ่ม:

```powershell
cd frontend
npx playwright install chromium
npm run test:e2e
```

ทดสอบ browser จะสร้าง screenshots และไฟล์ PDF ที่ดาวน์โหลดใน `frontend/test-results` โปรดตรวจ screenshot ด้วยสายตาด้วย ชุดทดสอบไม่แทนการทดสอบกับไฟล์จริงหลากหลายชนิด

## ปัญหาที่พบบ่อย

| อาการ | วิธีตรวจ |
|---|---|
| เปิด localhost ไม่ได้ | ตรวจว่า Terminal ที่รัน server ยังเปิดอยู่ ใช้พอร์ตที่ server แสดง และรันนอก sandbox ที่ห้าม localhost |
| `py` / `npm` ไม่พบ | ติดตั้ง Python Launcher/Node.js แล้วปิดเปิด VS Code ใหม่ |
| ไม่พบโมดูล Python | ใช้ Python ใน `backend/.venv` ตัวเดียวกับที่ติดตั้ง requirements |
| ค้นหาไม่พบ | ค้นหาแบบตรงตัว แยกตัวพิมพ์ และอยู่ในบรรทัดเดียว; ภาพสแกน/outline ไม่มีข้อความให้ค้นหา |
| เลือกข้อความไม่ได้ | หน้าหมุน/สแกน/outline หรือเส้นข้อความหลายรูปแบบ; หมุนกลับ 0° หรืออ่านด้วย OCR |
| เซสชันหมดอายุ | เปิด PDF ใหม่จากต้นฉบับหรือไฟล์ที่ส่งออกไปแล้ว ประวัติในหน่วยความจำไม่กู้หลัง restart |
| ข้อความยาวเกิน | ลดความยาวหรือเพิ่มกล่องใหม่ในพื้นที่ว่าง ระบบไม่ยอมขยายจนทับข้อความข้างเคียง |
| ฟอนต์เดิมใช้ไม่ได้ | ติดตั้งฟอนต์ชื่อเดิมที่มีสิทธิ์ใช้งาน หรือวางใน PDF_FONT_DIR แล้วเริ่ม Backend ใหม่ ระบบไม่เปลี่ยนฟอนต์หรือย่อข้อความเอง |
| OCR 503 | ตรวจ `TESSDATA_PREFIX`, `tha.traineddata`, `eng.traineddata` และ restart backend |
| Origin ไม่ตรงเซิร์ฟเวอร์ | ใช้ Vite proxy/nginx ที่มากับโปรเจกต์ ไม่เปิด CORS แบบ wildcard; ตรวจ Host และ HTTPS scheme ใน reverse proxy |
| Port ถูกใช้อยู่ | หยุด server เก่าของโปรเจกต์ หรือเปลี่ยนพอร์ตให้ frontend proxy ตรงกับ backend |

## ยังไม่รวมใน MVP

เพิ่ม/ย้าย/ลบรูปภาพหรือโลโก้, เครื่องมือเส้น/รูปทรง, drag-resize กล่อง, ตัวเลือกตัวหนา/เอียง/จัดแนวแบบเต็ม, แก้ภาพสแกนเฉพาะบริเวณ, OCR job queue, การแก้ PDF content stream แบบ operator โดยตรง, password workflow, ลายเซ็นใหม่, diff ทั้งเอกสาร, การเขียนทับไฟล์ต้นฉบับผ่าน File System Access API และระบบบัญชีผู้ใช้

การดาวน์โหลดเป็นไฟล์ใหม่เสมอ การเลือกเขียนทับจาก dialog ของ browser/OS ขึ้นกับผู้ใช้ ไม่มีการเขียนไฟล์ต้นฉบับในเครื่องโดยอัตโนมัติ

## ใบอนุญาต dependencies

Noto ใช้ SIL OFL; PyMuPDF มีตัวเลือก AGPL/commercial ดูเงื่อนไขผู้พัฒนาก่อนเลือกวิธีแจกจ่าย/เปิดบริการ โค้ดโปรเจกต์นี้ไม่ได้เลือกใบอนุญาตธุรกิจแทนเจ้าของโปรเจกต์

เอกสารอ้างอิง: [PyMuPDF Page API](https://pymupdf.readthedocs.io/en/latest/page.html), [Text shaping](https://pymupdf.readthedocs.io/en/latest/recipes-text.html), [PyMuPDF repository/license](https://github.com/pymupdf/PyMuPDF), [PDF.js](https://mozilla.github.io/pdf.js/)


### ทดสอบการแก้ข้อความบนหน้า

จาก `frontend` รัน `npm test` (component/UI interaction tests) และ `npm run build` ส่วน `npm run test:e2e` ต้องเปิดเซิร์ฟเวอร์และติดตั้ง Playwright browser ตามคู่มือเดิม ดูผลล่าสุดใน [docs/INLINE-EDIT.md](docs/INLINE-EDIT.md)

### คลังฟอนต์ไทยและอังกฤษ

เพิ่มฟอนต์ 82 ไฟล์พร้อมใบอนุญาตและปุ่มนำเข้า TTF/OTF ในแถบขวา สามารถเลือกฟอนต์ทดแทนด้วยตนเองโดยไม่ทิ้งร่างข้อความ ดู [คู่มือฟอนต์](docs/FONT-LIBRARY.md) ค่าเริ่มต้นยังรักษาฟอนต์เดิม ไม่มีการเปลี่ยนฟอนต์เงียบ ๆ

### ค้นหาฟอนต์และแก้ชื่อทีละจุด/ทั้งหมด

ค้นหาฟอนต์ด้วยชื่อบางส่วนในแถบขวา เพิ่มชุด THSarabunPSK (ไฟล์ THSarabun) 4 รูปแบบพร้อมใบอนุญาตแล้ว เครื่องมือค้นหามีปุ่มก่อนหน้า/ถัดไป แทนที่จุดนี้แล้วไปต่อ และแทนที่ทั้งหมด ดู [คู่มือรุ่นล่าสุด](docs/FONT-SEARCH-REPLACE.md)
