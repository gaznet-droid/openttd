/*
 * This file is part of OpenTTD.
 * OpenTTD is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 2.
 */
/** @file orbital.cpp Vertical launch, off-world mission and return to the originating spaceport. */
#include "../stdafx.h"
#include "orbital.h"
#include "tech_library.h"
#include "../aircraft.h"
#include "../airport.h"
#include "../company_base.h"
#include "../company_func.h"
#include "../debug.h"
#include "../economy_func.h"
#include "../economy_base.h"
#include "../engine_base.h"
#include "../landscape.h"
#include "../newgrf_airport.h"
#include "../station_base.h"
#include "../station_map.h"
#include "../viewport_func.h"
#include "../strings_func.h"
#include "../vehicle_func.h"
#include "../window_func.h"
#include "table/strings.h"
#include "../safeguards.h"

namespace {
/** Return the current calendar month index. @return Calendar month index. */
int32_t Month()
{
	const auto ymd = TimerGameCalendar::ConvertDateToYMD(TimerGameCalendar::date);
	return ymd.year.base() * 12 + ymd.month;
}

/**
 * Find the spaceport pad of a station whose hangar a shuttle stands in.
 * @param st Station.
 * @param tile Tile the shuttle is on.
 * @return The pad, or nullptr when the tile is not on one of the station's pads.
 */
Airport *PadAt(Station *st, TileIndex tile)
{
	if (st == nullptr || !IsTileType(tile, TileType::Station) || !st->TileBelongsToAirport(tile)) return nullptr;
	Airport &pad = st->GetAirportByTile(tile);
	return &pad == &st->airport ? nullptr : &pad;
}

/**
 * Find the original spaceport.
 * @param v Shuttle to inspect.
 * @return Home station, or nullptr.
 */
Station *Origin(const Aircraft *v)
{
	Station *st = Station::GetIfValid(v->orbital.origin);
	if (st == nullptr) return nullptr;
	const Airport *pad = st->GetSpaceport(v->orbital.origin_tile);
	return pad != nullptr && AircraftMeetsAirportRequirements(v->GetEngine(), pad->GetSpec()) ? st : nullptr;
}

/**
 * Find the home pad of a shuttle on a mission.
 * @param v Shuttle to inspect.
 * @return Home pad, or nullptr.
 */
Airport *HomePad(const Aircraft *v)
{
	Station *st = Origin(v);
	return st == nullptr ? nullptr : st->GetSpaceport(v->orbital.origin_tile);
}

/**
 * Set shuttle, shadow and rotor visibility.
 * @param v Primary aircraft.
 * @param visible Whether to show it.
 */
void Visible(Aircraft *v, bool visible)
{
	for (Aircraft *part = v; part != nullptr; part = part->Next()) {
		/* Aircraft::MarkDirty expects a primary with mail/shadow children. */
		part->UpdateViewport(true, false);
		if (visible) part->vehstatus.Reset(VehState::Hidden); else part->vehstatus.Set(VehState::Hidden);
	}
}

/**
 * Check whether a shuttle belongs to a spaceport pad.
 * @param other Aircraft to check.
 * @param st Station of the pad.
 * @param pad North tile of the pad.
 * @return Whether it is an orbital shuttle with that home pad.
 */
bool OnPad(const Aircraft *other, const Station *st, TileIndex pad)
{
	return other->IsNormalAircraft() && other->acache.orbital_shuttle && other->orbital.origin == st->index && other->orbital.origin_tile == pad;
}

/**
 * Check whether another shuttle is on a spaceport pad's launch mount: boarding or being serviced on the mount,
 * or lifting off from or landing on it. Only one shuttle uses a pad at a time; the others wait in its hangar or,
 * on their way back, in orbit. Each pad of a station has its own mount.
 * @param st Station.
 * @param pad North tile of the pad.
 * @param v Asking shuttle, which is not counted.
 * @return Whether the pad is taken.
 */
bool PadOccupied(const Station *st, TileIndex pad, const Aircraft *v)
{
	for (const Aircraft *other : Aircraft::Iterate()) {
		if (other == v || !OnPad(other, st, pad)) continue;
		switch (other->orbital.phase) {
			case OrbitalPhase::Boarding: case OrbitalPhase::Launching: case OrbitalPhase::Returning: case OrbitalPhase::Servicing: return true;
			default: break;
		}
	}
	return false;
}

/**
 * Show the docked or empty launch pad: while a shuttle of this pad is boarding or being serviced it stands
 * on the launch mount, and the pad's tiles draw it there (animation frame 1); otherwise they draw the empty pad.
 * While another shuttle is lifting off from or landing on the mount, the pad is drawn empty so the two never overlap.
 * @param st Station.
 * @param pad The spaceport pad to update.
 */
void UpdatePadDocked(Station *st, const Airport &pad)
{
	bool waiting = false, moving = false;
	for (const Aircraft *a : Aircraft::Iterate()) {
		if (!OnPad(a, st, pad.tile)) continue;
		if (a->orbital.phase == OrbitalPhase::Boarding || a->orbital.phase == OrbitalPhase::Servicing) waiting = true;
		if (a->orbital.phase == OrbitalPhase::Launching || a->orbital.phase == OrbitalPhase::Returning) moving = true;
	}
	const bool docked = waiting && !moving;
	for (TileIndex t : pad) {
		if (!st->TileBelongsToAirport(t, pad) || GetAnimationFrame(t) == (docked ? 1 : 0)) continue;
		SetAnimationFrame(t, docked ? 1 : 0);
		MarkTileDirtyByTile(t);
	}
}

/**
 * Book orbital revenue.
 * @param v Operating vehicle.
 * @param profit Revenue after feeder shares.
 */
void Pay(Aircraft *v, Money profit)
{
	SubtractMoneyFromCompany(v->owner, CommandCost(v->GetExpenseType(true), -profit));
	v->profit_this_year += profit * 256;
}

/**
 * Begin loading in the home service bay.
 * @param v Shuttle to load.
 * @param st Home station; the shuttle boards at its home pad.
 */
void Board(Aircraft *v, Station *st)
{
	const Airport &pad = *st->GetSpaceport(v->orbital.origin_tile);
	v->tile = pad.GetHangarTile(0);
	v->state = HANGAR;
	Visible(v, false);
	SetAircraftPosition(v, TileX(v->tile) * TILE_SIZE + 5, TileY(v->tile) * TILE_SIZE + 3, v->orbital.ground_z);
	v->last_station_visited = st->index;
	v->current_order.MakeGoToStation(st->index);
	v->current_order.SetLoadType(OrderLoadType::FullLoadAny);
	v->current_order.SetUnloadType(OrderUnloadType::NoUnload);
	v->BeginLoading();
	v->orbital.phase = OrbitalPhase::Boarding;
	v->orbital.manual_dispatch = false;
	UpdatePadDocked(st, pad);
}
} // namespace

