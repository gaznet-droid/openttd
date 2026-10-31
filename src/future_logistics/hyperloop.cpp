/* GPL-2.0-only. */
/** @file hyperloop.cpp Hyperloop viaducts, and the independent wormhole layer of straight underground Hyperloop tubes. */
#include "../stdafx.h"
#include "hyperloop.h"
#include "../rail.h"
#include "../tunnelbridge_map.h"
#include "../bridge.h"
#include "../bridge_map.h"
#include "../landscape.h"
#include "../newgrf_railtype.h"
#include "../safeguards.h"

namespace {
/** Geometry derived from native flat access shafts. */
struct Tube {
	TileIndex start; ///< First shaft.
	TileIndex end; ///< Paired exit.
	int z; ///< Native tunnel layer height.
};
std::vector<Tube> _tubes; ///< Derived tube segments.
bool _valid = false; ///< Whether geometry matches the map.

/** Rebuild derived geometry when needed. @return Current tube segments. */
const std::vector<Tube> &Tubes()
{
	if (_valid) return _tubes;
	_tubes.clear();
	for (TileIndex tile{0}; tile < Map::Size(); ++tile) {
		if (!IsHyperloopTube(tile)) continue;
		const auto dir = GetTunnelBridgeDirection(tile);
		if (dir != DiagDirection::SW && dir != DiagDirection::SE) continue;
		const TileIndex end = GetOtherTunnelEnd(tile);
		_tubes.push_back({tile, end, GetTileZ(tile)});
	}
	_valid = true;
	return _tubes;
}

/**
 * Check a surface coordinate.
 * @param tube Segment to inspect.
 * @param tile Surface coordinate.
 * @return Whether the coordinate lies on the segment.
 */
bool Contains(const Tube &tube, TileIndex tile)
{
	const uint x = TileX(tile), y = TileY(tile);
	const uint ax = TileX(tube.start), ay = TileY(tube.start), bx = TileX(tube.end), by = TileY(tube.end);
	return ax == bx ? x == ax && y >= std::min(ay, by) && y <= std::max(ay, by) :
		y == ay && x >= std::min(ax, bx) && x <= std::max(ax, bx);
}
} // namespace

/**
 * Identify the dedicated rail family independently of its NewGRF load order.
 * @param type Rail type to inspect.
 * @return Whether it is HYPL.
 */
bool IsHyperloopRailType(RailType type)
{
	return type < RAILTYPE_END && GetRailTypeInfo(type)->label == RailTypeLabel{"HYPL"};
}

/**
 * Identify a flat Hyperloop access shaft stored as a native rail tunnel endpoint.
 * @param tile Tile to inspect.
 * @return Whether it belongs to a flat underground Hyperloop tube.
 */
bool IsHyperloopTube(TileIndex tile)
{
	return IsTunnelTile(tile) && GetTunnelBridgeTransportType(tile) == TransportType::Rail &&
		IsHyperloopRailType(GetRailType(tile)) && GetTileSlope(tile) == SLOPE_FLAT;
}

/**
 * Identify a ramp of an elevated Hyperloop viaduct.
 * @param tile Tile to inspect.
 * @return Whether it is a bridge head of the dedicated Hyperloop viaduct type.
 */
bool IsHyperloopViaduct(TileIndex tile)
{
	return IsBridgeTile(tile) && GetTunnelBridgeTransportType(tile) == TransportType::Rail && GetBridgeType(tile) == BRIDGE_HYPERLOOP;
}

/** Invalidate derived geometry after a map load or tube mutation. */
void InvalidateHyperloopTubes() { _valid = false; }

/**
 * Check the underground layer, including its access shafts.
 * @param tile Surface coordinate.
 * @param z Native tunnel layer height.
 * @return Whether the specified layer contains a tube.
 */
bool HyperloopTubeUnder(TileIndex tile, int z)
{
	return std::ranges::any_of(Tubes(), [&](const Tube &tube) { return tube.z == z && Contains(tube, tile); });
}

/**
 * Check all underground layers for the inspection overlay.
 * @param tile Surface coordinate.
 * @return Whether there is a Hyperloop tube underneath.
 */
bool HyperloopTubeUnder(TileIndex tile)
{
	return std::ranges::any_of(Tubes(), [&](const Tube &tube) { return Contains(tube, tile); });
}

/**
 * Give the Hyperloop viaduct its own structure, drawn by the NewGRF that defines the HYPL rail type. The rail type's
 * bridge surface set holds the six usual deck surfaces followed by the viaduct: floor, roof and pillar for the X and
 * then Y axis, then eight heads in the game's head order. Without them the viaduct keeps its default sprites.
 * Called after NewGRFs are loaded and rail type sprites are resolved.
 */
void InitHyperloopViaductSprites()
{
	BridgeSpec &spec = _bridge[BRIDGE_HYPERLOOP];
	spec.sprite_table.clear();
	for (RailType rt : EnumRange(RAILTYPE_END)) {
		if (!IsHyperloopRailType(rt)) continue;
		const RailTypeInfo *rti = GetRailTypeInfo(rt);
		uint num = 0;
		const SpriteID base = GetCustomRailSprite(rti, INVALID_TILE, RailSpriteType::Bridge, TileContext::Normal, &num);
		static constexpr uint SURFACES = 6, MIDDLE = 6, HEADS = 8;
		if (base == 0 || num < SURFACES + MIDDLE + HEADS) return;
		/* Bridge tables are indexed from the rail type's bridge offset. */
		const uint offset = rti->bridge_offset;
		const SpriteID mid = base + SURFACES;
		std::vector<PalSpriteID> middle(offset + 8, PalSpriteID{0, PAL_NONE});
		for (uint axis = 0; axis < 2; axis++) {
			for (uint part = 0; part < 3; part++) middle[offset + axis * 4 + part] = {mid + axis * 3 + part, PAL_NONE};
		}
		std::vector<PalSpriteID> heads(offset + 8, PalSpriteID{0, PAL_NONE});
		for (uint i = 0; i < HEADS; i++) heads[offset + i] = {mid + MIDDLE + i, PAL_NONE};
		spec.sprite_table.assign(NUM_BRIDGE_PIECES, middle);
		spec.sprite_table[BRIDGE_PIECE_HEAD] = heads;
		return;
	}
}

/** Class label of the Hyperloop terminal station. */
static const StationClass::GlobalID HYPERLOOP_TERMINAL_CLASS{"HYPL"};

/**
 * Check for the Hyperloop terminal's station class.
 * @param cls Station class.
 * @return Whether it is the Hyperloop terminal class.
 */
bool IsHyperloopTerminalClass(StationClassID cls)
{
	return cls.base() < StationClass::GetClassCount() && StationClass::Get(cls)->global_id == HYPERLOOP_TERMINAL_CLASS;
}

/**
 * Find the Hyperloop terminal, which every Hyperloop station is built as.
 * @param[out] cls Its station class.
 * @param[out] index Its index in the class.
 * @return Whether a NewGRF provides it.
 */
bool FindHyperloopTerminal(StationClassID &cls, uint16_t &index)
{
	for (const auto &c : StationClass::Classes()) {
		if (c.global_id != HYPERLOOP_TERMINAL_CLASS || c.GetSpecCount() == 0) continue;
		cls = c.Index();
		index = 0;
		return true;
	}
	return false;
}
