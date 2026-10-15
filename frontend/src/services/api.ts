export async function api<T>(path:string, method='GET', body?:unknown):Promise<T> {
  const form=body instanceof FormData;
  const res=await fetch(`/api${path}`,{method,credentials:'same-origin',headers:{'X-Smart-PDF':'1',...(!form&&body?{'Content-Type':'application/json'}:{})},body:body?(form?body:JSON.stringify(body)):undefined});
  // Older running servers expose preview + commit but have no /apply route.
  // Only retry a missing route, never a validation error or uncertain network failure.
  if(path==='/apply'&&method==='POST'&&(res.status===404||res.status===405)&&body&&typeof body==='object'&&'revision' in body){
    const preview=await api<{preview_id:string;warnings:string[]}>('/preview','POST',body);
    return api<T>('/commit','POST',{preview_id:preview.preview_id,revision:body.revision});
  }
  if(!res.ok){let message='ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์';try{const data=await res.json();message=typeof data.detail==='string'?data.detail:JSON.stringify(data.detail);}catch{}throw new Error(message)}
  return res.json() as Promise<T>;
}
export async function pdfBytes(version='current'):Promise<Uint8Array>{const r=await fetch(`/api/pdf?version=${version}`);if(!r.ok)throw new Error('โหลด PDF ไม่สำเร็จ');return new Uint8Array(await r.arrayBuffer())}
export async function savePdf(name:string,pages=''){const r=await fetch(`/api/pdf?name=${encodeURIComponent(name)}&pages=${encodeURIComponent(pages)}`);if(!r.ok){const e=await r.json();throw new Error(e.detail)}const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=name.endsWith('.pdf')?name:name+'.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000)}
