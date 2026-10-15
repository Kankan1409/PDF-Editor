import {api} from './api';
export interface EditingContext {family:string;ascent:number;descent:number;background:Uint8Array;dispose:()=>void}
function decode(value:string){return Uint8Array.from(atob(value),c=>c.charCodeAt(0))}
export async function editingContext(page:number,line_id:string,revision:number,font_name?:string,text?:string):Promise<EditingContext>{
 const data=await api<{font:string;background:string;ascent:number;descent:number}>('/editing-context','POST',{kind:'edit',page,line_id,revision,font_name,text}).catch((error:unknown)=>{
  if(error instanceof Error&&['Method Not Allowed','Not Found'].includes(error.message))throw new Error('กรุณาเริ่ม Backend ใหม่เพื่อใช้โหมดแก้บนหน้า แล้วรีเฟรชเว็บ การรีเฟรชอย่างเดียวไม่อัปเดตเซิร์ฟเวอร์');
  throw error;
 });
 const family=`PDFEdit${crypto.randomUUID().replaceAll('-','')}`;
 const face=new FontFace(family,decode(data.font),{ascentOverride:`${data.ascent*100}%`,descentOverride:`${data.descent*100}%`,lineGapOverride:'0%'});
 try{await face.load()}catch{throw new Error('เบราว์เซอร์ไม่สามารถโหลดฟอนต์ต้นฉบับนี้ได้ จึงยังไม่เปิดการพิมพ์และไม่เปลี่ยนฟอนต์เอง')}
 document.fonts.add(face);
 return {family,ascent:data.ascent,descent:data.descent,background:decode(data.background),dispose:()=>{document.fonts.delete(face)}};
}
