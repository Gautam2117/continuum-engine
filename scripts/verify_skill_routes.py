#!/usr/bin/env python3
"""Validate local skill routing across all 48 independently authored channels."""
from __future__ import annotations
import argparse,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autopilot.playbooks import PLAYBOOKS
from autopilot.directors import DIRECTORS

def verify(routes:dict, available:set[str]|None=None)->list[str]:
    errors=[]
    if routes.get("schemaVersion")!=1:errors.append("invalid schemaVersion")
    if routes.get("scope")!="agent_assisted_creative_authoring_only":errors.append("scope must describe agent-only usage")
    entries=routes.get("routes")
    if not isinstance(entries,dict):return errors+["routes must be a mapping"]
    names=set(PLAYBOOKS)
    if set(entries)!=names or set(DIRECTORS)!=names:
        errors.append("route names do not match all 48 channel playbooks/directors")
    seen=set()
    for name,route in entries.items():
        if not isinstance(route,dict):
            errors.append(f"{name}: invalid route");continue
        lead,support=route.get("primary"),route.get("secondary")
        purpose=route.get("purpose")
        if not all(isinstance(x,str) and x.strip() for x in (lead,support,purpose)):
            errors.append(f"{name}: missing lead, support or rationale");continue
        pair=(lead,support)
        if lead==support or pair in seen:errors.append(f"{name}: duplicate or indistinguishable skill pair")
        seen.add(pair)
        if available is not None:
            if lead not in available:errors.append(f"{name}: missing installed primary {lead}")
            if support not in available:errors.append(f"{name}: missing installed supporting {support}")
            for q in route.get("qa",[]):
                if q not in available:errors.append(f"{name}: missing QA skill {q}")
    return errors

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--installed",action="store_true",help="also verify local agent skill file links")
    args=parser.parse_args()
    data=json.loads((ROOT/"docs/CHANNEL_SKILL_ROUTING.json").read_text())
    available=None
    if args.installed:
        homes=[pathlib.Path.home()/".agents/skills",pathlib.Path.home()/".claude/skills",
               pathlib.Path.home()/".codex/skills"]
        needed = {s for route in data.get("routes",{}).values() if isinstance(route,dict)
                  for s in [route.get("primary"),route.get("secondary"),*(route.get("qa") or [])]
                  if isinstance(s,str)}
        available={name for name in needed if all((folder/name/"SKILL.md").is_file() for folder in homes)}
    problems=verify(data,available)
    if problems:
        raise SystemExit("\n".join(problems))
    print(f"48 independent channel routes verified; installed={args.installed}")

if __name__=="__main__":main()
