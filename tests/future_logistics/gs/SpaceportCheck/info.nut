/* GPL-2.0-only. */
class SpaceportCheck extends GSInfo {
    function GetAuthor() { return "Future Logistics"; }
    function GetName() { return "SpaceportCheck"; }
    function GetDescription() { return "Three spaceport pads and an airport in one station, each pad launching its own Starship"; }
    function GetVersion() { return 1; }
    function GetDate() { return "2026-10-31"; }
    function CreateInstance() { return "SpaceportCheck"; }
    function GetShortName() { return "SPCP"; }
    function GetAPIVersion() { return "15"; }
}
RegisterGS(SpaceportCheck());
