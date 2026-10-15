import {afterEach,expect,it,vi} from 'vitest';
import {api} from './api';

afterEach(()=>vi.unstubAllGlobals());
const op={kind:'edit',revision:4,page:0,line_id:'line1',text:'ต้อนรับ'};
const response=(status:number,data:unknown)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});

it.each([404,405])('uses the existing session and revision on an older server (%s)',async(status)=>{
 const fetch=vi.fn().mockResolvedValueOnce(response(status,{detail:'Method Not Allowed'}))
  .mockResolvedValueOnce(response(200,{preview_id:'candidate',warnings:[]}))
  .mockResolvedValueOnce(response(200,{revision:5,can_undo:true}));
 vi.stubGlobal('fetch',fetch);
 expect(await api('/apply','POST',op)).toEqual({revision:5,can_undo:true});
 expect(fetch.mock.calls.map(c=>c[0])).toEqual(['/api/apply','/api/preview','/api/commit']);
 expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual(op);
 expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({preview_id:'candidate',revision:4});
 expect(fetch.mock.calls.every(c=>c[1].credentials==='same-origin')).toBe(true);
});
it('uses direct apply on a new server',async()=>{
 const fetch=vi.fn().mockResolvedValue(response(200,{revision:5}));vi.stubGlobal('fetch',fetch);
 expect(await api('/apply','POST',op)).toEqual({revision:5});expect(fetch).toHaveBeenCalledTimes(1);
});
it.each([409,422,500])('does not retry an edit after status %s',async(status)=>{
 const fetch=vi.fn().mockResolvedValue(response(status,{detail:'แก้ไขไม่ได้'}));vi.stubGlobal('fetch',fetch);
 await expect(api('/apply','POST',op)).rejects.toThrow('แก้ไขไม่ได้');expect(fetch).toHaveBeenCalledTimes(1);
});
it('never commits when legacy font validation fails',async()=>{
 const fetch=vi.fn().mockResolvedValueOnce(response(405,{})).mockResolvedValueOnce(response(422,{detail:'ฟอนต์เดิมใช้ไม่ได้'}));vi.stubGlobal('fetch',fetch);
 await expect(api('/apply','POST',op)).rejects.toThrow('ฟอนต์เดิมใช้ไม่ได้');expect(fetch).toHaveBeenCalledTimes(2);
});
it('does not retry after a network failure with unknown commit status',async()=>{
 const fetch=vi.fn().mockRejectedValue(new TypeError('Network error'));vi.stubGlobal('fetch',fetch);
 await expect(api('/apply','POST',op)).rejects.toThrow('Network error');expect(fetch).toHaveBeenCalledTimes(1);
});
