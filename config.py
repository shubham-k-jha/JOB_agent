from dataclasses import dataclass, field
from pathlib import Path
ROOT=Path(__file__).parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
@dataclass
class Settings:
    db_path:str=str(DATA/'job_agent.db')
    minimum_match_score:int=75
    minimum_ats_score:int=80
    lookback_days:int=7
    remote_worldwide:bool=True
    salary_min_lpa:float=8.0
    salary_target_lpa:float=10.0
    target_roles:list=field(default_factory=lambda:['Data Analyst','Data Scientist','Junior Data Scientist','BI Analyst','Business Analyst','Product Analyst','Analytics Engineer'])
settings=Settings()
