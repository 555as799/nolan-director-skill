#!/usr/bin/env python3
"""Render an original shot composition board and camera diagram with no API key."""
import argparse
import html
import json
from pathlib import Path


def esc(text):
    return html.escape(str(text), quote=True)


def lines(text, limit=24):
    text = str(text).replace('\n', ' ')
    return [text[i:i + limit] for i in range(0, min(len(text), limit * 3), limit)] or ['']


def text_block(x, y, text, color='#bcc7d5', size=17, limit=24):
    spans = ''.join(f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.45}">{esc(t)}</tspan>' for i, t in enumerate(lines(text, limit)))
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}">{spans}</text>'


def figure(x, y, scale=1):
    return f'''<g transform="translate({x},{y}) scale({scale})">
    <ellipse cx="0" cy="0" rx="17" ry="23" fill="#d7c1a2"/>
    <path d="M-18 25 Q0 12 18 25 L32 91 L-32 91 Z" fill="#243f4a"/>
    <path d="M-18 31 L-41 67 M18 31 L41 64" stroke="#d7c1a2" stroke-width="10" stroke-linecap="round"/>
    </g>'''


def composition(shot, w=410, h=180):
    scene = shot.get('scene', 'neutral')
    scale = shot.get('scale', 'medium')
    horizon = 95
    s = f'<rect width="{w}" height="{h}" fill="url(#sky)"/>'
    if scene == 'water':
        s += f'<path d="M0 88 Q90 78 185 90 T410 84 V180 H0Z" fill="#387286"/>'
        s += '<path d="M0 86 Q90 76 185 88 T410 82" fill="none" stroke="#d1e5dd" stroke-width="3"/>'
        s += '<path d="M245 83 L355 79 L390 81" fill="none" stroke="#626f65" stroke-width="5"/>'
        s += figure(190, 65 if scale == 'close' else 75, 1.35 if scale == 'close' else .65)
        s += '<path d="M0 126 Q80 115 170 132 T410 121 V180 H0Z" fill="#24495a" opacity=".77"/>'
        s += '<path d="M255 103 L305 99 L300 109 L258 111Z" fill="#cfbb90"/>'
    elif scene == 'underwater':
        s = '<rect width="410" height="180" fill="#244b61"/>'
        s += '<path d="M80 0 L175 180 H275 L155 0Z" fill="#aec9c5" opacity=".15"/>'
        s += figure(195, 74, .85 if scale == 'close' else .5)
        for bx, by, br in [(170,55,5),(182,35,3),(165,16,4),(242,88,5)]:
            s += f'<circle cx="{bx}" cy="{by}" r="{br}" fill="none" stroke="#adc6cc" opacity=".65"/>'
    elif scene == 'room':
        s = '<rect width="410" height="180" fill="#c7c1ac"/>'
        s += '<path d="M0 132 H410 V180 H0Z" fill="#77715f"/>'
        s += '<rect x="20" y="17" width="100" height="94" fill="#e6e4cf" stroke="#657268" stroke-width="5"/>'
        s += '<path d="M70 18 V111 M20 61 H120" stroke="#657268" stroke-width="4"/>'
        for actor in shot.get('actors', [{'x':205,'y':73,'scale':.75}]):
            s += figure(float(actor.get('x',205)), float(actor.get('y',73)), float(actor.get('scale',.75)))
        for prop in shot.get('props', []):
            px,py=float(prop.get('x',270)),float(prop.get('y',125))
            s += f'<rect x="{px}" y="{py}" width="45" height="36" fill="#b19164" stroke="#564f43"/>'
            s += text_block(px, py-7, prop.get('label','道具'), size=12,limit=9)
    elif scene == 'street':
        s += '<path d="M0 180 L175 65 H235 L410 180Z" fill="#696f70"/>'
        s += '<path d="M0 15 L150 60 V115 L0 172Z M410 15 L260 60 V115 L410 172Z" fill="#7f827b"/>'
        s += figure(205,94,.55)
    elif scene == 'shore':
        s += '<path d="M0 94 Q100 85 200 94 T410 89 V180 H0Z" fill="#508b96"/>'
        s += '<path d="M0 130 L80 107 L116 128 L158 139 L128 180 H0Z" fill="#827e6a"/>'
        s += figure(288, 118, .32)
        s += '<path d="M315 138 l32 -2 -4 8 -28 2Z" fill="#d7b779"/>'
        s += '<line x1="165" y1="134" x2="272" y2="131" stroke="#f2b877" stroke-dasharray="5 5"/>'
    elif scene == 'memory':
        s += '<path d="M0 110 L55 56 L115 106 L180 38 L264 112 L332 74 L410 119 V180 H0Z" fill="#5c7568"/>'
        s += '<path d="M0 134 Q125 99 225 145 T410 124 V180 H0Z" fill="#a89e72"/>'
        s += '<path d="M190 180 Q172 137 204 124" fill="none" stroke="#d1c5a6" stroke-width="8"/>'
        s += figure(215, 96, .48 if scale == 'wide' else .75)
        s += '<rect x="8" y="8" width="187" height="25" rx="4" fill="#10232a" opacity=".8"/>'
        s += '<text x="17" y="26" font-size="14" fill="#e4ece9">占位风光 · 真实素材待选</text>'
    else:
        s += '<path d="M0 110 L410 95 V180 H0Z" fill="#657879"/>'
        s += figure(200, 77, .8)
    s += '<path d="M0 60 H410 M0 120 H410 M136 0 V180 M273 0 V180" stroke="#fff" stroke-width=".6" opacity=".16"/>'
    return s


