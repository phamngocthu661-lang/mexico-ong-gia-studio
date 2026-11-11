#!/usr/bin/env python3
"""HOMELESS STORY V3 local-first orchestration and mechanical evidence gates.

This program cannot generate prose, assess artistic originality, certify genuine
editorial review, or validate factual accuracy of fictional legal processes.
All scores and editorial gates are evidence *declarations*, not objective measures.
Inputs and outputs are UTF-8 JSON. Exit 0=PASS, 2=FAIL.

Run `python homeless_controller.py -h` for commands.
"""
import argparse, hashlib, json, re, subprocess, sys
from difflib import SequenceMatcher
from pathlib import Path
from datetime import datetime, timezone

SCHEMA='HOMELESS_PROJECT_V3'
SEGMENTS={'A':[1,2], 'B':[3,4,5], 'C':[6,7]}
REQUIRED_CANON=('protagonist','property','timeline','money','object_states','knowledge','authority','resolution_mode')
HEAD=re.compile(r'^\[PART ([1-7])\]$')

def digest(b):return hashlib.sha256(b).hexdigest()
def read_json(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write_json(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');t.replace(p)
def utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def require(cond, msg):
 if not cond:raise ValueError(msg)
def textfile(p):
 raw=Path(p).read_bytes();require(not raw.startswith(b'\xef\xbb\xbf'),'UTF8 BOM forbidden')
 val=raw.decode('utf-8','strict');require('\r' not in val,'CR/CRLF forbidden; use LF');return val,raw

def state_file(ns):return Path(ns.project)/'PROJECT_STATE_V3.json'
def load_state(ns):
 p=state_file(ns); require(p.is_file(),'Project not initialized: '+str(p));s=read_json(p);require(s.get('schema')==SCHEMA,'Schema mismatch');return s

def save_state(ns,s):
 s['updated_at']=utc();write_json(state_file(ns),s)

def title_valid(title):
 require(isinstance(title,str) and title.strip() and title==title.strip(),'Title missing or leading/trailing spaces')
 require('\n' not in title and '\r' not in title,'Multiline title prohibited')
 require(len(title)<=100,f'Title exceeds 100 chars: {len(title)}')
 return title

def fingerprint(s):return ' '.join(re.findall(r'[a-z0-9]+',str(s).casefold()))

def memory_alert(ns, data):
 statepath=state_file(ns)
 state=read_json(statepath) if statepath.is_file() else {}
 path=Path(state.get('memory_path') or Path(ns.project)/'LOCAL_STORY_MEMORY.json')
 if not path.is_file():return {'status':'UNKNOWN','note':'No local historical data; absence of evidence is not proof of uniqueness','matches':[]}
 rows=read_json(path)
 if isinstance(rows,dict):rows=rows.get('entries',[])
 require(isinstance(rows,list),'Local story memory must be a list or {entries: []}')
 matches=[]
 for row in rows:
  if not isinstance(row,dict):continue
  sims={}
  for key in ('title','mechanism','payoff','premise'):
   q=fingerprint(data.get(key,''));p=fingerprint(row.get(key,''))
   if q and p:sims[key]=round(SequenceMatcher(None,q,p).ratio(),3)
  if sims and max(sims.values())>=0.70:
   matches.append({'reference':row.get('id') or row.get('title'),'similarities':sims,'strongest':max(sims.values())})
 matches.sort(key=lambda r:r['strongest'],reverse=True)
 worst=max((x['strongest'] for x in matches),default=0)
 return {'status':'RED_REVIEW' if worst>=0.88 else 'YELLOW_REVIEW' if worst>=0.70 else 'GREEN_HEURISTIC','matches':matches[:8], 'note':'Lexical heuristic only; not a semantic originality certificate'}

def cmd_init(ns):
 title=title_valid(ns.title); p=Path(ns.project);p.mkdir(parents=True,exist_ok=True)
 require(not state_file(ns).exists(),'Existing project; refusing to overwrite state')
 s={'schema':SCHEMA,'title':title,'title_sha12':digest(title.encode('utf-8'))[:12],
    'created_at':utc(),'updated_at':utc(),'memory_path':str(ns.memory.resolve()) if ns.memory else None,'phase':'TITLE_PENDING','title_card':None,'outline':None,
    'segments':{},'script':None,'qa':None,'revision_number':0,'qa_history':[],'seo':None,
    'handoff':{},'mechanical_warnings':['Editorial claims must be independently assessed; hashes do not prove quality']}
 save_state(ns,s)
 return {'state':str(state_file(ns)),'phase':s['phase'],'title_sha12':s['title_sha12']}

def cmd_title(ns):
 s=load_state(ns);d=read_json(ns.card)
 require(d.get('title')==s['title'],'Title card mismatch: locked title')
 require(d.get('readiness')=='READY' and isinstance(d.get('score'),(int,float)) and 98<=d['score']<=100,'Title not editorially READY 98..100')
 require(d.get('instant_comprehension') is True and d.get('opening_serviceability') is True,'Title hard review gates not attested')
 for k in ('source_title','viewer_contract','viral_dna','new_mechanism'):
  require(str(d.get(k,'')).strip(),f'Missing title card field: {k}')
 require(not s['title_card'] and s['phase']=='TITLE_PENDING','Title already locked')
 evidence={'score':d['score'],'card_sha256':digest(Path(ns.card).read_bytes()),'file':str(Path(ns.card).resolve()),'locked_at':utc(),'editorial_score_self_reported':True}
 s['title_card']=evidence;s['phase']='TITLE_LOCKED';save_state(ns,s)
 return {'phase':s['phase'],'title_card':evidence,'memory':memory_alert(ns,{'title':s['title']})}

def check_outline(d,s):
 require(d.get('title')==s['title'],'Outline title mismatch')
 require(isinstance(d.get('score'),(int,float)) and 98<=d['score']<=100,'Outline score not in 98..100')
 for k in ('premise','primary_mystery','deeper_mystery','mechanism','payoff','ending_action','dna_primary'):
  require(str(d.get(k,'')).strip(),f'Outline missing {k}')
 parts=d.get('parts');require(isinstance(parts,list) and len(parts)==7,'Outline must define 7 parts')
 require([x.get('part') for x in parts]==list(range(1,8)),'Part numbers not exactly 1..7 in order')
 budgets=[]
 for part in parts:
  require(len(part.get('beats',[]))>=3,f'Part {part["part"]} needs >=3 distinct beats')
  for k in ('entry','discovery','exit'):
   require(str(part.get(k,'')).strip(),f'Part {part["part"]} missing {k}')
  val=part.get('target_chars');require(isinstance(val,int) and 4000<=val<=20000,'Part budget out of sensible range')
  budgets.append(val)
 require(70000<=sum(budgets)<=80000,'Part budgets must sum to 70–80k')
 clues=d.get('clues');require(isinstance(clues,list) and len(clues)>=8,'Require 8+ clues')
 ids=[];reinterpreted=0
 for cl in clues:
  cid=cl.get('id');require(isinstance(cid,str) and cid,'Clue ID required');ids.append(cid)
  u=cl.get('setup_part');v=cl.get('payoff_part')
  require(isinstance(u,int) and isinstance(v,int) and 1<=u<=v<=7,f'Clue {cid}: invalid setup/payoff parts')
  require(str(cl.get('evidence','')).strip(),f'Clue {cid}: evidence required')
  if cl.get('reinterpreted') is True:reinterpreted+=1
 require(len(ids)==len(set(ids)),'Duplicate clue IDs');require(reinterpreted>=2,'Require >=2 reinterpreted clues')
 reveals=d.get('reveals');require(isinstance(reveals,list) and len(reveals)>=4,'Require 4+ reveals')
 for rev in reveals:
  require(1<=rev.get('part',0)<=7 and str(rev.get('answer','')).strip(),'Reveal requires valid part and answer')
 early=d.get('early_retention',{})
 for k,upper in [('title_promise_at',200),('physical_proof_at',400),('micro_payoff_1_at',1100),('forward_question_at',2000),('micro_payoff_2_at',5000)]:
  v=early.get(k);require(isinstance(v,int) and 0<=v<=upper,'Early-retention gate missing/late: '+k)
 canon=d.get('canon',{});require(isinstance(canon,dict),'Missing canon')
 for k in REQUIRED_CANON:require(canon.get(k) not in (None,'',[],{}),'Missing canon '+k)
 require(canon['resolution_mode'] in ('A','B'),'Resolution mode must be A or B')
 return {'sum_budgets':sum(budgets),'clues':len(clues),'reinterpreted':reinterpreted,'reveals':len(reveals)}

def cmd_outline(ns):
 s=load_state(ns);require(s['phase']=='TITLE_LOCKED','Must lock title first')
 d=read_json(ns.blueprint); metrics=check_outline(d,s)
 mem=memory_alert(ns,{k:d.get(k,'') for k in ('premise','mechanism','payoff')}|{'title':s['title']})
 require(mem['status']!='RED_REVIEW' or ns.allow_duplicate_review,'Strong local similarity requires explicit --allow-duplicate-review after editorial differentiation')
 s['outline']={'file':str(Path(ns.blueprint).resolve()),'sha256':digest(Path(ns.blueprint).read_bytes()),'metrics':metrics,'editorial_score_self_reported':True,'duplication':mem}
 s['phase']='OUTLINE_LOCKED';save_state(ns,s)
 return {'phase':s['phase'],'metrics':metrics,'originality_screen':mem}

def validate_handoff(d,s,segment,stage_file):
 require(d.get('title')==s['title'] and d.get('segment')==segment,'Handoff title/segment mismatch')
 txt,_=textfile(stage_file)
 allowed=SEGMENTS[segment]
 for e in d.get('evidence',[]):
  require(e.get('part') in allowed,'Handoff evidence from wrong Part')
  require(str(e.get('quote','')).strip() and e['quote'] in txt,'Handoff quote not found in source segment')
  pm=re.search(r'^\[PART '+str(e['part'])+r'\]\n(.*?)(?=^\[PART \d\]\n|\Z)',txt,re.M|re.S)
  require(pm is not None and e['quote'] in pm.group(1),'Evidence quote appears in wrong Part')
 facts=d.get('facts');require(isinstance(facts,list) and facts,'Handoff facts required')
 for f in facts:
  require(isinstance(f.get('key'),str) and str(f.get('value','')).strip(),'Handoff fact requires key/value')
 prior={}
 open_loops=set()
 for key in SEGMENTS:
  if key==segment:break
  past=s['handoff'].get(key)
  require(past is not None,'Missing earlier handoff '+key)
  for f in past.get('facts',[]):
   if f.get('immutable') is True:
    if f['key'] in prior:require(prior[f['key']]==f['value'],'Contradictory past immutable facts '+f['key'])
    prior[f['key']]=f['value']
  open_loops.update(past.get('open_loops',[]));open_loops.difference_update(past.get('closed_loops',[]))
 for f in facts:
  if f['key'] in prior:require(prior[f['key']]==f['value'],'Canon drift: '+f['key'])
 new_loops=d.get('open_loops',[]); closed=d.get('closed_loops',[])
 require(isinstance(new_loops,list) and isinstance(closed,list),'Open/closed loops must be arrays')
 require(len(new_loops)==len(set(new_loops)) and len(closed)==len(set(closed)),'Duplicate loop IDs')
 require(not (set(new_loops)&set(closed)),'Cannot both open and close loop in same handoff')
 require(set(closed).issubset(open_loops),'Cannot close an unregistered earlier open loop')
 if segment=='C':require(not ((open_loops-set(closed))|set(new_loops)),'Part C must close all major declared open loops')
 return True

def legacy(action,title,directory,segment=None,file=None):
 tool=Path(__file__).parent/'legacy_segment_workflow.py';require(tool.is_file(),'Missing bundled legacy_segment_workflow.py')
 cmd=[sys.executable,str(tool),action,'--title',title,'--directory',str(directory)]
 if action=='stage':cmd+=['--segment',segment,'--file',str(file)]
 proc=subprocess.run(cmd,text=True,capture_output=True)
 try:response=json.loads(proc.stdout)
 except json.JSONDecodeError:raise ValueError('Legacy segment workflow failed: '+proc.stderr+' '+proc.stdout)
 require(proc.returncode==0 and response.get('pass') is True,'Segment workflow rejected: '+str(response.get('error',response)))
 return response

def cmd_stage(ns):
 s=load_state(ns);seg=ns.segment
 require(s['outline'] is not None,'Outline missing')
 require(Path(s['outline']['file']).is_file() and digest(Path(s['outline']['file']).read_bytes())==s['outline']['sha256'],'Locked outline modified or missing')
 require(s['phase'] in ('OUTLINE_LOCKED','STAGING_A','STAGING_B'),'Project not in writing/staging phase')
 require(list(s['segments'])==list(SEGMENTS)[:len(s['segments'])],'Corrupt segment order')
 expected=list(SEGMENTS)[len(s['segments'])] if len(s['segments'])<3 else None
 require(seg==expected,f'Expected next stage {expected}, received {seg}')
 d=read_json(ns.handoff);validate_handoff(d,s,seg,ns.file)
 result=legacy('stage',s['title'],ns.directory,segment=seg,file=ns.file)
 s['segments'][seg]={'file_sha256':result['file_sha256'],'file':result['segment_path'],'body_chars':result['body_chars']}
 s['handoff'][seg]=d;s['phase']='STAGING_'+seg;save_state(ns,s)
 return {'phase':s['phase'],'stage':result,'handoff_sha256':digest(Path(ns.handoff).read_bytes())}

def cmd_assemble(ns):
 s=load_state(ns);require(s['phase']=='STAGING_C' and list(s['segments'])==['A','B','C'],'Segments A/B/C not complete')
 res=legacy('assemble',s['title'],ns.directory)
 require(res.get('pass') and 70000<=res['script_body_chars']<=80000,'Full body length invalid')
 s['script']={'file':str((Path(ns.directory)/f'HML_{s["title_sha12"]}_FULL_SCRIPT.txt').resolve()),'sha256':res['file_sha256'],'body_sha256':res['script_body_sha256'],'body_chars':res['script_body_chars'],'revision':0}
 s['phase']='SCRIPT_READY_FOR_QA';save_state(ns,s)
 return {'phase':s['phase'],'script':s['script']}

def verify_live(s):
 require(s['script'] is not None,'No script')
 p=Path(s['script']['file']);require(p.is_file(),'Current script file missing')
 from verify_full_script import report
 r=report(p)
 require(r.get('pass') is True and r['file_sha256']==s['script']['sha256'] and r['script_body_sha256']==s['script']['body_sha256'],'Current manuscript failed length/hash gate or changed after lock')
 return r

def check_frozen(d,s):
 require(d.get('schema')=='HOMELESS_QA_FROZEN_V1.8.1','Unexpected QA freeze schema')
 require(d.get('title')==s['title'],'QA title != locked title')
 q=d.copy();sig=q.pop('manifest_sha256',None)
 require(sig==digest(json.dumps(q,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')),'QA frozen manifest checksum invalid')
 live=verify_live(s);frozen=d.get('frozen_source',{})
 require(frozen.get('file_sha256')==live['file_sha256'] and frozen.get('body_sha256')==live['script_body_sha256'],'QA source stale/mismatch')
 require(frozen.get('body_chars')==live['script_body_chars'],'QA length mismatch')
 require(isinstance(d.get('frozen_baseline_score'),(int,float)),'QA score missing')
 ready=d.get('publication_readiness')=='READY'
 if ready:
  require(d['frozen_baseline_score']>=98 and d.get('hard_gate_pass') is True and not d.get('frozen_patch_ledger'),'Malformed QA READY status')
 return ready

def cmd_qa(ns):
 s=load_state(ns);require(s['script'] is not None,'Script must be assembled or patched first')
 require(s['phase'] in ('SCRIPT_READY_FOR_QA','QA_NOT_READY','QA_READY'),'Not in QA phase')
 d=read_json(ns.frozen);ready=check_frozen(d,s)
 if s['qa']:s['qa_history'].append(s['qa'])
 s['qa']={'file':str(Path(ns.frozen).resolve()),'sha256':digest(Path(ns.frozen).read_bytes()),'ready':ready,'score':d['frozen_baseline_score'],'script_sha256':s['script']['sha256']}
 s['phase']='QA_READY' if ready else 'QA_NOT_READY';s['seo']=None;save_state(ns,s)
 return {'phase':s['phase'],'score':s['qa']['score'],'ready':ready,'note':'Editorial evidence is reviewer-authored; mechanical validation cannot prove its truth'}

def check_patch(ns,s):
 require(s['phase']=='QA_NOT_READY' and s['qa'],'Only QA_NOT_READY can authorize patch')
 audit=read_json(s['qa']['file']);check_frozen(audit,s)
 original,_=textfile(s['script']['file']);candidate,_=textfile(ns.candidate)
 require(candidate!=original,'No changes')
 plan=read_json(ns.plan)
 require(plan.get('baseline_sha256')==s['script']['sha256'],'Patch plan baseline file SHA mismatch')
 ed=plan.get('edits');require(isinstance(ed,list) and ed,'Approved edits required')
 tickets={x['id']:x for x in audit.get('frozen_patch_ledger',[])}
 ticket_ids=set(tickets)
 require(ticket_ids,'No approved patch tickets')
 exp=original
 for e in ed:
  tid=e.get('ticket_id');require(tid in ticket_ids,'Unauthorized ticket: '+str(tid))
  pn=e.get('part');require(pn in range(1,8),'Patch Part invalid')
  require(tickets[tid].get('part')=='Part '+str(pn),'Ticket does not authorize this Part')
  old=e.get('old');new=e.get('new')
  require(isinstance(old,str) and len(old)>=5 and isinstance(new,str),'Patch requires >=5-char old anchor and new text')
  pattern=re.compile(r'(^\[PART '+str(pn)+r'\]\n)(.*?)(?=^\[PART \d\]\n|\Z)',re.M|re.S)
  m=pattern.search(exp);require(m is not None,f'Missing Part {pn}')
  content=m.group(2)
  require(content.count(old)==1,f'Anchor ambiguous/absent in Part {pn}')
  require(tickets[tid].get('anchor') in old,'Patch does not contain exact authorized anchor for '+tid)
  newcontent=content.replace(old,new,1)
  exp=exp[:m.start(2)]+newcontent+exp[m.end(2):]
 require(exp==candidate,'Candidate has unauthorized edits, reflow, or whitespace changes')
 for sp in audit.get('strong_span_ledger',[]):
  anchor=sp.get('anchor');require(not anchor or anchor in candidate,'Immutable PASS span altered: '+str(anchor)[:70])
 from verify_full_script import report
 verified=report(Path(ns.candidate));require(verified.get('pass') is True,'Candidate fails length or structural gate: '+str(verified.get('failures')))
 return {'candidate_sha256':verified['file_sha256'],'body_sha256':verified['script_body_sha256'],'body_chars':verified['script_body_chars'],'tickets':sorted({e['ticket_id'] for e in ed})}

def cmd_patch_verify(ns):
 s=load_state(ns);p=check_patch(ns,s)
 return {'pass':True,'patch':p,'note':'Only mechanical authorized diff verified; still requires fresh independent QA'}

def cmd_patch_commit(ns):
 s=load_state(ns);out=check_patch(ns,s)
 require(Path(ns.candidate).resolve()!=Path(s['script']['file']).resolve(),'Revision must be a new file, not overwrite baseline')
 s['qa_history'].append(s['qa']);s['qa']=None;s['seo']=None;s['revision_number']+=1
 s['script']={'file':str(Path(ns.candidate).resolve()),'sha256':out['candidate_sha256'],'body_sha256':out['body_sha256'],'body_chars':out['body_chars'],'revision':s['revision_number']}
 s['phase']='SCRIPT_READY_FOR_QA';save_state(ns,s)
 return {'phase':s['phase'],'script':s['script'],'require_fresh_qa':True,'patch':out}

def cmd_seo(ns):
 s=load_state(ns);require(s['phase']=='QA_READY' and s['qa'] and s['qa']['ready'],'SEO blocked: no ready QA')
 live=verify_live(s);require(live['file_sha256']==s['qa']['script_sha256'],'QA stale on current script')
 d=read_json(ns.pack)
 require(d.get('title')==s['title'],'SEO title changed')
 description=d.get('description','');require(isinstance(description,str) and 170<=len(description.split())<=280,'Description must be 170..280 whitespace-separated words')
 tags=d.get('tags','');require(isinstance(tags,str) and 0<len(tags)<=500,'YouTube tags 1..500 chars')
 hashtags=d.get('hashtags');require(isinstance(hashtags,list) and 3<=len(hashtags)<=15 and all(str(t).startswith('#') for t in hashtags),'Hashtag list invalid')
 thumb=d.get('thumbnail');require(isinstance(thumb,dict) and len(str(thumb.get('prompt','')))>80,'Thumbnail prompt missing')
 require(thumb.get('aspect_ratio')=='16:9','Thumbnail must be 16:9')
 body,_=textfile(s['script']['file'])
 require(str(thumb.get('evidence_quote','')) in body and len(str(thumb.get('evidence_quote','')))>=10,'Thumbnail must include an actual script evidence quote')
 trail=d.get('trailer');require(isinstance(trail,dict) and trail.get('seconds') in (10,20,30),'Trailer duration must be 10/20/30 seconds')
 require(trail.get('no_dialogue') is True and trail.get('no_lip_sync') is True,'Trailer audio/no lip sync restriction not acknowledged')
 clips=trail.get('clips')
 require(isinstance(clips,list) and len(clips)==trail['seconds']//10,'Trailer must provide 1–3 separate 10-second Omni clips')
 refs=d.get('evidence_quotes');require(isinstance(refs,list) and len(refs)>=3,'SEO needs >=3 script evidence quotes')
 for ref in refs:require(isinstance(ref,str) and len(ref)>=10 and ref in body,'SEO evidence quote not found in script')
 for ci,clip in enumerate(clips,1):
  require(clip.get('seconds')==10 and len(str(clip.get('prompt','')))>=80,f'OMNI clip {ci} must be 10s with complete prompt')
  shots=clip.get('shots')
  require(isinstance(shots,list) and len(shots)>=2,f'OMNI clip {ci} must contain multiple shots')
  for i,shot in enumerate(shots,1):
   require(str(shot.get('action','')).strip() and str(shot.get('environment','')).strip(),f'Trailer clip {ci} shot {i} missing action/environment')
   require(len(str(shot.get('evidence_quote','')))>=10 and shot['evidence_quote'] in body,f'Trailer clip {ci} shot {i} ungrounded in script')
 require(d.get('factual_review') is True and d.get('trailer_review') is True,'Editor must review fact lock and trailer continuity')
 s['seo']={'file':str(Path(ns.pack).resolve()),'sha256':digest(Path(ns.pack).read_bytes()),'script_sha256':live['file_sha256'],'checked_at':utc(),'status':'METADATA_READY_AS_PROMPTS'}
 s['phase']='SEO_PACK_READY';save_state(ns,s)
 return {'phase':s['phase'],'seo':s['seo'],'note':'Thumbnail/trailer prompts verified as JSON only. No actual media rendered.'}

def cmd_memory(ns):
 s=load_state(ns);require(s['phase'] in ('QA_READY','SEO_PACK_READY'),'Only approved content can enter story memory')
 require(s['outline'] and s['title_card'],'Missing approved title/outline')
 d=read_json(s['outline']['file']);mfile=Path(s.get('memory_path') or Path(ns.project)/'LOCAL_STORY_MEMORY.json')
 rows=read_json(mfile) if mfile.is_file() else []
 if isinstance(rows,dict):rows=rows.get('entries',[])
 require(isinstance(rows,list),'Invalid memory structure')
 row={'id':s['title_sha12'],'title':s['title'],'mechanism':d['mechanism'],'payoff':d['payoff'],'premise':d['premise'],'script_sha256':s['script']['sha256'],'saved_at':utc()}
 require(not any(x.get('id')==row['id'] for x in rows),'Story already in local memory')
 rows.append(row);write_json(mfile,rows)
 return {'memory':str(mfile),'count':len(rows),'added':row['id']}

def cmd_status(ns):
 s=load_state(ns);warning=None
 if s['script']:
  try:verify_live(s)
  except Exception as e:warning=str(e)
 return {'phase':s['phase'],'title':s['title'],'outline_ready':s['outline'] is not None,'segments':list(s['segments']), 'script':s['script'], 'qa':s['qa'], 'seo':s['seo'], 'warning':warning}

def main():
 ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest='cmd',required=True)
 def p(name,**kwargs):
  q=sub.add_parser(name,**kwargs);q.add_argument('--project',required=True,type=Path);return q
 x=p('init');x.add_argument('--title',required=True);x.add_argument('--memory',type=Path,help='Optional shared local cross-project memory JSON path')
 x=p('lock-title');x.add_argument('--card',required=True,type=Path)
 x=p('lock-outline');x.add_argument('--blueprint',required=True,type=Path);x.add_argument('--allow-duplicate-review',action='store_true')
 x=p('stage');x.add_argument('--segment',required=True,choices=list(SEGMENTS));x.add_argument('--file',required=True,type=Path);x.add_argument('--handoff',required=True,type=Path);x.add_argument('--directory',type=Path,required=True)
 x=p('assemble');x.add_argument('--directory',type=Path,required=True)
 x=p('attach-qa');x.add_argument('--frozen',required=True,type=Path)
 x=p('verify-patch');x.add_argument('--candidate',required=True,type=Path);x.add_argument('--plan',required=True,type=Path)
 x=p('commit-patch');x.add_argument('--candidate',required=True,type=Path);x.add_argument('--plan',required=True,type=Path)
 x=p('verify-seo');x.add_argument('--pack',required=True,type=Path)
 p('remember');p('status')
 ns=ap.parse_args()
 fn={'init':cmd_init,'lock-title':cmd_title,'lock-outline':cmd_outline,'stage':cmd_stage,'assemble':cmd_assemble,'attach-qa':cmd_qa,'verify-patch':cmd_patch_verify,'commit-patch':cmd_patch_commit,'verify-seo':cmd_seo,'remember':cmd_memory,'status':cmd_status}[ns.cmd]
 try:
  result=fn(ns)
  print(json.dumps({'pass':True,'command':ns.cmd,**result},ensure_ascii=False,indent=2));return 0
 except (OSError,ValueError,KeyError,TypeError,UnicodeError) as e:
  print(json.dumps({'pass':False,'command':ns.cmd,'error':str(e)},ensure_ascii=False,indent=2));return 2
if __name__=='__main__':sys.exit(main())
