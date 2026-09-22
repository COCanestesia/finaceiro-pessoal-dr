from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher

@dataclass(frozen=True)
class MatchScore: entry_id:int; score:int
@dataclass(frozen=True)
class MatchResult: candidates:tuple[MatchScore,...]; auto_confirm:bool

def _norm(s): return ' '.join((s or '').casefold().split())
def score_match(statement,entry)->MatchScore:
    score=0
    if abs(int(statement['amount_cents']))==int(entry.amount_cents): score+=60
    sd=date.fromisoformat(statement['posted_date']); ed=entry.settled_date or entry.competence_date; delta=abs((sd-ed).days)
    if delta==0: score+=25
    elif delta==1: score+=18
    if SequenceMatcher(None,_norm(statement['description']),_norm(entry.description)).ratio()>=.8: score+=15
    return MatchScore(entry.id,score)
def rank_matches(statement,entries)->MatchResult:
    ranked=sorted((score_match(statement,e) for e in entries),key=lambda x:x.score,reverse=True)
    auto=bool(ranked and ranked[0].score>=85 and (len(ranked)==1 or ranked[0].score-ranked[1].score>5))
    return MatchResult(tuple(ranked),auto)
