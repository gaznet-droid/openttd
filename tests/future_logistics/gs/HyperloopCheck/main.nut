/* GPL-2.0-only. All changes are confined to the isolated regression world. */
class HyperloopCheck extends GSController {
    ready = false;
    vehicle = -1;
    home = -1;
    other = -1;
    max_speed = 0;
    reached_far = false;
    function Save() { return { ready = this.ready, vehicle = this.vehicle, home = this.home,
                              other = this.other, max_speed = this.max_speed, reached_far = this.reached_far }; }
    function Load(version, data) {
        foreach (key, value in data) this[key] = value;
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
        local pod = -1, capsule = -1;
        foreach (engine, unused in GSEngineList(GSVehicle.VT_RAIL)) {
            if (GSEngine.GetName(engine) == "Hyperloop Propulsion Pod") pod = engine;
            if (GSEngine.GetName(engine) == "Hyperloop Passenger Capsule") capsule = engine;
        }
        this.vehicle = GSVehicle.BuildVehicle(depot, pod);
        local wagon = GSVehicle.BuildVehicle(depot, capsule);
        if (!GSVehicle.IsValidVehicle(this.vehicle) || !GSVehicle.IsValidVehicle(wagon) ||
            !GSVehicle.MoveWagon(wagon, 0, this.vehicle, 0) ||
            !GSOrder.AppendOrder(this.vehicle, near_station, GSOrder.OF_NONE) ||
            !GSOrder.AppendOrder(this.vehicle, far_station, GSOrder.OF_NONE) ||
            !GSVehicle.StartStopVehicle(this.vehicle)) {
            GSLog.Error("HYPL vehicle: " + GSError.GetLastErrorString()); return false;
        }
        this.home = a;
        this.other = b;
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
            if (this.reached_far && this.max_speed >= 3000) {
                GSLog.Info("HYPL movement reached_far=true max_speed=" + this.max_speed);
                while (true) this.Sleep(100);
            }
            this.Sleep(5);
        }
    }
}
