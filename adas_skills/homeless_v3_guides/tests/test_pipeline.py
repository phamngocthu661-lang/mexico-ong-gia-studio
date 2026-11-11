#!/usr/bin/env python3
"""Integration tests using explicitly SYNTHETIC prose. NOT a creative-content QA certificate."""
from pathlib import Path
import json, subprocess, tempfile, sys, hashlib, importlib.util
ROOT=Path(__file__).resolve().parents[1]
CTL=ROOT/'controller'/'homeless_controller.py'
QA=ROOT/'controller'/'qa_checkpoint.py'
TITLE='A Homeless Woman Found a Locked Hatch Beneath an Abandoned Station — Then She Saw a Familiar Mark'

def execute(*argv,ok=True):
 p=subprocess.run([sys.executable,str(CTL),*map(str,argv)],capture_output=True,text=True)
 try:d=json.loads(p.stdout)
 except:raise AssertionError((argv,p.stdout,p.stderr))
 if ok:assert p.returncode==0 and d.get('pass') is True,(argv,p.returncode,d)
 else:assert p.returncode==2 and d.get('pass') is False,(argv,p.returncode,d)
 return d

def dump(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()

def blueprint():
 b=[11000,11000,11000,11000,11000,11000,9000]
 return {'title':TITLE,'score':99,'premise':'An abandoned station becomes a community archive',
   'primary_mystery':'What lies under the station?','deeper_mystery':'Who preserved it and why?',
   'mechanism':'Physical inspection of drainage hatch','payoff':'A community museum built with legal permission',
   'ending_action':'She turns a found key and invites the community in','dna_primary':'DNA A',
   'parts':[{'part':i,'entry':f'entry {i}','discovery':f'discovery {i}','exit':f'exit {i}',
             'target_chars':n,'beats':['look','test','decision']} for i,n in enumerate(b,1)],
   'clues':[{'id':f'E{i:02}','setup_part':max(1,(i-1)//2+1),'payoff_part':min(7,max(1,(i-1)//2+3)), 'evidence':f'clue {i}', 'reinterpreted':i in (1,2)} for i in range(1,9)],
   'reveals':[{'part':p,'answer':f'reveal {p}'} for p in (2,3,5,6)],
   'early_retention':{'title_promise_at':150,'physical_proof_at':350,'micro_payoff_1_at':1050,'forward_question_at':1850,'micro_payoff_2_at':4800},
   'canon':{'protagonist':'Alex','property':'Old Station','timeline':'2024 summer','money':'$0 opening','object_states':'hatch locked','knowledge':'first clue','authority':'permit office','resolution_mode':'B'}}

def main():
 checks=[]
 def mark(name):checks.append(name);print('PASS:',name)
 with tempfile.TemporaryDirectory(prefix='homeless_v3_test_') as td:
  dr=Path(td);proj=dr/'project';scripts=dr/'scripts';scripts.mkdir()
  execute('init','--project',proj,'--title',TITLE); mark('init + immutable title hash')
  wrong={'title':TITLE+' Extra','score':99,'readiness':'READY','instant_comprehension':True,'opening_serviceability':True,'source_title':'source','viewer_contract':'promise','viral_dna':'dna','new_mechanism':'new'}
  card=dr/'title.json';dump(card,wrong);execute('lock-title','--project',proj,'--card',card,ok=False);mark('reject title mismatch')
  wrong['title']=TITLE;dump(card,wrong);execute('lock-title','--project',proj,'--card',card);mark('lock genuine title card')
  bb=blueprint();bb['clues']=bb['clues'][:5];bfile=dr/'blueprint.json';dump(bfile,bb)
  execute('lock-outline','--project',proj,'--blueprint',bfile,ok=False);mark('reject insufficient clue blueprint')
  bb=blueprint();dump(bfile,bb);execute('lock-outline','--project',proj,'--blueprint',bfile);mark('seven-part outline and canon gate')
  # Artificial prose intentionally repetitive to exercise length/count/integrity only.
  parts={}
  for i in range(1,8):
   phrase=f'Part {i} synthetic inspection proof. The metal rail rattled against the loose frame. '
   parts[i]=(phrase * 155)[:10560]+'\n'
  stage_names={'A':[1,2],'B':[3,4,5],'C':[6,7]}
  token=sha(TITLE)[:12]
  for seg,nums in stage_names.items():
   path=scripts/f'HML_{token}_SCRIPT_{seg}.txt';path.write_text(''.join(f'[PART {i}]\n{parts[i]}' for i in nums),encoding='utf-8')
  ledgerA={'title':TITLE,'segment':'A','facts':[{'key':'person_name','value':'Alex','immutable':True}], 'open_loops':['L1'], 'closed_loops':[], 'evidence':[{'part':1,'quote':'Part 1 synthetic inspection proof.'}]}
  lfile=dr/'handoff.json';dump(lfile,{**ledgerA,'segment':'B'})
  execute('stage','--project',proj,'--directory',scripts,'--segment','B','--file',scripts/f'HML_{token}_SCRIPT_B.txt','--handoff',lfile,ok=False)
  mark('reject out-of-order stage B')
  dump(lfile,ledgerA)
  execute('stage','--project',proj,'--directory',scripts,'--segment','A','--file',scripts/f'HML_{token}_SCRIPT_A.txt','--handoff',lfile)
  mark('stage A write-through + evidence quote')
  ledgerB={'title':TITLE,'segment':'B','facts':[{'key':'person_name','value':'Mira','immutable':True}], 'open_loops':['L2'], 'closed_loops':[], 'evidence':[{'part':3,'quote':'Part 3 synthetic inspection proof.'}]}
  dump(lfile,ledgerB);execute('stage','--project',proj,'--directory',scripts,'--segment','B','--file',scripts/f'HML_{token}_SCRIPT_B.txt','--handoff',lfile,ok=False)
  mark('reject immutable character identity drift')
  ledgerB['facts'][0]['value']='Alex';dump(lfile,ledgerB)
  execute('stage','--project',proj,'--directory',scripts,'--segment','B','--file',scripts/f'HML_{token}_SCRIPT_B.txt','--handoff',lfile);mark('stage B verified')
  ledgerC={'title':TITLE,'segment':'C','facts':[{'key':'person_name','value':'Alex','immutable':True}], 'open_loops':[], 'closed_loops':['L1'], 'evidence':[{'part':6,'quote':'Part 6 synthetic inspection proof.'}]}
  dump(lfile,ledgerC)
  execute('stage','--project',proj,'--directory',scripts,'--segment','C','--file',scripts/f'HML_{token}_SCRIPT_C.txt','--handoff',lfile,ok=False)
  mark('reject dangling open loop in C')
  ledgerC['closed_loops']=['L1','L2'];dump(lfile,ledgerC)
  execute('stage','--project',proj,'--directory',scripts,'--segment','C','--file',scripts/f'HML_{token}_SCRIPT_C.txt','--handoff',lfile);mark('stage C loops closed')
  assembled=execute('assemble','--project',proj,'--directory',scripts);file=Path(assembled['script']['file']);mark('assemble 7 parts 70k..80k with SHA')
  # Before QA, SEO cannot run.
  execute('verify-seo','--project',proj,'--pack',dr/'missing.json',ok=False);mark('SEO blocked before independent QA')
  # Create checkpoint using existing installed auditor. This is mock data for SOFTWARE tests, not an evidence review.
  cp=dr/'checkpoint.json';frozen=dr/'frozen.json'
  p=subprocess.run([sys.executable,str(QA),'init',str(file),'--title',TITLE,'--out',str(cp)],capture_output=True,text=True)
  assert p.returncode==0,p.stderr
  c=json.loads(cp.read_text())
  for name,stage in c['stages'].items():stage.update({'done':True,'evidence':'synthetic test fixture only'})
  for pn,dims in c['coverage'].items():
   for name,cell in dims.items():cell.update({'status':'PASS','evidence':'synthetic fixture placeholder'})
  for rub in c['rubric']: c['rubric'][rub]=dict(__import__('importlib').util.module_from_spec(__import__('importlib').util.spec_from_file_location('qa',QA)).__dict__).get('RUBRIC',None) if False else None
  for rub,mx in [('Title Fulfillment + Hook',10),('Causality / Discovery / Why-now',15),('Timeline / Money / State / Knowledge',15),('Legal / Historical / Authority / Professional',10),('Physical / Mechanical',10),('Mystery / Clue / Reveal',10),('Retention / Pressure / Pacing',10),('Character Agency / Competence / Human Behavior',8),('Human Prose / Dialogue / US40+ / TTS / Platform',7),('Emotional Payoff / Ending-by-Action',5)]:c['rubric'][rub]=mx
  for k in c['hard_gates']:c['hard_gates'][k]={'status':'PASS','evidence':'synthetic software test'}
  c['saturation_passes']=[{'complete':True,'body_sha256':c['source']['body_sha256'],'evidence':'synthetic regression fixture','new_defect_ids':[]}]
  dump(cp,c)
  p=subprocess.run([sys.executable,str(QA),'freeze',str(cp),'--out',str(frozen)],capture_output=True,text=True)
  assert p.returncode==0,(p.stderr,p.stdout)
  execute('attach-qa','--project',proj,'--frozen',frozen);mark('QA frozen binds score and hashes')
  execute('verify-seo','--project',proj,'--pack',dr/'missing.json',ok=False);mark('SEO requires real pack')
  # Tampered manuscript rejected, recovery restores exact bytes.
  old=file.read_bytes();file.write_bytes(old+b'tamper\n')
  execute('status','--project',proj) # status is non-blocking but warns
  pack=dr/'seo.json'
  desc=('A woman discovers an old station clue as she tests a long forgotten hatch. '*16).split()
  desc=' '.join((desc*4)[:190])
  ss={'title':TITLE,'description':desc,'tags':'homeless woman, old station, hidden legacy, restoration','hashtags':['#Story','#Mystery','#Restoration'],
      'evidence_quotes':['Part 1 synthetic inspection proof.','Part 3 synthetic inspection proof.','Part 6 synthetic inspection proof.'],
      'thumbnail':{'aspect_ratio':'16:9','evidence_quote':'Part 1 synthetic inspection proof.','prompt':'Cinematic daylight photo of a woman examining an old station hatch with one clear physical clue; realistic palette, quiet atmosphere, grounded environment, no fake documents'},
      'trailer':{'seconds':20,'no_dialogue':True,'no_lip_sync':True,'clips':[{'seconds':10,'prompt':'Silent cinematic opening at an abandoned station: restrained body movement, moving light, grounded objects, no spoken words or lip motion.','shots':[{'action':'opens gate','environment':'station','evidence_quote':'Part 1 synthetic inspection proof.'},{'action':'lifts hatch','environment':'railroad','evidence_quote':'Part 3 synthetic inspection proof.'}]}]*2},'factual_review':True,'trailer_review':True}
  dump(pack,ss)
  execute('verify-seo','--project',proj,'--pack',pack,ok=False);file.write_bytes(old)
  mark('reject stale script SHA after edit')
  execute('verify-seo','--project',proj,'--pack',pack);mark('SEO metadata gate + prompt-only status')
  execute('remember','--project',proj);mark('add approved story to local memory')
  execute('remember','--project',proj,ok=False);mark('refuse duplicate memory entry')
  # QA stale after a version change checked through complete trusted freeze SHA binding, no accidental overwrite.
  fake=dr/'fakeqa.json';fq=json.loads(frozen.read_text());fq['frozen_source']['body_sha256']='bad';dump(fake,fq)
  execute('attach-qa','--project',proj,'--frozen',fake,ok=False);mark('reject modified/stale frozen audit')
 print(f'ALL {len(checks)} INTEGRATION CHECKS PASSED (synthetic test data).')
if __name__=='__main__':main()