/**
 * Check an early dispatch without modifying the mission.
 * @param v Shuttle to dispatch.
 * @return An error string, or STR_NULL when ready.
 */
StringID OrbitalDispatchError(const Aircraft *v)
{
	if (!v->acache.orbital_shuttle || v->orbital.phase != OrbitalPhase::Boarding || v->vehstatus.Test(VehState::Stopped)) return STR_ORBITAL_NOT_BOARDING;
	const Station *st = Origin(v);
	const Airport *pad = HomePad(v);
	if (st == nullptr || pad->blocks.Test(AirportBlock::AirportClosed)) return STR_ORBITAL_NOT_BOARDING;
	if (const CargoLabel label = CargoSpec::Get(v->cargo_type)->label; label != CargoLabel{"PASS"} && label != CargoLabel{"MAIL"}) return STR_ORBITAL_PASSENGERS_ONLY;
	if (!st->goods[v->cargo_type].status.Test(GoodsEntry::State::Acceptance)) return STR_ORBITAL_NO_ACCEPTANCE;
	if (!OrbitalMonthAvailable(pad->last_orbital_launch_month, Month())) return STR_ORBITAL_MONTHLY_LIMIT;
	if (PadOccupied(st, pad->tile, v)) return STR_ORBITAL_PAD_BUSY;
	if (v->cargo.StoredCount() < std::min<uint>(v->cargo_cap, 500)) return STR_ORBITAL_MINIMUM_LOAD;
	return STR_NULL;
}

/**
 * Run the shuttle controller instead of the conventional airport flight circuit.
 * @param v Aircraft being ticked.
 * @return Whether the controller handled this aircraft.
 */
