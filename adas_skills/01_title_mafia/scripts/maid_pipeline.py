#!/usr/bin/env python3
"""Mafia Maid V2 local-first deterministic project/QA controller.
No APIs, no external dependencies. Narrative/semantic judgment remains human/LLM.
"""
from __future__ import annotations
import argparse, copy, difflib, hashlib, json, re, sys, unicodedata
from pathlib import Path
from datetime import datetime, timezone

VERSION = '2.0.0'
MAX_REPAIRS = 2
COMPONENTS = {'A':20,'B':20,'C':15,'D':10,'E':10,'F':10,'G':10,'H':5}
DEDUCTIONS = {'P0':None,'P1':0.30,'P2':0.12,'P3':0.04}
WORD_RX = re.compile(r"[A-Za-z0-9]+(?:[\u2019'\-][A-Za-z0-9]+)*")
HEADING_RX = re.compile(r'^PART\s+([1-9][0-9]*)\s*[\u2013\u2014-]\s*(.+?)\s*$', re.I)
BAD_CUE_RX = re.compile(r'\[[^\]\n]{1,90}\]')
META_LINE_RX = re.compile(r'^\s*(?:CAMERA|SFX|MUSIC|DIRECTOR(?:\'S)? NOTE|SCENE DESCRIPTION|VISUAL PROMPT|IMAGE PROMPT|EDITING NOTE|PRODUCTION NOTE|TIMECODE|TIMESTAMP)\s*:',re.I|re.M)
TITLE_KEYS = ['heroine_role','trigger_event','power_dynamic','hidden_competence','evidence_mechanism','core_reversal','payoff']
class GateError(Exception): pass

