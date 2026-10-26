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
#include "../strings_func.h"
#include "../vehicle_func.h"
#include "../window_func.h"
#include "table/strings.h"
#include "../safeguards.h"

namespace {
int32_t Month()
{
	const auto ymd = TimerGameCalendar::ConvertDateToYMD(TimerGameCalendar::date);
	return ymd.year.base() * 12 + ymd.month;
}

Station *Origin(const Aircraft *v)
{
	Station *st = Station::GetIfValid(v->orbital.origin);
	return st != nullptr && !st->airport.IsEmpty() && st->airport.tile == v->orbital.origin_tile &&
		AircraftMeetsAirportRequirements(v->GetEngine(), AirportSpec::Get(st->airport.type)) ? st : nullptr;
}

void Visible(Aircraft *v, bool visible)
{
	for (Aircraft *part = v; part != nullptr; part = part->Next()) {
		/* Aircraft::MarkDirty expects a primary with mail/shadow children. */
		part->UpdateViewport(true, false);
		if (visible) part->vehstatus.Reset(VehState::Hidden); else part->vehstatus.Set(VehState::Hidden);
	}
}

bool PadBusy(const Aircraft *v)
{
	for (const Aircraft *other : Aircraft::Iterate()) {
		if (other != v && other->IsNormalAircraft() && other->acache.orbital_shuttle &&
			other->orbital.origin == v->orbital.origin && other->orbital.phase >= OrbitalPhase::Launching) return true;
	}
	return false;
}

void Pay(Aircraft *v, Money profit)
{
	SubtractMoneyFromCompany(v->owner, CommandCost(v->GetExpenseType(true), -profit));
	v->profit_this_year += profit * 256;
}

void Board(Aircraft *v, Station *st)
{
	v->tile = st->airport.GetHangarTile(0);
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
	if (st == nullptr || st->airport.blocks.Test(AirportBlock::AirportClosed)) return STR_ORBITAL_NOT_BOARDING;
	if (CargoSpec::Get(v->cargo_type)->label != CargoLabel{"PASS"}) return STR_ORBITAL_PASSENGERS_ONLY;
	if (!st->goods[v->cargo_type].status.Test(GoodsEntry::State::Acceptance)) return STR_ORBITAL_NO_ACCEPTANCE;
	if (!OrbitalMonthAvailable(st->last_orbital_launch_month, Month())) return STR_ORBITAL_MONTHLY_LIMIT;
	if (PadBusy(v)) return STR_ORBITAL_PAD_BUSY;
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
		if (st == nullptr || st->airport.IsEmpty() || v->state != HANGAR || !v->IsInDepot()) return false;
		if (!AircraftMeetsAirportRequirements(v->GetEngine(), AirportSpec::Get(st->airport.type))) return false;
		mission.origin = st->index;
		mission.origin_tile = st->airport.tile;
		mission.ground_z = GetSlopePixelZ(TileX(st->airport.tile) * TILE_SIZE + 44, TileY(st->airport.tile) * TILE_SIZE + 38) + 1;
		Board(v, st);
	}
	Station *st = Origin(v);
	if (st == nullptr) return true; // Never silently reroute an off-world mission.
	const int x = TileX(st->airport.tile) * TILE_SIZE + 44;
	const int y = TileY(st->airport.tile) * TILE_SIZE + 38;
	const int32_t today = TimerGameCalendar::date.base();
	switch (mission.phase) {
		case OrbitalPhase::Boarding: {
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
				if (other != v && other->IsNormalAircraft() && other->acache.orbital_shuttle && other->orbital.origin == st->index &&
					other->orbital.phase == OrbitalPhase::Boarding && other->cargo.StoredCount() >= other->cargo_cap &&
					other->orbital.last_launch_month < mission.last_launch_month && OrbitalDispatchError(other) == STR_NULL) return true;
			}
			v->LeaveStation();
			v->current_order.MakeDummy();
			st->last_orbital_launch_month = Month();
			mission.last_launch_month = Month();
			mission.phase = OrbitalPhase::Launching;
			v->state = HELITAKEOFF;
			v->tile = TileVirtXY(x, y);
			Visible(v, true);
			SetAircraftPosition(v, x, y, mission.ground_z);
			Debug(Facility::Misc, Severity::Notice, "FL orbital launch vehicle={} origin={} month={} passengers={} manual={}", v->index, st->index, Month(), v->cargo.StoredCount(), mission.manual_dispatch);
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
			if (today < mission.due_date || !CargoPacket::CanAllocateItem()) break;
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
			VehicleServiceInDepot(v);
			break;
		case OrbitalPhase::Servicing:
			if (today >= mission.due_date) Board(v, st);
			break;
		case OrbitalPhase::None: NOT_REACHED();
	}
	v->cur_speed = 0;
	SetWindowDirty(WindowClass::VehicleView, v->index);
	return true;
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
			if (const Station *st = Origin(v); st != nullptr && st->last_orbital_launch_month == Month()) return GetString(STR_ORBITAL_WAIT_MONTH);
			return GetString(STR_ORBITAL_BOARDING, v->cargo.StoredCount(), v->cargo_cap);
		case OrbitalPhase::Launching: return GetString(STR_ORBITAL_LAUNCHING);
		case OrbitalPhase::Space: return GetString(STR_ORBITAL_SPACE, v->orbital.due_date);
		case OrbitalPhase::Returning: return GetString(STR_ORBITAL_RETURNING, v->cargo.StoredCount());
		case OrbitalPhase::Servicing: return GetString(STR_ORBITAL_SERVICING);
		default: return GetString(STR_ORBITAL_READY);
	}
}
