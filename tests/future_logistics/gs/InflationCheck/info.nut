/* GPL-2.0-only. Regression script for a controlled 2050 economy-price probe. */
class InflationCheck extends GSInfo {
    function GetAuthor() { return "Future Logistics"; }
    function GetName() { return "InflationCheck"; }
    function GetDescription() { return "Reports controlled road and airport build prices"; }
    function GetVersion() { return 1; }
    function GetDate() { return "2026-10-30"; }
    function CreateInstance() { return "InflationCheck"; }
    function GetShortName() { return "INFL"; }
    function GetAPIVersion() { return "15"; }
}
RegisterGS(InflationCheck());
