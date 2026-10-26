/* GPL-2.0-only. */
/** @file hyperloop.cpp Independent wormhole layer for straight underground Hyperloop tubes. */
#include "../stdafx.h"
#include "hyperloop.h"
#include "../rail.h"
#include "../tunnelbridge_map.h"
#include "../landscape.h"
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
