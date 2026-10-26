/* GPL-2.0-only. Run only in the isolated integration-test world. */
class DataCentreCheck extends GSController {
    function Start() {
        local type = GSIndustryType.ResolveNewGRFID(0x464C0101, 0);
        if (!GSIndustryType.IsValidIndustryType(type)) { GSLog.Error("DC missing industry"); return; }
        while (GSCompany.ResolveCompanyID(0) == GSCompany.COMPANY_INVALID) this.Sleep(10);
        GSCompany.ChangeBankBalance(0, 100000000, GSCompany.EXPENSES_OTHER, GSMap.TILE_INVALID);
        local company_mode = GSCompanyMode(0);
        local first_town = -1;
        local second_town = -1;
        local rejected_duplicate = false;
        local built = 0;
        /* Search open 4x4 sites, explicitly excluding house tiles. The old bank-derived
         * industry rejected all of these even when its town had no data centre. */
        for (local y = 8; y < GSMap.GetMapSizeY() - 8; y += 4) {
            for (local x = 8; x < GSMap.GetMapSizeX() - 8; x += 4) {
                local tile = GSMap.GetTileIndex(x, y);
                if (!GSTile.IsBuildableRectangle(tile, 4, 4)) continue;
                local flat = true;
                local height = GSTile.GetMinHeight(tile);
                for (local dx = 0; dx < 4; dx++) for (local dy = 0; dy < 4; dy++) {
                    local part = GSMap.GetTileIndex(x + dx, y + dy);
                    if (GSTile.GetSlope(part) != GSTile.SLOPE_FLAT || GSTile.GetMinHeight(part) != height) flat = false;
                }
                if (!flat) continue;
                local town = GSTile.GetClosestTown(tile);
                if (first_town == -1 && GSTown.GetPopulation(town) >= 1200) continue;
                if (first_town != -1 && town != first_town && second_town != -1) continue;
                if (town == first_town && rejected_duplicate) continue;
                if (town == first_town) {
                    if (!GSIndustryType.BuildIndustry(type, tile)) {
                        local error = GSError.GetLastErrorString();
                        GSLog.Info("DC duplicate result=" + error);
                        rejected_duplicate = true; /* Script API maps the per-town NewGRF rejection to ERR_UNKNOWN. */
                    }
                    else { GSLog.Error("DC duplicate allowed"); return; }
                } else if (GSIndustryType.BuildIndustry(type, tile)) {
                    built++;
                    if (first_town == -1) first_town = town;
                    else second_town = town;
                    GSLog.Info("DC funded town=" + town + " population=" + GSTown.GetPopulation(town) + " tile=" + tile);
                }
                if (built == 2 && rejected_duplicate) {
                    GSLog.Info("DC placement built=2 different_towns=true duplicate_rejected=true open_land=true");
                    return;
                }
            }
        }
        GSLog.Error("DC placement incomplete built=" + built + " duplicate=" + rejected_duplicate + " error=" + GSError.GetLastErrorString());
    }
}
