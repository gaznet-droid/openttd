/* GPL-2.0-only. */
/** @file hyperloop.h Hyperloop viaduct identification, and underground tube construction and inspection. */
#ifndef FUTURE_LOGISTICS_HYPERLOOP_H
#define FUTURE_LOGISTICS_HYPERLOOP_H

#include "../rail_type.h"
#include "../tile_type.h"
#include "../newgrf_station.h"

bool IsHyperloopRailType(RailType type);
bool IsHyperloopTube(TileIndex tile);
bool IsHyperloopViaduct(TileIndex tile);
bool HyperloopTubeUnder(TileIndex tile, int z);
bool HyperloopTubeUnder(TileIndex tile);
void InvalidateHyperloopTubes();
void InitHyperloopViaductSprites();
bool IsHyperloopTerminalClass(StationClassID cls);
bool FindHyperloopTerminal(StationClassID &cls, uint16_t &index);

#endif /* FUTURE_LOGISTICS_HYPERLOOP_H */
