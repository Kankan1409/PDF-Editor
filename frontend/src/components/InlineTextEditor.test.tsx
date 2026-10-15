import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {InlineTextEditor} from './InlineTextEditor';
import type {TextLine} from '../types';

afterEach(cleanup);
const line:TextLine={id:'line1',text:'ตอนรับ',bbox:[20,30,140,50],origin:[20,45],font:'THSarabunPSK',size:16,color:'#000000',flags:0,editable:true,mixed:false};
function setup(extra={}){
 const props={line,value:line.text,scale:1,pageWidth:600,busy:false,error:'',onChange:vi.fn(),onSave:vi.fn(),onCancel:vi.fn(),...extra};
 render(<InlineTextEditor {...props}/>);
 return {...props,input:screen.getByRole('textbox')};
}
it('focuses the original text and saves with Enter',()=>{
 const p=setup();expect(document.activeElement).toBe(p.input);
 fireEvent.change(p.input,{target:{value:'ต้อนรับ'}});expect(p.onChange).toHaveBeenCalledWith('ต้อนรับ');
 fireEvent.keyDown(p.input,{key:'Enter'});expect(p.onSave).toHaveBeenCalledTimes(1);
});
it('Escape cancels without saving',()=>{
 const p=setup();fireEvent.keyDown(p.input,{key:'Escape'});
 expect(p.onCancel).toHaveBeenCalledTimes(1);expect(p.onSave).not.toHaveBeenCalled();
});
it('does not save while an IME is composing Thai text',()=>{
 const p=setup();fireEvent.compositionStart(p.input);fireEvent.keyDown(p.input,{key:'Enter'});
 expect(p.onSave).not.toHaveBeenCalled();fireEvent.compositionEnd(p.input);
 fireEvent.keyDown(p.input,{key:'Enter'});expect(p.onSave).toHaveBeenCalledTimes(1);
});
it('blocks saves and cancellation while processing',()=>{
 const p=setup({busy:true});fireEvent.keyDown(p.input,{key:'Enter'});fireEvent.keyDown(p.input,{key:'Escape'});
 fireEvent.click(screen.getByRole('button',{name:'บันทึกข้อความบนหน้า'}));
 expect(p.onSave).not.toHaveBeenCalled();expect(p.onCancel).not.toHaveBeenCalled();
});
it('keeps the draft and shows a recoverable font error',()=>{
 const p=setup({value:'ต้อนรับ',error:'ใช้ฟอนต์เดิมไม่ได้'});
 expect((p.input as HTMLTextAreaElement).value).toBe('ต้อนรับ');expect(screen.getByRole('alert').textContent).toBe('ใช้ฟอนต์เดิมไม่ได้');
 fireEvent.keyDown(p.input,{key:'Escape'});expect(p.onCancel).toHaveBeenCalledOnce();
});
it('uses the supplied PDF font, original size and baseline without selecting the whole line',()=>{
 const p=setup({family:'EmbeddedOriginal',ascent:.8,descent:.2});
 const input=p.input as HTMLTextAreaElement;
 expect(input.style.fontFamily).toContain('EmbeddedOriginal');
 expect(input.style.fontSize).toBe('16px');
 expect(input.selectionStart).toBe(line.text.length);
 expect(input.selectionEnd).toBe(line.text.length);
 expect(screen.getByRole('group').style.top).toBe('32.2px');
 expect(input.getAttribute('wrap')).toBe('off');
});
