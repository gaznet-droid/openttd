/* GPL-2.0-only. Changes only the isolated regression world. */
class HubCheck extends GSController {
    ready = false; site = -1; second = -1; small = -1; vehicle = -1; entered = false;
    hub_visits = 0; return_visits = 0; last_stop = -1; probe_station = -1; joined = false;
    function Save() { return { ready = this.ready, site = this.site, second = this.second, small = this.small, vehicle = this.vehicle, entered = this.entered,
        hub_visits = this.hub_visits, return_visits = this.return_visits, last_stop = this.last_stop, probe_station = this.probe_station, joined = this.joined }; }
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
        if (!GSRoad.BuildRoad(this.Tile(4, 4), this.Tile(5, 4)) ||
            !GSRoad.BuildRoadDepot(this.Tile(6, 4), this.Tile(5, 4)) ||
            !GSRoad.BuildRoadStation(this.Tile(5, 5), this.Tile(5, 4), GSRoad.ROADVEHTYPE_TRUCK, GSStation.STATION_NEW)) {
            GSLog.Error("HUB traffic infrastructure: " + GSError.GetLastErrorString()); return false;
        }
        if (!GSRoad.BuildRoad(this.Tile(5, 4), this.Tile(6, 4)) ||
            !GSRoad.BuildRoad(this.Tile(5, 4), this.Tile(5, 5))) {
            GSLog.Error("HUB traffic approaches: " + GSError.GetLastErrorString()); return false;
        }
        for (local i = 0; i < 4; i++) {
            if (!GSRoad.AreRoadTilesConnected(this.Tile(4, i), this.Tile(3, i)) ||
                !GSRoad.AreRoadTilesConnected(this.Tile(3, i), this.Tile(4, i))) {
                GSLog.Error("HUB disconnected bay approach " + i); return false;
            }
        }
        GSLog.Info("HUB bay approaches connected automatically");
        if (!GSRoad.AreRoadTilesConnected(this.Tile(6, 4), this.Tile(5, 4)) ||
            !GSRoad.AreRoadTilesConnected(this.Tile(5, 4), this.Tile(6, 4)) ||
            !GSRoad.AreRoadTilesConnected(this.Tile(5, 4), this.Tile(5, 5)) ||
            !GSRoad.AreRoadTilesConnected(this.Tile(5, 5), this.Tile(5, 4))) {
            GSLog.Error("HUB disconnected depot or return approach"); return false;
        }
        GSLog.Info("HUB access connected bays=4 depot=true return=true");
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
        if (GSGameSettings.GetValue("station.distant_join_stations") != 0) {
            GSLog.Error("HUB regression requires distant station joining disabled"); return;
        }
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
        /* Road-stop queries use the script's current road type, which is not
         * restored by Load(). Select it before polling, not only in Traffic(). */
        GSRoad.SetCurrentRoadType(GSRoad.ROADTYPE_ROAD);
        if (this.probe_station == -1) {
            /* This ordinary stop touches the western warehouse side, not the eastern bay side.
             * A player-style hub placement must nevertheless append its four bays to this station. */
            if (!GSRoad.BuildRoad(this.Tile(-2, 0), this.Tile(-1, 0)) ||
                !GSRoad.BuildRoadStation(this.Tile(-1, 0), this.Tile(-2, 0), GSRoad.ROADVEHTYPE_TRUCK, GSStation.STATION_NEW)) {
                GSLog.Error("HUB join probe: " + GSError.GetLastErrorString()); return;
            }
            this.probe_station = GSStation.GetStationID(this.Tile(-1, 0));
            GSLog.Info("HUB join probe station=" + this.probe_station + " side=west");
            /* A road already runs along the bay side, as a town road often does, with no stubs into the bays:
             * building the hub must join the bays to it by itself. */
            if (!GSRoad.BuildRoad(this.Tile(4, 0), this.Tile(4, 4))) {
                GSLog.Error("HUB bay-side road: " + GSError.GetLastErrorString()); return;
            }
        }
        if (this.vehicle != -1) {
            GSLog.Info("HUB traffic restored vehicle=" + this.vehicle + " hub_visits=" + this.hub_visits + " return_visits=" + this.return_visits);
        }
        while (true) {
            local complete = true, station = -1;
            for (local i = 0; i < 4; i++) {
                local tile = this.Tile(3, i);
                if (!GSRoad.IsRoadStationTile(tile)) { complete = false; break; }
                local next = GSStation.GetStationID(tile);
                if (station == -1) station = next;
                if (station != next) complete = false;
            }
            if (complete && !this.joined) {
                if (station != this.probe_station) { GSLog.Error("HUB automatic join failed expected=" + this.probe_station + " actual=" + station); return; }
                this.joined = true;
                GSLog.Info("HUB automatic join station=" + station + " bays=4 warehouse_side=west");
            }
            if (complete && this.vehicle == -1 && !this.Traffic()) return;
            if (this.vehicle != -1 && GSVehicle.GetCurrentSpeed(this.vehicle) == 0 &&
                GSRoad.IsRoadStationTile(GSVehicle.GetLocation(this.vehicle))) {
                local stopped = GSStation.GetStationID(GSVehicle.GetLocation(this.vehicle));
                if (stopped == station && this.last_stop != station) {
                    if (!this.entered) {
                        this.entered = true;
                        GSLog.Info("HUB truck entered loading bay vehicle=" + this.vehicle + " station=" + station);
                    }
                    this.hub_visits++;
                    this.last_stop = stopped;
                    GSLog.Info("HUB traffic visit vehicle=" + this.vehicle + " kind=hub count=" + this.hub_visits + " tile=" + GSVehicle.GetLocation(this.vehicle));
                } else if (GSVehicle.GetLocation(this.vehicle) == this.Tile(5, 5) && this.last_stop != stopped) {
                    this.return_visits++;
                    this.last_stop = stopped;
                    GSLog.Info("HUB traffic visit vehicle=" + this.vehicle + " kind=return count=" + this.return_visits);
                }
            }
            this.Sleep(5);
        }
    }
}
