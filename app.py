import json
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st

from database import init, save, all_jobs
from engine import analyze
from export import excel
from discovery import discover, PUBLIC_WEB_SOURCES, COMPANY_TARGETS
from resume_parser import parse_resume

init()
profile = json.loads((Path('data') / 'candidate_profile.json').read_text(encoding='utf-8'))

st.set_page_config(page_title='AI Job Agent', page_icon='🤖', layout='wide')

st.markdown("""
<style>
.block-container{padding-top:2rem;max-width:1400px}
.hero{padding:28px;border-radius:22px;background:linear-gradient(135deg,#111827,#312e81 50%,#0f766e);color:white;margin-bottom:18px}
.hero h1{font-size:42px;margin:0}.hero p{font-size:17px;opacity:.9}
.card{padding:18px;border:1px solid rgba(128,128,128,.22);border-radius:16px;background:rgba(128,128,128,.06)}
</style>
<div class="hero"><h1>🤖 AI Job Agent</h1><p>Live job discovery • Today’s openings • Worldwide remote coverage • Evidence-first matching • Application tracking</p></div>
""", unsafe_allow_html=True)

pages = ['🌐 Discover Jobs', '🔍 Analyze Job', '📋 Application Queue', '👤 Profile', '📊 Export']
page = st.sidebar.radio('Navigate', pages)

candidate_text = json.dumps(profile, ensure_ascii=False)

# Resume is session-only by design; profile JSON is the fallback evidence source.
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ''
with st.sidebar:
    st.markdown('### 📄 Candidate Evidence')
    resume_file = st.file_uploader('Upload master CV (PDF/DOCX/TXT)', type=['pdf','docx','txt'], help='Processed in this Streamlit session. The app does not upload the CV to a third-party AI service.')
    if resume_file is not None:
        try:
            st.session_state.resume_text = parse_resume(resume_file)
            if not st.session_state.resume_text.strip():
                st.warning('The file was read but no text could be extracted. A scanned/image-only PDF needs OCR.')
        except ValueError as exc:
            st.error(str(exc))
    if st.session_state.resume_text.strip():
        candidate_text = st.session_state.resume_text
        st.success(f'CV loaded: {len(candidate_text.split()):,} words')
    else:
        st.info('No CV uploaded. Discovery will match against the structured candidate profile, not your full resume.')

