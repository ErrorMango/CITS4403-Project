"""Compact state changes and standalone playback"""
import json
import numpy as np


class Frames:
    """Store only changed cells"""
    def __init__(self, n):
        self.previous=np.zeros(n*n,dtype=np.uint8)
        self.frames=[]

    def __call__(self, state):
        flat=state.ravel()
        changed=np.flatnonzero(flat != self.previous)
        self.frames.append([int(i+1) if flat[i]==1 else -int(i+1) for i in changed])
        self.previous=flat.copy()


def save_animation(path, runs):
    """No server or online libraries"""
    template=(__import__('pathlib').Path(__file__).with_name('animation.html')).read_text()
    path.write_text(template.replace('/*RUNS*/',json.dumps(runs,separators=(',',':'))))


def link_animations(folder):
    """Add links without changing statistics"""
    pages=sorted((folder/'animations').glob('*.html'))
    links='<section id="animations"><h2>First-run animations</h2>'+''.join(f'<p><a href="animations/{p.name}">{p.stem}</a></p>' for p in pages)+'</section>'
    path=folder/'comparison.html'
    text=path.read_text()
    import re
    text=re.sub(r'<section id="animations">.*?</section>','',text,flags=re.S)
    path.write_text(text.replace('<table>',links+'<table>',1))
