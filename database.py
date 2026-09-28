import sqlite3, hashlib
from config import settings

def init():
    c=sqlite3.connect(settings.db_path)
    c.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, company TEXT, title TEXT, url TEXT, application_url TEXT, work_mode TEXT, salary TEXT, verification TEXT, score REAL, ats REAL, status TEXT, description TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, job_id TEXT, action TEXT, result TEXT)")
    # Migrate old databases without breaking existing installs.
    existing={r[1] for r in c.execute("PRAGMA table_info(jobs)")}
    for col, typ in [("source","TEXT"),("location","TEXT"),("posted_at","TEXT"),("source_job_id","TEXT"),("matched","TEXT"),("missing","TEXT")]:
        if col not in existing: c.execute(f"ALTER TABLE jobs ADD COLUMN {col} {typ}")
    c.commit(); c.close()

def save(job):
    job=dict(job); job['id']=hashlib.sha256((job.get('company','')+job.get('title','')+job.get('application_url','')).lower().encode()).hexdigest()[:16]
    c=sqlite3.connect(settings.db_path)
    cols=['id','company','title','url','application_url','work_mode','salary','verification','score','ats','status','description','source','location','posted_at','source_job_id','matched','missing']
    vals=[(', '.join(job.get(k,[]) if isinstance(job.get(k),list) else [])) if k in ('matched','missing') else job.get(k,'') for k in cols]
    vals[9]=job.get('ats',0); vals[10]=job.get('status','Discovered')
    placeholders=','.join('?' for _ in cols)
    updates=','.join(f"{k}=excluded.{k}" for k in cols[1:] if k not in ('id',))
    c.execute(f"INSERT INTO jobs ({','.join(cols)}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}", vals)
    c.execute("INSERT INTO audit_log(job_id,action,result) VALUES(?,?,?)",(job['id'],'Job discovered',f"{job.get('source','Unknown')} | {job.get('title','') }"))
    c.commit(); c.close(); return job['id']

def all_jobs(limit=None):
    c=sqlite3.connect(settings.db_path); c.row_factory=sqlite3.Row
    q='SELECT * FROM jobs ORDER BY COALESCE(posted_at,created_at) DESC'
    if limit: q += f' LIMIT {int(limit)}'
    rows=[dict(x) for x in c.execute(q)]; c.close(); return rows
