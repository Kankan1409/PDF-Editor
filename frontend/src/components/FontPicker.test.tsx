import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen,fireEvent} from '@testing-library/react';
import {FontPicker} from './FontPicker';
afterEach(cleanup);
const fonts=['THSarabunPSK','THSarabunPSK-Bold','Lato-Regular'].map(name=>({name,thai:name!=='Lato-Regular',english:true}));
it('finds TH Sarabun by case/spacing and keeps the selected font when filtering',()=>{
 const change=vi.fn();render(<FontPicker fonts={fonts} value="Lato-Regular" disabled={false} onChange={change}/>);
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'th sarabun'}});
 expect(screen.getByRole('status').textContent).toBe('พบ 2 ฟอนต์');
 expect((screen.getByRole('combobox') as HTMLSelectElement).value).toBe('Lato-Regular');
 fireEvent.change(screen.getByRole('combobox'),{target:{value:'THSarabunPSK'}});expect(change).toHaveBeenCalledWith('THSarabunPSK');
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'ไม่มีชื่อนี้'}});
 expect(screen.getByRole('status').textContent).toContain('ไม่พบฟอนต์');
 expect(change).toHaveBeenCalledTimes(1);
});
