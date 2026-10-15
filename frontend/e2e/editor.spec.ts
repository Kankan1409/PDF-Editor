import {test,expect} from '@playwright/test';
import path from 'node:path';

test('open PDF, edit English, correct Thai, undo/redo and download',async({page},testInfo)=>{
 await page.goto('/');
 await page.getByRole('button',{name:/ลองด้วยเอกสารตัวอย่าง/}).click();
 await expect(page.getByRole('button',{name:'เลือกข้อความ: A warm welcom to Northstar',exact:true})).toBeVisible();
 await page.screenshot({path:testInfo.outputPath('01-open-document.png'),fullPage:true});
 await page.getByRole('button',{name:'เลือกข้อความ: A warm welcom to Northstar',exact:true}).dblclick();
 const editor=page.getByRole('textbox',{name:'แก้ข้อความบนหน้า PDF'});
 await editor.fill('A warm welcome to Northstar');
 await editor.press('Escape');
 await expect(editor).toHaveCount(0);
 await page.getByRole('button',{name:'เลือกข้อความ: A warm welcom to Northstar',exact:true}).dblclick();
 await editor.fill('A warm welcome to Northstar');
 await page.screenshot({path:testInfo.outputPath('02-inline-edit.png'),fullPage:true});
 await editor.press('Enter');
 await expect(page.getByRole('button',{name:'เลือกข้อความ: A warm welcome to Northstar',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'ค้นหาและแทนที่',exact:true}).click();
 await page.getByRole('textbox',{name:'ค้นหาข้อความ',exact:true}).fill('ตอนรับ');
 await page.getByRole('textbox',{name:'แทนที่ด้วย',exact:true}).fill('ต้อนรับ');
 await page.getByRole('button',{name:'ค้นหาทั้งเอกสาร'}).click();
 await expect(page.getByText('พบ 1 ตำแหน่ง',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'แทนที่ทั้งหมด',exact:true}).click();
 await expect(page.getByRole('button',{name:'เลือกข้อความ: บริษัทมีความยินดีต้อนรับลูกค้า',exact:true})).toBeVisible();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await page.screenshot({path:testInfo.outputPath('03-thai-edited.png'),fullPage:true});
 await page.getByRole('button',{name:'Undo',exact:true}).click();
 await expect(page.getByRole('button',{name:'เลือกข้อความ: บริษัทมีความยินดีตอนรับลูกค้า',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Redo',exact:true}).click();
 await expect(page.getByRole('button',{name:'เลือกข้อความ: บริษัทมีความยินดีต้อนรับลูกค้า',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'ส่งออก PDF',exact:true}).click();
 await page.getByRole('textbox',{name:'ชื่อไฟล์ส่งออก'}).fill('browser-verified.pdf');
 const pendingDownload=page.waitForEvent('download');
 await page.getByRole('button',{name:'ดาวน์โหลด PDF',exact:true}).click();
 const download=await pendingDownload;
 expect(download.suggestedFilename()).toBe('browser-verified.pdf');
 await download.saveAs(testInfo.outputPath('browser-verified.pdf'));
 await page.screenshot({path:testInfo.outputPath('04-exported.png'),fullPage:true});
});

test('upload rejects corrupt PDF and accepts local sample',async({page})=>{
 await page.goto('/');
 await page.locator('input[type=file]').first().setInputFiles(path.resolve('../samples/corrupt.pdf'));
 await expect(page.getByRole('alert')).toContainText('เสียหาย');
 await page.locator('input[type=file]').first().setInputFiles(path.resolve('../samples/demo.pdf'));
 await expect(page.getByRole('button',{name:'หน้า 2',exact:true})).toBeVisible();
});
