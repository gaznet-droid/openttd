/* GPL-2.0-only. */
class OrbitalCheck extends GSInfo {
    function GetAuthor() { return "Future Logistics"; }
    function GetName() { return "OrbitalCheck"; }
    function GetDescription() { return "Exercise real orbital loading, shared slots and save/reload"; }
    function GetVersion() { return 1; }
    function GetDate() { return "2026-10-26"; }
    function CreateInstance() { return "OrbitalCheck"; }
    function GetShortName() { return "ORBT"; }
    function GetAPIVersion() { return "15"; }
}
RegisterGS(OrbitalCheck());
