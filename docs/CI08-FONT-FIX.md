# แก้ THSarabunPSK ใน CI.08 — 15 ตุลาคม 2026

พบและทำซ้ำปัญหาจาก PDF จริงได้: renderer สร้างวรรณยุกต์รูปแปรเป็น glyph ที่ cmap ชี้ไปยัง Private Use Area (เช่น U+F70B) และฟอนต์กำหนดทั้ง hyphen/soft hyphen ให้ glyph เดียวกัน ทำให้ภาพข้อความใช้ฟอนต์เดิม แต่ข้อความที่อ่านกลับไม่ตรงและ API ปฏิเสธด้วย 422

แก้โดยสร้าง mapping จาก cmap และความสัมพันธ์ GSUB ของไฟล์ฟอนต์เดิมสำหรับ glyph แปรรูปที่ไม่มี Unicode ปกติ เลือกตัวอักษรของ glyph ที่มีรหัสซ้ำเฉพาะเมื่อข้อความใหม่ระบุได้ไม่กำกวม จากนั้นแก้เฉพาะ ToUnicode stream ของฟอนต์ Identity-H ที่ renderer เพิ่งสร้าง ไม่เปลี่ยน font program ไม่แก้ฟอนต์อื่นในต้นฉบับ และไม่ข้าม exact read-back validation หากยังมีความกำกวมจะปฏิเสธเหมือนเดิม

ผล: 25 tests ผ่าน รวม CI.08 สองข้อความใหม่, font bytes hash, THSarabunPSK ขนาด 15.96 pt, สี, baseline (คลาดเคลื่อนต่ำกว่า .001 pt), ขนาดหน้า และพิกเซลนอกบรรทัดแก้ไขคงเดิม ทดสอบ API upload → preview → commit → download สำเร็จ ตรวจ render ของไฟล์ผลลัพธ์ด้วยสายตาแล้ว

ไม่ได้อ้างว่าทดสอบผ่าน browser UI ในรอบนี้ ต้อง restart backend ที่รันอยู่เพื่อโหลดโค้ดใหม่ ไฟล์ PDF ส่วนตัวไม่ได้รวมใน source ZIP; tests ใช้ environment variable `CI08_TEST_PDF` เพื่อรับ fixture จากเครื่องผู้ใช้

```powershell
$env:CI08_TEST_PDF = 'C:/Users/Kanyarat/Downloads/CI.08.pdf'
# รันจากโฟลเดอร์ backend ด้วย Python environment ของโปรเจกต์
python -m pytest -q
```
