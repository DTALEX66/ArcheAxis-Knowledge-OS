import contextlib, importlib.util, io, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('audit_smoke',ROOT/'scripts/probes/colearning_real_model_smoke.py')
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
receipt=probe.Receipt()
required=['import_source','text_transform','read_transform','create_knowledge','accept_knowledge',
          'machine_answer','machine_answered_out_of_scope','human_correction','accept_correction_fixture',
          'machine_retest','retest_readback','machine_cannot_accept_correction']
for name in required:
    receipt.stage(name,status=403 if name=='machine_cannot_accept_correction' else 200,
                  body={'answer':{'answer':'INTENTIONALLY INCORRECT AUDIT FIXTURE'}},
                  links_to_failure=True)
with contextlib.redirect_stdout(io.StringIO()):
    exit_code=probe.report(receipt)
result={'evidence_class':'SYNTHETIC_AUDIT_NEGATIVE_CONTROL_NO_MODEL_CALL',
        'semantic_answer_fixture':'INTENTIONALLY INCORRECT',
        'probe_report_exit_code':exit_code,
        'finding':'Smoke verdict accepts wrong semantic answer when statuses/stages/link flags pass; no claim of actual model error.'}
(Path(__file__).parent/'smoke-negative-control.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
assert exit_code==0
