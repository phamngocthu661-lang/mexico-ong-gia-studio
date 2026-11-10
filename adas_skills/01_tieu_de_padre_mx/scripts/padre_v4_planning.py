#!/usr/bin/env python3
"""PADRE MX V4 local-first creative blueprint, local project memory, title duplication checks.
No channel scraping, no market intelligence, no network calls. Mechanical gates only.
"""
import argparse, hashlib, json, re, sys, unicodedata
from pathlib import Path
from difflib import SequenceMatcher

def sha(b): return hashlib.sha256(b).hexdigest()
def bad(s): raise ValueError(s)
def load(path): return json.loads(Path(path).read_text(encoding='utf8'))
def canonical(v): return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')
def norm(s):
 s=''.join(c for c in unicodedata.normalize('NFKD',str(s).lower()) if not unicodedata.combining(c))
 return ' '.join(re.findall(r'[a-z0-9]+',s))
STOP={'me','mi','la','las','el','los','lo','de','del','con','por','en','a','y','que','un','una','su','sus','para','no','se','al','yo','era','fue','como','the','and'}
def tokens(s):return {x for x in norm(s).split() if x not in STOP and len(x)>2}
def similarity(a,b):
 at,bt=tokens(a),tokens(b)
 jac=len(at&bt)/len(at|bt) if at|bt else 1.0
 seq=SequenceMatcher(None,norm(a),norm(b)).ratio()
 return round(max(jac,seq*0.85),4)
SIG_FIELDS=('central_injustice','leverage','evidence_mechanism','antagonist_cost','earned_payoff')

def sig_similarity(a,b):
 if not isinstance(a,dict) or not isinstance(b,dict): return None
 return round(sum(1 for k in SIG_FIELDS if norm(a.get(k,'')) and norm(a.get(k,''))==norm(b.get(k,'')))/len(SIG_FIELDS),3)

def duplicates(title, signature, memory, corpus=None):
 candidates=[]
 if memory and Path(memory).exists():
  mem=load(memory)
  if mem.get('schema')!='PADRE_MX_PROJECT_MEMORY_V4':bad('Memory schema unsupported')
  for e in mem.get('projects',[]):candidates.append(('local-project',e['locked_title'],e.get('originality_signature',{}),e.get('video_id')))
 if corpus:
  arr=load(corpus)
  if not isinstance(arr,list):bad('Corpus must be list of reference titles')
  for x in arr:
   if isinstance(x,dict) and x.get('title'):candidates.append(('supplied-reference',x['title'],None,x.get('url')))
 hits=[]
 for source,old,oldsig,ref in candidates:
  lexical=similarity(title,old);sig=sig_similarity(signature,oldsig)
  exact=(norm(title)==norm(old));same_sig=(sig is not None and sig>=0.8)
  if exact or lexical>=0.57 or (sig is not None and sig>=0.6):
   status='BLOCK_EXACT' if exact else ('BLOCK_SAME_MECHANISM' if same_sig and source=='local-project' else 'MANUAL_REVIEW')
   hits.append({'source':source,'reference':ref,'title':old,'lexical_similarity':lexical,'signature_match':sig,'decision':status})
 order={'BLOCK_EXACT':0,'BLOCK_SAME_MECHANISM':1,'MANUAL_REVIEW':2}
 hits=sorted(hits,key=lambda x:(order[x['decision']],-x['lexical_similarity']))[:30]
 return {'candidate_title':title,'title_length':len(title),'pass_title_length':1<=len(title)<=100,'status':'BLOCK_LENGTH' if not 1<=len(title)<=100 else ('BLOCK' if any(h['decision'].startswith('BLOCK') for h in hits) else 'REVIEW' if hits else 'NO_HIGH_SIMILARITY_FOUND'),'comparisons':len(candidates),'matches':hits,'disclaimer':'Lexical or declared-mechanism matching is an aid only; it cannot prove story originality or detect all semantic duplication.'}

