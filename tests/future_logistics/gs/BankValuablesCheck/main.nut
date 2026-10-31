/* GPL-2.0-only. Runs only in an isolated integration-test world. */
class BankValuablesCheck extends GSController {
    function Save() { return {}; }

    function WaitForFollowingEconomyMonth() {
        local date = GSDate.GetCurrentDate();
        local year = GSDate.GetYear(date);
        local month = GSDate.GetMonth(date);
        while (GSDate.GetYear(GSDate.GetCurrentDate()) == year && GSDate.GetMonth(GSDate.GetCurrentDate()) == month) this.Sleep(74);
    }

    function Start() {
        const BANK_TEMP = 12;
        while (GSCompany.ResolveCompanyID(0) == GSCompany.COMPANY_INVALID) this.Sleep(10);
        local valuables = -1;
        foreach (cargo, unused in GSCargoList()) if (GSCargo.GetCargoLabel(cargo) == "VALU") valuables = cargo;
        if (valuables == -1 || !GSIndustryType.IsValidIndustryType(BANK_TEMP) || GSIndustryType.GetName(BANK_TEMP) != "Bank") {
            GSLog.Error("BANK missing temperate Bank or Valuables cargo");
            return;
        }
        local largest = -1, population = -1;
        foreach (town, unused in GSTownList()) if (GSTown.GetPopulation(town) > population) { largest = town; population = GSTown.GetPopulation(town); }
        GSTown.ExpandTown(largest, 1200);
        while (GSTown.GetPopulation(largest) < 1200) this.Sleep(10);
        GSLog.Info("BANK town=" + largest + " population=" + GSTown.GetPopulation(largest) + " date=" + GSDate.GetCurrentDate());
        GSCompany.ChangeBankBalance(0, 100000000, GSCompany.EXPENSES_OTHER, GSMap.TILE_INVALID);
        local company_mode = GSCompanyMode(0);
        local bank = -1;
        /* A base Bank is a 2x1 town-replacement industry, not an open-land facility. */
        for (local y = 1; y < GSMap.GetMapSizeY() - 1 && bank == -1; y++) {
            for (local x = 1; x < GSMap.GetMapSizeX() - 2; x++) {
                local tile = GSMap.GetTileIndex(x, y);
                local east = GSMap.GetTileIndex(x + 1, y);
                if (GSTile.GetClosestTown(tile) != largest || GSTile.GetClosestTown(east) != largest ||
                        !GSTile.IsHouseTile(tile) || !GSTile.IsHouseTile(east)) continue;
                if (GSIndustryType.BuildIndustry(BANK_TEMP, tile)) bank = GSIndustry.GetIndustryID(tile);
            }
        }
        if (!GSIndustry.IsValidIndustry(bank)) { GSLog.Error("BANK construction failed: " + GSError.GetLastErrorString()); return; }
        GSLog.Info("BANK built industry=" + bank + " date=" + GSDate.GetCurrentDate());
        /* Discard the construction month, then sample several whole following economy months. */
        this.WaitForFollowingEconomyMonth();
        for (local month = 1; month <= 4; month++) {
            this.WaitForFollowingEconomyMonth();
            local output = GSIndustry.GetLastMonthProduction(bank, valuables);
            GSLog.Info("BANK month=" + month + " date=" + GSDate.GetCurrentDate() + " last_month=" + output);
            if (output > 0) {
                GSLog.Info("BANK valuables type=12 industry=" + bank + " last_month=" + output);
                return;
            }
        }
        GSLog.Error("BANK did not report a completed production month");
    }
}
