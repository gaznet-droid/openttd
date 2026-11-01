/* GPL-2.0-only. Isolated test-world fixture, using ordinary construction and cargo generation. */
class OrbitalCheck extends GSController {
    ready = false;
    function Save() { return { ready = this.ready }; }
    function Load(version, data) { if ("ready" in data) this.ready = data.ready; }
    function Start() {
        if (!this.ready) {
            while (GSCompany.ResolveCompanyID(0) == GSCompany.COMPANY_INVALID) this.Sleep(10);
            GSCompany.ChangeBankBalance(0, 100000000, GSCompany.EXPENSES_OTHER, GSMap.TILE_INVALID);
            local company_mode = GSCompanyMode(0);
            local airport_type = -1, pass = -1, engine = -1;
            for (local type = 0; type < 128; type++) {
                if (GSAirport.IsValidAirportType(type) && GSAirport.GetAirportWidth(type) * GSAirport.GetAirportHeight(type) == 12 && GSAirport.GetAirportWidth(type) >= 3) {
                    airport_type = type; break;
                }
            }
            foreach (cargo, unused in GSCargoList()) if (GSCargo.GetCargoLabel(cargo) == "PASS") pass = cargo;
            foreach (type, unused in GSEngineList(GSVehicle.VT_AIR)) if (GSEngine.GetName(type) == "Starship") engine = type;
            if (airport_type == -1 || pass == -1 || engine == -1) { GSLog.Error("ORBIT missing tagged content"); return; }
            local site = GSMap.TILE_INVALID, best_production = -1;
            /* Pick a busy catchment rather than the first edge tile accepting passengers. */
            foreach (town, unused in GSTownList()) {
                local centre = GSTown.GetLocation(town);
                local cx = GSMap.GetTileX(centre), cy = GSMap.GetTileY(centre);
                for (local y = max(8, cy - 14); y <= min(GSMap.GetMapSizeY() - 8, cy + 14); y++) {
                    for (local x = max(8, cx - 14); x <= min(GSMap.GetMapSizeX() - 8, cx + 14); x++) {
                        local tile = GSMap.GetTileIndex(x, y);
                        if (!GSTile.IsBuildableRectangle(tile, 4, 4) || GSTile.GetCargoAcceptance(tile, pass, 3, 4, 6) < 8) continue;
                        local production = GSTile.GetCargoProduction(tile, pass, 3, 4, 6);
                        if (production <= best_production) continue;
                        local test_mode = GSTestMode();
                        if (GSAirport.BuildAirport(tile, airport_type, GSStation.STATION_NEW)) { site = tile; best_production = production; }
                    }
                }
            }
            if (site != GSMap.TILE_INVALID && !GSAirport.BuildAirport(site, airport_type, GSStation.STATION_NEW)) site = GSMap.TILE_INVALID;
            if (site == GSMap.TILE_INVALID) { GSLog.Error("ORBIT no launch site: " + GSError.GetLastErrorString()); return; }
            local spaceport_name = GSStation.GetName(GSStation.GetStationID(site));
            if (spaceport_name.find("Spaceport") == null) { GSLog.Error("ORBIT wrong station name: " + spaceport_name); return; }
            /* The spaceport's catchment reaches 12 tiles beyond its edge, so it can serve a town from outside it. */
            local cover = GSTileList_StationCoverage(GSStation.GetStationID(site));
            local x0 = 99999, x1 = -1, y0 = 99999, y1 = -1;
            foreach (t, unused in cover) {
                x0 = min(x0, GSMap.GetTileX(t)); x1 = max(x1, GSMap.GetTileX(t));
                y0 = min(y0, GSMap.GetTileY(t)); y1 = max(y1, GSMap.GetTileY(t));
            }
            GSLog.Info("ORBIT catchment radius=" + GSAirport.GetAirportCoverageRadius(airport_type) +
                " reach_x=" + (GSMap.GetTileX(site) - x0) + " reach_y=" + (GSMap.GetTileY(site) - y0) +
                " span=" + (x1 - x0 + 1) + "x" + (y1 - y0 + 1) +
                " footprint=" + GSAirport.GetAirportWidth(airport_type) + "x" + GSAirport.GetAirportHeight(airport_type));
            local depot = GSAirport.GetHangarOfAirport(site);
            local ship = GSVehicle.BuildVehicle(depot, engine);
            if (!GSVehicle.IsValidVehicle(ship)) { GSLog.Error("ORBIT build failed: " + GSError.GetLastErrorString()); return; }
            GSOrder.AppendOrder(ship, site, GSOrder.OF_NONE);
            local copy = GSVehicle.CloneVehicle(depot, ship, false);
            if (!GSVehicle.IsValidVehicle(copy) || !GSVehicle.StartStopVehicle(copy) || !GSVehicle.StartStopVehicle(ship)) {
                GSLog.Error("ORBIT fleet start failed: " + GSError.GetLastErrorString()); return;
            }
            local town = GSTile.GetClosestTown(depot);
            company_mode = null;
            GSTown.ExpandTown(town, 4000);
            this.ready = true;
            GSLog.Info("ORBIT fixture ready home=" + depot + " town=" + town + " production=" + best_production + " station=" + spaceport_name);
        }
        while (true) this.Sleep(100);
    }
}
