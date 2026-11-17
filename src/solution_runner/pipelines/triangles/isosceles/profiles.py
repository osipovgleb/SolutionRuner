"""Ordered bindings for the isosceles triangle domain."""

from .area_angle_profiles import PROFILES as AREA_ANGLE_PROFILES
from .side_altitude_profiles import PROFILES as SIDE_ALTITUDE_PROFILES

PROFILES = SIDE_ALTITUDE_PROFILES + AREA_ANGLE_PROFILES
