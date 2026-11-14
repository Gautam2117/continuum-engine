"""Distinct editorial and motion contracts for each automated Continuum channel.

These are executable camera/caption presets plus an editorial storyboard language.
An art-direction brief is not proof that a bespoke asset or 3D shot exists.
All 48 channels are intentionally independent and no generic fallback channel
may provide an example for another channel.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

VERSION = 1
CAMERAS = frozenset({"float", "snap", "hold", "drift_left", "drift_right", "parallax", "orbit", "push", "tilt", "pull"})
CAPTIONS = frozenset({"minimal", "impact", "ledger", "documentary", "typewriter", "soft"})

@dataclass(frozen=True)
class Director:
    channel: str
    visual_world: str
    shot_sequence: str
    camera: str
    captions: str
    sound_brief: str
    avoid: str

    def fingerprint(self) -> str:
        data = [VERSION, self.channel, self.visual_world, self.shot_sequence, self.camera, self.captions, self.sound_brief, self.avoid]
        return sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    def prompt(self) -> str:
        return (
            f"INDEPENDENT VISUAL DIRECTOR CONTRACT v{VERSION}: {self.channel}\n"
            f"Visual world: {self.visual_world}\n"
            f"Shot grammar: {self.shot_sequence}\n"
            f"Camera: {self.camera}; Captions: {self.captions}\n"
            f"Audio direction for post-production: {self.sound_brief}\n"
            f"Explicitly avoid: {self.avoid}\n"
            "Make every scene visually specific to this channel. Use only documented show types "
            "supported by the current engine, not imagined capabilities. A palette change alone "
            "is insufficient. Do not reference or copy another Continuum channel's episode."
        )

RAW = (
    ["Counterfactual Atlas","A precision observatory with volumetric moons, orbital cutaways and calibrated physical scales","Start with a physical impossibility, traverse a changing 3D model, end on the verified counterfactual","float","minimal","deep low-frequency pulse, restrained documentary voice","No emoji, cartoon mascot, unexplained chart or literal disaster forecast"],
    ["10SecScientist","Macro laboratory inserts with a single clean experiment and kinetic measurement","Present the result immediately, one visual mechanism, one compact payoff","snap","impact","bright short tick, no sustained intro","No padding or claim too complex for a true ten-second demonstration"],
    ["Oddly Proven","Peer-reviewed evidence drawer with paper inserts, experiment cards and replication stamps","Reveal unusual finding, show study source, then bound its interpretation","hold","ledger","quiet laboratory clicks with dry delivery","No unnamed paper, invented sample size or casual confidence"],
    ["Crazy Clipz","Sports-broadcast shockboard of extreme numbers over original animated stunts","Open on a record number then isolate the physical feat in a recreation","snap","impact","punchy rhythmic percussion without stock impact spam","No unsafe copycat tutorial or unsupported record"],
    ["Wild Creature Files","Field naturalist's wet-plate diorama with anatomy silhouettes and habitat depth","Reveal one animal behavior through a close habitat-to-anatomy move","drift_left","documentary","soft habitat ambience from self-generated layers","No generic stock montage substituting for the actual animal"],
    ["Foundbeam","Vintage startup war-room with timeline cards, source documents and product flow maps","Follow one causally supported acquisition mechanism with original interface schematics","parallax","ledger","muted analogue keys and calm storytelling","No invented founder quotes, unproved growth attribution or repeated bar charts"],
    ["Workflow Verdict","Clinical side-by-side interface specification lab, grids and feature traces","State a use-case, compare published attributes, reveal dated verdict","hold","ledger","dry interface taps and close-mic impartial narration","No false hands-on claims or unverified live pricing"],
    ["History to Drift To","Candlelit illustrated atlas with slow maps and hand-inked everyday objects","Walk through one ordinary historical day as an unhurried spatial journey","float","soft","warm evolving drone with no sharp hits","No jump cuts, battle spectacle or mid-roll subscription prompts"],
    ["What Happens in 10","Luminous chronograph tunnel with second-by-second process bands","Pin a clock on screen and follow the process at explicitly marked moments","snap","typewriter","metronome accents aligned to process transitions","No unsupported precise timecodes"],
    ["What Drives It","Industrial sectional workshop with exploded machines and visible force arrows","Trace force or energy through exactly one mechanism step by step","push","documentary","subtle engineered whirs and measured workshop ambience","No unrelated vehicle B-roll or repair instructions"],
    ["OH, THIS EXISTS","Museum-of-oddities product turntable with calibrated annotations and exhibit card","Introduce a documented object, rotate to its surprise function, then limitation","orbit","minimal","curious mechanical pluck and deadpan reveal","No invented object or purchase pitch"],
    ["What If Anomaly","Minimal alternate-reality municipal CCTV render with one changed physical rule","Begin with the fiction label then escalate observable consequences coherently","drift_right","typewriter","unsettling modular pulses, deliberate silence","No fiction disguised as current news"],
    ["Gears Unseen","Parchment engineering plate where brass gears assemble in precise meshing layers","Explode then reconstruct a specific historically grounded mechanism","orbit","documentary","tooth-tick rhythm and mechanical tension","No decorative fake gears that cannot physically mesh"],
    ["Brain Fool Lab","Magenta-black interactive perception test board with timer and reveal mask","Invite one viewer test, hold the illusion, reveal its limitations","hold","impact","sparse clicks and intentional quiet for interaction","No flashing hazard or claim the effect works for everyone"],
    ["Drawn Out Minds","Hand-drawn charcoal notebook with erasure, annotation and ink accumulation","Sketch a psychological idea as a character thought journey, then reframe it","tilt","soft","paper rub and pencil scratch, gentle voice","No diagnoses or borrowed comic characters"],
    ["Think Beyond This","Deep-space philosophical stage with large silent symbols, expanding geometric thought bubbles","Create a single philosophical paradox then unfold competing viewpoints","pull","minimal","long airy harmonic beds and pauses","No confident answers to unresolved philosophy"],
    ["The Low Battery Show","Original miniature clay room and Pip's visible prop-driven facial reactions","Show a silent physical gag through preparation, escalation and distinct visual payoff","push","soft","original foley synchronized to contact points","No objects outside the built set or offscreen actions narrated as visible"],
    ["Strata","Real app capture under crystalline lavender interaction overlays","Demonstrate genuine app behavior and one surprising interactive use case","snap","impact","short interaction sounds, truthful product demo voice","No fabricated UI screenshots or downloads claims"],
    ["Sienna Carter","Portrait-led cinematic personal diary with warm window light and location continuity","Tell one fictional persona vignette through emotionally linked compositions","float","soft","intimate sparse acoustic ambience","No implied real-person identity or unverifiable biography"],
    ["Aditi Raichand","Contemporary Hindi urban illustrated journal with fabrics, warm lighting and Devanagari lettering","Tell a character-driven fictional mini-episode with a clear beginning and return","drift_left","documentary","gentle city ambience and Hindi phrasing","No synthetic person presented as real"],
    ["Kiara","Soft pastel editorial lookbook with spatially composed persona frames and natural light","Carry a fictional visual microstory across three consistent places or moments","parallax","soft","quiet melodic textures and scene-specific ambience","No misleading real-life claims from a synthetic persona"],
    ["Samjho System","Hindi-first clean engineering blackboard with Devanagari typesetting and verified schematics","State a common confusion, animate system components, then correct the misconception","push","documentary","dry electronic tap with clear Hindi instruction","No false security demonstration or invented specs"],
    ["Inkbound","Monochrome calligraphy theatre where words become objects and scenes","Convert one original fictional line into a kinetic ink transformation","tilt","typewriter","ink-scrape percussion and breathing room","No copied poetry or generic quotation compilation"],
    ["Founder, Actually","Original clay founder interview set with ledger receipts and modest humor","Expose one startup assumption through a staged but clearly simulated office exchange","push","ledger","dry office foley and subtle timing","No impersonation or invented founder interviews"],
    ["LifeSpawn","Animated ecosystem cross-section with branching biological timelines and generational transitions","Follow one evolving life cycle from stage to stage with evidence boundaries","pull","documentary","organic rhythmic texture matching biological change","No unsupported evolutionary just-so story"],
    ["Next Frame","Kinetic film storyboard wall with camera-frame annotations and transformation arrows","Demonstrate one cinematography or animation principle through before-after frames","snap","typewriter","clapper clicks then a clean musical resolving beat","No copyrighted film clips or frame grabs without rights"],
    ["Majority Rules","Voting mechanism infographic board with tokens, counted ballots and threshold lines","Run one explicit choice system and show its counterintuitive result","hold","ledger","counting ticks and clean confirmation tones","No partisan persuasion or fake polling"],
    ["Room 404","First-person liminal architectural corridor with coherent continuous camera path","Build an original supernatural mystery around one navigable room","drift_right","minimal","room-tone drones and distant original knocks","No cheap jump-scare strobe or real found-footage framing"],
    ["Epic Elsewhere","Wide fantasy atlas with original maps, miniature caravan routes and landscape reveals","Launch one invented journey and pay off its discovery through a large environmental reveal","orbit","documentary","original orchestral motif kept behind dialogue","No franchise names, characters or lifted fantasy maps"],
    ["The Night Archive","Dusty archival evidence wall, numbered folders and reconstructed event objects","Follow one historical record mystery while separating evidence and inference","float","ledger","tape hiss, restrained documentary piano","No paranormal claim marketed as fact"],
    ["The Odd Units","Surreal scale-measuring studio with a single consistent measuring instrument","Convert a surprising quantity into a relatable physical comparison","snap","impact","precise meter ticks and playful measurement cadence","No unit conversion errors or size comparisons without scale"],
    ["Unreal Goods Co.","Fictional product commercials with original absurd item modeling and disclaimer","Pitch one impossible object as a clearly fictional ad with a comedic catch","orbit","impact","original jingle fragments and spoof commercial foley","No actual product availability or false purchase links"],
    ["Tiny Histories","Microscope-like tabletop history diorama with miniature date cards and artifacts","Tell a verified microhistory through an overlooked object and its journey","push","documentary","tiny tactile object sounds and soft historical ambience","No invented provenance for real artifacts"],
    ["Sent In","Message-window stage where anonymous fictional letters transform into illustrated scenes","Read an original audience-style prompt and show its fictional consequence","parallax","typewriter","quiet type-on, paper fold and scene-tail ambience","No real private submissions presented without permission"],
    ["The Builders Long Game","Architectural time-lapse blueprint with foundations, milestones and budget constraints","Follow a multi-year build through irreversible decisions and verified milestones","pull","ledger","measured construction pulses, no sensational drops","No false timelines or invented project economics"],
    ["One-Dollar Builds","DIY design table with actual bill-of-materials price cards and one testable build","Show an achievable design inside a verified strict materials budget","hold","documentary","light workshop tools and candid practical voice","No pretend builds, unsafe material handling or fake prices"],
    ["Unsealed Show","Forensic evidence unpacking table with seal-break closeups and public-record sources","Reveal a document's significance by opening a layered evidence chain","tilt","ledger","paper peel, stamp and quiet uncertainty","No confidential leak or unverified allegation"],
    ["Heist & Con","Illustrated crime-mechanism storyboard with redacted actors and consequence map","Explain documented fraud prevention or historical deception without operational steps","drift_left","documentary","quiet suspense strings and measured pauses","No actionable criminal playbooks or glamorized victims"],
    ["Survive This","Physics survival simulator with clear boundary conditions and safe decision overlays","Ask a hypothetical safety question, show key constraints and general principles","push","impact","restrained environmental sound and sober warning","No dangerous step-by-step survival stunt"],
    ["News From 2099","Clearly fictional future news studio, holographic maps and timestamp 2099","Deliver one original sci-fi future dispatch with visible FICTION labeling","snap","typewriter","synthetic broadcast ident and original city ambience","No fictional news presented as today's real events"],
    ["Money Has Mechanics","Exploded financial flow diagrams with cash arrows and explicit definitions","Explain one financial mechanism without forecasting individual assets","parallax","ledger","precise transaction ticks, sober voice","No investment advice or distorted return charts"],
    ["The India Machine","Hindi-English technical infrastructure map with realistic Indian system diagrams","Trace how one Indian public or private system works through its actual components","drift_right","documentary","ambient Indian streets recorded or self-generated with rights","No unsupported government claims or misleading national statistics"],
    ["Truth Over Propaganda","Source-first neutral fact-check ledger with split claims, evidence and uncertainty columns","Compare a specific factual claim against original records and show uncertainty","hold","ledger","minimal nonpartisan newsroom bed","No partisan framing, fake quotations or unsupported allegations"],
    ["BLANK HOURS","Near-black analog nightscape with low-motion gradients and uninterrupted continuity","Build a long ambient audiovisual world with gradual change, no narrator interruptions","float","soft","original low-level evolving texture, safely mastered","No repetitive synthetic loops that imply unique footage"],
    ["Benchwisedeals","Retail comparison workbench with dated verified price tags and explicit qualification","Compare actual sourced options by use-case rather than arbitrary rank","push","ledger","gentle interface ticks and clear disclosures","No fabricated real-time prices or affiliate statements"],
    ["Brieflylatest","Clean date-stamped news explainer desk with source overlays and sequence map","Give one verifiable recent development with exact date and context","snap","documentary","restrained modern bulletin sting, no clickbait siren","No stale news mislabeled as today or unsupported breaking update"],
    ["OHGUMMY","Original gummy stop-motion candy island with squash and stretch and practical foley","Tell one visual-comedy arc through expressive deformations and prop consequences","orbit","soft","original elastic squeaks and whimsical miniature percussion","No branded candy packaging or reused cartoon mascot"],
    ["Pixel Fables","Original isometric voxel-storybook world with editable tile sets and character paths","Tell a short original parable through map traversal and environmental payoff","parallax","typewriter","original 8-bit textures under cinematic storytelling","No copied game sprites or generic stock pixel background"]
)

DIRECTORS = {r[0]: Director(*r) for r in RAW}

def director_for(channel: str) -> Director:
    return DIRECTORS[channel]

def verify_directors(channels: set[str]) -> None:
    if set(DIRECTORS) != channels:
        raise ValueError(f"Channel director mismatch: missing={sorted(channels-set(DIRECTORS))}, extra={sorted(set(DIRECTORS)-channels)}")
    if len({d.fingerprint() for d in DIRECTORS.values()}) != len(DIRECTORS):
        raise ValueError("Some channels share identical creative fingerprints")
    for d in DIRECTORS.values():
        if d.camera not in CAMERAS or d.captions not in CAPTIONS:
            raise ValueError(f"Unsupported camera/caption mode for {d.channel}")
        if any(len(value) < 25 for value in (d.visual_world, d.shot_sequence, d.sound_brief, d.avoid)):
            raise ValueError(f"Underspecified unique art direction for {d.channel}")
