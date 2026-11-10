#!/usr/bin/env python3
"""PADRE MX V4 per-project immutable progressive state/checkpoint ledger, local only."""
import argparse,hashlib,json,re,sys
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text('utf8'))
def error(s):raise ValueError(s)
def dump(p,o):
 if Path(p).exists():error('Checkpoint cannot overwrite a prior ledger: '+str(p))
 Path(p).parent.mkdir(parents=True,exist_ok=True)
 Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n','utf8')
def seal(x):x['seal_sha256']=sha(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8'));return x
def check(x):
 if x.get('schema')!='PADRE_MX_CONTINUITY_LEDGER_V4':error('Wrong ledger schema')
 y={k:v for k,v in x.items() if k!='seal_sha256'}
 if sha(json.dumps(y,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8'))!=x.get('seal_sha256'):error('Ledger hash/seal mismatch')
def create(n):
 bp=load(n.blueprint);out=Path(n.outline).read_bytes();out.decode('utf8')
 if bp.get('schema')!='PADRE_MX_STORY_BLUEPRINT_V4' or len(bp.get('parts',[]))!=7:error('Validated seven-Part blueprint required')
 vid=sha((bp['locked_title']+'\n'+sha(out)).encode('utf8'))[:16]
 data={'schema':'PADRE_MX_CONTINUITY_LEDGER_V4','video_id':vid,'locked_title':bp['locked_title'],'outline_sha256':sha(out),'blueprint_sha256':sha(Path(n.blueprint).read_bytes()),
       'narrative_spine':bp['narrative_spine'],'originality_signature':bp['originality_signature'],
       'canon_parts':[{'part':p['part'],'objective':p['objective'],'consequence':p['consequence'],'exit_to_next':p['exit_to_next']} for p in bp['parts']],
       'planned_payoffs':bp['setup_payoff_map'],'last_stage':None,'checkpoints':[],'reported_knowledge':[], 'reported_evidence':[], 'open_loops':[]}
 dump(n.out,seal(data));return {'pass':True,'ledger':str(n.out),'video_id':vid}
def checkpoint(n):
 data=load(n.ledger);check(data)
 stages={'A':([1,2],None),'B':([3,4,5],'A'),'C':([6,7],'B')}
 nums,prev=stages[n.stage]
 if data['last_stage']!=prev:error('Stages must advance in order; cannot jump or replay')
 raw=Path(n.segment).read_bytes();txt=raw.decode('utf8','strict')
 if '\r' in txt or txt.startswith('\ufeff'):error('Segment must be UTF-8 LF no BOM')
 matches=list(re.finditer(r'(?m)^\[PART ([1-7])\]\n',txt))
 if [int(x.group(1)) for x in matches]!=nums:error('Segment heading sequence does not match stage '+n.stage)
 report=load(n.report);updates=report.get('part_updates')
 if not isinstance(updates,list) or [p.get('part') for p in updates]!=nums:error('Exactly one ordered part_update per stage Part required')
 new_open=set(data['open_loops']);new_evidence=list(data['reported_evidence']);new_knowledge=list(data['reported_knowledge'])
 for i,p in enumerate(updates):
  start=matches[i].end();end=matches[i+1].start() if i+1<len(matches) else len(txt)
  parttext=txt[start:end];quote=p.get('source_quote','')
  if not isinstance(quote,str) or len(quote)<18 or quote not in parttext:error('Part '+str(nums[i])+' needs exact source quote >=18 chars')
  for field in ('continuity_bridge','new_value','character_change'):
   if not isinstance(p.get(field),str) or len(p[field].strip())<18:error('Part '+str(nums[i])+' missing substantial '+field)
  for field in ('knowledge_delta','evidence_delta','open_loops','closed_loops'):
   if not isinstance(p.get(field),list):error(field+' must be list')
  for loop in p['closed_loops']:
   if loop not in new_open:error('Cannot close an unregistered narrative loop: '+str(loop))
   new_open.remove(loop)
  if any(x in new_open for x in p['open_loops']):error('Loop ID already open; no duplicate re-seeding')
  new_open.update(p['open_loops']);new_evidence+=p['evidence_delta'];new_knowledge+=p['knowledge_delta']
 # At C, all loops required to be closed OR explicitly identified as intentionally open with reason.
 if n.stage=='C' and new_open and not report.get('intentional_open_loops_justification'):
  error('Final stage retains open loops without documented justification: '+str(sorted(new_open)))
 data['last_stage']=n.stage
 data['checkpoints'].append({'stage':n.stage,'segment_sha256':sha(raw),'parts':nums,'part_updates':updates,'report_sha256':sha(Path(n.report).read_bytes())})
 data['reported_knowledge']=new_knowledge;data['reported_evidence']=new_evidence;data['open_loops']=sorted(new_open)
 data.pop('seal_sha256');dump(n.out,seal(data))
 return {'pass':True,'stage':n.stage,'ledger':str(n.out),'source_sha256':sha(raw),'open_loops':len(new_open)}
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
 a=sub.add_parser('create');a.add_argument('--blueprint',required=True,type=Path);a.add_argument('--outline',required=True,type=Path);a.add_argument('--out',required=True,type=Path)
 b=sub.add_parser('checkpoint');b.add_argument('--ledger',required=True,type=Path);b.add_argument('--segment',required=True,type=Path);b.add_argument('--stage',required=True,choices=['A','B','C']);b.add_argument('--report',required=True,type=Path);b.add_argument('--out',required=True,type=Path)
 n=p.parse_args()
 try:r=create(n) if n.mode=='create' else checkpoint(n)
 except (ValueError,OSError,KeyError,TypeError,UnicodeError,json.JSONDecodeError) as e:r={'pass':False,'error':str(e)}
 print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['pass'] else 2
if __name__=='__main__':sys.exit(main())
