import {useState} from 'react';
export interface FontOption {name:string;thai:boolean;english:boolean}
const key=(value:string)=>value.toLowerCase().replace(/[\s_-]/g,'');
export function FontPicker({fonts,value,disabled,onChange}:{fonts:FontOption[];value:string;disabled:boolean;onChange:(name:string)=>void}){
 const [query,setQuery]=useState('');
 const matches=fonts.filter(font=>key(font.name+' '+(font.name.startsWith('THSarabunPSK')?'THSarabun สารบรรณ':'')).includes(key(query)));
 const selected=fonts.find(font=>font.name===value);
 const options=selected&&!matches.includes(selected)?[selected,...matches]:matches;
 return <><label>ค้นหาฟอนต์<input type="search" aria-label="ค้นหาฟอนต์" placeholder="เช่น THSarabun, PSK, Sarabun" value={query} disabled={disabled} onChange={e=>setQuery(e.target.value)}/></label><label>ฟอนต์สำหรับแก้ข้อความ<select aria-label="ฟอนต์สำหรับแก้ข้อความ" value={value} disabled={disabled} onChange={e=>onChange(e.target.value)}><option value="">รักษาฟอนต์ต้นฉบับ</option>{options.map(font=><option key={font.name} value={font.name}>{font.name}{font.name.startsWith('THSarabunPSK')?' (THSarabun)':''}{font.thai?' · ไทย':''}{font.english?' / EN':''}</option>)}</select></label>{query&&<p className="hint" role="status">{matches.length?`พบ ${matches.length} ฟอนต์`:'ไม่พบฟอนต์ ลองชื่ออื่นหรือเพิ่มไฟล์ฟอนต์'}</p>}</>;
}