bool TickOrbitalAircraft(Aircraft *v)
{
	if (!v->acache.orbital_shuttle || v->vehstatus.Test(VehState::Crashed)) return false;
	if (v->vehstatus.Test(VehState::Stopped)) return true;
	OrbitalState &mission = v->orbital;
	if (mission.phase == OrbitalPhase::None) {
		/* Existing aircraft in flight finish their current approach before adopting orbital service. */
		Station *st = Station::GetIfValid(v->targetairport);
		if (st == nullptr || v->state != HANGAR || !v->IsInDepot()) return false;
		/* The shuttle belongs to the pad whose hangar it stands in. */
		const Airport *pad = PadAt(st, v->tile);
		if (pad == nullptr || !AircraftMeetsAirportRequirements(v->GetEngine(), pad->GetSpec())) return false;
		/* A new shuttle waits in the hangar until the pad is free. */
		if (PadOccupied(st, pad->tile, v)) return true;
		mission.origin = st->index;
		mission.origin_tile = pad->tile;
		mission.ground_z = GetSlopePixelZ(TileX(pad->tile) * TILE_SIZE + ORBITAL_MOUNT_X, TileY(pad->tile) * TILE_SIZE + ORBITAL_MOUNT_Y) + 1;
		Board(v, st);
	}
	Station *st = Origin(v);
	if (st == nullptr) return true; // Never silently reroute an off-world mission.
	Airport &pad = *st->GetSpaceport(mission.origin_tile);
	const int x = TileX(pad.tile) * TILE_SIZE + ORBITAL_MOUNT_X;
	const int y = TileY(pad.tile) * TILE_SIZE + ORBITAL_MOUNT_Y;
	const int32_t today = TimerGameCalendar::date.base();
	const OrbitalPhase before = mission.phase;
	switch (mission.phase) {
		case OrbitalPhase::Boarding: {
			/* Saves from before the pad took one shuttle at a time can have several boarding at once. All but the
			 * oldest (or one being serviced) step back into the hangar and queue, keeping what they have loaded. */
			bool yield = false;
			for (const Aircraft *other : Aircraft::Iterate()) {
				if (other == v || !OnPad(other, st, pad.tile)) continue;
				if (other->orbital.phase == OrbitalPhase::Servicing || other->orbital.phase == OrbitalPhase::Launching ||
						other->orbital.phase == OrbitalPhase::Returning || (other->orbital.phase == OrbitalPhase::Boarding && other->index < v->index)) {
					yield = true;
					break;
				}
			}
			if (yield) {
				if (v->current_order.IsType(OT_LOADING)) v->LeaveStation();
				v->current_order.MakeDummy();
				v->tile = pad.GetHangarTile(0);
				v->state = HANGAR;
				v->targetairport = st->index;
				mission.phase = OrbitalPhase::None;
				break;
			}
			/* External order edits must not strand the shuttle or leave duplicate loading entries. */
			if (!v->current_order.IsType(OT_LOADING)) {
				v->CancelReservation(StationID::Invalid(), st);
				st->loading_vehicles.remove(v);
				delete v->cargo_payment;
				Board(v, st);
			}
			v->current_order.SetLoadType(OrderLoadType::FullLoadAny);
			v->current_order.SetUnloadType(OrderUnloadType::NoUnload);
			const bool load_ready = v->cargo_cap == 1000 ? OrbitalLoadReady(v->cargo.StoredCount(), mission.manual_dispatch) :
				v->cargo.StoredCount() >= (mission.manual_dispatch ? std::min<uint>(500, v->cargo_cap) : v->cargo_cap);
			if (!load_ready || OrbitalDispatchError(v) != STR_NULL) break;
			/* A ready ship that has waited longer gets first use of the shared monthly slot. */
			for (const Aircraft *other : Aircraft::Iterate()) {
				if (other != v && OnPad(other, st, pad.tile) &&
					other->orbital.phase == OrbitalPhase::Boarding && other->cargo.StoredCount() >= other->cargo_cap &&
					other->orbital.last_launch_month < mission.last_launch_month && OrbitalDispatchError(other) == STR_NULL) return true;
			}
			v->LeaveStation();
			v->current_order.MakeDummy();
			pad.last_orbital_launch_month = Month();
			mission.last_launch_month = Month();
			mission.phase = OrbitalPhase::Launching;
			v->state = HELITAKEOFF;
			v->tile = TileVirtXY(x, y);
			Visible(v, true);
			SetAircraftPosition(v, x, y, mission.ground_z);
			Debug(Facility::Misc, Severity::Notice, "FL orbital launch vehicle={} origin={} month={} passengers={} manual={} pad={}", v->index, st->index, Month(), v->cargo.StoredCount(), mission.manual_dispatch, pad.tile);
			break;
		}
		case OrbitalPhase::Launching:
			SetAircraftPosition(v, x, y, std::min(v->z_pos + 4, mission.ground_z + 600));
			if (v->z_pos < mission.ground_z + 600) break;
			for (Aircraft *part = v; part != nullptr; part = part->Next()) {
				const uint count = part->cargo.StoredCount();
				if (count == 0) continue;
				/* Actual boarded cargo leaves for the orbital destination. No synthetic outbound passengers. */
				Pay(v, GetTransportedGoodsIncome(count, 256, 0, part->cargo_type) - part->cargo.GetFeederShare());
				Company::Get(v->owner)->cur_economy.delivered_cargo[part->cargo_type] += count;
				part->cargo.Truncate();
			}
			mission.phase = OrbitalPhase::Space;
			mission.due_date = today + 7;
			Visible(v, false);
			break;
		case OrbitalPhase::Space:
			/* A returning shuttle stays in orbit until the pad is free. */
			if (today < mission.due_date || PadOccupied(st, pad.tile, v) || !CargoPacket::CanAllocateItem()) break;
			{
				CargoPacket *packet = CargoPacket::Create(StationID::Invalid(), v->cargo_cap, Source{Source::Invalid, SourceType::Industry});
				packet->UpdateLoadingTile(v->tile);
				v->cargo.Append(packet);
			}
			mission.phase = OrbitalPhase::Returning;
			v->state = HELILANDING;
			Visible(v, true);
			break;
		case OrbitalPhase::Returning:
			SetAircraftPosition(v, x, y, std::max(v->z_pos - 4, mission.ground_z));
			if (v->z_pos != mission.ground_z || !st->goods[v->cargo_type].status.Test(GoodsEntry::State::Acceptance)) break;
			Pay(v, DeliverOrbitalCargo(v->cargo.StoredCount(), v->cargo_type, st->index, v->owner));
			Debug(Facility::Misc, Severity::Notice, "FL orbital landed vehicle={} origin={} inbound={} trips={}", v->index, st->index, v->cargo.StoredCount(), mission.completed_trips + 1);
			v->cargo.Truncate();
			mission.completed_trips++;
			mission.phase = OrbitalPhase::Servicing;
			mission.due_date = today + 2;
			v->state = HANGAR;
			Visible(v, false); // The pad now draws it docked on the mount.
			VehicleServiceInDepot(v);
			break;
		case OrbitalPhase::Servicing:
			if (today >= mission.due_date) Board(v, st);
			break;
		case OrbitalPhase::None: NOT_REACHED();
	}
	if (mission.phase != before && Origin(v) != nullptr) UpdatePadDocked(st, pad);
	v->cur_speed = 0;
	SetWindowDirty(WindowClass::VehicleView, v->index);
	return true;
}

