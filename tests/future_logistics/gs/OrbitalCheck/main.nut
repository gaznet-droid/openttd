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
            if (!GSFutureLogistics.BuildService(2, "rocket/airport_pair/town_pair")) {
                GSLog.Error("ORBIT fixture build failed: " + GSError.GetLastErrorString());
                return;
            }
            local ships = GSVehicleList();
            ships.Valuate(GSVehicle.GetVehicleType);
            ships.KeepValue(GSVehicle.VT_AIR);
            if (ships.Count() == 0) { GSLog.Error("ORBIT no ships"); return; }
            local ship = ships.Begin();
            local depot = GSFutureLogistics.GetRouteDepot(ship);
            if (ships.Count() < 2) {
                local clone = GSVehicle.CloneVehicle(depot, ship, false);
                if (!GSVehicle.IsValidVehicle(clone) || !GSVehicle.StartStopVehicle(clone)) {
                    GSLog.Error("ORBIT clone failed: " + GSError.GetLastErrorString()); return;
                }
            }
            local town = GSTile.GetClosestTown(depot);
            company_mode = null;
            GSTown.ExpandTown(town, 400);
            this.ready = true;
            GSLog.Info("ORBIT fixture ready home=" + depot + " town=" + town);
        }
        while (true) this.Sleep(100);
    }
}
