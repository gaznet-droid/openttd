/*
 * This file is part of OpenTTD.
 * OpenTTD is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 2.
 */
/** @file orbital.h Persistent orbital shuttle missions. */
#ifndef FUTURE_LOGISTICS_ORBITAL_H
#define FUTURE_LOGISTICS_ORBITAL_H

#include "../station_type.h"
#include "../tile_type.h"
#include "../strings_type.h"

struct Aircraft;
enum class OrbitalPhase : uint8_t { None, Boarding, Launching, Space, Returning, Servicing };

/** Mission state belongs to the vehicle, including when it is off the map. */
struct OrbitalState {
	OrbitalPhase phase = OrbitalPhase::None;
	StationID origin = StationID::Invalid();
	TileIndex origin_tile = INVALID_TILE;
	int32_t due_date = 0;
	int32_t last_launch_month = -1;
	int32_t ground_z = 0;
	uint32_t completed_trips = 0;
	bool manual_dispatch = false;
};

constexpr bool OrbitalLoadReady(uint passengers, bool manual) { return passengers >= (manual ? 500U : 1000U); }
constexpr bool OrbitalMonthAvailable(int32_t last, int32_t current) { return last != current; }
bool TickOrbitalAircraft(Aircraft *v);
StringID OrbitalDispatchError(const Aircraft *v);
std::string OrbitalStatus(const Aircraft *v);

#endif /* FUTURE_LOGISTICS_ORBITAL_H */
