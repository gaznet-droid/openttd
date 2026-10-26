/* GPL-2.0-only. */
class HyperloopCheck extends GSInfo {
    function GetAuthor() { return "Future Logistics"; }
    function GetName() { return "HyperloopCheck"; }
    function GetDescription() { return "Native underground tubes, independent surface land and moving pods"; }
    function GetVersion() { return 1; }
    function GetDate() { return "2026-10-26"; }
    function CreateInstance() { return "HyperloopCheck"; }
    function GetShortName() { return "HYPC"; }
    function GetAPIVersion() { return "15"; }
}
RegisterGS(HyperloopCheck());