def blueprint_check(bp):
 errors=[]
 def need(condition,msg):
  if not condition:errors.append(msg)
 need(bp.get('schema')=='PADRE_MX_STORY_BLUEPRINT_V4','Invalid blueprint schema')
 title=bp.get('locked_title','');need(isinstance(title,str) and 1<=len(title)<=100,'locked_title must have 1-100 Unicode chars')
 for k in ['primary_dna','story_mode','hook_pattern','central_promise','emotional_axis','original_angle']:
  need(isinstance(bp.get(k),str) and len(bp.get(k,'').strip())>=8,k+' is missing or too short')
 secondary=bp.get('secondary_dna');need(isinstance(secondary,list) and 1<=len(secondary)<=2 and all(isinstance(x,str) and x.strip() for x in secondary),'secondary_dna needs 1-2 names')
 signature=bp.get('originality_signature')
 need(isinstance(signature,dict),'originality_signature object required')
 if isinstance(signature,dict):
  for k in SIG_FIELDS:need(isinstance(signature.get(k),str) and len(signature.get(k,'').strip())>=10,'originality_signature.'+k+' required')
 spine=bp.get('narrative_spine')
 need(isinstance(spine,dict),'narrative_spine object required')
 if isinstance(spine,dict):
  for k in ['initial_situation','central_question','investigation_path','core_answer','transformed_perspective']:
   need(isinstance(spine.get(k),str) and len(spine.get(k,'').strip())>=12,'narrative_spine.'+k+' required')
 parts=bp.get('parts')
 need(isinstance(parts,list) and len(parts)==7,'parts requires exactly seven records')
 if isinstance(parts,list) and len(parts)==7:
  for idx,p in enumerate(parts,1):
   need(isinstance(p,dict) and p.get('part')==idx,f'Part {idx} wrong number/order')
   if not isinstance(p,dict):continue
   for k in ['objective','new_action','new_evidence','consequence','entry_from_previous','exit_to_next','character_cost']:
    need(isinstance(p.get(k),str) and len(p.get(k,'').strip())>=10,f'Part {idx} {k} missing')
   beats=p.get('retention_beats',[])
   need(isinstance(beats,list) and len(beats)>=2 and all(isinstance(x,dict) and all(len(str(x.get(q,'')))>=8 for q in ('trigger','new_value')) for x in beats),f'Part {idx} requires >=2 meaningful retention beats')
   scenes=p.get('scenes',[])
   need(isinstance(scenes,list) and 8<=len(scenes)<=12,f'Part {idx} requires 8-12 scene beats')
   if isinstance(scenes,list):
    ids=set()
    for j,scene in enumerate(scenes):
     if not isinstance(scene,dict):errors.append(f'Part {idx} scene {j+1} must be object');continue
     for k in ['scene_id','location','time','objective','action','consequence']:
      need(isinstance(scene.get(k),str) and bool(scene.get(k).strip()),f'Part {idx} scene {j+1}.{k} missing')
     if scene.get('scene_id') in ids:errors.append(f'Part {idx} duplicate scene_id')
     ids.add(scene.get('scene_id'))
 payoffs=bp.get('setup_payoff_map',[])
 need(isinstance(payoffs,list) and len(payoffs)>=3,'At least 3 distinct planted setup/payoff entries required')
 if isinstance(payoffs,list):
  for i,x in enumerate(payoffs):
   if not isinstance(x,dict):errors.append(f'Payoff {i+1} must be object');continue
   a,b=x.get('seed_part'),x.get('payoff_part')
   need(type(a)==int and type(b)==int and 1<=a<b<=7,f'Payoff {i+1} must be seeded before payoff')
   for k in ('seed','payoff','causal_link'):
    need(isinstance(x.get(k),str) and len(x.get(k,'').strip())>=10,f'Payoff {i+1} missing {k}')
 for k in ('character_knowledge_matrix','evidence_provenance','timeline_constraints'):
  need(isinstance(bp.get(k),list) and len(bp[k])>=1,k+' requires at least one record')
 return errors

def command_dedup(n):
 inp=load(n.candidate)
 for k in ('title','originality_signature'):
  if k not in inp:bad('Candidate missing '+k)
 result=duplicates(inp['title'],inp['originality_signature'],n.memory,n.corpus)
 result['pass']=result['status'] not in ('BLOCK','BLOCK_LENGTH')
 return result

