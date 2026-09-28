import re,json
from pathlib import Path
T=json.loads((Path(__file__).parent/'data'/'skill_taxonomy.json').read_text())
def skills(text):
 out=[]
 for parent,children in T.items():
  for x in [parent]+children:
   if re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',text,re.I):out.append(x)
 return sorted(set(out))
def remote_status(text):
 low=text.lower()
 if 'remote' not in low:return 'On-site or unclear'
 if any(x in low for x in ['worldwide','anywhere','global remote']):return 'Remote worldwide'
 if any(x in low for x in ['india only','remote india','within india']):return 'Remote India'
 if any(x in low for x in ['us only','united states only','uk only','europe only','eu only']):return 'Remote restricted — review eligibility'
 return 'Remote — location restriction unclear'
def analyze(cv,jd):
 cs=set(skills(cv)); js=set(skills(jd)); matched=sorted(cs&js); missing=sorted(js-cs); req_score=round(100*len(matched)/max(1,len(js))); sem=round(100*len(set(re.findall(r'\w{5,}',cv.lower()))&set(re.findall(r'\w{5,}',jd.lower())))/max(1,len(set(re.findall(r'\w{5,}',jd.lower())))))
 comm_req=bool(re.search(r'communication|present|stakeholder|client',jd,re.I)); comm_ev=len(re.findall(r'present|communicat|report|stakeholder|collaborat',cv,re.I)); comm=min(100,45+10*comm_ev) if comm_req else 100
 ats=round(.7*req_score+.2*sem+.1*comm); overall=round(.55*req_score+.2*sem+.15*comm+.1*ats)
 tier='A' if overall>=75 and not missing else ('B' if overall>=60 else 'C')
 return {'overall':overall,'ats':ats,'matched':matched,'missing':missing,'required_skills_score':req_score,'semantic_score':sem,'communication_score':comm,'remote_status':remote_status(jd),'tier':tier,'disclaimer':'Scores are application-generated estimates, not interview guarantees. Missing skills must not be added without genuine evidence.'}
