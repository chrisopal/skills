#!/usr/bin/env python3
"""Refresh reusable DataV province geometry and first-level administrative labels."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

BASE = 'https://geo.datav.aliyun.com/areas_v3/bound/'
DEST = Path(__file__).resolve().parents[1] / 'display/workbench/china-map.json'


def read(code):
    with urlopen(BASE + str(code) + '_full.json', timeout=35) as response:
        return json.load(response)


def cities(feature):
    code = feature['properties']['adcode']
    try:
        rows = read(code)['features']
    except HTTPError as exc:
        if code == 710000 and exc.code == 404:
            return str(code), []
        raise
    return str(code), [{'code': str(p['adcode']), 'name': p['name'], 'center': p.get('center') or p.get('centroid'), 'level': p.get('level', 'unknown')} for row in rows if (p := row['properties']).get('name') and (p.get('center') or p.get('centroid'))]


def main():
    source = read(100000)
    provinces = [f for f in source['features'] if str(f['properties']['adcode']).isdigit()]
    assert len(provinces) == 34, 'Unexpected province coverage; review source before replacing data'
    with ThreadPoolExecutor(max_workers=6) as pool:
        children = dict(pool.map(cities, provinces))
    features = [{'code': str(f['properties']['adcode']), 'name': f['properties']['name'], 'center': f['properties'].get('centroid') or f['properties'].get('center'), 'geometry': f['geometry']} for f in source['features']]
    data = {'source': '阿里云 DataV GeoAtlas', 'source_url': 'https://datav.aliyun.com/portal/school/atlas/area_selector', 'geometry_url': BASE + '100000_full.json', 'accessed_on': date.today().isoformat(), 'child_source_pattern': BASE + '{adcode}_full.json', 'city_coverage_note': '省内显示地级市、自治州、地区、盟及省直辖单位；直辖市和港澳显示下辖区。台湾市县点位在此来源缺失。', 'features': features, 'cities': children}
    DEST.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Saved {len(provinces)} provinces and {sum(map(len, children.values()))} child labels to {DEST}')


if __name__ == '__main__':
    main()