/**
 * Put the spaceports' hangar under the hangar drawn in the pad's left corner. The spaceports reuse the country
 * airport's movement and with it its hangar, which on the rotated 3x4 pad lands on the north tile behind the tower,
 * where it cannot be clicked. Called once the NewGRF airports are known.
 */
void InitSpaceportHangars()
{
	/* (3, 2) in the country airport's frame is the west (left-hand) corner tile once the layout is rotated east. */
	static const HangarTileTable left_corner[] = { {{3, 2}, Direction::SE, 0} };
	for (uint8_t i = 0; i < NUM_AIRPORTS; i++) {
		AirportSpec *as = AirportSpec::GetWithoutOverride(i);
		if (!as->enabled || as->layouts.size() != 1 || as->layouts[0].rotation != Direction::E || as->size_x != 4 || as->size_y != 3) continue;
		const ItemTags tags = ReadItemTags(as->badges);
		if (tags.id == "spaceport" || tags.id == "starship_launch_site") as->depots = left_corner;
	}
}

/**
 * Format the mission status for the vehicle window.
 * @param v Orbital shuttle.
 * @return Localized status text.
 */
std::string OrbitalStatus(const Aircraft *v)
{
	switch (v->orbital.phase) {
		case OrbitalPhase::Boarding:
			if (const Airport *pad = HomePad(v); pad != nullptr && pad->last_orbital_launch_month == Month()) return GetString(STR_ORBITAL_WAIT_MONTH);
			return GetString(STR_ORBITAL_BOARDING, v->cargo.StoredCount(), v->cargo_cap);
		case OrbitalPhase::Launching: return GetString(STR_ORBITAL_LAUNCHING);
		case OrbitalPhase::Space:
			if (const Station *st = Origin(v); st != nullptr && TimerGameCalendar::date.base() >= v->orbital.due_date && PadOccupied(st, v->orbital.origin_tile, v)) return GetString(STR_ORBITAL_WAIT_PAD_ORBIT);
			return GetString(STR_ORBITAL_SPACE, v->orbital.due_date);
		case OrbitalPhase::Returning: return GetString(STR_ORBITAL_RETURNING, v->cargo.StoredCount());
		case OrbitalPhase::Servicing: return GetString(STR_ORBITAL_SERVICING);
		default:
			if (Station *st = Station::GetIfValid(v->targetairport); st != nullptr && v->IsInDepot()) {
				if (const Airport *pad = PadAt(st, v->tile); pad != nullptr && PadOccupied(st, pad->tile, v)) return GetString(STR_ORBITAL_WAIT_PAD_HANGAR);
			}
			return GetString(STR_ORBITAL_READY);
	}
}
