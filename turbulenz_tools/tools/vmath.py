#!/usr/bin/python
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Collection of math functions.
"""

import math

__version__ = '1.0.0'

# pylint: disable=C0302,C0111,R0914,R0913
# C0111 - Missing docstring
# C0302 - Too many lines in module
# R0914 - Too many local variables
# R0913 - Too many arguments

#######################################################################################################################

PRECISION = 1e-6

def tidy(m, tolerance=PRECISION):
    def __tidy(x, tolerance):
        if abs(x) < tolerance:
            return 0
        return x
    return tuple([__tidy(x, tolerance) for x in m])

#######################################################################################################################

def select(m, a, b):
    if m:
        return a
    return b

def rcp(a):
    if (a != 0.0):
        return 1 / a
    return 0.0

def iszero(a, tolerance=PRECISION):
    return (abs(a) < tolerance)


#######################################################################################################################

def v2equal(a, b, tolerance=PRECISION):
    (a0, a1) = a
    (b0, b1) = b
    return (abs(a0 - b0) <= tolerance and abs(a1 - b1) <= tolerance)

#######################################################################################################################

V3ZERO = (0.0, 0.0, 0.0)
V3HALF = (0.5, 0.5, 0.5)
V3ONE = (1.0, 1.0, 1.0)
V3TWO = (2.0, 2.0, 2.0)

V3XAXIS = (1.0, 0.0, 0.0)
V3YAXIS = (0.0, 1.0, 0.0)
V3ZAXIS = (0.0, 0.0, 1.0)

#######################################################################################################################

def v3create(a, b, c):
    return (a, b, c)

def v3neg(a):
    (a0, a1, a2) = a
    return (-a0, -a1, -a2)

def v3add(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 + b0), (a1 + b1), (a2 + b2))

def v3add3(a, b, c):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    return ((a0 + b0 + c0), (a1 + b1 + c1), (a2 + b2 + c2))

def v3add4(a, b, c, d):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    (d0, d1, d2) = d
    return ((a0 + b0 + c0 + d0), (a1 + b1 + c1 + d1), (a2 + b2 + c2 + d2))

def v3sub(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 - b0), (a1 - b1), (a2 - b2))

def v3mul(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 * b0), (a1 * b1), (a2 * b2))

def v3madd(a, b, c):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    return (((a0 * b0) + c0), ((a1 * b1) + c1), ((a2 * b2) + c2))

def v3dot(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 * b0) + (a1 * b1) + (a2 * b2))

def v3cross(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a1 * b2) - (a2 * b1), (a2 * b0) - (a0 * b2), (a0 * b1) - (a1 * b0))

def v3lengthsq(a):
    (a0, a1, a2) = a
    return ((a0 * a0) + (a1 * a1) + (a2 * a2))

def v3length(a):
    (a0, a1, a2) = a
    return math.sqrt((a0 * a0) + (a1 * a1) + (a2 * a2))

def v3distancesq(a, b):
    return v3lengthsq(v3sub(a, b))

def v3recp(a):
    (a0, a1, a2) = a
    return (rcp(a0), rcp(a1), rcp(a2))

def v3normalize(a):
    (a0, a1, a2) = a
    lsq = ((a0 * a0) + (a1 * a1) + (a2 * a2))
    if (lsq > 0.0):
        lr = 1.0 / math.sqrt(lsq)
        return ((a0 * lr), (a1 * lr), (a2 * lr))
    return V3ZERO

def v3abs(a):
    (a0, a1, a2) = a
    return (abs(a0), abs(a1), abs(a2))

def v3max(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return (max(a0, b0), max(a1, b1), max(a2, b2))

def v3max3(a, b, c):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    return (max(max(a0, b0), c0), max(max(a1, b1), c1), max(max(a2, b2), c2))

def v3max4(a, b, c, d):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    (d0, d1, d2) = d
    return (max(max(a0, b0), max(c0, d0)),
            max(max(a1, b1), max(c1, d1)),
            max(max(a2, b2), max(c2, d2)))

def v3min(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return (min(a0, b0), min(a1, b1), min(a2, b2))

def v3min3(a, b, c):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    return (min(min(a0, b0), c0), min(min(a1, b1), c1), min(min(a2, b2), c2))

def v3min4(a, b, c, d):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    (d0, d1, d2) = d
    return (min(min(a0, b0), min(c0, d0)),
            min(min(a1, b1), min(c1, d1)),
            min(min(a2, b2), min(c2, d2)))

def v3equal(a, b, tolerance=PRECISION):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return (abs(a0 - b0) <= tolerance and abs(a1 - b1) <= tolerance and abs(a2 - b2) <= tolerance)

def v3mulm33(a, m):
    (a0, a1, a2) = a
    return v3add3( v3muls(m33right(m), a0),
                   v3muls(m33up(m),    a1),
                   v3muls(m33at(m),    a2) )

def v3mequal(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((abs(a0 - b0) <= PRECISION), (abs(a1 - b1) <= PRECISION), (abs(a2 - b2) <= PRECISION))

def v3mless(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 < b0), (a1 < b1), (a2 < b2))

def v3mgreater(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 > b0), (a1 > b1), (a2 > b2))

def v3mgreatereq(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 >= b0), (a1 >= b1), (a2 >= b2))

def v3mnot(a):
    (a0, a1, a2) = a
    return (not a0, not a1, not a2)

def v3mor(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 or b0), (a1 or b1), (a2 or b2))

def v3mand(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 and b0), (a1 and b1), (a2 and b2))

def v3select(m, a, b):
    (m0, m1, m2) = m
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return (select(m0, a0, b0), select(m1, a1, b1), select(m2, a2, b2))

def v3creates(a):
    return (a, a, a)

def v3maxs(a, b):
    (a0, a1, a2) = a
    return (max(a0, b), max(a1, b), max(a2, b))

def v3mins(a, b):
    (a0, a1, a2) = a
    return (min(a0, b), min(a1, b), min(a2, b))

def v3adds(a, b):
    (a0, a1, a2) = a
    return ((a0 + b), (a1 + b), (a2 + b))

def v3subs(a, b):
    (a0, a1, a2) = a
    return ((a0 - b), (a1 - b), (a2 - b))

def v3muls(a, b):
    (a0, a1, a2) = a
    if (b == 0):
        return V3ZERO
    return ((a0 * b), (a1 * b), (a2 * b))

def v3equals(a, b):
    (a0, a1, a2) = a
    return (abs(a0 - b) <= PRECISION and abs(a1 - b) <= PRECISION and abs(a2 - b) <= PRECISION)

def v3equalsm(a, b):
    (a0, a1, a2) = a
    return ((abs(a0 - b) <= PRECISION), (abs(a1 - b) <= PRECISION), (abs(a2 - b) <= PRECISION))

def v3lesssm(a, b):
    (a0, a1, a2) = a
    return ((a0 > b), (a1 > b), (a2 > b))

def v3greatersm(a, b):
    (a0, a1, a2) = a
    return ((a0 > b), (a1 > b), (a2 > b))

def v3greatereqsm(a, b):
    (a0, a1, a2) = a
    return ((a0 >= b), (a1 >= b), (a2 >= b))

def v3lerp(a, b, t):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 + (b0 - a0) * t), (a1 + (b1 - a1) * t), (a2 + (b2 - a2) * t))

def v3is_zero(a, tolerance=PRECISION):
    return (abs(v3lengthsq(a)) < (tolerance * tolerance))

def v3is_similar(a, b, tolerance=PRECISION):
    return (v3dot(a, b) > tolerance)

def v3is_within_tolerance(a, b, tolerance):
    """The tolerance must be defined as the square of the cosine angle tolerated. Returns True is 'a' is zero."""
    if v3is_zero(a): # Should we test b is_zero as well?
        return True
    dot = v3dot(a, b)
    if dot < 0:
        return False
    if (dot * dot) < (v3lengthsq(a) * v3lengthsq(b) * tolerance):
        return False
    return True

def v3unitcube_clamp(a):
    (a0, a1, a2) = a
    if (a0 > 1.0):
        a0 = 1.0
    elif (a0 < -1.0):
        a0 = -1.0
    if (a1 > 1.0):
        a1 = 1.0
    elif (a1 < -1.0):
        a1 = -1.0
    if (a2 > 1.0):
        a2 = 1.0
    elif (a2 < -1.0):
        a2 = -.10
    return (a0, a1, a2)

#######################################################################################################################

def v3s_min_max(points):
    (min_x, min_y, min_z) = points[0]
    (max_x, max_y, max_z) = points[0]
    for (x, y, z) in points:
        min_x = min(x, min_x)
        min_y = min(y, min_y)
        min_z = min(z, min_z)
        max_x = max(x, max_x)
        max_y = max(y, max_y)
        max_z = max(z, max_z)
    return ((min_x, min_y, min_z), (max_x, max_y, max_z))

#######################################################################################################################

V4ZERO = (0.0, 0.0, 0.0, 0.0)
V4HALF = (0.5, 0.5, 0.5, 0.5)
V4ONE  = (1.0, 1.0, 1.0, 1.0)
V4TWO  = (2.0, 2.0, 2.0, 2.0)

#######################################################################################################################

def v4create(a, b, c, d):
    return (a, b, c, d)

def v4neg(a):
    (a0, a1, a2, a3) = a
    return (-a0, -a1, -a2, -a3)

def v4add(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 + b0), (a1 + b1), (a2 + b2), (a3 + b3))

def v4add3(a, b, c):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    return ((a0 + b0 + c0), (a1 + b1 + c1), (a2 + b2 + c2), (a3 + b3 + c3))

def v4add4(a, b, c, d):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    (d0, d1, d2, d3) = d
    return ((a0 + b0 + c0 + d0), (a1 + b1 + c1 + d1), (a2 + b2 + c2 + d2), (a3 + b3 + c3 + d3))

def v4sub(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 - b0), (a1 - b1), (a2 - b2), (a3 - b3))

def v4mul(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 * b0), (a1 * b1), (a2 * b2), (a3 * b3))

def v4madd(a, b, c):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    return (((a0 * b0) + c0), ((a1 * b1) + c1), ((a2 * b2) + c2), ((a3 * b3) + c3))

def v4dot(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 * b0) + (a1 * b1) + (a2 * b2) + (a3 * b3))

def v4lengthsq(a):
    (a0, a1, a2, a3) = a
    return ((a0 * a0) + (a1 * a1) + (a2 * a2) + (a3 * a3))

def v4length(a):
    (a0, a1, a2, a3) = a
    return math.sqrt((a0 * a0) + (a1 * a1) + (a2 * a2) + (a3 * a3))

def v4recp(a):
    (a0, a1, a2, a3) = a
    return (rcp(a0), rcp(a1), rcp(a2), rcp(a3))

def v4normalize(a):
    (a0, a1, a2, a3) = a
    lsq = ((a0 * a0) + (a1 * a1) + (a2 * a2) + (a3 * a3))
    if (lsq > 0.0):
        lr = 1.0 / math.sqrt(lsq)
        return ((a0 * lr), (a1 * lr), (a2 * lr), (a3 * lr))
    return V4ZERO

def v4abs(a):
    (a0, a1, a2, a3) = a
    return (abs(a0), abs(a1), abs(a2), abs(a3))

def v4max(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return (max(a0, b0), max(a1, b1), max(a2, b2), max(a3, b3))

def v4max3(a, b, c):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    return (max(max(a0, b0), c0),
            max(max(a1, b1), c1),
            max(max(a2, b2), c2),
            max(max(a3, b3), c3))

def v4max4(a, b, c, d):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    (d0, d1, d2, d3) = d
    return (max(max(a0, b0), max(c0, d0)),
            max(max(a1, b1), max(c1, d1)),
            max(max(a2, b2), max(c2, d2)),
            max(max(a3, b3), max(c3, d3)))

def v4min(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return (min(a0, b0), min(a1, b1), min(a2, b2), min(a3, b3))

def v4min3(a, b, c):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    return (min(min(a0, b0), c0),
            min(min(a1, b1), c1),
            min(min(a2, b2), c2),
            min(min(a3, b3), c3))

def v4min4(a, b, c, d):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    (d0, d1, d2, d3) = d
    return (min(min(a0, b0), min(c0, d0)),
            min(min(a1, b1), min(c1, d1)),
            min(min(a2, b2), min(c2, d2)),
            min(min(a3, b3), min(c3, d3)))

def v4equal(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return (abs(a0 - b0) <= PRECISION and
            abs(a1 - b1) <= PRECISION and
            abs(a2 - b2) <= PRECISION and
            abs(a3 - b3) <= PRECISION)

def v4mulm44(v, m):
    (v0, v1, v2, v3) = v
    return v4add4(v4muls(m44right(m), v0),
                  v4muls(m44up(m),    v1),
                  v4muls(m44at(m),    v2),
                  v4muls(m44pos(m),   v3))

def v4mequal(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((abs(a0 - b0) <= PRECISION),
            (abs(a1 - b1) <= PRECISION),
            (abs(a2 - b2) <= PRECISION),
            (abs(a3 - b3) <= PRECISION))

def v4mless(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 < b0), (a1 < b1), (a2 < b2), (a3 < b3))

def v4mgreater(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 > b0), (a1 > b1), (a2 > b2), (a3 > b3))

def v4mgreatereq(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 >= b0), (a1 >= b1), (a2 >= b2), (a3 >= b3))

def v4mnot(a):
    (a0, a1, a2, a3) = a
    return ( not a0, not a1, not a2, not a3)

def v4mor(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 or b0), (a1 or b1), (a2 or b2), (a3 or b3))

def v4mand(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 and b0), (a1 and b1), (a2 and b2), (a3 and b3))

def v4many(m):
    (m0, m1, m2, m3) = m
    return (m0 or m1 or m2 or m3)

def v4mall(m):
    (m0, m1, m2, m3) = m
    return (m0 and m1 and m2 and m3)

def v4select(m, a, b):
    (m0, m1, m2, m3) = m
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return (select(m0, a0, b0), select(m1, a1, b1), select(m2, a2, b2), select(m3, a3, b3))

def v4creates(a):
    return (a, a, a, a)

def v4maxs(a, b):
    (a0, a1, a2, a3) = a
    return (max(a0, b), max(a1, b), max(a2, b), max(a3, b))

def v4mins(a, b):
    (a0, a1, a2, a3) = a
    return (min(a0, b), min(a1, b), min(a2, b), min(a3, b))

def v4adds(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 + b), (a1 + b), (a2 + b), (a3 + b))

def v4subs(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 - b), (a1 - b), (a2 - b), (a3 - b))

def v4muls(a, b):
    if (b == 0):
        return V4ZERO
    else:
        (a0, a1, a2, a3) = a
        return ((a0 * b), (a1 * b), (a2 * b), (a3 * b))

def v4equals(a, b):
    (a0, a1, a2, a3) = a
    return (abs(a0 - b) <= PRECISION and
            abs(a1 - b) <= PRECISION and
            abs(a2 - b) <= PRECISION and
            abs(a3 - b) <= PRECISION)

def v4equalsm(a, b):
    (a0, a1, a2, a3) = a
    return ((abs(a0 - b) <= PRECISION),
            (abs(a1 - b) <= PRECISION),
            (abs(a2 - b) <= PRECISION),
            (abs(a3 - b) <= PRECISION))

def v4lesssm(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 < b), (a1 < b), (a2 < b), (a3 < b))

def v4greatersm(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 > b), (a1 > b), (a2 > b), (a3 > b))

def v4greatereqsm(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 >= b), (a1 >= b), (a2 >= b), (a3 >= b))

def v4lerp(a, b, t):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 + (b0 - a0) * t), (a1 + (b1 - a1) * t), (a2 + (b2 - a2) * t), (a3 + (b3 - a3) * t))

#######################################################################################################################

M33IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
M43IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
M44IDENTITY = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)

#######################################################################################################################

def m33(r0, r1, r2, u0, u1, u2, a0, a1, a2):
    return (r0, r1, r2, u0, u1, u2, a0, a1, a2)

def m33create(r, u, a):
    (r0, r1, r2) = r
    (u0, u1, u2) = u
    (a0, a1, a2) = a
    return (r0, r1, r2, u0, u1, u2, a0, a1, a2)

def m33is_identity(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    return (m0 == 1 and m1 == 0 and m2 == 0 and
            m3 == 0 and m4 == 1 and m5 == 0 and
            m6 == 0 and m7 == 0 and m8 == 1)

def m33from_axis_rotation(axis, angle):
    s = math.sin(angle)
    c = math.cos(angle)
    t = 1.0 - c
    (axisX, axisY, axisZ) = axis
    tx = t * axisX
    ty = t * axisY
    tz = t * axisZ
    sx = s * axisX
    sy = s * axisY
    sz = s * axisZ

    return (tx * axisX + c, tx * axisY + sz, tx * axisZ - sy,
            ty * axisX - sz, ty * axisY + c, ty * axisZ + sx,
            tz * axisX + sy, tz * axisY - sx, tz * axisZ + c)

def m33right(m):
    return m[:3]

def m33up(m):
    return m[3:6]

def m33at(m):
    return m[6:]

def m33setright(m, v):
    (_, _, _, m3, m4, m5, m6, m7, m8) = m
    (v0, v1, v2) = v
    return (v0, v1, v2, m3, m4, m5, m6, m7, m8)

def m33setup(m, v):
    (m0, m1, m2, _, _, _, m6, m7, m8) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, v0, v1, v2, m6, m7, m8)

def m33setat(m, v):
    (m0, m1, m2, m3, m4, m5, _, _, _) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, m3, m4, m5, v0, v1, v2)

def m33transpose(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    return (m0, m3, m6, m1, m4, m7, m2, m5, m8)

def m33determinant(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    return (m0 * (m4 * m8 - m5 * m7) + m1 * (m5 * m6 - m3 * m8) + m2 * (m3 * m7 - m4 * m6))

def m33inverse(m):
    det = m33determinant(m)
    if (det == 0.0):
        return ( )
    else:
        (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
        detrecp = 1.0 / det
        return (((m4 * m8 + m5 * (-m7)) * detrecp),
                ((m7 * m2 + m8 * (-m1)) * detrecp),
                ((m1 * m5 - m2 *   m4)  * detrecp),
                ((m5 * m6 + m3 * (-m8)) * detrecp),
                ((m8 * m0 + m6 * (-m2)) * detrecp),
                ((m3 * m2 - m0 *   m5)  * detrecp),
                ((m3 * m7 + m4 * (-m6)) * detrecp),
                ((m6 * m1 + m7 * (-m0)) * detrecp),
                ((m0 * m4 - m3 *   m1)  * detrecp))

def m33inversetranspose(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    det = (m0 * (m4 * m8 - m5 * m7) +
           m1 * (m5 * m6 - m3 * m8) +
           m2 * (m3 * m7 - m4 * m6))
    if (det == 0.0):
        return ( )
    else:
        detrecp = 1.0 / det
        r0 = ((m4 * m8 + m5 * (-m7)) * detrecp)
        r1 = ((m7 * m2 + m8 * (-m1)) * detrecp)
        r2 = ((m1 * m5 - m2 *   m4)  * detrecp)
        r3 = ((m5 * m6 + m3 * (-m8)) * detrecp)
        r4 = ((m8 * m0 + m6 * (-m2)) * detrecp)
        r5 = ((m3 * m2 - m0 *   m5)  * detrecp)
        r6 = ((m3 * m7 + m4 * (-m6)) * detrecp)
        r7 = ((m6 * m1 + m7 * (-m0)) * detrecp)
        r8 = ((m0 * m4 - m3 *   m1)  * detrecp)
        return (r0, r3, r6,
                r1, r4, r7,
                r2, r5, r8)

def m33mul(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8) = b
    return ( (b0 * a0 + b3 * a1 + b6 * a2),
             (b1 * a0 + b4 * a1 + b7 * a2),
             (b2 * a0 + b5 * a1 + b8 * a2),

             (b0 * a3 + b3 * a4 + b6 * a5),
             (b1 * a3 + b4 * a4 + b7 * a5),
             (b2 * a3 + b5 * a4 + b8 * a5),

             (b0 * a6 + b3 * a7 + b6 * a8),
             (b1 * a6 + b4 * a7 + b7 * a8),
             (b2 * a6 + b5 * a7 + b8 * a8) )

def m33mulm43(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11) = b
    return ( (b0 * a0 + b3 * a1 + b6 * a2),
             (b1 * a0 + b4 * a1 + b7 * a2),
             (b2 * a0 + b5 * a1 + b8 * a2),

             (b0 * a3 + b3 * a4 + b6 * a5),
             (b1 * a3 + b4 * a4 + b7 * a5),
             (b2 * a3 + b5 * a4 + b8 * a5),

             (b0 * a6 + b3 * a7 + b6 * a8),
             (b1 * a6 + b4 * a7 + b7 * a8),
             (b2 * a6 + b5 * a7 + b8 * a8),

             b9, b10, b11 )

def m33mulm44(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13, b14, b15) = b
    return ( (b0 * a0 + b4 * a1 + b8  * a2),
             (b1 * a0 + b5 * a1 + b9  * a2),
             (b2 * a0 + b6 * a1 + b10 * a2),
             (b3 * a0 + b7 * a1 + b11 * a2),

             (b0 * a3 + b4 * a4 + b8  * a5),
             (b1 * a3 + b5 * a4 + b9  * a5),
             (b2 * a3 + b6 * a4 + b10 * a5),
             (b3 * a3 + b7 * a4 + b11 * a5),

             (b0 * a6 + b4 * a7 + b8  * a8),
             (b1 * a6 + b5 * a7 + b9  * a8),
             (b2 * a6 + b6 * a7 + b10 * a8),
             (b3 * a6 + b7 * a7 + b11 * a8),

             b12, b13, b14, b15 )

def m33adds(m, s):
    return tuple([ m[n] + s for n in range(9) ])

def m33subs(m, s):
    return tuple([ m[n] - s for n in range(9) ])

def m33muls(m, s):
    return tuple([ m[n] * s for n in range(9) ])

#######################################################################################################################

def m43(r0, r1, r2, u0, u1, u2, a0, a1, a2, p0, p1, p2):
    return (r0, r1, r2, u0, u1, u2, a0, a1, a2, p0, p1, p2)

def m43create(r, u, a, p):
    (r0, r1, r2) = r
    (u0, u1, u2) = u
    (a0, a1, a2) = a
    (p0, p1, p2) = p
    return (r0, r1, r2, u0, u1, u2, a0, a1, a2, p0, p1, p2)

def m43from_m44(m):
    return m43create(m[0:3], m[4:7], m[8:11], m[12:15])

def m43is_identity(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    return (m0 == 1 and m1 == 0 and m2 == 0 and
            m3 == 0 and m4 == 1 and m5 == 0 and
            m6 == 0 and m7 == 0 and m8 == 1 and
            m9 == 0 and m10 == 0 and m11 == 0)

def m43from_axis_rotation(axis, angle):
    s = math.sin(angle)
    c = math.cos(angle)
    t = 1.0 - c
    (axisX, axisY, axisZ) = axis
    tx = t * axisX
    ty = t * axisY
    tz = t * axisZ
    sx = s * axisX
    sy = s * axisY
    sz = s * axisZ

    return (tx * axisX + c,
            tx * axisY + sz,
            tx * axisZ - sy,
            ty * axisX - sz,
            ty * axisY + c,
            ty * axisZ + sx,
            tz * axisX + sy,
            tz * axisY - sx,
            tz * axisZ + c,
            0.0,
            0.0,
            0.0)

def m43right(m):
    return m[:3]

def m43up(m):
    return m[3:6]

def m43at(m):
    return m[6:9]

def m43pos(m):
    return m[9:]

def m43setright(m, v):
    (_, _, _, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    (v0, v1, v2) = v
    return (v0, v1, v2, m3, m4, m5, m6, m7, m8, m9, m10, m11)

def m43setup(m, v):
    (m0, m1, m2, _, _, _, m6, m7, m8, m9, m10, m11) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, v0, v1, v2, m6, m7, m8, m9, m10, m11)

def m43setat(m, v):
    (m0, m1, m2, m3, m4, m5, _, _, _, m9, m10, m11) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, m3, m4, m5, v0, v1, v2, m9, m10, m11)

def m43setpos(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, _, _, _) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, m8, v0, v1, v2)

def m43translate(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9 + v0, m10 + v1, m11 + v2)

def m43inverse_orthonormal(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, px, py, pz) = m
    return ( m0, m3, m6,
             m1, m4, m7,
             m2, m5, m8,
             -((px * m0) + (py * m1) + (pz * m2)),
             -((px * m3) + (py * m4) + (pz * m5)),
             -((px * m6) + (py * m7) + (pz * m8)) )

def m43ortho_normalize(m):
    right = m43right(m)
    up    = m43up(m)
    at    = m43at(m)
    pos   = m43pos(m)

    innerX = v3length(right)
    innerY = v3length(up)
    innerZ = v3length(at)

    right = v3normalize(right)
    up    = v3normalize(up)
    at    = v3normalize(at)

    if (innerX > 0.0):
        if (innerY > 0.0):
            if (innerZ > 0.0):
                outerX = abs(v3dot(up, at))
                outerY = abs(v3dot(at, right))
                outerZ = abs(v3dot(right, up))
                if (outerX < outerY):
                    if (outerX < outerZ):
                        vpU = up
                        vpV = at
                        vpW = right
                    else:
                        vpU = right
                        vpV = up
                        vpW = at
                else:
                    if (outerY < outerZ):
                        vpU = at
                        vpV = right
                        vpW = up
                    else:
                        vpU = right
                        vpV = up
                        vpW = at
            else:
                vpU = right
                vpV = up
                vpW = at
        else:
            vpU = at
            vpV = right
            vpW = up
    else:
        vpU = up
        vpV = at
        vpW = right
    vpW = v3normalize(v3cross(vpV, vpU))
    vpV = v3normalize(v3cross(vpU, vpW))
    return m43create(right, up, at, pos)

def m43determinant(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, _m9, _m10, _m11) = m
    return (m0 * (m4 * m8 - m5 * m7) +
            m1 * (m5 * m6 - m3 * m8) +
            m2 * (m3 * m7 - m4 * m6))

def m43inverse(m):
    det = m43determinant(m)
    if (det == 0.0):
        return ( )
    else:
        (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
        detrecp = 1.0 / det
        return (((m4 * m8 + m5 * (-m7)) * detrecp),
                ((m7 * m2 + m8 * (-m1)) * detrecp),
                ((m1 * m5 - m2 *   m4)  * detrecp),
                ((m5 * m6 + m3 * (-m8)) * detrecp),
                ((m8 * m0 + m6 * (-m2)) * detrecp),
                ((m3 * m2 - m0 *   m5)  * detrecp),
                ((m3 * m7 + m4 * (-m6)) * detrecp),
                ((m6 * m1 + m7 * (-m0)) * detrecp),
                ((m0 * m4 - m3 *   m1)  * detrecp),
                ((m3 * (m10 * m8  - m7 * m11) + m4  * (m6 * m11 - m9 * m8) + m5  * (m9 * m7 - m6 * m10)) * detrecp),
                ((m6 * (m2  * m10 - m1 * m11) + m7  * (m0 * m11 - m9 * m2) + m8  * (m9 * m1 - m0 * m10)) * detrecp),
                ((m9 * (m2  * m4  - m1 * m5)  + m10 * (m0 * m5  - m3 * m2) + m11 * (m3 * m1 - m0 * m4))  * detrecp))

def m43transformn(m, v):
    (v0, v1, v2) = v
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, _m9, _m10, _m11) = m
    return ( (m0 * v0 + m3 * v1 + m6 * v2),
             (m1 * v0 + m4 * v1 + m7 * v2),
             (m2 * v0 + m5 * v1 + m8 * v2) )

def m43transformp(m, v):
    (v0, v1, v2) = v
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    return ( (m0 * v0 + m3 * v1 + m6 * v2 + m9),
             (m1 * v0 + m4 * v1 + m7 * v2 + m10),
             (m2 * v0 + m5 * v1 + m8 * v2 + m11) )

def m43mul(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11) = b
    return ( (b0 * a0 + b3 * a1 + b6 * a2),
             (b1 * a0 + b4 * a1 + b7 * a2),
             (b2 * a0 + b5 * a1 + b8 * a2),
             (b0 * a3 + b3 * a4 + b6 * a5),
             (b1 * a3 + b4 * a4 + b7 * a5),
             (b2 * a3 + b5 * a4 + b8 * a5),
             (b0 * a6 + b3 * a7 + b6 * a8),
             (b1 * a6 + b4 * a7 + b7 * a8),
             (b2 * a6 + b5 * a7 + b8 * a8),
             (b0 * a9 + b3 * a10 + b6 * a11 + b9),
             (b1 * a9 + b4 * a10 + b7 * a11 + b10),
             (b2 * a9 + b5 * a10 + b8 * a11 + b11) )

def m43mulm44(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13, b14, b15) = b
    return ( (b0 * a0 + b4 * a1 + b8  * a2),
             (b1 * a0 + b5 * a1 + b9  * a2),
             (b2 * a0 + b6 * a1 + b10 * a2),
             (b3 * a0 + b7 * a1 + b11 * a2),
             (b0 * a3 + b4 * a4 + b8  * a5),
             (b1 * a3 + b5 * a4 + b9  * a5),
             (b2 * a3 + b6 * a4 + b10 * a5),
             (b3 * a3 + b7 * a4 + b11 * a5),
             (b0 * a6 + b4 * a7 + b8  * a8),
             (b1 * a6 + b5 * a7 + b9  * a8),
             (b2 * a6 + b6 * a7 + b10 * a8),
             (b3 * a6 + b7 * a7 + b11 * a8),
             (b0 * a9 + b4 * a10 + b8  * a11 + b12),
             (b1 * a9 + b5 * a10 + b9  * a11 + b13),
             (b2 * a9 + b6 * a10 + b10 * a11 + b14),
             (b3 * a9 + b7 * a10 + b11 * a11 + b15) )

def m43transpose(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    return (m0, m3, m6, m9,
            m1, m4, m7, m10,
            m2, m5, m8, m11)

def m43adds(m, s):
    return tuple([ m[n] + s for n in range(12) ])

def m43subs(m, s):
    return tuple([ m[n] - s for n in range(12) ])

def m43muls(m, s):
    return tuple([ m[n] * s for n in range(12) ])

#######################################################################################################################

def m44(r0, r1, r2, r3,
        u0, u1, u2, u3,
        a0, a1, a2, a3,
        p0, p1, p2, p3):
    return (r0, r1, r2, r3,
            u0, u1, u2, u3,
            a0, a1, a2, a3,
            p0, p1, p2, p3)

def m44create(r, u, a, p):
    (r0, r1, r2, r3) = r
    (u0, u1, u2, u3) = u
    (a0, a1, a2, a3) = a
    (p0, p1, p2, p3) = p
    return (r0, r1, r2, r3,
            u0, u1, u2, u3,
            a0, a1, a2, a3,
            p0, p1, p2, p3)

def m44is_identity(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = m
    return (m0 == 1 and m1 == 0 and m2 == 0 and m3 == 0 and
            m4 == 0 and m5 == 1 and m6 == 0 and m7 == 0 and
            m8 == 0 and m9 == 0 and m10 == 1 and m11 == 0 and
            m12 == 0 and m13 == 0 and m14 == 0 and m15 == 1)

def m44right(m):
    return m[:4]

def m44up(m):
    return m[4:8]

def m44at(m):
    return m[8:12]

def m44pos(m):
    return m[12:]

def m44setright(m, v):
    (_, _, _, _, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = m
    (v0, v1, v2, v3) = v
    return (v0, v1, v2, v3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15)

def m44setup(m, v):
    (m0, m1, m2, m3, _, _, _, _, m8, m9, m10, m11, m12, m13, m14, m15) = m
    (v0, v1, v2, v3) = v
    return (m0, m1, m2, m3, v0, v1, v2, v3, m8, m9, m10, m11, m12, m13, m14, m15)

def m44setat(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, _, _, _, _, m12, m13, m14, m15) = m
    (v0, v1, v2, v3) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, v0, v1, v2, v3, m12, m13, m14, m15)

def m44setpos(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, _, _, _, _) = m
    (v0, v1, v2, v3) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, v0, v1, v2, v3)

def m44translate(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = m
    (v0, v1, v2, v3) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12 + v0, m13 + v1, m14 + v2, m15 + v3)

def m44transformn(m, v):
    (v0, v1, v2) = v
    return v4add3(v4muls(m44right(m), v0),
                  v4muls(m44up(m),    v1),
                  v4muls(m44at(m),    v2))

def m44transformp(m, v):
    (v0, v1, v2) = v
    return v4add4(v4muls(m44right(m), v0),
                  v4muls(m44up(m),    v1),
                  v4muls(m44at(m),    v2),
                  m44pos(m))

def m44mul(a, b):
    return m44create(v4mulm44(m44right(a), b),
                     v4mulm44(m44up(a),    b),
                     v4mulm44(m44at(a),    b),
                     v4mulm44(m44pos(a),   b))

def m44transpose(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = m
    return (m0, m4, m8,  m12,
            m1, m5, m9,  m13,
            m2, m6, m10, m14,
            m3, m7, m11, m15)

def m44adds(m, s):
    return tuple([ m[n] + s for n in range(16) ])

def m44subs(m, s):
    return tuple([ m[n] - s for n in range(16) ])

def m44muls(m, s):
    return tuple([ m[n] * s for n in range(16) ])

#######################################################################################################################

def is_visible_box(center, halfDimensions, vpm):
    (c0, c1, c2) = center
    (h0, h1, h2) = halfDimensions
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = (m0  * h0)
    i1 = (m1  * h0)
    i2 = (m2  * h0)
    i3 = (m3  * h0)
    j0 = (m4  * h1)
    j1 = (m5  * h1)
    j2 = (m6  * h1)
    j3 = (m7  * h1)
    k0 = (m8  * h2)
    k1 = (m9  * h2)
    k2 = (m10 * h2)
    k3 = (m11 * h2)

    t0 = (m0 * c0 + m4 * c1 + m8  * c2 + m12)
    t1 = (m1 * c0 + m5 * c1 + m9  * c2 + m13)
    t2 = (m2 * c0 + m6 * c1 + m10 * c2 + m14)
    t3 = (m3 * c0 + m7 * c1 + m11 * c2 + m15)

    return not (((t0 - t3) >  (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < -(abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < -(abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < -(abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < -(abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def is_visible_box_origin(halfDimensions, vpm):
    (h0, h1, h2) = halfDimensions
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = (m0  * h0)
    i1 = (m1  * h0)
    i2 = (m2  * h0)
    i3 = (m3  * h0)
    j0 = (m4  * h1)
    j1 = (m5  * h1)
    j2 = (m6  * h1)
    j3 = (m7  * h1)
    k0 = (m8  * h2)
    k1 = (m9  * h2)
    k2 = (m10 * h2)
    k3 = (m11 * h2)
    t0 = m12
    t1 = m13
    t2 = m14
    t3 = m15

    return not (((t0 - t3) >  (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < -(abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < -(abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < -(abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < -(abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def is_visible_sphere(center, radius, vpm):
    (c0, c1, c2) = center
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = m0
    i1 = m1
    i2 = m2
    i3 = m3
    j0 = m4
    j1 = m5
    j2 = m6
    j3 = m7
    k0 = m8
    k1 = m9
    k2 = m10
    k3 = m11

    t0 = (m0 * c0 + m4 * c1 + m8  * c2 + m12)
    t1 = (m1 * c0 + m5 * c1 + m9  * c2 + m13)
    t2 = (m2 * c0 + m6 * c1 + m10 * c2 + m14)
    t3 = (m3 * c0 + m7 * c1 + m11 * c2 + m15)

    nradius = -radius

    return not (((t0 - t3) >  radius * (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < nradius * (abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  radius * (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < nradius * (abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  radius * (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < nradius * (abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  radius * (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < nradius * (abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def is_visible_sphere_origin(radius, vpm):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = m0
    i1 = m1
    i2 = m2
    i3 = m3
    j0 = m4
    j1 = m5
    j2 = m6
    j3 = m7
    k0 = m8
    k1 = m9
    k2 = m10
    k3 = m11
    t0 = m12
    t1 = m13
    t2 = m14
    t3 = m15

    nradius = -radius

    return not (((t0 - t3) >  radius * (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < nradius * (abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  radius * (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < nradius * (abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  radius * (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < nradius * (abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  radius * (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < nradius * (abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def is_visible_sphere_unit(vpm):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = m0
    i1 = m1
    i2 = m2
    i3 = m3
    j0 = m4
    j1 = m5
    j2 = m6
    j3 = m7
    k0 = m8
    k1 = m9
    k2 = m10
    k3 = m11
    t0 = m12
    t1 = m13
    t2 = m14
    t3 = m15

    return not (((t0 - t3) >  (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < -(abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < -(abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < -(abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < -(abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def transform_box(center, halfExtents, matrix):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = matrix
    (c0, c1, c2) = center
    (h0, h1, h2) = halfExtents

    return { center : ((m0 * c0 + m3 * c1 + m6 * c2 + m9),
                       (m1 * c0 + m4 * c1 + m7 * c2 + m10),
                       (m2 * c0 + m5 * c1 + m8 * c2 + m11)),
             halfExtents : ((abs(m0) * h0 + abs(m3) * h1 + abs(m6) * h2),
                            (abs(m1) * h0 + abs(m4) * h1 + abs(m7) * h2),
                            (abs(m2) * h0 + abs(m5) * h1 + abs(m8) * h2)) }

def plane_normalize(plane):
    (a, b, c, d) = plane
    lsq = ((a * a) + (b * b) + (c * c))
    if (lsq > 0.0):
        lr = 1.0 / math.sqrt(lsq)
        return ((a * lr), (b * lr), (c * lr), (d * lr))
    return V4ZERO

#######################################################################################################################

def quat(qx, qy, qz, qw):
    return (qx, qy, qz, qw)

def quatis_similar(q1, q2):
    # this compares for similar rotations not raw data
    (_, _, _, w1) = q1
    (_, _, _, w2) = q2
    if (w1 * w2 < 0.0):
        # quaternions in opposing hemispheres, negate one
        q1 = v4mul((-1, -1, -1, -1), q1)

    mag_sqrd = v4lengthsq(v4sub(q1, q2))
    epsilon_sqrd = (PRECISION * PRECISION)
    return mag_sqrd < epsilon_sqrd

def quatlength(q):
    return v4length(q)

def quatdot(q1, q2):
    return v4dot(q1, q2)

# Note quaternion multiplication is the opposite way around from our matrix multiplication
def quatmul(q1, q2):
    (v2, w2) = (q1[:3], q1[3])
    (v1, w1) = (q2[:3], q2[3])

    imag = v3add3(v3muls(v2, w1), v3muls(v1, w2), v3cross(v2, v1))
    real = (w1 * w2) - v3dot(v1, v2)

    (i0, i1, i2) = imag
    return (i0, i1, i2, real)

def quatnormalize(q):
    norme = math.sqrt(quatdot(q, q))

    if (norme == 0.0):
        return V4ZERO
    else:
        recip = 1.0 / norme
        return v4muls(q, recip)

def quatconjugate(q):
    (x, y, z, w) = q
    return (-x, -y, -z, w)

def quatlerp(q1, q2, t):
    if (v4dot(q1, q2) > 0.0):
        return v4add(v4muls(v4sub(q2, q1), t), q1)
    else:
        return v4add(v4muls(v4sub(q2, q1), -t), q1)

def quatslerp(q1, q2, t):
    cosom = quatdot(q1, q2)

    if (cosom < 0.0):
        q1 = v4muls(q1, -1.0)
        cosom = -cosom

    if(cosom > math.cos(math.pi / 180.0)):  # use a lerp for angles <= 1 degree
        return quatnormalize(quatlerp(q1, q2, t))

    omega = math.acos(cosom)
    sin_omega = math.sin(omega)

    q1 = v4muls(q1, math.sin((1.0-t)*omega)/sin_omega)

    return v4add(q1, v4muls(q2, math.sin(t*omega)/sin_omega))


def quatfrom_axis_rotation(axis, angle):
    omega = 0.5 * angle
    s = math.sin(omega)
    c = math.cos(omega)
    (a0, a1, a2) = axis
    q = (a0 * s, a1 * s, a2 * s, c)
    return quatnormalize(q)

def quatto_axis_rotation(q):
    angle = math.acos(q[3]) * 2.0

    sin_sqrd = 1.0 - q[3] * q[3]
    if sin_sqrd < PRECISION:
        # we can return any axis
        return ( (1.0, 0.0, 0.0), angle )
    else:
        scale = 1.0 / math.sqrt(sin_sqrd)
        axis = v3muls(q[:3], scale)
        return ( axis, angle )

def quattransformv(q, v):
    (qx, qy, qz, qw) = q
    qimaginary = (qx, qy, qz)

    s = (qw * qw) - v3dot(qimaginary, qimaginary)

    r = v3muls(v, s)

    s = v3dot(qimaginary, v)
    r = v3add(r, v3muls(qimaginary, s + s))
    r = v3add(r, v3muls(v3cross(qimaginary, v), qw + qw))
    return r

def quatto_m43(q):
    """Convert a quaternion to a matrix43."""
    (q0, q1, q2, q3) = q

    xx = 2.0 * q0 * q0
    yy = 2.0 * q1 * q1
    zz = 2.0 * q2 * q2
    xy = 2.0 * q0 * q1
    zw = 2.0 * q2 * q3
    xz = 2.0 * q0 * q2
    yw = 2.0 * q1 * q3
    yz = 2.0 * q1 * q2
    xw = 2.0 * q0 * q3

    return m43(1.0 - yy - zz, xy - zw,       xz + yw,
               xy + zw,       1.0 - xx - zz, yz - xw,
               xz - yw,       yz + xw,       1.0 - xx - yy,
               0.0,           0.0,           0.0)

def quatfrom_m33(m):
    """Convert the top of an m33 matrix into a quaternion."""
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    trace = m0 + m4 + m8 + 1
    if trace > PRECISION:
        w = math.sqrt(trace) / 2
        x = (m5 - m7) / (4*w)
        y = (m6 - m2) / (4*w)
        z = (m1 - m3) / (4*w)
    else:
        if ((m0 > m4) and (m0 > m8)):
            s = math.sqrt( 1.0 + m0 - m4 - m8 ) * 2 # S=4*qx
            w = (m5 - m7) / s
            x = 0.25 * s
            y = (m3 + m1) / s
            z = (m6 + m2) / s
        elif (m4 > m8):
            s = math.sqrt( 1.0 + m4 - m0 - m8 ) * 2 # S=4*qy
            w = (m6 - m2) / s
            x = (m3 + m1) / s
            y = 0.25 * s
            z = (m7 + m5) / s
        else:
            s = math.sqrt( 1.0 + m8 - m0 - m4 ) * 2 # S=4*qz
            w = (m1 - m3) / s
            x = (m6 + m2) / s
            y = (m7 + m5) / s
            z = 0.25 * s

    return quatnormalize((-x, -y, -z, w))

def quatfrom_m43(m):
    """ Convert the top of an m33 matrix into a quaternion."""
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, _, _, _) = m
    trace = m0 + m4 + m8 + 1
    if trace > PRECISION:
        w = math.sqrt(trace) / 2
        x = (m5 - m7) / (4*w)
        y = (m6 - m2) / (4*w)
        z = (m1 - m3) / (4*w)
    else:
        if ((m0 > m4) and (m0 > m8)):
            s = math.sqrt( 1.0 + m0 - m4 - m8 ) * 2 # S=4*qx
            w = (m5 - m7) / s
            x = 0.25 * s
            y = (m3 + m1) / s
            z = (m6 + m2) / s
        elif (m4 > m8):
            s = math.sqrt( 1.0 + m4 - m0 - m8 ) * 2 # S=4*qy
            w = (m6 - m2) / s
            x = (m3 + m1) / s
            y = 0.25 * s
            z = (m7 + m5) / s
        else:
            s = math.sqrt( 1.0 + m8 - m0 - m4 ) * 2 # S=4*qz
            w = (m1 - m3) / s
            x = (m6 + m2) / s
            y = (m7 + m5) / s
            z = 0.25 * s

    return quatnormalize((-x, -y, -z, w))

def quatpos(qx, qy, qz, qw, px, py, pz):
    return ( (qx, qy, qz, qw), (px, py, pz) )

def quatpostransformn(qp, n):
    (q, _) = qp

    return quattransformv(q, n)

def quatpostransformp(qp, p):
    (q, v) = qp

    rotated_p = quattransformv(q, p)
    return v3add(rotated_p, v)

# Note quaternion multiplication is the opposite way around from our matrix multiplication
def quatposmul(qp1, qp2):
    (q1, _) = qp1
    (q2, v2) = qp2

    qr = quatmul(q1, q2)
    pr = quatpostransformp(v2, qp1)

    return (qr, pr)

def quat_from_qx_qy_qz(qx, qy, qz):
    """Calculate the w field of a quaternion."""
    qw = 1.0 - ((qx * qx) + (qy * qy) + (qz * qz))
    if (qw < 0.0):
        qw = 0.0
    else:
        qw = -math.sqrt(qw)
    return (qx, qy, qz, qw)

#######################################################################################################################
