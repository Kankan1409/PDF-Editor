# Deploy และขอบเขตความปลอดภัย

## แบบ Docker Compose

1. คัดลอกโค้ดไปเซิร์ฟเวอร์ Linux ที่มี Docker Engine + Compose
2. คัดลอก `.env.example` เป็น `.env` ตั้ง TTL/ขนาดหน่วยความจำตามเหมาะสม
3. `docker compose up --build -d`
4. ตรวจ `curl http://127.0.0.1:8080/api/health`
5. วาง reverse proxy สำหรับ HTTPS และระบบ login ขององค์กรไว้หน้า `127.0.0.1:8080` หากต้องการเปิดให้ผู้อื่นใช้ ต้องตั้ง DNS/TLS/firewall โดยผู้ดูแล ไม่ควรเปลี่ยน bind เป็น public โดยไม่จัดการส่วนนี้
6. ตั้ง `COOKIE_SECURE=true` เมื่อใช้งานผ่าน HTTPS เท่านั้น และส่ง original Host/scheme อย่างถูกต้อง ตรวจ proxy trust ก่อนเปิดบริการ

Compose จำกัด backend 2 CPU/2 GB, ไม่ publish port 8000, ใช้ user ที่ไม่ใช่ root และ tmpfs สำหรับไฟล์ชั่วคราวจาก upload parser

## เซสชัน

ไฟล์เก็บใน memory ของ process แยกด้วย cookie HttpOnly + SameSite Strict ที่สุ่ม 256 บิต ไม่มี API list เซสชัน ไม่มีการใช้ชื่อไฟล์เป็น path และไม่ log เนื้อหา PDF สูงสุด 8 เซสชันต่อ process; แต่ละเซสชันมีเพดาน snapshots ตาม `MAX_SESSION_BYTES` ค่าเริ่มต้น 150 MB โดยประมาณ ยังมีหน่วยความจำชั่วคราวระหว่าง render/แก้ไขเพิ่มจากเพดานนี้

ใช้ worker **1 ตัว** เท่านั้น ไม่เปิดหลาย replica โดยไม่มี session affinity/ส่วนจัดเก็บที่ออกแบบเพิ่มเติม ทุก operation สำคัญใช้ lock ป้องกัน simultaneous mutations และ revision ป้องกัน Preview เก่า Undo/Redo สูงสุด 20 snapshots; pruning อาจทำให้ Undo ไปไกลกว่านั้นไม่ได้

เซสชันหมดอายุเมื่อไม่มีการเรียก API 1 ชั่วโมง sweep ทุก 60 วินาที และ request ตรวจ TTL ทุกครั้ง ปิดเอกสารหรืออัปโหลดไฟล์ใหม่จะล้างเซสชันก่อนหน้า ใช้ browser เดียวกันหลายแท็บจะเป็นเซสชันเดียวกัน จึงควรเปิดเอกสารเดียวต่อ browser profile

## ขอบเขตที่ยังต้องทำก่อน production ที่รับไฟล์สาธารณะ

ระบบนี้เป็น MVP ไม่ใช่ hardened public SaaS ยังไม่มี user login, rate limiting, distributed storage, task queue, OCR timeout/killable worker, comprehensive PDF sanitization หรือ malware scanner ต้องเพิ่ม isolation ต่อ PDF job, request streaming size limit ที่ gateway, resource limits และ authentication ก่อนใช้งานแบบรับไฟล์ไม่เชื่อถือจากอินเทอร์เน็ต

nginx จำกัด request 26 MB, backend ตรวจ payload PDF 25 MB และตรวจ Content-Length 26 MB; chunked multipart ที่เรียกตรง backend อาจใช้ทรัพยากรก่อนตรวจ จึงต้องใช้ gateway และไม่เปิด backend สู่เครือข่ายสาธารณะ

PDF มี JavaScript/attachment/links เดิมอาจยังอยู่ในไฟล์ที่ส่งออก แอปนี้ไม่ใช่ sanitization/CDR service โดย PDF.js ไม่เรียก Acrobat JavaScript ใน UI นี้ และไม่มี auto-open attachments แต่ไฟล์ที่ส่งออกยังควรถือเป็นเอกสารจากแหล่งเดิม

ไม่เก็บไฟล์ถาวร แต่ HTTP server/parser อาจ spool upload ลง temp ก่อนอ่าน RAM; context manager/UploadFile.close จะปิดและลบ tempfile ส่วน Docker temp เป็น tmpfs การหยุด process จะล้าง session ทั้งหมด ไม่มี recovery

## การตรวจ deployment

Docker build/run ยังไม่ได้ทดสอบบนเครื่องที่สร้างชุดส่งมอบ เนื่องจากไม่มี Docker CLI ที่ตรวจพบ ให้รันชุด smoke test หลัง deploy: เปิด sample → แก้ English → แก้ Thai → Preview → Undo/Redo → ดาวน์โหลด → เปิดใน reader ที่ใช้งานจริง และรัน browser tests ตาม README
