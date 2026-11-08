"""Readable, diverse English esports handles for game-generated people.

Never changes a real player's registered nickname. No Korean pseudo-syllables,
no shared two-part template, and near-duplicate names are rejected.
"""
import hashlib
import re
from difflib import SequenceMatcher

CANDIDATES = """
Axiom Vesper Kairo Duskfall Noxium Aether Flintlock Onyx Vandal
Cipher Halcyon Jetstream Bastian Quasar Riptide Helix Drifter
Solace Nyx Paradox Vertex Lucent Mirage Ascend Octane Orbit
Tempest Torrent Cobalt Praxis Rook Specter Zenith Kestrel
Runecrest Strider Lumen Axion Sable Breaker Kismet Torrentia
Voltari Perigee Noctis Zephyr Valen Indigo Sypher Garrick
Echoes Kineto Arcadia Mistral Hollowpoint Caldera Vortex
Crux Maverick Radiant Vaelor Kynetic Harrier Valiant Corsair
Arcturus Emberlyn Gladius Legacy Sequoia Polaris Salvo
Eclipse Morningstar Nexus Resolve Tempo Silverline Graviton
Nightshade Boundless Catalyst Wildfire Monolith Keystone
Oblivion Cerulean Dagger Antares Comet Archon Momentum
Overdrive Tenacity Solaris Runeblade Satyr Scythe
Outrider Sentinel Flint Eon Maveron Revelry Odyssey
Wayfarer Cadence Carbon Prism Hawkeye Calyx Aurelion
Nimble Veridian Torq Elysian Ravage Cascade Ardent
Peregrine Blitzar Umbra Glacier Equinox Emberfall
Raiden Velaris Kestium Lockstep Renegade Sparx Moonrise
Vigilance Bluejay Windward Solstice Argon
""".split()

def valid(name):
    return bool(re.fullmatch(r'[A-Za-z]{3,20}',name))

def too_similar(name, used):
    candidate=name.casefold()
    for other in used:
        other=str(other).casefold()
        if candidate==other: return True
        if len(candidate)>4 and len(other)>4:
            if candidate.startswith(other) or other.startswith(candidate): return True
            if SequenceMatcher(None,candidate,other).ratio()>=0.74: return True
    return False

def choose(seed, used):
    """Deterministic per identity, unique among all existing source names."""
    used=set(str(n).casefold() for n in used if n)
    start=int.from_bytes(hashlib.sha256(str(seed).encode()).digest()[:8],'big')%len(CANDIDATES)
    for offset in range(len(CANDIDATES)):
        name=CANDIDATES[(start+offset)%len(CANDIDATES)]
        if valid(name) and not too_similar(name,used):
            return name
    raise ValueError('Unique, sufficiently distinct English nicknames exhausted')