def render(data):
    shots = data.get('shots', [])
    if not 1 <= len(shots) <= 6:
        raise ValueError('Provide 1–6 shots.')
    if any(not isinstance(s, dict) or not s.get('id') for s in shots):
        raise ValueError('Every shot needs an id.')
    ids = [str(s['id']) for s in shots]
    if len(set(ids)) != len(ids):
        raise ValueError('Shot ids must be unique.')
    cols = 2 if len(shots) <= 4 else 3
    width = 990 if cols == 2 else 1460
    rows = (len(shots) + cols - 1) // cols
    height = 185 + rows * 575 + 365
    svg = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="#b8d1d3"/><stop offset="1" stop-color="#e4dfca"/></linearGradient></defs>
    <rect width="100%" height="100%" fill="#101923"/>
    <g font-family="PingFang SC, Microsoft YaHei, sans-serif">
    <text x="40" y="56" font-size="32" font-weight="650" fill="#f1eee4">{esc(data.get('title', '场次视觉拍法'))}</text>
    <text x="40" y="92" font-size="17" fill="#92a6b6">原创构图示意 · {esc(data.get('aspect', '宽画幅'))} · 镜号、机位、切点与声音</text>
    <text x="40" y="126" font-size="16" fill="#b7c1c9">{esc(data.get('note', '画面用来讨论拍法，具体地点与人物材料由创作者提供。'))}</text>''']
    for i, shot in enumerate(shots):
        x = 40 + (i % cols) * 475
        y = 155 + (i // cols) * 575
        svg += [f'<g transform="translate({x},{y})">', '<rect width="440" height="550" rx="10" fill="#1a2835"/>',
                f'<text x="15" y="33" font-size="19" fill="#efbb77" font-weight="650">{esc(shot["id"])}  {esc(shot.get("label", ""))}</text>',
                f'<svg x="15" y="48" width="410" height="180" viewBox="0 0 410 180" overflow="hidden">{composition(shot)}</svg>']
        for line_y, label, field in [(259, '动作', 'action'), (326, '相机', 'camera'), (393, '切点 / 声音', 'cut_sound'), (460, '制作 / 体验', 'production_experience')]:
            if field == 'cut_sound':
                value = f'{shot.get("cut", "待定")} / {shot.get("sound", "待定")}'
            elif field == 'production_experience':
                value = f'{shot.get("production", "待定")} / {shot.get("experience", "待定")}'
            else:
                value = shot.get(field, '待定')
            svg += [f'<text x="15" y="{line_y}" fill="#efbb77" font-size="14">{label}</text>', text_block(15, line_y + 25, value, size=16, limit=25)]
        svg.append('</g>')
    bottom = 165 + rows * 575
    svg += [f'<text x="40" y="{bottom}" font-size="23" fill="#f1eee4">空间与剪辑关系</text>',
            f'<g transform="translate(40,{bottom + 26})">',
            '<rect width="420" height="235" rx="8" fill="#1a2835"/>',
            '<text x="20" y="29" font-size="16" fill="#bcc7d5">方位讨论图 · 非实际场地测绘</text>']
    layout = data.get('layout')
    water_scene = any(s.get('scene') in ['water','shore','underwater'] for s in shots)
    if layout:
        for item in layout:
            lx=max(25,min(float(item.get('x',210)),390))
            ly=max(60,min(float(item.get('y',130)),195))
            if item.get('type') == 'camera':
                svg.append(f'<path d="M{lx-8} {ly-7} l16 7 -16 7Z" fill="#e9f0ed"/>')
            else:
                svg.append(f'<circle cx="{lx}" cy="{ly}" r="8" fill="#efbb77"/>')
            svg.append(text_block(lx-20,ly+24,item.get('label','位置'),size=13,limit=10))
    elif water_scene:
        svg += ['<path d="M20 155 H400 V211 H20Z" fill="#39788a"/>',
                '<path d="M20 85 H400 V155 H20Z" fill="#7a8572"/>',
                '<text x="25" y="105" font-size="16" fill="#eef0dd">岸</text>',
                '<text x="25" y="182" font-size="16" fill="#d0e4ea">水</text>',
                '<circle cx="250" cy="173" r="8" fill="#efbb77"/>',
                '<text x="263" y="178" font-size="14" fill="#efbb77">人物</text>',
                '<path d="M324 184 l45 -6 2 13 -45 6Z" fill="#bcaf90"/>',
                '<text x="341" y="220" font-size="14" fill="#c9d3dc">板</text>',
                '<path d="M192 189 l18 -12 v24 Z" fill="#e9f0ed"/>',
                '<path d="M210 177 L250 165 L250 184Z" fill="#fff" opacity=".2"/>',
                '<text x="133" y="219" font-size="13" fill="#c9d3dc">受控水线机位</text>']
    else:
        svg += [text_block(32,100,'平面位置按本场次补充。可提供layout中人物、道具和相机的位置。',size=17,limit=21),
                text_block(32,195,'各镜空间关系见上方镜号与相机说明。',size=14,limit=25)]
    svg += ['</g>', text_block(495, bottom + 64, data.get('timeline', '按各镜标出的切点试剪；声音关系随当前方案调整。'), size=19, limit=22)]
    if water_scene:
        svg.append(text_block(495, bottom + 180, '水上/水下危险动作在受控场地分拍，相机位置按现场条件核定。', size=16, limit=25))
    svg.append('</g></svg>')
    return ''.join(svg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    svg = render(data)
    args.out.mkdir(parents=True, exist_ok=True)
    svg_path = args.out / 'shotboard.svg'
    html_path = args.out / 'shotboard.html'
    svg_path.write_text(svg, encoding='utf-8')
    html_path.write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(data.get('title', '场次视觉拍法')) + '</title><style>body{margin:0;background:#101923}svg{display:block;width:min(100%,1200px);height:auto;margin:auto}</style>' + svg + '</html>', encoding='utf-8')
    print(json.dumps({'svg': str(svg_path.resolve()), 'html': str(html_path.resolve()), 'shots': len(data['shots'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
