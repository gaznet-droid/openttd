/* GPL-2.0-only. All changes are confined to the isolated regression world. */
class HyperloopCheck extends GSController {
    ready = false;
    vehicle = -1;
    home = -1;
    other = -1;
    max_speed = 0;
    reached_far = false;
    via_vehicle = -1;
    via_far = -1;
    via_reached = false;
    function Save() { return { ready = this.ready, vehicle = this.vehicle, home = this.home,
                              other = this.other, max_speed = this.max_speed, reached_far = this.reached_far,
                              via_vehicle = this.via_vehicle, via_far = this.via_far }; }
    function Load(version, data) {
        foreach (key, value in data) this[key] = value;
        /* After a reload both pods must cross again, proving the tube and viaduct survived it. */
        this.reached_far = false;
        this.via_reached = false;
    }
    /* Land a viaduct can pass over: clear of buildings and no higher than its ramps. */
    function Under(tile, height) { return GSTile.IsBuildable(tile) && GSTile.GetMaxHeight(tile) <= height; }
    function Engines() {
        local pod = -1, capsule = -1;
        foreach (engine, unused in GSEngineList(GSVehicle.VT_RAIL)) {
            if (GSEngine.GetName(engine) == "Hyperloop Propulsion Pod") pod = engine;
            if (GSEngine.GetName(engine) == "Hyperloop Passenger Capsule") capsule = engine;
        }
        return [pod, capsule];
    }
    function Line(depot, near_station, far_station) {
        local engines = this.Engines();
        local pod = GSVehicle.BuildVehicle(depot, engines[0]);
        local wagon = GSVehicle.BuildVehicle(depot, engines[1]);
        if (!GSVehicle.IsValidVehicle(pod) || !GSVehicle.IsValidVehicle(wagon) ||
            !GSVehicle.MoveWagon(wagon, 0, pod, 0) ||
            !GSOrder.AppendOrder(pod, near_station, GSOrder.OF_NONE) ||
            !GSOrder.AppendOrder(pod, far_station, GSOrder.OF_NONE) ||
            !GSVehicle.StartStopVehicle(pod)) return -1;
        return pod;
    }
    /* A short viaduct line with a road passing beneath it, away from the tube's row. */
    function BuildViaduct(tube_y) {
        local span = 20, cross = 10;
        local x0 = -1, y0 = -1;
        for (local y = 16; y < GSMap.GetMapSizeY() - 16 && x0 == -1; y += 2) {
            if (abs(y - tube_y) <= 4) continue;
            for (local x = 16; x < GSMap.GetMapSizeX() - span - 26; x += 2) {
                local h = GSTile.GetMinHeight(GSMap.GetTileIndex(x, y));
                local ok = true;
                foreach (dx in [0, 1, 2, 3, 4, 5, span + 6, span + 7, span + 8, span + 9]) {
                    if (!this.Flat(GSMap.GetTileIndex(x + dx, y), h)) { ok = false; break; }
                }
                for (local dx = 6; dx < span + 6 && ok; dx++) if (!this.Under(GSMap.GetTileIndex(x + dx, y), h)) ok = false;
                for (local dy = -2; dy <= 2 && ok; dy++) if (!this.Flat(GSMap.GetTileIndex(x + 6 + cross, y + dy), h)) ok = false;
                if (ok) { x0 = x; y0 = y; break; }
            }
        }
        if (x0 == -1) { GSLog.Error("HYPL no viaduct site"); return false; }
        local hypl = GSRail.GetCurrentRailType();
        local plain = -1;
        foreach (type, unused in GSRailTypeList()) if (type != hypl) { plain = type; break; }
        /* Prove a short ordinary bridge fits for ordinary rail, then require it to be refused for HYPL. */
        local short_a = GSMap.GetTileIndex(x0 + 1, y0), short_b = GSMap.GetTileIndex(x0 + 4, y0);
        local ordinary = GSBridgeList_Length(2);
        if (plain == -1 || ordinary.IsEmpty()) { GSLog.Error("HYPL no ordinary bridge to compare"); return false; }
        GSRail.SetCurrentRailType(plain);
        local fits = false;
        { local test = GSTestMode(); fits = GSBridge.BuildBridge(GSVehicle.VT_RAIL, ordinary.Begin(), short_a, short_b); }
        GSRail.SetCurrentRailType(hypl);
        if (!fits) { GSLog.Error("HYPL ordinary bridge control failed: " + GSError.GetLastErrorString()); return false; }
        if (GSBridge.BuildBridge(GSVehicle.VT_RAIL, ordinary.Begin(), short_a, short_b)) { GSLog.Error("HYPL ordinary bridge allowed"); return false; }
        GSLog.Info("HYPL ordinary_bridge_rejected=true");
        local depot = GSMap.GetTileIndex(x0, y0);
        local front = GSMap.GetTileIndex(x0 + 1, y0);
        local near_station = GSMap.GetTileIndex(x0 + 2, y0);
        local a = GSMap.GetTileIndex(x0 + 5, y0);
        local b = GSMap.GetTileIndex(x0 + span + 6, y0);
        local far_station = GSMap.GetTileIndex(x0 + span + 7, y0);
        if (!GSBridge.BuildHyperloopViaduct(a, b)) { GSLog.Error("HYPL viaduct: " + GSError.GetLastErrorString()); return false; }
        if (!GSBridge.IsBridgeTile(a) || GSBridge.GetOtherBridgeEnd(a) != b || GSBridge.GetOtherBridgeEnd(b) != a) { GSLog.Error("HYPL viaduct ends disagree"); return false; }
        /* Roads pass under the viaduct. */
        GSRoad.SetCurrentRoadType(GSRoad.ROADTYPE_ROAD);
        if (!GSRoad.BuildRoad(GSMap.GetTileIndex(x0 + 6 + cross, y0 - 2), GSMap.GetTileIndex(x0 + 6 + cross, y0 + 2))) {
            GSLog.Error("HYPL road under viaduct: " + GSError.GetLastErrorString()); return false;
        }
        if (GSRail.ConvertRailType(a, a, plain) || GSRail.GetRailType(a) != hypl) { GSLog.Error("HYPL viaduct converted to ordinary rail"); return false; }
        GSLog.Info("HYPL conversion_rejected=true");
        if (!GSRail.BuildRailDepot(depot, front) || !GSRail.BuildRail(depot, front, near_station) ||
            !GSRail.BuildRailStation(near_station, GSRail.RAILTRACK_NE_SW, 1, 3, GSStation.STATION_NEW) ||
            !GSRail.BuildRailStation(far_station, GSRail.RAILTRACK_NE_SW, 1, 3, GSStation.STATION_NEW)) {
            GSLog.Error("HYPL viaduct approaches: " + GSError.GetLastErrorString()); return false;
        }
        this.via_vehicle = this.Line(depot, near_station, far_station);
        if (this.via_vehicle == -1) { GSLog.Error("HYPL viaduct vehicle: " + GSError.GetLastErrorString()); return false; }
        this.via_far = b;
        GSLog.Info("HYPL viaduct ready vehicle=" + this.via_vehicle + " road_under=true length=" + (span + 2));
        return true;
    }
    function Flat(tile, height) { return GSTile.IsBuildable(tile) && GSTile.GetSlope(tile) == GSTile.SLOPE_FLAT && GSTile.GetMinHeight(tile) == height; }
    function Build() {
        foreach (type, unused in GSRailTypeList()) {
            GSLog.Info("HYPL railtype=" + type + " name=" + GSRail.GetName(type));
            if (GSRail.GetName(type).find("Hyperloop") != null) { GSRail.SetCurrentRailType(type); break; }
        }
        local x0 = -1, y0 = -1;
        for (local y = 16; y < GSMap.GetMapSizeY() - 16 && x0 == -1; y += 3) {
            for (local x = 16; x < GSMap.GetMapSizeX() - 230; x += 3) {
                local h = GSTile.GetMinHeight(GSMap.GetTileIndex(x, y));
                local flat = true;
                foreach (dx in [0, 1, 2, 3, 4, 5, 6, 207, 208, 209, 210]) {
                    if (!this.Flat(GSMap.GetTileIndex(x + dx, y), h)) flat = false;
                }
                for (local dy = -2; dy <= 2; dy++) if (!this.Flat(GSMap.GetTileIndex(x + 105, y + dy), h)) flat = false;
                if (flat) { x0 = x; y0 = y; break; }
            }
        }
        if (x0 == -1) { GSLog.Error("HYPL no fixture site"); return false; }
        local depot = GSMap.GetTileIndex(x0, y0);
        local front = GSMap.GetTileIndex(x0 + 1, y0);
        local near_station = GSMap.GetTileIndex(x0 + 2, y0);
        local a = GSMap.GetTileIndex(x0 + 5, y0);
        local b = GSMap.GetTileIndex(x0 + 207, y0);
        local far_station = GSMap.GetTileIndex(x0 + 208, y0);
        if (!GSTunnel.BuildHyperloopTube(a, b)) { GSLog.Error("HYPL tube: " + GSError.GetLastErrorString()); return false; }
        if (GSTunnel.GetOtherTunnelEnd(a) != b || GSTunnel.GetOtherTunnelEnd(b) != a) { GSLog.Error("HYPL endpoints disagree"); return false; }
        local surface_test = -1;
        for (local dy = 8; dy <= 20 && surface_test == -1; dy++) for (local dx = 40; dx <= 120; dx++) {
            local tile = GSMap.GetTileIndex(x0 + dx, y0 + dy);
            if (GSTile.IsBuildable(tile) && GSTile.GetSlope(tile) == GSTile.SLOPE_FLAT) { surface_test = tile; break; }
        }
        if (surface_test == -1 || GSRail.BuildRail(surface_test - 1, surface_test, surface_test + 1)) {
            GSLog.Error("HYPL surface route allowed"); return false;
        }
        GSLog.Info("HYPL surface_routes_rejected=true");
        local middle = GSMap.GetTileIndex(x0 + 105, y0);
        if (GSRail.IsRailTile(middle)) { GSLog.Error("HYPL occupies surface"); return false; }
        GSRoad.SetCurrentRoadType(GSRoad.ROADTYPE_ROAD);
        if (!GSRoad.BuildRoad(GSMap.GetTileIndex(x0 + 105, y0 - 2), GSMap.GetTileIndex(x0 + 105, y0 + 2))) {
            GSLog.Error("HYPL surface road: " + GSError.GetLastErrorString()); return false;
        }
        if (GSTunnel.BuildHyperloopTube(GSMap.GetTileIndex(x0 + 100, y0), GSMap.GetTileIndex(x0 + 210, y0))) {
            GSLog.Error("HYPL overlap allowed"); return false;
        }
        if (!GSRail.BuildRailDepot(depot, front) || !GSRail.BuildRail(depot, front, near_station) ||
            !GSRail.BuildRailStation(near_station, GSRail.RAILTRACK_NE_SW, 1, 3, GSStation.STATION_NEW) ||
            !GSRail.BuildRailStation(far_station, GSRail.RAILTRACK_NE_SW, 1, 3, GSStation.STATION_NEW)) {
            GSLog.Error("HYPL approaches: " + GSError.GetLastErrorString()); return false;
        }
        this.vehicle = this.Line(depot, near_station, far_station);
        if (this.vehicle == -1) { GSLog.Error("HYPL vehicle: " + GSError.GetLastErrorString()); return false; }
        this.home = a;
        this.other = b;
        if (!this.BuildViaduct(y0)) return false;
        GSLog.Info("HYPL fixture ready vehicle=" + this.vehicle + " surface_road=true overlap_rejected=true length=202");
        return true;
    }
    function Start() {
        while (GSCompany.ResolveCompanyID(0) == GSCompany.COMPANY_INVALID) this.Sleep(10);
        if (!this.ready) GSCompany.ChangeBankBalance(0, 100000000, GSCompany.EXPENSES_OTHER, GSMap.TILE_INVALID);
        local company_mode = GSCompanyMode(0);
        if (!this.ready) { this.ready = this.Build(); if (!this.ready) return; }
        while (true) {
            this.max_speed = max(this.max_speed, GSVehicle.GetCurrentSpeed(this.vehicle));
            if (GSVehicle.GetLocation(this.vehicle) == this.other) this.reached_far = true;
            if (GSVehicle.GetLocation(this.via_vehicle) == this.via_far) this.via_reached = true;
            if (this.reached_far && this.max_speed >= 3000 && this.via_reached) {
                GSLog.Info("HYPL viaduct reached_far=true");
                GSLog.Info("HYPL movement reached_far=true max_speed=" + this.max_speed);
                while (true) this.Sleep(100);
            }
            this.Sleep(5);
        }
    }
}
