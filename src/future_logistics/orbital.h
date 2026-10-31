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
/* The launch mount on the 3x4 spaceport, in sixteenths of a tile from its north corner: Starship stands and
 * launches here, and the pad's docked graphics draw it in this spot (mods/newgrf/tools/make_spaceport_art.py). */
static constexpr int ORBITAL_MOUNT_X = 21;
static constexpr int ORBITAL_MOUNT_Y = 36;
/** Persistent stages of an orbital mission. */
enum class OrbitalPhase : uint8_t {
	None, ///< Not yet assigned to its home spaceport.
	Boarding, ///< Loading in the home service bay.
	Launching, ///< Ascending from the launch mount.
	Space, ///< Off-world until the saved return date.
	Returning, ///< Descending onto the original launch mount.
	Servicing, ///< Visible on the pad while serviced.
};

/** Mission state belongs to the vehicle, including when it is off the map. */
struct OrbitalState {
	OrbitalPhase phase = OrbitalPhase::None; ///< Current mission stage.
	StationID origin = StationID::Invalid(); ///< Home station ID.
	TileIndex origin_tile = INVALID_TILE; ///< Home airport location, guarding against station ID reuse.
	int32_t due_date = 0; ///< Calendar date of the next timed transition.
	int32_t last_launch_month = -1; ///< Last departure month for fleet fairness.
	int32_t ground_z = 0; ///< Launch mount altitude.
	uint32_t completed_trips = 0; ///< Completed round trips.
	bool manual_dispatch = false; ///< Pending early-departure request.
};

/**
 * Check the Starship manifest threshold.
 * @param passengers Boarded passengers.
 * @param manual Whether early dispatch was requested.
 * @return Whether the manifest meets the threshold.
 */
constexpr bool OrbitalLoadReady(uint passengers, bool manual) { return passengers >= (manual ? 500U : 1000U); }
/**
 * Check a calendar launch slot.
 * @param last Last launch month.
 * @param current Current calendar month.
 * @return Whether the current slot is unused.
 */
constexpr bool OrbitalMonthAvailable(int32_t last, int32_t current) { return last != current; }
bool TickOrbitalAircraft(Aircraft *v);
StringID OrbitalDispatchError(const Aircraft *v);
std::string OrbitalStatus(const Aircraft *v);

#endif /* FUTURE_LOGISTICS_ORBITAL_H */
