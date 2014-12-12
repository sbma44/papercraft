#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <math.h>

#define EPS 0.0001

typedef struct
{
	char header[80];
	uint32_t num_triangles;
} __attribute__((__packed__))
stl_header_t;

typedef struct
{
	float p[3];
} v3_t;

typedef struct
{
	v3_t normal;
	v3_t p[3];
	uint16_t attr;
} __attribute__((__packed__))
stl_face_t;


#define MAX_POINTS 24

typedef struct
{
	int n;
	int p[MAX_POINTS];
} poly_t;


static int
v3_eq(
	const v3_t * v1,
	const v3_t * v2
)
{
	float dx = v1->p[0] - v2->p[0];
	float dy = v1->p[1] - v2->p[1];
	float dz = v1->p[2] - v2->p[2];

	if (-EPS < dx && dx < EPS
	&&  -EPS < dy && dy < EPS
	&&  -EPS < dz && dz < EPS)
		return 1;

	return 0;
}


static int
edge_eq(
	const stl_face_t * const t0,
	const stl_face_t * const t1,
	int e0,
	int e1
)
{
	const v3_t * const v0 = &t0->p[e0];
	const v3_t * const v1 = &t0->p[e1];

	if (v3_eq(v0, &t1->p[0]) && v3_eq(v1, &t1->p[1]))
		return 1;
	if (v3_eq(v0, &t1->p[1]) && v3_eq(v1, &t1->p[0]))
		return 1;

	if (v3_eq(v0, &t1->p[0]) && v3_eq(v1, &t1->p[2]))
		return 1;
	if (v3_eq(v0, &t1->p[2]) && v3_eq(v1, &t1->p[0]))
		return 1;

	if (v3_eq(v0, &t1->p[1]) && v3_eq(v1, &t1->p[2]))
		return 1;
	if (v3_eq(v0, &t1->p[2]) && v3_eq(v1, &t1->p[1]))
		return 1;

	return 0;
}


double
v3_len(
	const v3_t * const v0,
	const v3_t * const v1
)
{
	float dx = v0->p[0] - v1->p[0];
	float dy = v0->p[1] - v1->p[1];
	float dz = v0->p[2] - v1->p[2];

	return sqrt(dx*dx + dy*dy + dz*dz);
}


/** recursively try to fix up the triangles.
 *
 * returns 0 if this should be unwound, 1 if was successful
 */
int
recurse(
	const stl_face_t * const faces,
	int start,
	const int num_faces,
	int * const used
)
{
	static int depth;

	depth++;

	const stl_face_t * const t = &faces[start];
	double d0 = v3_len(&t->p[0], &t->p[1]);
	double d1 = v3_len(&t->p[1], &t->p[2]);
	double d2 = v3_len(&t->p[1], &t->p[2]);

	// flag that we are looking into this one
	used[start] = 1;

	// start with the first triangle, find the ones that connect

	// for each edge, find the triangle that matches
	for (int j = 0 ; j < num_faces ; j++)
	{
		if (used[j])
			continue;

		const stl_face_t * const t2 = &faces[j];
		if (edge_eq(t, t2, 0, 1))
		{
			fprintf(stderr, "%d.0 -> %d\n", start, j);
			recurse(faces, j, num_faces, used);
		}
		if (edge_eq(t, t2, 0, 2))
		{
			fprintf(stderr, "%d.1 -> %d\n", start, j);
			recurse(faces, j, num_faces, used);
		}
		if (edge_eq(t, t2, 1, 2))
		{
			fprintf(stderr, "%d.2 -> %d\n", start, j);
			recurse(faces, j, num_faces, used);
		}
	}

	// no success
	return 0;
}



int main(void)
{
	const size_t max_len = 1 << 20;
	uint8_t * const buf = calloc(max_len, 1);

	ssize_t rc = read(0, buf, max_len);
	if (rc == -1)
		return EXIT_FAILURE;

	const stl_header_t * const hdr = (const void*) buf;
	const stl_face_t * const faces = (const void*)(hdr+1);
	const int num_triangles = hdr->num_triangles;

	fprintf(stderr, "header: '%s'\n", hdr->header);
	fprintf(stderr, "num: %d\n", num_triangles);

	int * const used = calloc(num_triangles, sizeof(*used));

	recurse(faces, 0, num_triangles, used);

#if 0
	// worst case -- all separate polygons
	poly_t * const polys = calloc(num_triangles, sizeof(*polys));
	v3_t * const vertices = calloc(num_triangles*3, sizeof(*vertices));
	int num_vertices = 0;

	for(int i = 0 ; i < num_triangles ; i++)
	{
		// see if this matches an existing vertex
		const stl_face_t * const t = &faces[i];
		poly_t * const p = &polys[i];
		p->n = 3;
		p->p[0] = p->p[1] = p->p[2] = -1;

		for (int j = 0 ; j < num_vertices ; j++)
		{
			const v3_t * const v = &vertices[j];
			if (p->p[0] == -1 && v3_eq(v, &t->p0))
				p->p[1] = j;
			if (p->p[1] == -1 && v3_eq(v, &t->p1))
				p->p[1] = j;
			if (p->p[2] == -1 && v3_eq(v, &t->p2))
				p->p[2] = j;

			// check if we've found all of them
			if (p->p[0] >= 0 && p->p[1] >= 0 && p->p[2] >= 0)
				break;
		}

		// create new points if we haven't found matches
		if (p->p[0] < 0)
		{
			p->p[0] = num_vertices;
			vertices[num_vertices++] = t->p0;
		}
		if (p->p[1] < 0)
		{
			p->p[1] = num_vertices;
			vertices[num_vertices++] = t->p1;
		}
		if (p->p[3] < 0)
		{
			p->p[3] = num_vertices;
			vertices[num_vertices++] = t->p2;
		}
	}

	fprintf(stderr, "unique vertices: %d\n", num_vertices);
#endif

	
	return 0;
}