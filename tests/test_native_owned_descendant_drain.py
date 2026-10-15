from pathlib import Path
import ast
import unittest
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'scripts/probes/aaos01_tauri_webdriver_loop.py').read_text(encoding='utf8')
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='wait_owned_descendant_drain')
namespace={}
exec(compile(ast.Module(body=[node],type_ignores=[]),'proposed_helper','exec'),namespace)
wait=namespace['wait_owned_descendant_drain']
class Clock:
 def __init__(self):self.now=0.
 def monotonic(self):return self.now
 def sleep(self,value):self.now+=value
class DrainTests(unittest.TestCase):
 def run_drain(self,rows,timeout=1.):
  clock=Clock();queue=iter(rows);last=rows[-1]
  return wait([{'pid':10,'created':100}],snapshot=lambda:next(queue,last),monotonic=clock.monotonic,sleep=clock.sleep,timeout=timeout)
 def test_delayed_exit_is_waited_for_and_read_back(self):
  result=self.run_drain([[{'pid':10,'created':100,'name':'msedgewebview2.exe'}],[]]);self.assertEqual(result['remaining'],[]);self.assertEqual(result['samples'],2);self.assertGreater(result['elapsed_seconds'],0)
 def test_recycled_pid_is_not_owned(self):
  result=self.run_drain([[{'pid':10,'created':101}]]);self.assertEqual(result['remaining'],[]);self.assertEqual(result['samples'],1)
 def test_persistent_owned_process_remains_failure(self):
  result=self.run_drain([[{'pid':10,'created':100}]]);self.assertEqual(result['remaining'][0]['pid'],10);self.assertGreaterEqual(result['elapsed_seconds'],1.)
 def test_snapshot_failure_is_never_success(self):
  clock=Clock()
  def failed():raise OSError('metadata unavailable')
  with self.assertRaises(OSError):wait([{'pid':10,'created':100}],snapshot=failed,monotonic=clock.monotonic,sleep=clock.sleep)
if __name__=='__main__':unittest.main()
