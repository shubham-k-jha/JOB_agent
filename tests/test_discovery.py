from discovery import dedupe, is_fresh
from datetime import datetime, timezone

def test_dedupe():
    jobs=[{'url':'https://x/a','title':'Data Analyst'},{'url':'https://x/a','title':'Data Analyst'}]
    assert len(dedupe(jobs))==1

def test_today_and_24h():
    now=datetime.now(timezone.utc)
    assert is_fresh({'posted_at':now.isoformat()},'today')
    assert is_fresh({'posted_at':now.isoformat()},'24h')

def test_public_web_sources_include_major_global_boards():
    from discovery import PUBLIC_WEB_SOURCES
    for name in ["LinkedIn", "Naukri", "Indeed", "Wellfound", "We Work Remotely", "Seek Australia", "MyCareersFuture Singapore", "GulfTalent UAE"]:
        assert name in PUBLIC_WEB_SOURCES


def test_source_registry_has_user_list():
    from discovery import PUBLIC_WEB_SOURCES, COMPANY_TARGETS
    assert len(PUBLIC_WEB_SOURCES) >= 50
    assert "LinkedIn" in PUBLIC_WEB_SOURCES
    assert "Naukri" in PUBLIC_WEB_SOURCES
    assert "TELUS Digital" in COMPANY_TARGETS
    assert "Spotify" in COMPANY_TARGETS


def test_free_web_search_function_exists():
    from discovery import free_web_search
    assert callable(free_web_search)
