"""Synthetic gate tests; not a literary quality certification."""
import importlib.util,json, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('maid_pipeline',ROOT/'controller'/'maid_pipeline.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def put(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(obj,str):p.write_text(obj,encoding='utf-8')
    else:p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    return p

def good_title():
    title='The Maid Found One Receipt—Then the Mafia Boss Changed His Mind'
    return {'selected_title':title,'candidates':[{'title':title if i==0 else f'Maid Evidence Story — Version {i}','score':90+i} for i in range(5)],'fingerprint':{'heroine_role':'maid','trigger_event':'hidden receipt','power_dynamic':'boss trusts underestimated maid','hidden_competence':'forensic accounting','evidence_mechanism':'inventory receipt','core_reversal':'the boss was misled','payoff':'she exposes corrupt lieutenant'}}

def good_outline(t):
    return {'title':t,'primary_dna':'C','content_family':'Competence Reveal','story_core':{'premise':'An overlooked maid notices evidence','central_conflict':'Corrupt lieutenant controls access','heroine_agency':'She verifies the inventory and reports discrepancies','core_reversal':'The boss checks the ledger instead of blaming her','major_payoff':'She exposes the lie on her own terms'},'beats':[{'number':i,'name':f'Beat {i}','cause':'Prior action creates new pressure','action':'Heroine checks one new fact','consequence':'A contradiction drives the next beat','heroine_contribution':'Heroine independently verifies evidence','transition':'Cause of the next beat is established'} for i in range(1,6)],'open_loops':[{'id':'L01','opened_at':1,'closed_at':5,'payoff':'Receipt checked against authenticated stock records'}], 'evidence_chain':[{'id':'E01','setup':'The receipt appears','payoff':'The receipt matches records'}]}

def good_script():
    parts=[]
    for i in range(1,6):
        words=['siren','glass','trace','stare','shift']*300
        if i==2:words[0:3]=['unique','evidence','anomaly']
        parts.append(f'PART {i} — Beat {i}\n'+ ' '.join(words) + '\n')
    return '\n'.join(parts)

def continuity_doc(d,state):
    return {'script_sha256':state['script_sha256'],'part_handoffs':[{'part':i,'entry_bridge':'START' if i==1 else f'E{i-1}','exit_bridge':f'E{i}' if i<5 else 'END','location_end':f'Place {i}','timeline_end':f'Day {i}','heroine_action':f'The heroine verifies clue {i}','relationship_state':'careful trust','character_knowledge':{'heroine':['receipt evidence']},'open_loops':['L01'] if i<5 else []} for i in range(1,6)]}

class Gates(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.proj=self.root/'project'
        m.init(self.proj,'test_001')
    def prepare_title(self):
        t=good_title();m.title_stage(self.proj,put(self.root/'title.json',t));return t
    def prepare_outline(self):
        t=self.prepare_title();m.outline_stage(self.proj,put(self.root/'outline.json',good_outline(t['selected_title'])));return t
    def prepare_script(self):
        self.prepare_outline();s=good_script();m.script_stage(self.proj,put(self.root/'script.txt',s));d,state=m.project(self.proj);m.continuity_stage(d,put(self.root/'continuity.json',continuity_doc(d,state)));return s
    def qa_doc(self,findings=None):
        d,s=m.project(self.proj)
        q={'script_sha256':s['script_sha256'],'title_sha256':s['title_sha256'],'outline_sha256':s['artifacts']['outline']['sha256'],'continuity_sha256':s['artifacts']['continuity']['sha256'],'audit_passes':[{'type':f'READ_{i}','parts':[1,2,3,4,5],'summary':'Read each Part for logic and causal closure'} for i in [1,2]],'part_anchors':[{'part':i,'quote':'siren glass trace stare shift' if i!=2 else 'unique evidence anomaly'} for i in range(1,6)],'findings':findings or []}
        q['score']=m.qa_score(q['findings'])['total']
        return q
    def test_01_init_reuse_rejected(self):
        with self.assertRaises(m.GateError):m.init(self.proj,'duplicate')
    def test_02_title_five_candidates_required(self):
        x=good_title();x['candidates'].pop()
        with self.assertRaises(m.GateError):m.title_stage(self.proj,put(self.root/'t.json',x))
    def test_03_title_max100(self):
        x=good_title();x['selected_title']='A'*101;x['candidates'][0]['title']=x['selected_title']
        with self.assertRaises(m.GateError):m.title_stage(self.proj,put(self.root/'t.json',x))
    def test_04_title_fingerprint_fields(self):
        x=good_title();x['fingerprint']={}
        with self.assertRaises(m.GateError):m.title_stage(self.proj,put(self.root/'t.json',x))
    def test_05_memory_duplicate(self):
        t=good_title();memory=self.root/'memory.json';m.title_stage(self.proj,put(self.root/'t.json',t),memory)
        p2=self.root/'other';m.init(p2,'test_002')
        with self.assertRaises(m.GateError):m.title_stage(p2,self.root/'t.json',memory)
    def test_06_title_immutable(self):
        self.prepare_title()
        with self.assertRaises(m.GateError):m.title_stage(self.proj,self.root/'title.json')
    def test_07_outline_wrong_title(self):
        t=self.prepare_title();x=good_outline('A changed title')
        with self.assertRaises(m.GateError):m.outline_stage(self.proj,put(self.root/'o.json',x))
    def test_08_outline_unclosed_loop(self):
        t=self.prepare_title();x=good_outline(t['selected_title']);x['open_loops'][0]['closed_at']=100
        with self.assertRaises(m.GateError):m.outline_stage(self.proj,put(self.root/'o.json',x))
    def test_09_outline_missing_heroine_action(self):
        t=self.prepare_title();x=good_outline(t['selected_title']);x['beats'][1]['heroine_contribution']=''
        with self.assertRaises(m.GateError):m.outline_stage(self.proj,put(self.root/'o.json',x))
    def test_10_beat_dynamic_count(self):
        self.prepare_outline();_,s=m.project(self.proj);self.assertEqual(s['part_count'],5)
    def test_11_script_metrics(self):
        self.prepare_outline();x=m.metrics(good_script())
        self.assertTrue(44000<=x['visible_characters']<=48000,x)
        self.assertTrue(7400<=x['spoken_words']<=7650,x)
    def test_12_script_wrong_part_count(self):
        self.prepare_outline();x=good_script().split('PART 5 —')[0]
        with self.assertRaises(m.GateError):m.script_stage(self.proj,put(self.root/'s.txt',x))
    def test_13_script_bracketed_cue(self):
        self.prepare_outline();x=good_script().replace('unique evidence anomaly','[beat] unique evidence anomaly')
        with self.assertRaises(m.GateError):m.script_stage(self.proj,put(self.root/'s.txt',x))
    def test_14_script_too_short(self):
        self.prepare_outline();x=good_script().replace('siren glass trace stare shift','siren')
        with self.assertRaises(m.GateError):m.script_stage(self.proj,put(self.root/'s.txt',x))
    def test_15_script_word_ceiling(self):
        self.prepare_outline();x=good_script().replace('siren glass trace stare shift','siren glass trace stare shift more')
        with self.assertRaises(m.GateError):m.script_stage(self.proj,put(self.root/'s.txt',x))
    def test_16_sha_tamper_rejected(self):
        self.prepare_script();d,s=m.project(self.proj)
        (d/'artifacts'/'script.txt').write_text('tampered',encoding='utf-8')
        with self.assertRaises(m.GateError):m.verify(d)
    def test_17_qa_score_mismatch(self):
        self.prepare_script();q=self.qa_doc();q['score']=90
        with self.assertRaises(m.GateError):m.qa_stage(self.proj,put(self.root/'q.json',q))
    def test_18_qa_stale_sha(self):
        self.prepare_script();q=self.qa_doc();q['script_sha256']='bad'
        with self.assertRaises(m.GateError):m.qa_stage(self.proj,put(self.root/'q.json',q))
    def test_19_qa_quote_not_found(self):
        self.prepare_script();f=[{'id':'P01','component':'B','severity':'P1','part':2,'quote':'nonexistent quote'}]
        with self.assertRaises(m.GateError):m.qa_stage(self.proj,put(self.root/'q.json',self.qa_doc(f)))
    def test_20_qa_needs_patch(self):
        self.prepare_script();f=[{'id':'P01','component':'B','severity':'P1','part':2,'quote':'unique evidence anomaly'}]
        out=m.qa_stage(self.proj,put(self.root/'q.json',self.qa_doc(f)))
        self.assertEqual(out['state'],'WAIT_REPAIR');self.assertEqual(out['qa_score'],94)
    def test_21_patch_unauthorized_issue(self):
        self.test_20_qa_needs_patch();_,s=m.project(self.proj)
        c={'base_sha256':s['script_sha256'],'patches':[{'issue_id':'P02','part':2,'old':'unique evidence anomaly','new':'unique verified anomaly'}]}
        with self.assertRaises(m.GateError):m.repair_stage(self.proj,put(self.root/'patch.json',c))
    def test_22_patch_wrong_part(self):
        self.test_20_qa_needs_patch();_,s=m.project(self.proj)
        c={'base_sha256':s['script_sha256'],'patches':[{'issue_id':'P01','part':1,'old':'unique evidence anomaly','new':'unique verified anomaly'}]}
        with self.assertRaises(m.GateError):m.repair_stage(self.proj,put(self.root/'patch.json',c))
    def test_23_patch_and_reaudit(self):
        self.test_20_qa_needs_patch();d,s=m.project(self.proj);before=m.read_text(m.artifact(d,s,'script'))
        c={'base_sha256':s['script_sha256'],'patches':[{'issue_id':'P01','part':2,'old':'unique evidence anomaly','new':'unique verified anomaly'}]}
        out=m.repair_stage(self.proj,put(self.root/'patch.json',c));self.assertEqual(out['state'],'WAIT_CONTINUITY')
        after=m.read_text(d/'artifacts'/'script.txt')
        b=m.parse_script(before);a=m.parse_script(after)
        for i in (0,2,3,4):self.assertEqual(b[i]['text'],a[i]['text'])
        self.assertEqual(s['opb_sha256'],m.project(d)[1]['opb_sha256'])
        ds=m.project(d)[1];m.continuity_stage(d,put(self.root/'cont2.json',continuity_doc(d,ds)))
        with self.assertRaises(m.GateError):m.seo_stage(self.proj,put(self.root/'seo.json',{}))
        q=self.qa_doc();q['part_anchors'][1]['quote']='unique verified anomaly'
        out=m.qa_stage(self.proj,put(self.root/'q2.json',q))
        self.assertEqual(out['state'],'READY_FOR_SEO')
    def test_24_stale_audit_after_repair(self):
        self.test_20_qa_needs_patch();d,s=m.project(self.proj);old=self.qa_doc([{'id':'P01','component':'B','severity':'P1','part':2,'quote':'unique evidence anomaly'}])
        c={'base_sha256':s['script_sha256'],'patches':[{'issue_id':'P01','part':2,'old':'unique evidence anomaly','new':'unique verified anomaly'}]}
        m.repair_stage(d,put(self.root/'patch.json',c))
        ds=m.project(d)[1];m.continuity_stage(d,put(self.root/'cont_stale.json',continuity_doc(d,ds)))
        with self.assertRaises(m.GateError):m.qa_stage(d,put(self.root/'qold.json',old))
    def test_25_qa_ready(self):
        self.prepare_script();o=m.qa_stage(self.proj,put(self.root/'q.json',self.qa_doc()))
        self.assertEqual(o['readiness'],'READY');self.assertEqual(o['qa_score'],100)
    def make_seo(self):
        d,s=m.project(self.proj);q=m.artifact(d,s,'qa');return {'primary_title':s['locked_title'],'supporting_titles':['Maid Notices a Receipt That Changes Everything','One Hidden Receipt Exposes a Dangerous Lie'],'script_sha256':s['script_sha256'],'qa_sha256':m.sha(q.read_bytes()),'description':'Story of a maid','tags':[f'maid story {i}' for i in range(12)],'hashtags':['#maid','#mafiaromance','#story'],'thumbnail_hypotheses':[{'scene':str(i),'click_hypothesis':'Evidence versus power','viewer_question':'What was discovered?','score':89} for i in range(3)],'thumbnail_final':{'scene':'maid with receipt'},'image_prompt':'Cinematic 16:9 photograph of a maid holding a paper','hook_8s':{'0-2s':'looks at paper','2-5s':'steps aside','5-7s':'reacts','7-8s':'cut'},'video_prompt':'An 8-second cinematic hook','visual_evidence':[{'source':'PART 2','fact':'receipt'}],'script_accuracy_confirmed':True,'complement_check':{'Locked Title altered?':'NO','Result':'PASS'},'qa_summary':{'Package Cohesion':'PASS','Evidence':'PASS'},'channel_recommendation':'SHIP — evidence-based packaging'}
    def test_26_seo_before_qa_blocked(self):
        self.prepare_script()
        with self.assertRaises(m.GateError):m.seo_stage(self.proj,put(self.root/'seo.json',{}))
    def test_27_seo_wrong_title(self):
        self.test_25_qa_ready();x=self.make_seo();x['primary_title']='changed'
        with self.assertRaises(m.GateError):m.seo_stage(self.proj,put(self.root/'seo.json',x))
    def test_28_seo_three_titles_total(self):
        self.test_25_qa_ready();x=self.make_seo();x['supporting_titles']=['one']
        with self.assertRaises(m.GateError):m.seo_stage(self.proj,put(self.root/'seo.json',x))
    def test_29_seo_hook_blocks(self):
        self.test_25_qa_ready();x=self.make_seo();x['hook_8s'].pop('7-8s')
        with self.assertRaises(m.GateError):m.seo_stage(self.proj,put(self.root/'seo.json',x))
    def test_30_seo_valid_and_verify(self):
        self.test_25_qa_ready();x=self.make_seo();o=m.seo_stage(self.proj,put(self.root/'seo.json',x))
        self.assertEqual(o['state'],'PACKAGED');self.assertEqual(m.verify(self.proj)['status'],'PACKAGED')
    def test_31_casefold_dup_similarity(self):
        fp=m.fingerprint(good_title()['fingerprint']);self.assertEqual(m.similarity(fp,fp),1.0)
    def test_32_qa_P0_cap(self):
        x=m.qa_score([{'id':'P0','component':'B','severity':'P0'}]);self.assertEqual(x['total'],59)
    def test_33_exact_word_8000_fail(self):
        s=good_script();parts=m.parse_script(s);self.assertEqual(len(parts),5)
        # Add 500 words without altering the underlying 5 PART map.
        s+=' extra'*500
        self.assertTrue(any(x['severity']=='P0' for x in m.length_findings(m.metrics(s))))
    def test_34_fourth_or_further_qa_after_max_repairs(self):
        self.prepare_script()
        for cycle in range(2):
            d,state=m.project(self.proj);script=m.read_text(m.artifact(d,state,'script'))
            phrase='unique evidence anomaly' if cycle==0 else 'unique verified anomaly'
            q=self.qa_doc([{'id':'P01','component':'B','severity':'P1','part':2,'quote':phrase}]);q['part_anchors'][1]['quote']=phrase;m.qa_stage(d,put(self.root/f'qa{cycle}.json',q))
            next_phrase='unique verified anomaly' if cycle==0 else 'unique stable anomaly'
            c={'base_sha256':state['script_sha256'],'patches':[{'issue_id':'P01','part':2,'old':phrase,'new':next_phrase}]}
            m.repair_stage(d,put(self.root/f'p{cycle}.json',c))
            ds=m.project(d)[1];m.continuity_stage(d,put(self.root/f'cont{cycle}.json',continuity_doc(d,ds)))
        d,state=m.project(self.proj);phrase='unique stable anomaly'
        q=self.qa_doc([{'id':'P01','component':'B','severity':'P1','part':2,'quote':phrase}]);q['part_anchors'][1]['quote']=phrase;m.qa_stage(d,put(self.root/'qlast.json',q))
        c={'base_sha256':state['script_sha256'],'patches':[{'issue_id':'P01','part':2,'old':phrase,'new':'unique last anomaly'}]}
        with self.assertRaises(m.GateError):m.repair_stage(d,put(self.root/'plast.json',c))
    def test_35_part_headings_count_nfc(self):
        x=m.metrics(good_script());self.assertGreater(x['part_visible_characters'][0],4400)
    def test_37_continuity_stale_sha(self):
        self.prepare_outline();m.script_stage(self.proj,put(self.root/'s.txt',good_script()))
        d,state=m.project(self.proj);c=continuity_doc(d,state);c['script_sha256']='wrong'
        with self.assertRaises(m.GateError):m.continuity_stage(d,put(self.root/'c.json',c))
    def test_38_continuity_broken_bridge(self):
        self.prepare_outline();m.script_stage(self.proj,put(self.root/'s.txt',good_script()))
        d,state=m.project(self.proj);c=continuity_doc(d,state);c['part_handoffs'][2]['entry_bridge']='MISPLACED'
        with self.assertRaises(m.GateError):m.continuity_stage(d,put(self.root/'c.json',c))
    def test_39_continuity_open_loop_not_closed(self):
        self.prepare_outline();m.script_stage(self.proj,put(self.root/'s.txt',good_script()))
        d,state=m.project(self.proj);c=continuity_doc(d,state);c['part_handoffs'][-1]['open_loops']=['L01']
        with self.assertRaises(m.GateError):m.continuity_stage(d,put(self.root/'c.json',c))
    def test_41_seo_render_exact_twelve_sections(self):
        self.test_25_qa_ready();x=self.make_seo();m.seo_stage(self.proj,put(self.root/'seo12.json',x))
        d,state=m.project(self.proj);t=m.read_text(m.artifact(d,state,'seo_markdown'))
        self.assertEqual(len(__import__('re').findall(r'^# [0-9]+\. ',t,__import__('re').M)),12)
        self.assertIn('# 8. 8-SECOND VIDEO HOOK STRATEGY',t)
    def test_42_seo_image_16_9_gate(self):
        self.test_25_qa_ready();x=self.make_seo();x['image_prompt']='cinematic portrait'
        with self.assertRaises(m.GateError):m.seo_stage(self.proj,put(self.root/'seo_bad.json',x))
    def test_40_qa_missing_double_read_coverage(self):
        self.prepare_script();q=self.qa_doc();q['audit_passes'][0]['parts']=[1,2]
        with self.assertRaises(m.GateError):m.qa_stage(self.proj,put(self.root/'q.json',q))
    def test_36_metadata_contamination(self):
        self.prepare_outline();x=good_script().replace('unique evidence anomaly','CAMERA: Pan. unique evidence anomaly')
        with self.assertRaises(m.GateError):m.script_stage(self.proj,put(self.root/'s.txt',x))

if __name__=='__main__':unittest.main(verbosity=2)
