/* GPL-2.0-only. Read-only probe; never changes settings, companies or prices. */
class InflationCheck extends GSController {
    function Start() {
        GSLog.Info("FL inflation probe year=" + GSDate.GetYear(GSDate.GetCurrentDate()) +
            " setting=" + GSGameSettings.GetValue("economy.inflation") +
            " road=" + GSRoad.GetBuildCost(GSRoad.ROADTYPE_ROAD, GSRoad.BT_ROAD) +
            " truck_stop=" + GSRoad.GetBuildCost(GSRoad.ROADTYPE_ROAD, GSRoad.BT_TRUCK_STOP) +
            " road_depot=" + GSRoad.GetBuildCost(GSRoad.ROADTYPE_ROAD, GSRoad.BT_DEPOT) +
            " international_airport=" + GSAirport.GetPrice(GSAirport.AT_INTERNATIONAL));
        while (true) this.Sleep(1000);
    }
}
