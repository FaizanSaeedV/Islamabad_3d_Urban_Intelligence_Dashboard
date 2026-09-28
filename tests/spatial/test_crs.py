"""CRS correctness tests - the foundation of every metric result in the app.

Verifies that EPSG:32643 (WGS 84 / UTM zone 43N) behaves as documented:
correct coordinates for a known Islamabad point, centimetre round-trips,
and planar distances that agree with WGS 84 geodesics at city scale.
"""

import math

import pytest
from pyproj import Geod, Transformer

TO_32643 = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
TO_4326 = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
GEOD = Geod(ellps="WGS84")

ISLAMABAD_CENTER = (73.0479, 33.6844)  # lon, lat


def test_known_point_projection():
    """Central Islamabad in UTM 43N - broad regression anchor."""
    x, y = TO_32643.transform(*ISLAMABAD_CENTER)
    assert 315_000 < x < 325_000
    assert 3_725_000 < y < 3_735_000


def test_round_trip_precision():
    x, y = TO_32643.transform(*ISLAMABAD_CENTER)
    lon, lat = TO_4326.transform(x, y)
    # < 1e-7 degrees ~ 1 cm on the ground - far tighter than any data here
    assert abs(lon - ISLAMABAD_CENTER[0]) < 1e-7
    assert abs(lat - ISLAMABAD_CENTER[1]) < 1e-7


@pytest.mark.parametrize("p1,p2", [
    ((73.0790, 33.6642), (73.0561, 33.7112)),  # Faizabad -> Blue Area
    ((73.0551, 33.7060), (73.0225, 33.7007)),  # PIMS -> F-9 Park
    ((72.80, 33.60), (73.25, 33.82)),          # bbox diagonal
])
def test_planar_32643_matches_geodesic(p1, p2):
    """UTM planar distance must closely agree with the WGS 84 geodesic
    inside the Islamabad study area."""
    x1, y1 = TO_32643.transform(*p1)
    x2, y2 = TO_32643.transform(*p2)
    planar = math.hypot(x2 - x1, y2 - y1)
    _, _, geodesic = GEOD.inv(p1[0], p1[1], p2[0], p2[1])
    assert abs(planar - geodesic) / geodesic < 0.0005


def test_degree_metric_confusion_would_be_catastrophic():
    """Documents WHY metric math in EPSG:4326 is forbidden: treating degrees
    as metres misstates distance by ~5 orders of magnitude."""
    p1, p2 = (73.0790, 33.6642), (73.0561, 33.7112)
    degree_distance = math.hypot(p2[0] - p1[0], p2[1] - p1[1])  # 'degrees'
    _, _, true_m = GEOD.inv(p1[0], p1[1], p2[0], p2[1])
    assert true_m / degree_distance > 100_000  # ~111 km per degree
