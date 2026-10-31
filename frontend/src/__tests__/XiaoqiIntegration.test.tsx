import {describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {XiaoqiAvatar} from '../components/XiaoqiAvatar';
import {xiaoqiImages} from '../companion/xiaoqiAssets';
import provenance from '../companion/PROVENANCE.json';

describe('Xiaoqi source integration',()=>{
 it('preserves the nine source assets byte for byte with original provenance',()=>{
  const records=provenance.records.filter(record=>'state' in record);
  expect(records).toHaveLength(9);
  expect(new Set(records.map(record=>record.state))).toEqual(new Set(Object.keys(xiaoqiImages)));
  for(const record of provenance.records){
   const bytes=readFileSync(resolve(dirname(fileURLToPath(import.meta.url)),'../../..',record.path));
   expect(bytes.length).toBe(record.bytes);
   expect(createHash('sha256').update(bytes).digest('hex')).toBe(record.sha256);
  }
  expect(provenance.source_commit).toBe('3115378bb3fe13849ed422c739002428fef82892');
  expect(provenance.asset_license).toContain('MINIMAX DESIGN');
 });
 it('exposes keyboard interaction through a native button',async()=>{
  const action=vi.fn();render(<XiaoqiAvatar onInteract={action}/>);
  const button=screen.getByRole('button',{name:'与小栖互动：待命'});
  button.focus();await userEvent.setup().keyboard('{Enter} ');
  expect(action).toHaveBeenCalledTimes(2);
 });
 it('reports image failure and recovers when a different real state is presented',()=>{
  const view=render(<XiaoqiAvatar state="thinking"/>);
  fireEvent.error(screen.getByRole('img',{name:'小栖：思考中'}));
  expect(screen.getByRole('img',{name:'小栖：思考中'})).toHaveAttribute('src',xiaoqiImages.thinking);
  fireEvent.error(screen.getByRole('img',{name:'小栖：思考中'}));
  expect(screen.getByRole('img',{name:'小栖：思考中，图像暂不可用'})).toBeVisible();
  view.rerender(<XiaoqiAvatar state="completed"/>);
  expect(screen.getByRole('img',{name:'小栖：已完成'})).toHaveAttribute('src',xiaoqiImages.completed);
 });
});
