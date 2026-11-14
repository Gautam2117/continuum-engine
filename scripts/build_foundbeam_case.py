"""Reproducible source-led illustration spec for the historical Dropbox case.

Input is an independently authored editorial script and source ledger.
No model rewrites, invented figures, unlicensed interface screenshots or
corporate API requests are involved. Output is a PRIVATE review proposal.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autopilot.directors import director_for,VERSION
from engine.spec_check import problems

SOURCE=ROOT/'editorial/foundbeam/dropbox-referrals-narration.md'
OUT=ROOT/'specs/2026-11-17/foundbeam-l1.json'
SECTIONS={
    'Opening':('split','folder','referral'),
    'The search box':('folder','split','folder','signup'),
    'The invitation':('referral','meter','split','folder'),
    'Three numbers, three questions':('milestone','milestone','referral','signup'),
    'Back at the desk':('folder','referral','return'),
    'What the team could learn':('signup','folder','referral','return'),
    'What the numbers cannot prove':('milestone','signup','split'),
    'Reading the result':('milestone','signup','return'),
    'Closing':('return',),
}


# Explicitly reviewed visual beats, keyed to the independently written narration.
# Scene index is deliberately not used: inserted sentences cannot silently
# redirect a chart to an unrelated passage. Unmatched anchors fail the build.
REVIEWED_VISUAL_BEATS = {
    'In his 2010 talk, cofounder Drew Houston described this a': 'split',
    'Some recipients could ignore it. That number tells you ho': 'referral',
    'Imagine that you can see only one line on a dashboard: to': 'split',
    'On the invitation path, the first question is whether Sam': 'referral',
    'Give the person receiving it a reason to care, and measur': 'return',
    'It does not give us the probability that any single invit': 'split',
    'The useful lesson is more concrete: show which user actio': 'return',
    'If those are separate questions in the actual product, th': 'split',
    'The two registration figures are snapshots many months ap': 'milestone',
    'The other thing to keep in view is what the reward asks p': 'meter',
    'In our illustration, Alex already has a file to send and ': 'folder',
}


def sections_from_markdown(source: pathlib.Path = SOURCE) -> dict[str,list[str]]:
    if not source.is_file():
        raise FileNotFoundError(source)
    text=source.read_text()
    blocks=re.split(r'\n\s*\n',text)
    result:dict[str,list[str]]={}
    name=None
    for block in blocks:
        block=block.strip()
        if block.startswith('## '):
            name=block[3:].strip()
            if name not in SECTIONS or name in result:
                raise ValueError(f'Unknown or duplicated editorial section: {name}')
            result[name]=[]
        elif name and block and not block.startswith('*Visual:') and not block.startswith('#'):
            result[name].append(block)
    if set(result)!=set(SECTIONS):
        raise ValueError(f'Editorial source sections changed: {sorted(set(SECTIONS)^set(result))}')
    return result


def sentence_groups(paragraph:str, max_words:int=28) -> list[str]:
    """Preserve words in order, splitting at actual sentence boundaries."""
    parts=re.split(r'(?<=[.!?])\s+(?=[A-Z“\"’])',paragraph.strip())
    groups=[]
    pending=[]
    for item in parts:
        if not item.strip():
            continue
        if pending and len(' '.join(pending).split())+len(item.split())>max_words:
            groups.append(' '.join(pending))
            pending=[]
        pending.append(item)
    if pending:
        groups.append(' '.join(pending))
    if ' '.join(groups).split() != paragraph.split():
        raise ValueError('Sentence grouping corrupted the authored narration')
    return groups


def scene_for(section:str, line:str, index:int, total:int, *, chapter_index:int) -> dict:
    if section=='Opening' and index==0:
        # Show the core dual-path illustration during the hook; a motionless
        # title card spends the highest-value opening seconds on a logo.
        return {'type':'foundbeam_flow','variant':'split','title':'ONE PERSON. TWO INVITES.'}
    if section=='Closing' and index==total-1:
        return {'type':'end','text':'A SHARED FILE IS NOT A REFERRAL'}
    low=line.lower()
    if section=='Three numbers, three questions':
        if '2.8 million' in low:
            return {'type':'number','from':2.8,'value':2.8,'unit':'million',
                    'label':'Direct referral invitations SENT in 30 days (April 2010)', 'decimals':1}
        if '35 percent' in low or '20 percent' in low:
            return {'type':'foundbeam_flow','variant':'signup','title':'REPORTED DAILY SIGNUP SOURCES'}
        if '100,000' in low or 'four million' in low or 'september 2008' in low:
            return {'type':'foundbeam_flow','variant':'milestone', 'title':'REGISTRATIONS AT TWO DATES'}
    patterns=SECTIONS[section]
    variant=patterns[index%len(patterns)]
    # Alternate diagram passages with precise verbal emphasis. No arbitrary
    # third-party archival assets or noisy stock B-roll.
    if index%6==5 and section not in ('Opening','Closing'):
        return {'type':'say','text':' '.join(line.split()[:10])}
    return {'type':'foundbeam_flow','variant':variant}


def build(source:pathlib.Path = SOURCE) -> dict:
    source_sections=sections_from_markdown(source)
    scenes=[]
    editorial=[]
    overrides_seen=set()
    for chapter_index,(section,paragraphs) in enumerate(source_sections.items()):
        groups=[g for para in paragraphs for g in sentence_groups(para)]
        for j,line in enumerate(groups):
            show=scene_for(section,line,j,len(groups),chapter_index=chapter_index)
            matches=[(anchor,variant) for anchor,variant in REVIEWED_VISUAL_BEATS.items()
                     if line.startswith(anchor)]
            if len(matches)>1:
                raise ValueError('Overlapping reviewed Foundbeam scene anchors')
            if matches:
                anchor,variant=matches[0]
                if show['type']!='foundbeam_flow':
                    raise ValueError('Reviewed visual anchor conflicts with a factual-number scene')
                show={'type':'foundbeam_flow','variant':variant}
                overrides_seen.add(anchor)
            scenes.append({'say':line,'show':show})
            editorial.append((section,line))
    if overrides_seen != set(REVIEWED_VISUAL_BEATS):
        raise ValueError('Foundbeam editorial scene anchors changed; review visual assignments again')
    author_text=' '.join(para for paragraphs in source_sections.values() for para in paragraphs)
    rendered_text=' '.join(line for _,line in editorial)
    if author_text.split()!=rendered_text.split():
        raise ValueError('Narration text differs from original verified editorial source')
    director=director_for('Foundbeam')
    s={
        'id':'2026-11-17-foundbeam-l1',
        'channel':'Foundbeam','format':'long',
        'title':'Why Dropbox Rewarded Both People for One Referral',
        'thumb':'TWO WAYS TO GROW',
        'description': (
            'Dropbox did not attribute its first 100,000 users solely to referrals. This episode distinguishes a shared folder from a rewarded invite, and explains the company-reported figures from Drew Houston’s April 2010 presentation: 100,000 registered users in September 2008, four million in January 2010, 2.8 million direct referral invitations sent in one 30-day period, and referrals accounting for 35% of daily signups alongside another 20% through shared folders and other viral features. Those are different denominators and observation periods; the presentation does not establish an individual invite conversion rate. Alex and Sam are fictional and the animated desktop is an original illustration, NOT a Dropbox interface recreation. No referral reward size is asserted.\n\n'
            'Sources (company-reported historical figures):\n'
            'Drew Houston, Startup Lessons Learned (2010), slides 27–32: '
            'https://www.slideshare.net/slideshow/dropbox-startup-lessons-learned-239520249/239520249\n'
            'Sequoia Capital, interview with Drew Houston, The Journey to Attract Early Users: '
            'https://sequoiacap.com/podcast/crucible-moments-dropbox/\n\n'
            'This is an independently written editorial and diagrammatic recreation narrated with a synthetic voice. Not financial advice.'
        ),
        'tags':['Dropbox history','startup growth','referral programs','shared folders','product led growth','Foundbeam','startup case study','founder lessons'],
        'links':[{'label':'More from Continuum Arc','url':'https://continuumarc.tech'}],
        'publishAt':'2026-11-17T14:00:00Z',
        'synthetic':True,'madeForKids':False,
        'meta': {
            'generator':'sourced-human-editorial','topic':'Dropbox referral invitations versus shared folders',
            'axis':'early distribution tactics', 'reviewStatus':'EDITORIAL_HOLD_NOT_APPROVED',
            'sourceLedger':'editorial/foundbeam/dropbox-referrals-sources.md',
            'creativeDirector':{'id':'Foundbeam','fingerprint':director.fingerprint(),
                                'version':VERSION,'camera':director.camera,'captions':director.captions},
            'chapters':[{'name':title,'sceneStart':next(i for i,(name,_) in enumerate(editorial) if name==title)}
                        for title in source_sections],
        },
        'scenes':scenes,
    }
    bad=problems(s,'2026-11-17',strict=True)
    if bad:
        raise ValueError('Strict editorial spec validation failed: '+'; '.join(bad))
    return s


def main() -> None:
    spec=build()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
    print(f'Created {spec["id"]} with {len(spec["scenes"])} scenes, '
          f'{sum(len(x["say"].split()) for x in spec["scenes"])} spoken words; '
          'publication status: HELD')

if __name__=='__main__':main()
