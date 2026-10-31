/* GPL-2.0-only. */
/** @file hyperloop.h Hyperloop viaduct identification, and underground tube construction and inspection. */
#ifndef FUTURE_LOGISTICS_HYPERLOOP_H
#define FUTURE_LOGISTICS_HYPERLOOP_H

#include "../rail_type.h"
#include "../tile_type.h"

bool IsHyperloopRailType(RailType type);
bool IsHyperloopTube(TileIndex tile);
bool IsHyperloopViaduct(TileIndex tile);
bool HyperloopTubeUnder(TileIndex tile, int z);
bool HyperloopTubeUnder(TileIndex tile);
void InvalidateHyperloopTubes();

#endif /* FUTURE_LOGISTICS_HYPERLOOP_H */