if page == '🌐 Discover Jobs':
    st.subheader('🌐 Live Worldwide Job Discovery')
    st.caption('Free-first discovery: public feeds + employer ATS APIs + portal web discovery. A job only qualifies for Today/24h when a real timestamp is available.')

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        role_options = profile.get('target_roles', [])
        selected = st.multiselect('Target roles', role_options, default=role_options[:4])
        custom = st.text_input('Additional search term', placeholder='e.g. SQL Data Analyst, Product Analytics')
    with c2:
        freshness_label = st.selectbox('Freshness', ['Posted today (UTC)', 'Last 24 hours'])
        freshness = 'today' if freshness_label.startswith('Posted') else '24h'
    with c3:
        max_per_source = st.number_input('Max/source/query', min_value=10, max_value=200, value=50, step=10)

    direct_sources = [
        'Jobicy', 'Remotive', 'RemoteOK', 'Arbeitnow', 'Himalayas',
        'Remote Landers — Employer ATS', 'RemoteJobs.org', 'Nomado24', 'Startup Jobs RSS'
    ]
    web_sources = list(PUBLIC_WEB_SOURCES.keys())
    company_targets = list(COMPANY_TARGETS.keys())
    has_serper = bool(__import__('os').getenv('SERPER_API_KEY'))
    st.markdown('### 🔌 Source status')
    st.caption('The app now distinguishes real direct feeds from web-index discovery. It will not label a source as live when its required search integration is missing.')
    st.write('**Free live feeds / ATS-derived feeds:** ' + ', '.join(direct_sources))
    if has_serper:
        st.success('🟢 Google-index discovery enabled via Serper. The same source registry is searched with higher result coverage.')
    else:
        st.info('🟢 No Serper key is required for the direct feeds or company ATS adapters. Portal-wide web discovery uses a best-effort public search fallback; add SERPER_API_KEY for higher web-index coverage.')
    selected_direct = st.multiselect('Direct live sources', direct_sources, default=direct_sources)
    selected_web = st.multiselect('All portal sources from your source list', web_sources, default=web_sources)
    company_option = 'Named company career pages from your source list'
    company_search = st.checkbox(company_option, value=True)
    sources = selected_direct + selected_web + ([company_option] if company_search else [])
    st.caption('🏢 Employer ATS layer: Greenhouse • Lever • Ashby • SmartRecruiters • Workable • Recruitee • Breezy • BambooHR • Personio • Teamtailor • Rippling. Public boards are queried directly when their company slug is discoverable.')
    st.caption(f'📚 Source registry: {len(web_sources)} portals/platforms + {len(company_targets)} named company career targets from your uploaded list.')
    x1,x2,x3=st.columns(3)
    x1.metric('Portal registry', len(web_sources))
    x2.metric('Company watchlist', len(company_targets))
    x3.metric('Free direct feeds', len(direct_sources))
    regions = st.multiselect('Target hiring regions', ['Worldwide', 'United States', 'Canada', 'UK', 'Europe', 'Australia', 'Singapore', 'UAE', 'India', 'Asia-Pacific'],
                             default=['Worldwide', 'United States', 'UK', 'Europe', 'Australia', 'Singapore', 'UAE'])
    if company_search:
        st.info('🏢 Additional company ATS discovery: Greenhouse • Lever • Ashby • SmartRecruiters via indexed public company-board discovery.')

    if 'last_discovery' not in st.session_state:
        st.session_state.last_discovery = None

    if st.button('🔄 Search the Internet for Fresh Jobs', type='primary', width='stretch'):
        queries = selected + ([custom] if custom.strip() else [])
        if not queries:
            st.error('Select at least one target role or enter a search term.')
        elif not sources:
            st.error('Select at least one source.')
        else:
            with st.spinner('Searching live job sources, filtering freshness, deduplicating, and scoring matches…'):
                jobs, errors = discover(queries, freshness=freshness, sources=sources, limit_per_source=int(max_per_source), company_search=company_search, regions=regions)
                saved = 0
                for j in jobs:
                    r = analyze(candidate_text, j.get('description','') or j.get('title',''))
                    j.update({'score': r['overall'], 'ats': r['ats'], 'matched': r['matched'], 'missing': r['missing'], 'verification': 'Source listing — verify official application page', 'status': 'Discovered'})
                    save(j); saved += 1
                st.session_state.last_discovery = {'jobs': jobs, 'errors': errors, 'queries': queries, 'when': datetime.now(timezone.utc).isoformat()}
            st.success(f'Found and tracked {saved} fresh matching jobs.')
            if not st.session_state.resume_text.strip():
                st.warning('⚠️ These scores use the candidate profile fallback. Upload your actual CV for a meaningful resume-to-JD match.')
            if errors:
                st.warning(f'{len(errors)} source/query calls failed. Failed sources are shown below.')

    if st.session_state.last_discovery:
        result = st.session_state.last_discovery
        jobs = result['jobs']
        st.caption(f"Last search: {result['when']} • Queries: {', '.join(result['queries'])}")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric('Fresh jobs found', len(jobs))
        m2.metric('Sources used', len(sources))
        m3.metric('High match ≥75', sum(j.get('score',0) >= 75 for j in jobs))
        m4.metric('Tracked in SQLite', len(all_jobs()))

        if jobs:
            min_score = st.slider('Minimum match score', 0, 100, 50)
            view = [j for j in jobs if j.get('score',0) >= min_score]
            for j in view[:100]:
                with st.container(border=True):
                    a,b,c = st.columns([5,1,1])
                    with a:
                        st.markdown(f"### {j['title']}")
                        st.write(f"**{j['company']}** · {j.get('location','Not disclosed')} · **{j.get('source','Unknown')}**")
                        st.caption(f"Posted: {j.get('posted_at','Unknown')} · Work mode: {j.get('work_mode','Unclear')} · Salary: {j.get('salary','Not disclosed')}")
                    with b: st.metric('Match', f"{j.get('score',0)}/100")
                    with c: st.metric('ATS', f"{j.get('ats',0)}/100")
                    st.write((j.get('description') or '')[:500] + ('…' if len(j.get('description') or '') > 500 else ''))
                    st.link_button('🔗 Open listing / apply', j['url'])
        else:
            st.info('No jobs matched the freshness + role filters. Try Last 24 hours, broaden the role, or enable more sources.')

        if result['errors']:
            with st.expander('Source errors / rate limits'):
                for e in result['errors'][:30]: st.code(e)

    st.info('Coverage note: no public application can guarantee every job on the internet. Direct ATS feeds are the highest-confidence company source; portal web results are discovery signals. LinkedIn/Naukri/Indeed/etc. are not represented as unrestricted APIs.')

elif page == '🔍 Analyze Job':
    st.subheader('🔍 Analyze a Specific Job')
    cv=st.text_area('Paste CV text',height=200,placeholder='Use your master CV text. It stays in this browser session.')
    company=st.text_input('Company'); title=st.text_input('Job title'); url=st.text_input('Official application URL'); salary=st.text_input('Salary, if disclosed'); jd=st.text_area('Paste job description',height=240)
    if st.button('Analyze and add to queue', type='primary'):
        if not cv or not jd: st.error('CV and job description are required.')
        else:
            r=analyze(cv,jd); job={'company':company,'title':title,'url':url,'application_url':url,'salary':salary or 'Not disclosed','work_mode':r['remote_status'],'verification':'Needs Review','score':r['overall'],'ats':r['ats'],'description':jd,'status':'Prepared','source':'Manual','matched':r['matched'],'missing':r['missing'],'location':'Not disclosed','posted_at':'','source_job_id':''}; save(job)
            st.metric('Overall Match',f"{r['overall']}/100"); st.metric('ATS Estimate',f"{r['ats']}/100"); st.write('Tier:',r['tier']); st.write('Matched:',r['matched']); st.write('Missing:',r['missing']); st.warning(r['disclaimer'])

elif page == '📋 Application Queue':
    st.subheader('📋 Tracked Jobs')
    rows=all_jobs()
    if rows:
        st.dataframe(rows,width='stretch',hide_index=True)
    else: st.info('No tracked jobs yet. Use Discover Jobs first.')

elif page == '👤 Profile':
    st.subheader('👤 Candidate Profile')
    st.json(profile)

else:
    st.subheader('📊 Export Application Tracker')
    rows=all_jobs(); p=Path('output/job_application_tracker.xlsx'); p.parent.mkdir(exist_ok=True); excel(rows,p)
    st.download_button('⬇️ Download Excel tracker',p.read_bytes(),'job_application_tracker.xlsx',width='stretch')
