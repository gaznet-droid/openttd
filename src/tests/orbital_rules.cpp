/* GPL-2.0-only. */
/** @file orbital_rules.cpp Orbital loading thresholds and calendar launch slots. */
#include "../stdafx.h"
#include "../3rdparty/catch2/catch.hpp"
#include "../future_logistics/orbital.h"
#include "../safeguards.h"

TEST_CASE("Orbital loading thresholds")
{
	CHECK_FALSE(OrbitalLoadReady(499, true));
	CHECK(OrbitalLoadReady(500, true));
	CHECK(OrbitalLoadReady(999, true));
	CHECK_FALSE(OrbitalLoadReady(999, false));
	CHECK(OrbitalLoadReady(1000, false));
}
TEST_CASE("Orbital calendar launch slots")
{
	CHECK(OrbitalMonthAvailable(-1, 2050 * 12));
	CHECK_FALSE(OrbitalMonthAvailable(2050 * 12 + 11, 2050 * 12 + 11));
	CHECK(OrbitalMonthAvailable(2050 * 12 + 11, 2051 * 12));
}
