"""Compact server replay format shared by the Windows and Android viewers."""
import gzip
import json
from pathlib import Path

STEP = 0.2

class Recorder:
    def __init__(self, clip_selector):
        self.clip_selector = clip_selector
        self.frames = []
        self.next_frame = 0.0

    def record(self, match, final=False):
        if not final and match.t + 0.001 < self.next_frame:
            return
        self.next_frame = match.t + STEP
        units = [[u.id, round(u.pos[0], 1), round(u.pos[1], 1), round(100 * u.hp / u.maxhp)]
                 for u in match.alive if u.alive]
        if self.frames and self.frames[-1][0] == match.t:
            self.frames[-1] = [match.t, units]
        else:
            self.frames.append([match.t, units])

    def finish(self, match, directory, fixture, offset=0):
        self.record(match, final=True)
        meta = [dict(id=u.id, name=u.name, team=u.team, kind=u.kind, role=u.role,
                     player_id=getattr(u,'player_id',None),player_name=getattr(u,'player_name',None))
                for u in match.units]
        clips = self.clip_selector(match.events, match.t, meta)
        directory.mkdir(parents=True, exist_ok=True)
        public_clips = []
        cursor = 0
        for index, clip in enumerate(clips):
            while cursor < len(self.frames) and self.frames[cursor][0] < clip['start']:
                cursor += 1
            end = cursor
            while end < len(self.frames) and self.frames[end][0] <= clip['end']:
                end += 1
            frames = self.frames[max(0, cursor-1):min(end+1, len(self.frames))]
            ids = {unit[0] for frame in frames for unit in frame[1]}
            header = {key:clip[key] for key in ('start','end','label','anchors')}
            path = clip_path(directory, fixture, index+offset)
            temporary = path.with_suffix('.tmp')
            with gzip.open(temporary,'wt',encoding='utf-8',compresslevel=3) as out:
                json.dump({'version':1,'clip':header,'units':[meta[i] for i in sorted(ids)],'frames':frames},
                          out, ensure_ascii=False, separators=(',',':'))
            temporary.replace(path)
            public_clips.append({key:header[key] for key in ('start','end','label')})
        return public_clips

def clip_path(directory: Path, fixture: int, index: int):
    return directory / f'{fixture}-{index}.json.gz'