def err(msg): raise GateError(msg)
def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def nfc(t): return unicodedata.normalize('NFC',t)
def sha(b): return hashlib.sha256(b).hexdigest()
def t_sha(t): return sha(nfc(t).encode('utf-8'))
def read_text(p): return nfc(Path(p).read_text(encoding='utf-8-sig'))
def read_json(p): return json.loads(read_text(p))
def write_json(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_text(p,t):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8')
def require(cond,msg):
    if not cond: err(msg)
def project(path):
    d=Path(path).resolve(); f=d/'state.json'
    require(f.is_file(),f'Project not initialized: {f}')
    s=read_json(f);require(s.get('controller_version')=='2.0.0','Project controller version mismatch')
    return d,s
def persist(d,s): s['updated_at']=now();write_json(d/'state.json',s)
def artifact(d,s,key):
    entry=s.get('artifacts',{}).get(key)
    require(entry, f'Missing artifact: {key}')
    file=d/entry['path'];require(file.is_file(),f'File missing: {file}')
    require(sha(file.read_bytes())==entry['sha256'],f'Artifact SHA mismatch for {key}: stale or modified file')
    return file

def store(d,s,key,name,data):
    file=d/'artifacts'/name
    if isinstance(data,str): write_text(file,data)
    else:write_json(file,data)
    s.setdefault('artifacts',{})[key]={'path':str(file.relative_to(d)),'sha256':sha(file.read_bytes()),'bytes':file.stat().st_size}
    return file

def norm(s): return re.sub(r'\W+',' ',nfc(str(s)).casefold()).strip()
def fingerprint(record):
    return {key:norm(record.get(key,'')) for key in TITLE_KEYS}
def similarity(a,b):
    def tokens(k):return set(norm(k).split())
    sims=[]
    for key in TITLE_KEYS:
        x=tokens(a.get(key,''));y=tokens(b.get(key,''))
        if x and y: sims.append(len(x&y)/len(x|y))
    return round(sum(sims)/len(sims),3) if sims else 0.0

def init(d,project_id):
    d=Path(d).resolve();d.mkdir(parents=True,exist_ok=True)
    require(not (d/'state.json').exists(),'Project already initialized')
    require(bool(re.fullmatch('[A-Za-z0-9_-]{3,80}',project_id)),'project_id requires 3-80 safe characters')
    s={'controller_version':VERSION,'project_id':project_id,'status':'WAIT_TITLE','created_at':now(),'updated_at':now(),'locked_title':None,'repairs':0,'artifacts':{},'history':[]}
    persist(d,s);return s

def title_stage(d,source,memory=None):
    d,s=project(d);require(s['status']=='WAIT_TITLE','Title already locked; create a new project or explicitly rebase offline')
    t=read_json(source);title=t.get('selected_title','')
    require(isinstance(title,str) and title.strip(),'selected_title is required')
    require(len(nfc(title))<=100,'Title exceeds 100 Unicode characters')
    candidates=t.get('candidates',[])
    require(isinstance(candidates,list) and len(candidates)==5,'Normal title mode requires exactly five candidate entries')
    for x in candidates:
        require(isinstance(x,dict) and isinstance(x.get('title'),str),'Candidate must have title')
        require(len(nfc(x['title']))<=100,'Candidate title exceeds 100 chars')
        require(isinstance(x.get('score'),(int,float)) and 0<=x['score']<=100,'Candidate must have QA score 0..100')
    require(title in [x['title'] for x in candidates],'selected_title must match one of five candidates')
    fp=fingerprint(t.get('fingerprint',{}));require(sum(bool(x) for x in fp.values())>=4,'At least 4 fingerprint dimensions needed')
    report={'risk':'UNKNOWN','matches':[]}
    if memory:
        mp=Path(memory)
        db=read_json(mp) if mp.exists() else {'entries':[]}
        matches=[]
        for row in db.get('entries',[]):
            if row.get('project_id')==s['project_id']:continue
            other=row.get('fingerprint',{})
            sim=similarity(fp,other)
            exact=(norm(row.get('title',''))==norm(title))
            if exact or sim>=0.60:matches.append({'project_id':row.get('project_id'),'title':row.get('title'),'similarity':sim,'exact_title':exact})
        matches.sort(key=lambda x:(x['exact_title'],x['similarity']),reverse=True)
        report={'risk':'RED' if any(x['exact_title'] or x['similarity']>=0.9 for x in matches) else ('YELLOW' if matches else 'GREEN'),'matches':matches[:10]}
        require(report['risk']!='RED','High duplication risk / identical title; resolve or choose independent premise first')
        t['duplication_report']=report
    store(d,s,'title','title.json',t)
    s['locked_title']=title;s['title_sha256']=t_sha(title);s['status']='WAIT_OUTLINE';s['history'].append({'at':now(),'event':'TITLE_LOCKED','duplication_risk':report['risk']});persist(d,s)
    if memory:
        mp=Path(memory);db=read_json(mp) if mp.exists() else {'entries':[]};db['entries'].append({'project_id':s['project_id'],'title':title,'fingerprint':fp,'created_at':now()});write_json(mp,db)
    return {'state':s['status'],'title_sha256':s['title_sha256'],'duplication':report}

def check_outline(x,title):
    issues=[]
    def check(test,label):
        if not test:issues.append(label)
    check(x.get('title')==title,'outline title mismatch')
    check(x.get('primary_dna') in ('A','B','C'),'primary_dna A/B/C required')
    check(bool(x.get('content_family')),'content_family required')
    sc=x.get('story_core',{})
    if not isinstance(sc,dict):sc={}
    for key in ('premise','central_conflict','heroine_agency','core_reversal','major_payoff'):
        check(isinstance(sc.get(key),str) and bool(sc.get(key,'').strip()),f'missing story_core.{key}')
    beats=x.get('beats',[])
    check(isinstance(beats,list) and bool(beats),'beats list required')
    if isinstance(beats,list):
        for i,b in enumerate(beats,1):
            if not isinstance(b,dict):issues.append(f'beat {i} not object');continue
            check(b.get('number')==i,f'Beat {i} numbering mismatch')
            for key in ('name','cause','action','consequence','heroine_contribution','transition'):
                check(isinstance(b.get(key),str) and bool(b.get(key,'').strip()),f'Beat {i} missing {key}')
        loops=x.get('open_loops',[])
        check(isinstance(loops,list),'open_loops must be list')
        if isinstance(loops,list):
            ids=set()
            for row in loops:
                if not isinstance(row,dict):issues.append('loop not object');continue
                lid=row.get('id');check(bool(lid) and lid not in ids,'loop ID missing/duplicated');ids.add(lid)
                opened=row.get('opened_at');closed=row.get('closed_at')
                check(isinstance(opened,int) and isinstance(closed,int) and 1<=opened<=closed<=len(beats),f'loop {lid} invalid closure')
                check(bool(row.get('payoff')),'loop payoff required')
        evidence=x.get('evidence_chain',[])
        check(isinstance(evidence,list) and bool(evidence),'evidence_chain required')
        if isinstance(evidence,list):
            for e in evidence:
                check(isinstance(e,dict) and bool(e.get('id')) and bool(e.get('setup')) and bool(e.get('payoff')),'evidence requires id/setup/payoff')
    return issues

def outline_stage(d,source):
    d,s=project(d);require(s['status']=='WAIT_OUTLINE','Need locked title and WAIT_OUTLINE')
    x=read_json(source);issues=check_outline(x,s['locked_title']);require(not issues,'Outline gate: '+'; '.join(issues[:12]))
    store(d,s,'outline','outline.json',x);s['part_count']=len(x['beats']);s['status']='WAIT_SCRIPT';s['history'].append({'at':now(),'event':'BLUEPRINT_LOCKED','parts':len(x['beats'])});persist(d,s)
    return {'state':s['status'],'parts':len(x['beats'])}

def parse_script(t):
    t=nfc(t).replace('\r\n','\n').replace('\r','\n')
    lines=t.splitlines(keepends=True)
    headings=[];parts=[];start=None;head=None
    for i,line in enumerate(lines):
        mt=HEADING_RX.match(line.rstrip('\n'))
        if mt:
            if start is not None:parts.append({'number':head[0],'name':head[1],'text':''.join(lines[start:i])})
            elif ''.join(lines[:i]).strip():err('Unexpected text before first PART heading')
            start=i+1;head=(int(mt[1]),mt[2]);headings.append(line.strip())
    if start is not None:parts.append({'number':head[0],'name':head[1],'text':''.join(lines[start:])})
    require(parts,'No PART headings found; use PART 1 — Title')
    require(all(p['text'].strip() for p in parts),'Empty PART')
    nums=[p['number'] for p in parts];require(nums==list(range(1,len(parts)+1)),'PART numbers not sequential 1..N')
    return parts

def metrics(t):
    t=nfc(t);parts=parse_script(t)
    body='\n'.join(p['text'] for p in parts)
    # Visible characters include spaces, punctuation and Part headings; LF/CR are structural separators.
    visible_chars=len(t.replace('\r','').replace('\n',''))
    words=len(WORD_RX.findall(body))
    if BAD_CUE_RX.search(body):err('Script has bracketed TTS/stage cues')
    if META_LINE_RX.search(body):err('Script has production metadata inside TTS body')
    return {'visible_characters':visible_chars,'spoken_words':words,'parts':len(parts),'part_visible_characters':[len(p['text'].replace('\n',''))+len(f"PART {p['number']} — {p['name']}") for p in parts], 'part_words':[len(WORD_RX.findall(p['text'])) for p in parts]}

def length_findings(m):
    findings=[]
    def f(id,sev,reason):findings.append({'id':id,'severity':sev,'component':'F','reason':reason})
    n=m['visible_characters'];w=m['spoken_words']
    if n<40000 or n>55000 or w>=8000: f('LENGTH_HARD','P0',f'{n} chars / {w} words violates hard envelope')
    elif not (44000<=n<=48000 and 7400<=w<=7650):
        f('LENGTH_TARGET','P1' if w>7750 else 'P2',f'{n} chars / {w} words misses standard target')
    return findings

def script_stage(d,source):
    d,s=project(d);require(s['status']=='WAIT_SCRIPT','Script stage requires WAIT_SCRIPT')
    artifact(d,s,'outline')
    t=read_text(source);m=metrics(t)
    require(m['parts']==s['part_count'],f'Expected {s["part_count"]} PARTs, got {m["parts"]}')
    problems=length_findings(m);require(not problems,'Script length gate: '+str(problems))
    store(d,s,'script','script.txt',t);s['script_sha256']=t_sha(t)
    s['opb_sha256']=s.get('opb_sha256') or s['script_sha256'];s['status']='WAIT_CONTINUITY';s['history'].append({'at':now(),'event':'SCRIPT_ACCEPTED','metrics':m});persist(d,s)
    return {'state':s['status'],'metrics':m,'sha256':s['script_sha256']}

def continuity_stage(d,source):
    d,s=project(d);require(s['status']=='WAIT_CONTINUITY','Continuity checkpoint must follow SCRIPT acceptance')
    c=read_json(source)
    require(c.get('script_sha256')==s['script_sha256'],'Continuity report source script SHA mismatch')
    h=c.get('part_handoffs',[])
    require(isinstance(h,list) and len(h)==s['part_count'],'One handoff per PART is required')
    outline=read_json(artifact(d,s,'outline'))
    loops=outline.get('open_loops',[])
    prior=None
    for i,row in enumerate(h,1):
        require(isinstance(row,dict) and row.get('part')==i,f'Continuity handoff Part {i} missing')
        for key in ('entry_bridge','exit_bridge','location_end','timeline_end','heroine_action','relationship_state'):
            require(isinstance(row.get(key),str) and bool(row[key].strip()),f'Part {i} missing continuity field {key}')
        if prior is not None:require(row['entry_bridge']==prior['exit_bridge'],f'PART {i-1} -> {i} bridge mismatch')
        require(isinstance(row.get('character_knowledge'),dict),'character_knowledge map required')
        expected={loop['id'] for loop in loops if loop['opened_at']<=i<loop['closed_at']}
        actual=set(row.get('open_loops',[]))
        require(actual==expected,f'Part {i} open loop ledger inconsistent with outline: expected {sorted(expected)}')
        prior=row
    require(not h[-1]['open_loops'],'Final PART still has unresolved loops')
    store(d,s,'continuity','continuity.json',c)
    s['status']='WAIT_QA';s['history'].append({'at':now(),'event':'CONTINUITY_LOCKED'});persist(d,s)
    return {'state':s['status'],'parts':len(h),'open_loops_at_end':0}

def qa_score(findings):
    scores={k:float(v) for k,v in COMPONENTS.items()}
    for issue in findings:
        key=issue['component'];sev=issue['severity']
        if sev=='P0':scores[key]=0
        else:scores[key]-=COMPONENTS[key]*DEDUCTIONS[sev]
    scores={k:max(0,round(v,1)) for k,v in scores.items()}
    total=round(sum(scores.values()))
    if any(f['severity']=='P0' for f in findings):total=min(59,total)
    return {'components':scores,'total':total}

def check_qa(d,s,qa):
    t=read_text(artifact(d,s,'script'))
    # Two independent editorial passes are attestations, not proof of having read every line.
    passes=qa.get('audit_passes',[])
    require(isinstance(passes,list) and len(passes)==2,'QA must declare READ_1 and READ_2 passes')
    for j,a in enumerate(passes,1):
        require(isinstance(a,dict) and a.get('type')==f'READ_{j}' and a.get('parts')==list(range(1,s['part_count']+1)) and bool(a.get('summary')),'Invalid QA double-read coverage statement')
    anchors=qa.get('part_anchors',[])
    require(isinstance(anchors,list) and len(anchors)==s['part_count'],'QA needs one exact evidence anchor per PART')
    pp=parse_script(t)
    for i,anchor in enumerate(anchors,1):
        require(isinstance(anchor,dict) and anchor.get('part')==i and isinstance(anchor.get('quote'),str) and len(anchor['quote'])>=10 and anchor['quote'] in pp[i-1]['text'],f'QA evidence anchor Part {i} is not in script')
    require(qa.get('continuity_sha256')==s['artifacts'].get('continuity',{}).get('sha256'),'QA continuity ledger SHA mismatch')
    require(qa.get('script_sha256')==s['script_sha256'],'QA script hash stale/mismatch')
    require(qa.get('title_sha256')==s['title_sha256'],'QA title hash mismatch')
    require(qa.get('outline_sha256')==s['artifacts']['outline']['sha256'],'QA outline hash mismatch')
    findings=qa.get('findings',[]);require(isinstance(findings,list),'findings must be list')
    ids=set()
    for issue in findings:
        require(isinstance(issue,dict),'issue must be object')
        issue_id=issue.get('id');require(isinstance(issue_id,str) and bool(issue_id.strip()) and issue_id not in ids,'Issue ID missing/duplicated')
        ids.add(issue_id)
        require(issue.get('component') in COMPONENTS and issue.get('severity') in DEDUCTIONS,f'Invalid issue {issue_id} rubric')
        require(issue.get('status','ACTIONABLE') in ('ACTIONABLE','PREFERENCE'),'Invalid issue status')
        require(issue.get('status','ACTIONABLE')!='PREFERENCE','Preferences belong in separate notes, not scored findings')
        quote=issue.get('quote','')
        require(isinstance(quote,str) and quote and quote in t,f'Issue {issue_id} requires exact quote present in current script')
        require(1<=int(issue.get('part',0))<=s['part_count'],f'Issue {issue_id} requires correct PART')
        pp=parse_script(t)[int(issue['part'])-1]
        require(quote in pp['text'],f'Issue {issue_id} quote is not in declared part')
    score=qa_score(findings)
    require(qa.get('score')==score['total'],'Reported QA score not equal deterministic calculation')
    m=metrics(t)
    if length_findings(m):require(any(i['component']=='F' for i in findings),'Length target failure not recorded as F issue')
    return score,m

def qa_stage(d,source):
    d,s=project(d);require(s['status']=='WAIT_QA','QA requires WAIT_QA')
    qa=read_json(source);score,m=check_qa(d,s,qa)
    ready=not qa['findings'] and not length_findings(m)
    qa['verified_at']=now();qa['controller_score']=score;qa['readiness']='READY' if ready else 'NEEDS_PATCH'
    store(d,s,'qa','qa.json',qa)
    s['status']='READY_FOR_SEO' if ready else 'WAIT_REPAIR'
    s['history'].append({'at':now(),'event':'QA_VERIFIED','score':score['total'],'ready':ready});persist(d,s)
    return {'state':s['status'],'qa_score':score['total'],'readiness':qa['readiness']}

def replace_one_in_part(t,part_no,old,new):
    parts=parse_script(t);p=parts[part_no-1]
    require(old and old in p['text'],f'Patch old span missing in PART {part_no}')
    require(p['text'].count(old)==1,'Patch old span must be unique inside PART')
    # Rebuild using original full text position of heading and text with unique partition.
    header_rx=re.compile(r'(?m)^PART\s+'+str(part_no)+r'\s*[\u2013\u2014-]\s*.+$')
    match=header_rx.search(t);require(match,'PART heading not found')
    body_start=t.find('\n',match.start());body_start=len(t) if body_start==-1 else body_start+1
    nextmatch=re.search(r'(?m)^PART\s+'+str(part_no+1)+r'\s*[\u2013\u2014-]\s*.+$',t[body_start:])
    body_end=len(t) if nextmatch is None else body_start+nextmatch.start()
    segment=t[body_start:body_end]
    require(segment.count(old)==1,'Patch replacement region not uniquely located')
    return t[:body_start]+segment.replace(old,new,1)+t[body_end:]

def repair_stage(d,source):
    d,s=project(d);require(s['status']=='WAIT_REPAIR','Repair only after QA actionable findings')
    require(s['repairs']<MAX_REPAIRS,f'Max {MAX_REPAIRS} repair cycles exceeded')
    qa=read_json(artifact(d,s,'qa'));require(qa['script_sha256']==s['script_sha256'],'QA stale')
    contract=read_json(source);require(contract.get('base_sha256')==s['script_sha256'],'Repair contract base SHA mismatch')
    patches=contract.get('patches',[]);require(isinstance(patches,list) and bool(patches),'Nonempty patches required')
    issues={x['id']:x for x in qa['findings']};t=read_text(artifact(d,s,'script'));before=metrics(t)
    used=set()
    for p in patches:
        id=p.get('issue_id');require(id in issues,'Unauthorized patch issue ID')
        require(id not in used,f'Duplicate patch ID {id}');used.add(id)
        pn=p.get('part');require(pn==issues[id]['part'],'Patch PART must match QA issue')
        old=p.get('old','');new=p.get('new','');require(isinstance(new,str) and new.strip(),'Patch replacement must be nonempty text')
        require(isinstance(old,str) and issues[id]['quote'] in old,'Patch original must include exact issue quote')
        t=replace_one_in_part(t,pn,old,new)
    after=metrics(t);require(after['parts']==before['parts'],'PART count changed')
    require(after['visible_characters']<=55000 and after['spoken_words']<8000,'Repair violates hard length bounds')
    if not contract.get('authorized_net_change',False):
        relative=abs(after['visible_characters']-before['visible_characters'])/max(1,before['visible_characters'])
        require(relative<=0.01,'Unapproved >1% length drift from current baseline')
    # All edits are programmatically constructed from exact approved old/new substrings.
    store(d,s,'script','script.txt',t);s['script_sha256']=t_sha(t)
    # Retain immutable OPB. Any QA/SEO from old version is explicitly invalidated.
    s['artifacts'].pop('qa',None);s['artifacts'].pop('seo',None);s['artifacts'].pop('continuity',None)
    s['repairs']+=1;s['status']='WAIT_CONTINUITY'
    s['history'].append({'at':now(),'event':'CONTROLLED_REPAIR','issue_ids':sorted(used),'old_sha256':contract['base_sha256'],'new_sha256':s['script_sha256'],'metrics':after})
    persist(d,s)
    return {'state':s['status'],'repair_cycle':s['repairs'],'metrics':after,'sha256':s['script_sha256'],'note':'Mandatory fresh continuity checkpoint + audit after repair'}

def render_seo(x):
    title=x['primary_title'];supp=x['supporting_titles'];hyp=x['thumbnail_hypotheses']
    sections=[]
    sections.append('# 1. TITLE SET — LOCKED TITLE + 2 NEW TITLES\n\n'+f'**LOCKED / PRIMARY TITLE:** {title}\n\n**NEW TITLE 1:** {supp[0]}\n\n**NEW TITLE 2:** {supp[1]}')
    sections.append('# 2. SEO DESCRIPTION\n\n'+x['description'])
    sections.append('# 3. SEO TAGS\n\n'+', '.join(x['tags']))
    sections.append('# 4. HASHTAGS\n\n'+' '.join(x['hashtags']))
    h=[]
    for i,item in enumerate(hyp,1):
        h.append(f"### H{i}\nClick hypothesis: {item['click_hypothesis']}\nScene: {item['scene']}\nViewer question: {item['viewer_question']}\nScore: {item['score']}/100")
    sections.append('# 5. THUMBNAIL HYPOTHESES\n\n'+'\n\n'.join(h))
    t=x['thumbnail_final'];sections.append('# 6. FINAL THUMBNAIL CONCEPT\n\n'+'\n'.join(f'{k}: {v}' for k,v in t.items()))
    sections.append('# 7. FINAL CHATGPT IMAGE PROMPT\n\n'+x['image_prompt'])
    hook=x['hook_8s'];sections.append('# 8. 8-SECOND VIDEO HOOK STRATEGY\n\n'+'\n'.join(f'{k}: {v}' for k,v in hook.items()))
    sections.append('# 9. FINAL 8-SECOND VIDEO GENERATION PROMPT\n\n'+x['video_prompt'])
    sections.append('# 10. LOCKED TITLE × THUMBNAIL × HOOK CHECK\n\n'+'\n'.join(f'{k}: {v}' for k,v in x['complement_check'].items()))
    sections.append('# 11. FINAL QA\n\n'+'\n'.join(f'{k}: {v}' for k,v in x['qa_summary'].items()))
    sections.append('# 12. FINAL CHANNEL RECOMMENDATION\n\n'+x['channel_recommendation'])
    return '\n\n'.join(sections)+'\n'

def seo_stage(d,source):
    d,s=project(d);require(s['status']=='READY_FOR_SEO','SEO publish gate requires READY_FOR_SEO')
    artifact(d,s,'script');qf=artifact(d,s,'qa');qa=read_json(qf)
    require(qa['readiness']=='READY' and qa['script_sha256']==s['script_sha256'],'Current QA is not READY for current script')
    x=read_json(source)
    require(x.get('primary_title')==s['locked_title'],'SEO must not rewrite primary title')
    supp=x.get('supporting_titles',[]);require(isinstance(supp,list) and len(supp)==2,'Exactly two supporting titles required')
    require(all(isinstance(v,str) and 1<=len(nfc(v))<=100 for v in supp),'Supporting title >100 or empty')
    require(len({norm(s['locked_title']),*(norm(t) for t in supp)})==3,'Titles must be distinct')
    require(x.get('script_sha256')==s['script_sha256'],'SEO script SHA mismatch')
    require(x.get('qa_sha256')==sha(qf.read_bytes()),'SEO QA proof SHA mismatch')
    require(bool(x.get('description')),'SEO description required')
    require(12<=len(x.get('tags',[]))<=20,'SEO tags must have 12-20')
    require(3<=len(x.get('hashtags',[]))<=5,'SEO hashtags must have 3-5')
    hyps=x.get('thumbnail_hypotheses',[]);require(len(hyps)==3,'Exactly three thumbnail hypotheses')
    for h in hyps:
        require(isinstance(h,dict) and all(h.get(k) for k in ('click_hypothesis','scene','viewer_question')) and isinstance(h.get('score'),(int,float)) and 0<=h['score']<=100,'Thumbnail hypothesis must include click/scene/question/0-100 score')
    require(bool(x.get('thumbnail_final')),'Final thumbnail concept missing')
    require('16:9' in x.get('image_prompt',''),'Image prompt must explicitly specify 16:9')
    hook=x.get('hook_8s',{});require(isinstance(hook,dict),'8-second hook must be object')
    for k in ['0-2s','2-5s','5-7s','7-8s']:
        require(bool(hook.get(k)),f'Missing 8s hook time block {k}')
    require(bool(x.get('video_prompt')),'8-second video prompt missing')
    require(x.get('visual_evidence',[]),'visual_evidence required; do not invent pictured objects')
    require(x.get('script_accuracy_confirmed') is True,'Visual fact check must be explicitly confirmed by reviewer')
    require(isinstance(x.get('complement_check'),dict) and x['complement_check'] and isinstance(x.get('qa_summary'),dict) and x['qa_summary'] and bool(x.get('channel_recommendation')),'Missing final packaging cross-check, QA or recommendation')
    store(d,s,'seo','seo.json',x)
    store(d,s,'seo_markdown','seo_master.md',render_seo(x));s['status']='PACKAGED';s['history'].append({'at':now(),'event':'SEO_PACKAGED'});persist(d,s)
    return {'state':s['status'],'primary_title_unchanged':True,'supporting_titles':2,'thumbnail_hypotheses':3,'note':'Media prompts only: no image/video rendered by this controller'}

def verify(d):
    d,s=project(d)
    for k in s['artifacts']: artifact(d,s,k)
    report={'project_id':s['project_id'],'status':s['status'],'title_sha256':s.get('title_sha256'),'script_sha256':s.get('script_sha256'),'artifacts_verified':sorted(s['artifacts']),'repair_cycles':s['repairs']}
    if s.get('script_sha256'):
        require(t_sha(read_text(artifact(d,s,'script')))==s['script_sha256'],'Logical script SHA mismatch')
        report['script_metrics']=metrics(read_text(artifact(d,s,'script')))
    if s['status'] in ('READY_FOR_SEO','PACKAGED'):
        qa=read_json(artifact(d,s,'qa'));require(qa.get('readiness')=='READY' and qa.get('script_sha256')==s['script_sha256'],'Final QA stale')
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description='Mafia Maid V2 verified local pipeline');sub=p.add_subparsers(dest='command',required=True)
    for cmd in ['init','title','outline','script','continuity','qa','repair','seo','verify','status']:
        sp=sub.add_parser(cmd);sp.add_argument('--project',required=True)
        if cmd=='init':sp.add_argument('--id',required=True)
        elif cmd in ('title','outline','script','continuity','qa','repair','seo'):sp.add_argument('--input',required=True)
        if cmd=='title':sp.add_argument('--memory')
    a=p.parse_args(argv)
    try:
        if a.command=='init':res=init(a.project,a.id)
        elif a.command=='title':res=title_stage(a.project,a.input,a.memory)
        elif a.command=='outline':res=outline_stage(a.project,a.input)
        elif a.command=='script':res=script_stage(a.project,a.input)
        elif a.command=='continuity':res=continuity_stage(a.project,a.input)
        elif a.command=='qa':res=qa_stage(a.project,a.input)
        elif a.command=='repair':res=repair_stage(a.project,a.input)
        elif a.command=='seo':res=seo_stage(a.project,a.input)
        elif a.command=='verify':res=verify(a.project)
        else:res=project(a.project)[1]
        print(json.dumps({'ok':True,'result':res},ensure_ascii=False,indent=2));return 0
    except (GateError,ValueError,KeyError,TypeError,UnicodeError,OSError) as ex:
        print(json.dumps({'ok':False,'error':str(ex)},ensure_ascii=False,indent=2),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
