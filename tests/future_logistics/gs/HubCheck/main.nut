/* GPL-2.0-only. Changes only the isolated regression world. */
class HubCheck extends GSController {
    ready = false; site = -1; second = -1; small = -1; vehicle = -1; entered = false;
    function Save() { return { ready = this.ready, site = this.site, second = this.second, small = this.small, vehicle = this.vehicle, entered = this.entered }; }
    function Load(version, data) { foreach (key, value in data) this[key] = value; }
    function Tile(dx, dy) { return GSMap.GetTileIndex(GSMap.GetTileX(this.site) + dx, GSMap.GetTileY(this.site) + dy); }
    function Site(tile) {
        if (!GSTile.IsBuildableRectangle(tile, 8, 8)) return false;
        local height = GSTile.GetMinHeight(tile);
        local x = GSMap.GetTileX(tile), y = GSMap.GetTileY(tile);
        for (local dx = 0; dx < 8; dx++) for (local dy = 0; dy < 8; dy++) {
            local part = GSMap.GetTileIndex(x + dx, y + dy);
            if (GSRoad.IsRoadTile(part) || GSTile.GetSlope(part) != GSTile.SLOPE_FLAT || GSTile.GetMinHeight(part) != height) return false;
        }
        return true;
    }
    function Traffic() {
        GSRoad.SetCurrentRoadType(GSRoad.ROADTYPE_ROAD);
        if (!GSRoad.BuildRoad(this.Tile(4, 0), this.Tile(4, 4)) ||
            !GSRoad.BuildRoad(this.Tile(4, 4), this.Tile(5, 4)) ||
            !GSRoad.BuildRoadDepot(this.Tile(6, 4), this.Tile(5, 4)) ||
            !GSRoad.BuildRoadStation(this.Tile(5, 5), this.Tile(5, 4), GSRoad.ROADVEHTYPE_TRUCK, GSStation.STATION_NEW)) {
            GSLog.Error("HUB traffic infrastructure: " + GSError.GetLastErrorString()); return false;
        }
        local mail = -1, engine = -1;
        foreach (cargo, unused in GSCargoList()) if (GSCargo.GetCargoLabel(cargo) == "MAIL") mail = cargo;
        foreach (candidate, unused in GSEngineList(GSVehicle.VT_ROAD)) {
            if (GSEngine.GetCargoType(candidate) == mail && GSEngine.IsBuildable(candidate)) { engine = candidate; break; }
        }
        this.vehicle = GSVehicle.BuildVehicle(this.Tile(6, 4), engine);
        if (!GSVehicle.IsValidVehicle(this.vehicle) || !GSOrder.AppendOrder(this.vehicle, this.Tile(3, 0), GSOrder.OF_NONE) ||
            !GSOrder.AppendOrder(this.vehicle, this.Tile(5, 5), GSOrder.OF_NONE) || !GSVehicle.StartStopVehicle(this.vehicle)) {
            GSLog.Error("HUB traffic vehicle: " + GSError.GetLastErrorString()); return false;
        }
        return true;
    }
    function Start() {
        while (GSCompany.ResolveCompanyID(0) == GSCompany.COMPANY_INVALID) this.Sleep(10);
        if (!this.ready) {
            GSCompany.ChangeBankBalance(0, 100000000, GSCompany.EXPENSES_OTHER, GSMap.TILE_INVALID);
            local largest = -1, population = -1;
            foreach (town, unused in GSTownList()) if (GSTown.GetPopulation(town) > population) { largest = town; population = GSTown.GetPopulation(town); }
            GSTown.ExpandTown(largest, 1200);
            while (GSTown.GetPopulation(largest) < 5000) this.Sleep(100);
            local mode = GSCompanyMode(0);
            for (local y = 8; y < GSMap.GetMapSizeY() - 12 && this.second == -1; y += 4) {
                for (local x = 8; x < GSMap.GetMapSizeX() - 12; x += 4) {
                    local tile = GSMap.GetTileIndex(x, y);
                    if (GSTile.GetClosestTown(tile) != largest || !this.Site(tile)) continue;
                    if (this.site == -1) this.site = tile;
                    else if (max(abs(x - GSMap.GetTileX(this.site)), abs(y - GSMap.GetTileY(this.site))) >= 12) { this.second = tile; break; }
                }
            }
            foreach (town, unused in GSTownList()) if (GSTown.GetPopulation(town) < 5000) { this.small = GSTown.GetLocation(town); break; }
            this.ready = this.site != -1 && this.second != -1;
            if (!this.ready) { GSLog.Error("HUB no fixture sites"); return; }
            GSLog.Info("HUB fixture ready tile=" + this.site + " second=" + this.second + " small=" + this.small);
        }
        local mode = GSCompanyMode(0);
        while (true) {
            local complete = true, station = -1;
            for (local i = 0; i < 4; i++) {
                local tile = this.Tile(3, i);
                if (!GSRoad.IsRoadStationTile(tile)) { complete = false; break; }
                local next = GSStation.GetStationID(tile);
                if (station == -1) station = next;
                if (station != next) complete = false;
            }
            if (complete && this.vehicle == -1 && !this.Traffic()) return;
            if (this.vehicle != -1 && !this.entered && GSVehicle.GetCurrentSpeed(this.vehicle) == 0 &&
                GSRoad.IsRoadStationTile(GSVehicle.GetLocation(this.vehicle)) && GSStation.GetStationID(GSVehicle.GetLocation(this.vehicle)) == station) {
                this.entered = true;
                GSLog.Info("HUB truck entered loading bay vehicle=" + this.vehicle + " station=" + station);
            }
            this.Sleep(5);
        }
    }
}