def command_blueprint(n):
 bp=load(n.blueprint);errors=blueprint_check(bp)
 if n.title and bp.get('locked_title')!=n.title:errors.append('Title differs from LOCKED_TITLE')
 if n.outline:
  txt=Path(n.outline).read_bytes().decode('utf8')
  if '\r' in txt:errors.append('Outline must use LF-only')
  if not all(re.search(r'^\[PART '+str(p)+r'\]$',txt,re.M) for p in range(1,8)):errors.append('Outline missing [PART 1]...[PART 7] exact headings')
  if n.title and n.title not in txt and bp.get('locked_title')!=n.title:errors.append('Locked title not represented')
 result={'pass':not errors,'errors':errors,'parts':len(bp.get('parts',[])),'setup_payoffs':len(bp.get('setup_payoff_map',[])),'blueprint_sha256':sha(Path(n.blueprint).read_bytes()),'note':'This verifies structured completeness, not causal truth; independent story editor must evaluate.'}
 if not errors and n.memory:
  dd=duplicates(bp['locked_title'],bp['originality_signature'],n.memory,n.corpus)
  result['duplication']=dd
  if dd['status']=='BLOCK':result['pass']=False;result['errors'].append('Exact/local signature duplication: revise or document a different original angle')
 return result

def command_register(n):
 bp=load(n.blueprint);errs=blueprint_check(bp)
 if errs:bad('Blueprint invalid: '+str(errs[:5]))
 qa=load(n.qa)
 if qa.get('schema')!='PADRE_MX_QA_FINAL_V4' or qa.get('status')!='PASS_PUBLISH_READY':bad('V4 final QA PASS required')
 s=Path(n.script).read_bytes();s.decode('utf8','strict'); o=Path(n.outline).read_bytes();o.decode('utf8','strict')
 osh=sha(o);vid=sha((bp['locked_title']+'\n'+osh).encode('utf8'))[:16]
 if qa.get('locked_title')!=bp['locked_title'] or qa.get('script_sha256')!=sha(s) or qa.get('outline_sha256')!=osh or qa.get('video_id')!=vid:bad('QA identity/hash mismatch')
 if qa.get('blueprint_sha256')!=sha(Path(n.blueprint).read_bytes()):bad('QA-blueprint binding mismatch')
 path=Path(n.memory)
 if path.exists():m=load(path)
 else:m={'schema':'PADRE_MX_PROJECT_MEMORY_V4','projects':[]}
 if m.get('schema')!='PADRE_MX_PROJECT_MEMORY_V4':bad('Memory schema mismatch')
 if any(x['video_id']==vid for x in m['projects']):bad('Already registered, refuse duplicate append')
 dd=duplicates(bp['locked_title'],bp['originality_signature'],path if path.exists() else None)
 if dd['status']=='BLOCK':bad('Duplicate confirmed/local signature conflict: '+str(dd['matches'][:2]))
 m['projects'].append({'video_id':vid,'locked_title':bp['locked_title'],'originality_signature':bp['originality_signature'],'primary_dna':bp['primary_dna'],'story_mode':bp['story_mode'],'major_payoff':bp['narrative_spine']['core_answer'],'script_sha256':sha(s),'final_qa_sha256':sha(Path(n.qa).read_bytes()),'blueprint_sha256':sha(Path(n.blueprint).read_bytes())})
 path.parent.mkdir(parents=True,exist_ok=True)
 # No silent overwrites: existing memory is explicitly updated only via register; tmp replace is atomic.
 tmp=path.with_name(path.name+'.tmp')
 if tmp.exists():bad('Pending memory temp exists')
 tmp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
 return {'pass':True,'registered_video_id':vid,'memory':str(path),'entries':len(m['projects'])}

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
 d=sub.add_parser('dedup');d.add_argument('--candidate',type=Path,required=True);d.add_argument('--memory',type=Path);d.add_argument('--corpus',type=Path)
 b=sub.add_parser('blueprint');b.add_argument('--blueprint',type=Path,required=True);b.add_argument('--title');b.add_argument('--outline',type=Path);b.add_argument('--memory',type=Path);b.add_argument('--corpus',type=Path)
 r=sub.add_parser('register');r.add_argument('--blueprint',type=Path,required=True);r.add_argument('--qa',type=Path,required=True);r.add_argument('--script',type=Path,required=True);r.add_argument('--outline',type=Path,required=True);r.add_argument('--memory',type=Path,required=True)
 a=p.parse_args()
 try:out={'dedup':command_dedup,'blueprint':command_blueprint,'register':command_register}[a.cmd](a)
 except (ValueError,KeyError,OSError,TypeError,json.JSONDecodeError,UnicodeError) as e:out={'pass':False,'error':str(e)}
 print(json.dumps(out,ensure_ascii=False,indent=2));return 0 if out.get('pass',True) else 2
if __name__=='__main__':sys.exit(main())
