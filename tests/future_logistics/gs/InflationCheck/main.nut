/* GPL-2.0-only. Runs only in an isolated integration-test world. */
class InflationCheck extends GSController {
    function Save() { return {}; }
    function Start() {
        while (GSCompany.ResolveCompanyID(0) == GSCompany.COMPANY_INVALID) this.Sleep(10);
        if (!GSGameSettings.IsValid("economy.inflation")) {
            GSLog.Error("INFLATION setting unavailable");
            return;
        }
        local company_mode = GSCompanyMode(0);
        GSRoad.SetCurrentRoadType(GSRoad.ROADTYPE_ROAD);
        local road = GSRoad.GetBuildCost(GSRoad.ROADTYPE_ROAD, GSRoad.BT_ROAD);
        local truck_stop = GSRoad.GetBuildCost(GSRoad.ROADTYPE_ROAD, GSRoad.BT_TRUCK_STOP);
        local depot = GSRoad.GetBuildCost(GSRoad.ROADTYPE_ROAD, GSRoad.BT_DEPOT);
        local airport = GSAirport.GetPrice(GSAirport.AT_INTERNATIONAL);
        GSLog.Info("INFLATION probe setting=" + GSGameSettings.GetValue("economy.inflation")
            + " road=" + road + " truck_stop=" + truck_stop + " depot=" + depot
            + " international_airport=" + airport);
    }
}
