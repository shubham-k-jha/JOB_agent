from engine import analyze
def test_matching():
 r=analyze('Python SQL Power BI statistics. Presented reports.','Remote worldwide Data Analyst needs Python SQL Power BI and communication.')
 assert r['overall']>0 and 'Python' in r['matched']
def test_remote():assert analyze('Python','Remote US only role')['remote_status'].startswith('Remote restricted')
