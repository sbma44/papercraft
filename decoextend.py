#!/bin/env python3
# usage: python3 decoextend.py < toroid.svg > toroid-de.svg

import sys
import xml.etree.ElementTree as ET

EPS_M = 0.01

def coord(e, attr):
    c = e.attrib.get(attr)
    if not c:
        return False
    return float(c.replace('px', ''))

def slope(p0, p1):
    dx = p1[0] - p0[0]
    if dx == 0:
        return sys.float_info.max
    return (p1[1] - p0[1]) / dx

def process_set(working_set):
    if len(working_set) < 2:
        return (True, working_set)

    # sort working set left to right
    working_set.sort(key=lambda x: x['p0'][0])
    for i in range(0, len(working_set)):
        for j in range(i + 1, len(working_set)):

            # calculate slope from S0P0 to S1P1 and S0P1 to S1P0
            # if slopes all match the working set's slope, we're collinear
            # if not, these segments are parallel but not collinear and should be left alone
            p0 = working_set[i]['p0']
            expected_slope = working_set[i]['slope']
            if (abs(slope(working_set[i]['p1'], working_set[j]['p0']) - expected_slope) > EPS_M) or (abs(slope(working_set[i]['p0'], working_set[j]['p1']) - expected_slope) > EPS_M):
                continue

            # the only remaining permissible configuration: collinear segments with a gap between them
            # e.g. ---  -----
            # otherwise we combine segments and flag the set as requiring more processing
            s0x0 = working_set[i]['p0'][0]
            s0x1 = working_set[i]['p1'][0]
            s1x0 = working_set[j]['p0'][0]
            s1x1 = working_set[j]['p1'][0]
            if not (s0x0 < s0x1 and s0x1 < s1x0 and s1x0 < s1x1):
                # make a duplicate set, omitting segments i and j
                new_set = [x for (k, x) in enumerate(working_set) if k not in (i, j)]
                
                # add a segment representing i and j's furthest points
                pts = [ working_set[i]['p0'], working_set[i]['p1'], working_set[j]['p0'], working_set[j]['p1'] ]
                pts.sort(key=lambda x: x[0])
                new_set.append({
                    'p0': pts[0], 
                    'p1': pts[-1],
                    'slope': slope(pts[0], pts[-1])
                })
                return (False, new_set)

    return (True, working_set)

if __name__ == '__main__':
    segments = []
    root = ET.parse(sys.stdin).getroot()

    # collect segments, calculate their slopes, order their points left-to-right
    for line in root.iter('{http://www.w3.org/2000/svg}line'):
        x1 = coord(line, 'x1')
        y1 = coord(line, 'y1')
        x2 = coord(line, 'x2')
        y2 = coord(line, 'y2')

        if not (x1 and y1 and x2 and y2):
            continue

        # ensure p0 is left of p1
        if x1 < x2:
            s = {
                'p0': [x1, y1],
                'p1': [x2, y2]
            }
        else:
            s = {
                'p0': [x2, y2],
                'p1': [x1, y1]
            }
        s['slope'] = slope(s['p0'], s['p1'])
        segments.append(s)

    working_set = []
    output_set = []
    segments.sort(key=lambda x: x['slope'])
    current_slope = segments[0]['slope']
    for seg in segments:

        # bin sets of segments by slope (within a tolerance)
        dm = abs(seg['slope'] - current_slope)
        if dm < EPS_M:
            working_set.append(seg)

        # slope discontinuity, process accumulated set
        else:
            while True:
                (done, working_set) = process_set(working_set)
                if done:
                    output_set.extend(working_set)
                    break

            # begin new working set
            working_set = [seg]
            current_slope = seg['slope']


    # handle any lingering contents of working_set
    while True:
        (done, working_set) = process_set(working_set)
        if done:
            output_set.extend(working_set)
            break

    print("""<svg xmlns="http://www.w3.org/2000/svg" width="3000px" height="2000px" viewbox="0 0 3000 2000">
    <g transform="translate(1500.000000 1000.000000)">""")
    for s in output_set:
        print('<line x1="{}px" y1="{}px" x2="{}px" y2="{}px" style="stroke:#0000FF;stroke-width=1.0;fill:none"/>'.format(s['p0'][0], s['p0'][1], s['p1'][0], s['p1'][1]))
    print("</g></svg>")

    sys.stderr.write('finished, reduced segment count from {} to {}\n'.format(len(segments), len(output_set)))