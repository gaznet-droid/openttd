/* GPL-2.0-only. Regression script for player-funded data-centre placement. */
class DataCentreCheck extends GSInfo {
    function GetAuthor() { return "Future Logistics"; }
    function GetName() { return "DataCentreCheck"; }
    function GetDescription() { return "Tests open-land placement and one data centre per town"; }
    function GetVersion() { return 1; }
    function GetDate() { return "2026-10-25"; }
    function CreateInstance() { return "DataCentreCheck"; }
    function GetShortName() { return "DCTR"; }
    function GetAPIVersion() { return "15"; }
}
RegisterGS(DataCentreCheck());
