#!/usr/bin/env python3
"""Verify authorized surgical patch, stale-QA rejection, shared-memory screening.
All manuscript and evidence are deliberately SYNTHETIC mechanical fixtures.
"""
from pathlib import Path
import sys,tempfile,subprocess,json,hashlib
sys.path.insert(0,str(Path(__file__).parent))
from test_pipeline import execute,dump,blueprint,TITLE,QA,sha
RUBRIC=[('Title Fulfillment + Hook',10),('Causality / Discovery / Why-now',15),('Timeline / Money / State / Knowledge',15),('Legal / Historical / Authority / Professional',10),('Physical / Mechanical',10),('Mystery / Clue / Reveal',10),('Retention / Pressure / Pacing',10),('Character Agency / Competence / Human Behavior',8),('Human Prose / Dialogue / US40+ / TTS / Platform',7),('Emotional Payoff / Ending-by-Action',5)]

def qa_freeze(script,title,outdir,defective):
 cp=outdir/'cp.json'; frozen=outdir/'frozen.json'
 p=subprocess.run([sys.executable,str(QA),'init',str(script),'--title',title,'--out',str(cp)],capture_output=True,text=True)
 assert p.returncode==0,p.stderr
 d=json.loads(cp.read_text())
 for x in d['stages'].values():x.update({'done':True,'evidence':'SYNTHETIC test fixture'})
 for part in d['coverage'].values():
  for x in part.values():x.update({'status':'PASS','evidence':'SYNTHETIC test fixture'})
 d['strong_spans']=[{'part':'Part 1','anchor':'Part 1 synthetic station story.'}]
 for key,mx in RUBRIC:d['rubric'][key]=mx
 for key in d['hard_gates']:d['hard_gates'][key]={'status':'PASS','evidence':'SYNTHETIC test fixture'}
 d['defects']=[]
 if defective:
  anchor='UNIQUE_AUTHORIZE_P01_OLD'
  d['defects']=[{'id':'P01','severity':'P1','part':'Part 3','problem':'Test-only marker', 'repair':'Replace marker',
       'zone':'Exact marker in Part 3','length_intent':'KEEP','rubric_category':'Causality / Discovery / Why-now','deduction':3,
       'anchor':anchor,'dependencies':[], 'occurrences':[{'anchor':anchor,'action':'replace'}]}]
  d['coverage']['Part 3']['Causality']['status']='PATCH' if 'Causality' in d['coverage']['Part 3'] else 'PASS'
  d['coverage']['Part 3']['Causality']['patch_ids']=['P01'] if 'Causality' in d['coverage']['Part 3'] else []
  # Actual schema uses 'Causality' coverage dimension.
  d['rubric']['Causality / Discovery / Why-now']=12
 d['saturation_passes']=[{'complete':True,'body_sha256':d['source']['body_sha256'],'evidence':'synthetic zero new defects','new_defect_ids':[]}]
 dump(cp,d)
 p=subprocess.run([sys.executable,str(QA),'freeze',str(cp),'--out',str(frozen)],capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 return frozen

def main():
 tests=[]
 def mark(x):tests.append(x); print('PASS:',x)
 with tempfile.TemporaryDirectory(prefix='hml_patch_') as td:
  d=Path(td);sdir=d/'manuscripts';sdir.mkdir();pr=d/'project';memory=d/'SHARED_HISTORY.json'
  execute('init','--project',pr,'--title',TITLE,'--memory',memory)
  card={'title':TITLE,'source_title':'Source','viewer_contract':'Mystery','viral_dna':'Situation','new_mechanism':'Secret hatch','score':99,'readiness':'READY','instant_comprehension':True,'opening_serviceability':True}
  cf=d/'title.json';dump(cf,card);execute('lock-title','--project',pr,'--card',cf)
  bf=d/'outline.json';dump(bf,blueprint());execute('lock-outline','--project',pr,'--blueprint',bf)
  mark('verified title/outline setup')
  token=sha(TITLE)[:12]
  segs={'A':[1,2],'B':[3,4,5],'C':[6,7]}
  for seg,nums in segs.items():
   path=sdir/f'HML_{token}_SCRIPT_{seg}.txt';txt=''
   for no in nums:
    filler=(f'Part {no} synthetic station story. '*420)[:10600]
    if no==3:filler='UNIQUE_AUTHORIZE_P01_OLD. '+filler
    txt+=f'[PART {no}]\n'+filler+'\n'
   path.write_text(txt,encoding='utf-8')
   hp=d/f'handoff_{seg}.json';dump(hp,{'title':TITLE,'segment':seg,'facts':[{'key':'owner','value':'Alex','immutable':True}],
        'open_loops':['L1'] if seg=='A' else [],'closed_loops':['L1'] if seg=='C' else [],
        'evidence':[{'part':nums[0],'quote':f'Part {nums[0]} synthetic station story.'}]})
   execute('stage','--project',pr,'--directory',sdir,'--segment',seg,'--file',path,'--handoff',hp)
  file=Path(execute('assemble','--project',pr,'--directory',sdir)['script']['file'])
  mark('persisted A/B/C real 7-part manuscript')
  q=qa_freeze(file,TITLE,d,True)
  result=execute('attach-qa','--project',pr,'--frozen',q);assert result['phase']=='QA_NOT_READY'
  mark('bind QA NOT_READY and real patch ID')
  original=file.read_text()
  candidate=d/'HML_REVISED_V1.txt';candidate.write_text(original.replace('UNIQUE_AUTHORIZE_P01_OLD','UNIQUE_AUTHORIZE_P01_NEW',1))
  wrong={'baseline_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'edits':[{'ticket_id':'P99','part':3,'old':'UNIQUE_AUTHORIZE_P01_OLD','new':'UNIQUE_AUTHORIZE_P01_NEW'}]}
  plan=d/'repair.json';dump(plan,wrong);execute('verify-patch','--project',pr,'--candidate',candidate,'--plan',plan,ok=False)
  mark('reject patch with unknown ticket')
  wrong['edits'][0]['ticket_id']='P01';wrong['edits'][0]['part']=4;dump(plan,wrong)
  execute('verify-patch','--project',pr,'--candidate',candidate,'--plan',plan,ok=False);mark('reject patch to unauthorized Part')
  wrong['edits'][0]['part']=3;dump(plan,wrong)
  execute('verify-patch','--project',pr,'--candidate',candidate,'--plan',plan);mark('authorize exact single-span replacement')
  evil=d/'EVIL_REVISION.txt';evil.write_text(candidate.read_text().replace('Part 4 synthetic station story.','Changed without approval',1))
  execute('verify-patch','--project',pr,'--candidate',evil,'--plan',plan,ok=False);mark('reject unauthorized diff outside ticket')
  execute('commit-patch','--project',pr,'--candidate',candidate,'--plan',plan);mark('commit versioned revision and invalidate QA')
  execute('verify-seo','--project',pr,'--pack',d/'nonexistent.json',ok=False);mark('reject SEO after revision before new QA')
  execute('attach-qa','--project',pr,'--frozen',q,ok=False);mark('reject stale QA on revised manuscript')
  fresh=qa_freeze(candidate,TITLE,d,False)
  execute('attach-qa','--project',pr,'--frozen',fresh);mark('accept fresh QA tied to new script SHA')
  execute('remember','--project',pr);assert memory.exists();mark('write user-selected cross-project local memory')
  pr2=d/'project2';execute('init','--project',pr2,'--title',TITLE,'--memory',memory)
  execute('lock-title','--project',pr2,'--card',cf)
  execute('lock-outline','--project',pr2,'--blueprint',bf,ok=False);mark('detect local duplicate in a second project')
  r=execute('lock-outline','--project',pr2,'--blueprint',bf,'--allow-duplicate-review')
  assert r['originality_screen']['status']=='RED_REVIEW';mark('explicit originality review override reported')
 print(f'ALL {len(tests)} PATCH/MEMORY CHECKS PASSED (synthetic test data).')
if __name__=='__main__':main()
