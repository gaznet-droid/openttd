/* GPL-2.0-only. Isolated test-world fixture: a station of three spaceport pads with an airport docked beside them. */
class SpaceportCheck extends GSController {
    ready = false;
    function Save() { return { ready = this.ready }; }
    function Load(version, data) { if ("ready" in data) this.ready = data.ready; }
    /* Flat, buildable land all at one height. */
    function Level(tile, w, h) {
        if (!GSTile.IsBuildableRectangle(tile, w, h)) return false;
        local height = GSTile.GetMinHeight(tile);
        local x0 = GSMap.GetTileX(tile), y0 = GSMap.GetTileY(tile);
        for (local y = y0; y < y0 + h; y++) for (local x = x0; x < x0 + w; x++) {
            local t = GSMap.GetTileIndex(x, y);
            if (GSTile.GetSlope(t) != GSTile.SLOPE_FLAT || GSTile.GetMinHeight(t) != height) return false;
        }
        return true;
    }
    function Fail(what) { GSLog.Error("PADS " + what + ": " + GSError.GetLastErrorString()); }
    function Start() {
        if (!this.ready) {
            while (GSCompany.ResolveCompanyID(0) == GSCompany.COMPANY_INVALID) this.Sleep(10);
            GSCompany.ChangeBankBalance(0, 200000000, GSCompany.EXPENSES_OTHER, GSMap.TILE_INVALID);
            local company_mode = GSCompanyMode(0);
            local pad_type = -1, airport_type = -1, pass = -1, starship = -1;
            foreach (type, unused in GSEngineList(GSVehicle.VT_AIR)) if (GSEngine.GetName(type) == "Starship") starship = type;
            foreach (cargo, unused in GSCargoList()) if (GSCargo.GetCargoLabel(cargo) == "PASS") pass = cargo;
            for (local type = 0; type < 128; type++) {
                if (!GSAirport.IsValidAirportType(type)) continue;
                local w = GSAirport.GetAirportWidth(type), h = GSAirport.GetAirportHeight(type);
                if (pad_type == -1 && w * h == 12 && w >= 3) { pad_type = type; continue; }
                /* An ordinary airport small enough to sit beside the pads. */
                if (airport_type == -1 && w * h != 12 && w <= 6 && h <= 6) airport_type = type;
            }
            if (pad_type == -1 || airport_type == -1 || pass == -1 || starship == -1) { GSLog.Error("PADS missing content pad=" + pad_type + " airport=" + airport_type); return; }
            /* The pads are three tiles along x once rotated: three of them, then the airport, in one row. */
            local aw = GSAirport.GetAirportWidth(airport_type), ah = GSAirport.GetAirportHeight(airport_type);
            local span_x = 9 + max(aw, ah) + 1, span_y = max(4, max(aw, ah)) + 1;
            local site = GSMap.TILE_INVALID, best = -1;
            foreach (town, unused in GSTownList()) {
                local centre = GSTown.GetLocation(town);
                local cx = GSMap.GetTileX(centre), cy = GSMap.GetTileY(centre);
                for (local y = max(8, cy - 16); y <= min(GSMap.GetMapSizeY() - 16, cy + 16); y += 2) {
                    for (local x = max(8, cx - 20); x <= min(GSMap.GetMapSizeX() - 24, cx + 20); x += 2) {
                        local tile = GSMap.GetTileIndex(x, y);
                        local production = GSTile.GetCargoProduction(tile, pass, 3, 4, 12);
                        if (production <= best || !this.Level(tile, span_x, span_y)) continue;
                        local test_mode = GSTestMode();
                        if (GSAirport.BuildAirport(tile, pad_type, GSStation.STATION_NEW)) { site = tile; best = production; }
                    }
                }
            }
            if (site == GSMap.TILE_INVALID) { this.Fail("no site"); return; }
            local x = GSMap.GetTileX(site), y = GSMap.GetTileY(site);
            local pads = [site, GSMap.GetTileIndex(x + 3, y), GSMap.GetTileIndex(x + 6, y)];
            if (!GSAirport.BuildAirport(pads[0], pad_type, GSStation.STATION_NEW)) { this.Fail("first pad"); return; }
            local station = GSStation.GetStationID(pads[0]);
            /* More pads beside the first join the same station. */
            for (local i = 1; i < 3; i++) {
                if (!GSAirport.BuildAirport(pads[i], pad_type, GSStation.STATION_JOIN_ADJACENT)) { this.Fail("pad " + i); return; }
                if (GSStation.GetStationID(pads[i]) != station) { GSLog.Error("PADS pad " + i + " is a separate station"); return; }
            }
            /* A fourth is refused. */
            local fourth = GSMap.GetTileIndex(x + 9, y);
            if (GSAirport.BuildAirport(fourth, pad_type, GSStation.STATION_JOIN_ADJACENT)) { GSLog.Error("PADS fourth pad allowed"); return; }
            if (GSError.GetLastErrorString() == "ERR_FLAT_LAND_REQUIRED" || GSError.GetLastErrorString() == "ERR_AREA_NOT_CLEAR") { this.Fail("fourth pad site"); return; }
            GSLog.Info("PADS fourth_pad_refused=true error=" + GSError.GetLastErrorString());
            /* An ordinary airport docks to the side and shares the station. */
            if (!GSAirport.BuildAirport(fourth, airport_type, GSStation.STATION_JOIN_ADJACENT)) { this.Fail("airport"); return; }
            if (GSStation.GetStationID(fourth) != station) { GSLog.Error("PADS airport is a separate station"); return; }
            local airport_hangar = GSAirport.GetHangarOfAirport(fourth);
            if (GSMap.IsValidTile(airport_hangar) && GSVehicle.IsValidVehicle(GSVehicle.BuildVehicle(airport_hangar, starship))) { GSLog.Error("PADS Starship built at the airport"); return; }
            /* One Starship per pad, each from its own pad's hangar. */
            local hangars = {};
            foreach (pad in pads) {
                local hangar = GSAirport.GetHangarOfAirport(pad);
                if (!GSMap.IsValidTile(hangar) || hangar in hangars) { GSLog.Error("PADS pad hangar missing or shared"); return; }
                hangars[hangar] <- true;
                local ship = GSVehicle.BuildVehicle(hangar, starship);
                if (!GSVehicle.IsValidVehicle(ship)) { this.Fail("Starship"); return; }
                GSOrder.AppendOrder(ship, pad, GSOrder.OF_NONE);
                if (!GSVehicle.StartStopVehicle(ship)) { this.Fail("start"); return; }
            }
            local town = GSTile.GetClosestTown(site);
            company_mode = null;
            GSTown.ExpandTown(town, 6000);
            this.ready = true;
            GSLog.Info("PADS fixture ready station=" + station + " pads=" + pads[0] + "," + pads[1] + "," + pads[2] + " airport=" + fourth + " name=" + GSStation.GetName(station));
        }
        while (true) this.Sleep(100);
    }
}
