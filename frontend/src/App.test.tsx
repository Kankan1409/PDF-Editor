import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import App from './App';
import {api,pdfBytes} from './services/api';
import {editingContext} from './services/editing';
import type {DocumentInfo} from './types';

vi.mock('./services/editing',()=>({editingContext:vi.fn(async()=>({family:'TestOriginal',ascent:.8,descent:.2,background:new Uint8Array([2]),dispose:vi.fn()}))}));
vi.mock('./services/api',()=>({api:vi.fn(),pdfBytes:vi.fn(),savePdf:vi.fn()}));
vi.mock('pdfjs-dist',()=>({GlobalWorkerOptions:{},getDocument:()=>({promise:new Promise(()=>{}),destroy:vi.fn()})}));
const doc:DocumentInfo={name:'sample.pdf',revision:0,page_count:1,size:1000,editable:true,warnings:[],can_undo:false,can_redo:false,pages:[{index:0,width:600,height:800,base_width:600,base_height:800,rotation:0,kind:'text',lines:[{id:'line1',text:'ตอนรับ',bbox:[20,30,140,50],origin:[20,45],font:'THSarabunPSK',size:16,color:'#000000',flags:0,editable:true,mixed:false}]}]};
beforeEach(()=>{
 vi.mocked(pdfBytes).mockResolvedValue(new Uint8Array([1]));
 vi.mocked(api).mockImplementation(async(path)=>{
  if(path==='/document')return structuredClone(doc);
  if(path==='/fonts')return {fonts:[{name:'Sarabun-SemiBold',thai:true,english:true}]};
  if(path==='/apply'){const next=structuredClone(doc);next.pages[0].lines[0].text='ต้อนรับ';next.revision=1;next.can_undo=true;return next;}
  throw new Error('Unexpected API '+path);
 });
});
afterEach(()=>{cleanup();vi.clearAllMocks()});
it('double-click edits on the page, Enter saves once without a comparison dialog',async()=>{
 render(<App/>);
 const line=await screen.findByRole('button',{name:'เลือกข้อความ: ตอนรับ'});
 fireEvent.doubleClick(line);
 const input=await screen.findByRole('textbox',{name:'แก้ข้อความบนหน้า PDF'});
 fireEvent.change(input,{target:{value:'ต้อนรับ'}});
 fireEvent.keyDown(input,{key:'Enter'});
 fireEvent.keyDown(input,{key:'Enter'});
 await screen.findByRole('button',{name:'เลือกข้อความ: ต้อนรับ'});
 expect(vi.mocked(api).mock.calls.filter(c=>c[0]==='/apply')).toHaveLength(1);
 expect(api).toHaveBeenCalledWith('/apply','POST',{kind:'edit',page:0,line_id:'line1',text:'ต้อนรับ',revision:0});
 expect(screen.queryByRole('dialog')).toBeNull();expect(screen.queryByRole('textbox')).toBeNull();
 expect((screen.getByRole('button',{name:'Undo'}) as HTMLButtonElement).disabled).toBe(false);
});
it('Escape discards the draft without an API mutation',async()=>{
 render(<App/>);fireEvent.doubleClick(await screen.findByRole('button',{name:'เลือกข้อความ: ตอนรับ'}));
 const input=await screen.findByRole('textbox');fireEvent.change(input,{target:{value:'new'}});fireEvent.keyDown(input,{key:'Escape'});
 expect(screen.queryByRole('textbox')).toBeNull();expect(vi.mocked(api).mock.calls.filter(c=>c[0]==='/apply')).toHaveLength(0);
});
it('failed save keeps the draft, blocks navigation, and permits correction',async()=>{
 render(<App/>);const line=await screen.findByRole('button',{name:'เลือกข้อความ: ตอนรับ'});
 vi.mocked(api).mockRejectedValueOnce(new Error('ฟอนต์ไม่รองรับ'));
 fireEvent.doubleClick(line);const input=await screen.findByRole('textbox');fireEvent.change(input,{target:{value:'ต้อนรับ'}});fireEvent.keyDown(input,{key:'Enter'});
 await waitFor(()=>expect(screen.getAllByRole('alert')[0].textContent).toContain('ฟอนต์ไม่รองรับ'));
 expect((input as HTMLTextAreaElement).value).toBe('ต้อนรับ');
 expect((screen.getByRole('button',{name:'ส่งออก PDF'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.keyDown(input,{key:'Enter'});await screen.findByRole('button',{name:'เลือกข้อความ: ต้อนรับ'});
});
it('Ctrl+Z undoes a saved PDF edit and Ctrl+Y redoes it',async()=>{
 render(<App/>);fireEvent.doubleClick(await screen.findByRole('button',{name:'เลือกข้อความ: ตอนรับ'}));
 const input=await screen.findByRole('textbox');fireEvent.change(input,{target:{value:'ต้อนรับ'}});fireEvent.keyDown(input,{key:'Enter'});
 await screen.findByRole('button',{name:'เลือกข้อความ: ต้อนรับ'});
 const undone={...structuredClone(doc),revision:2,can_redo:true};
 vi.mocked(api).mockResolvedValueOnce(undone);
 fireEvent.keyDown(window,{key:'z',ctrlKey:true});
 await screen.findByRole('button',{name:'เลือกข้อความ: ตอนรับ'});
 expect(api).toHaveBeenCalledWith('/history/undo','POST');
 vi.mocked(api).mockResolvedValueOnce({...doc,revision:3});
 fireEvent.keyDown(window,{key:'y',ctrlKey:true});
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/history/redo','POST'));
});
it('explicit font selection preserves the draft and is sent when saving',async()=>{
 render(<App/>);await screen.findByRole('option',{name:'Sarabun-SemiBold · ไทย / EN'});
 fireEvent.doubleClick(await screen.findByRole('button',{name:'เลือกข้อความ: ตอนรับ'}));
 const input=await screen.findByRole('textbox');fireEvent.change(input,{target:{value:'ต้อนรับ'}});
 fireEvent.change(screen.getByRole('combobox',{name:'ฟอนต์สำหรับแก้ข้อความ'}),{target:{value:'Sarabun-SemiBold'}});
 await waitFor(()=>expect(editingContext).toHaveBeenCalledWith(0,'line1',0,'Sarabun-SemiBold','ต้อนรับ'));
 await waitFor(()=>expect((screen.getByRole('combobox') as HTMLSelectElement).disabled).toBe(false));
 expect((input as HTMLTextAreaElement).value).toBe('ต้อนรับ');
 fireEvent.keyDown(input,{key:'Enter'});
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/apply','POST',{kind:'edit',page:0,line_id:'line1',text:'ต้อนรับ',font_name:'Sarabun-SemiBold',revision:0}));
});
it('reviews matches, replaces one, refreshes locations, then replaces all',async()=>{
 const base=vi.mocked(api).getMockImplementation()!;
 let replacements=0;
 vi.mocked(api).mockImplementation(async(path,method,body)=>{
  if(path.startsWith('/search?'))return {hits:replacements===0?[
   {page:0,line_id:'line1',start:0,before:'ตอนรับ ตอนรับ',bbox:[20,30,140,50]},
   {page:0,line_id:'line1',start:7,before:'ตอนรับ ตอนรับ',bbox:[20,30,140,50]},
  ]:replacements===1?[{page:0,line_id:'fresh-line',start:0,before:'ตอนรับ',bbox:[20,80,140,100]}]:[]};
  if(path==='/apply'){replacements++;return {...structuredClone(doc),revision:replacements,can_undo:true};}
  return base(path,method,body);
 });
 render(<App/>);await screen.findByRole('button',{name:'เลือกข้อความ: ตอนรับ'});
 fireEvent.click(screen.getByRole('button',{name:'ค้นหาและแทนที่'}));
 fireEvent.change(screen.getByRole('textbox',{name:'ค้นหาข้อความ'}),{target:{value:'ตอนรับ'}});
 fireEvent.change(screen.getByRole('textbox',{name:'แทนที่ด้วย'}),{target:{value:'ต้อนรับ'}});
 fireEvent.click(screen.getByRole('button',{name:'ค้นหาทั้งเอกสาร'}));
 await screen.findByText('ตำแหน่ง 1 จาก 2');
 fireEvent.click(screen.getByRole('button',{name:'ถัดไป'}));
 expect(screen.getByText('ตำแหน่ง 2 จาก 2')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'แทนที่จุดนี้ แล้วไปต่อ'}));
 await screen.findByText('ตำแหน่ง 1 จาก 1');
 expect(api).toHaveBeenCalledWith('/apply','POST',{kind:'replace',query:'ตอนรับ',text:'ต้อนรับ',revision:0,page:0,line_id:'line1',start:7});
 fireEvent.click(screen.getByRole('button',{name:'แทนที่ทั้งหมด'}));
 await screen.findByText('ไม่พบข้อความที่ค้นหา');
 expect(api).toHaveBeenCalledWith('/apply','POST',{kind:'replace',query:'ตอนรับ',text:'ต้อนรับ',revision:1,all:true});
});
