import {useEffect,useRef} from 'react';
import {Check,X} from 'lucide-react';
import type {TextLine} from '../types';

interface Props {
 line:TextLine; value:string; scale:number; pageWidth:number; busy:boolean; error:string;
 onChange:(value:string)=>void; onSave:()=>void; onCancel:()=>void;
 family?:string;ascent?:number;descent?:number;
}

export function InlineTextEditor({line,value,scale,pageWidth,busy,error,onChange,onSave,onCancel,family,ascent=.8,descent=.2}:Props){
 const input=useRef<HTMLTextAreaElement>(null);
 const composing=useRef(false);
 useEffect(()=>{input.current?.focus();input.current?.setSelectionRange(value.length,value.length)},[line.id]);
 const height=(ascent+descent)*line.size*scale;
 return <div className="inline-editor direct-editor" role="group" aria-label="แก้ไขข้อความบนเอกสาร" style={{left:line.origin[0]*scale,top:(line.origin[1]-ascent*line.size)*scale,width:Math.max(20,pageWidth*scale-line.origin[0]*scale-8)}} onClick={e=>e.stopPropagation()}>
  <textarea ref={input} aria-label="แก้ข้อความบนหน้า PDF" value={value} readOnly={busy} spellCheck={false} wrap="off" style={{fontSize:line.size*scale,color:line.color,fontFamily:family?`"${family}"`:`"${line.font}", Tahoma, sans-serif`,height,lineHeight:`${height}px`}}
   onChange={e=>onChange(e.target.value.replace(/[\r\n]+/g,' '))}
   onCompositionStart={()=>{composing.current=true}} onCompositionEnd={()=>{composing.current=false}}
   onKeyDown={e=>{if(composing.current||e.nativeEvent.isComposing||e.keyCode===229)return;if(e.key==='Enter'){e.preventDefault();if(!busy)onSave()}else if(e.key==='Escape'){e.preventDefault();if(!busy)onCancel()}}}/>
  <div className="inline-editor-actions"><span>{busy?'กำลังบันทึก…':'Enter บันทึก · Esc ยกเลิก'}</span><button className="primary" aria-label="บันทึกข้อความบนหน้า" disabled={busy} onClick={onSave}><Check size={16}/>บันทึก</button><button aria-label="ยกเลิกข้อความบนหน้า" disabled={busy} onClick={onCancel}><X size={16}/></button></div>
  {error&&<p className="inline-editor-error" role="alert">{error}</p>}
 </div>
}
