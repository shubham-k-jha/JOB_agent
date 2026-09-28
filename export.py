from openpyxl import Workbook

def excel(rows,path):
    wb=Workbook(); ws=wb.active; ws.title='Applications'
    headers=['Job ID','Date Found','Posted At','Source','Company','Job Title','Location','Remote/Hybrid/On-site','Salary','Job Match Score','ATS Compatibility','Missing Critical Skills','Matched Skills','Job URL','Application URL','Verification','Application Status','Notes']
    ws.append(headers)
    for r in rows:
        ws.append([r.get('id',''),r.get('created_at',''),r.get('posted_at',''),r.get('source',''),r.get('company',''),r.get('title',''),r.get('location',''),r.get('work_mode',''),r.get('salary',''),r.get('score',0),r.get('ats',0),', '.join(r.get('missing',[]) if isinstance(r.get('missing'),list) else []),', '.join(r.get('matched',[]) if isinstance(r.get('matched'),list) else []),r.get('url',''),r.get('application_url',''),r.get('verification',''),r.get('status',''),r.get('notes','')])
    dash=wb.create_sheet('Dashboard'); dash.append(['Metric','Value']); dash.append(['Total Jobs Tracked',len(rows)]); dash.append(['Shortlisted (Match ≥75)',sum((r.get('score') or 0)>=75 for r in rows)]); dash.append(['Prepared',sum(r.get('status')=='Prepared' for r in rows)]); dash.append(['Discovered',sum(r.get('status')=='Discovered' for r in rows)])
    for sh in wb.worksheets:
        sh.freeze_panes='A2'; sh.auto_filter.ref=sh.dimensions
        for cell in sh[1]: cell.font=cell.font.copy(bold=True)
    wb.save(path)
