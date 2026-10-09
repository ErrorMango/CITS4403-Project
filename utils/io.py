"""Data input and output"""
import csv
import json
import numpy as np


def map_file(root, name, filename):
    """Accept original or map-prefixed input names"""
    folder=root/'data'/'maps'/name
    for path in (folder/filename,folder/(name+filename)):
        if path.exists():return path
    raise FileNotFoundError(f'Missing {name}/{filename}')


def load_map(root, name):
    """Heights use cell-length units"""
    folder = root/'data'/'maps'/name
    fuel = np.loadtxt(map_file(root,name,'base_relative_fuel.csv'),delimiter=',')
    height = np.loadtxt(map_file(root,name,'height_grid.csv'),delimiter=',')/90.
    if fuel.shape != (100,100) or height.shape != fuel.shape:
        raise ValueError('Expected 100 x 100 maps')
    if not np.isfinite(fuel).all() or not np.isfinite(height).all() or (fuel<0).any():
        raise ValueError('Invalid map values')
    return fuel,height


def write_csv(path, rows):
    with path.open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
