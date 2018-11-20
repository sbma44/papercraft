#!/bin/env python3

import sys
import math
import argparse
import xml.etree.ElementTree as ET
import kdtree

EPS_M = 0.1
PAUSE = 'G4 P0.5; pause'

parser = argparse.ArgumentParser()
parser.add_argument('--fit', help='x,y range to normalize output gcode to')
parser.add_argument('--offset', help='x,y offset for output')
args = parser.parse_args()


class Point(object):
    def __init__(self, x, y, segments):
        self.coords = (x, y)
        self.segments = segments

    def __len__(self):
        return len(self.coords)

    def __getitem__(self, i):
        return self.coords[i]

    def __repr__(self):
        return 'Point({}, {}, [{}])'.format(self.coords[0], self.coords[1], ','.join([str(x) for x in sorted(self.segments)]))

class Transformer(object):
	def __init__(self, extents, fit, offset):
		self.extents = extents
		dx = extents[2] - extents[0]
		dy = extents[3] - extents[1]
		self.t = (extents[0], extents[1])
		if fit:
			self.r = min(fit[0] / dx, fit[1] / dy) # scale to fit fully inside bounds
		else:
			self.r = 1
		self.offset = offset and offset or [0, 0]

	def xform(self, pt):
		return (self.offset[0] + (self.r * (pt[0] - self.t[0])), self.offset[1] + (self.r * (pt[1] - self.t[1])))


def dist(p0, p1):
	return math.sqrt(((p1[1] - p0[1])**2) + ((p1[0] - p0[0])**2))

def coord(e, attr):
    c = e.attrib.get(attr)
    if not c:
        return False
    return float(c.replace('px', ''))

if __name__ == '__main__':

	print('G21 ; all units in mm')

	drawn = 0
	extents = [None, None, None, None]

	root = ET.parse(sys.stdin).getroot()
	segments = [] # ( (x1, y1), (x2, y2), length ), ...
	kdt = kdtree.create(dimensions=2)

	# collect segments, add to kd-tree
	for (i, line) in enumerate(root.iter('{http://www.w3.org/2000/svg}line')):
		x1 = coord(line, 'x1')
		x2 = coord(line, 'x2')
		y1 = coord(line, 'y1')
		y2 = coord(line, 'y2')

		# track max & min points
		for (j, d) in enumerate((x1, y1, x2, y2)):
			if extents[j] is None:
				extents[j] = d
			else:
				f = j < 2 and min or max
				extents[j] = f(extents[j], d)

		segments.append([[x1, y1], [x2, y2], dist((x1, y1), (x2, y2))])
		for pt in ((x1, y1), (x2, y2)):
			closest = kdt.search_nn(pt)
			if not closest or len(closest) == 0 or dist(pt, closest[0].data) > EPS_M:
				kdt.add(Point(pt[0], pt[1], [i]))
			else:
				closest[0].data.segments.append(i)


	fit = False
	if args.fit:
		fit = [int(x) for x in args.fit.split(',')]
	offset = False
	if args.offset:
		offset = [int(x) for x in args.offset.split(',')]
	xformer = Transformer(extents, fit, offset)

	# start with upper left-most point
	last_pt = (0,0)
	closest = None
	
	while drawn < len(segments):

		if not closest:
			closest = kdt.search_nn(last_pt)
			if closest and len(closest) > 1:
				closest = closest[0]

		# find the longest segment passing through this point
		current_seg_index = sorted(closest.data.segments, key=lambda q: segments[q][2], reverse=True)[0]
		current_seg = segments[current_seg_index]

		# figure out which of the segment's points is closest
		pts = [current_seg[0], current_seg[1]]
		pts.sort(key=lambda q: dist(q, last_pt))

		# if the closest point is more than EPS_M away, left the pen & move
		if dist(last_pt, pts[0]) > EPS_M: # @TODO: make this in mm not SVG units
			print('M3 S100; pen up')
			print(PAUSE)
			xpt = xformer.xform(pts[0])
			print('G00 X{:0.5f} Y{:0.5f}'.format(xpt[0], xpt[1]))
			print('M3 0; pen down')
			print(PAUSE)

		# draw to the other point
		xpt = xformer.xform(pts[1])
		print('G01 X{:0.5f} Y{:0.5f}'.format(xpt[0], xpt[1]))

		last_pt = pts[1]

		# remove segment index from first point's list of segment indices
		closest.data.segments.remove(current_seg_index)
		# if it was the last one, remove point from kdtree
		if len(closest.data.segments) == 0:
			kdt = kdt.remove(closest.data)

		# do same for the other point of the segment
		closest = kdt.search_nn(last_pt)
		if closest and len(closest) > 1:
			closest = closest[0]
		closest.data.segments.remove(current_seg_index)
		if len(closest.data.segments) == 0:
			kdt = kdt.remove(closest.data)

		drawn = drawn + 1

	print('M3 100; pen up')
	print(PAUSE)
	print('G00 X0 Y0; home')
