import sys
import xml.etree.ElementTree as ET

def coord(e, attr):
    c = e.attrib.get(attr)
    if not c:
        return False
    return float(c.replace('px', ''))

if __name__ == '__main__':
    segments = []
    root = ET.parse(sys.stdin).getroot()

    print("""<svg xmlns="http://www.w3.org/2000/svg" width="3000px" height="2000px" viewbox="0 0 3000 2000">
    <g transform="translate(1500.000000 1000.000000)">""")
    

    # collect segments, calculate their slopes, order their points left-to-right
    for line in root.iter('{http://www.w3.org/2000/svg}line'):
        x1 = coord(line, 'x1')
        y1 = coord(line, 'y1')
        x2 = coord(line, 'x2')
        y2 = coord(line, 'y2')

        if not (x1 and y1 and x2 and y2):
            continue

        print('<path d="M {} {} L {} {} Z" stroke="#000000" stroke-width="1" />'.format(x1, y1, x2, y2))
    print("</g></svg>")