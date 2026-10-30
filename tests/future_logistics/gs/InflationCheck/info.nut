/* GPL-2.0-only. */
class InflationCheck extends GSInfo {
    function GetAuthor() { return "Future Logistics"; }
    function GetName() { return "InflationCheck"; }
    function GetDescription() { return "Read-only price probe for fresh 2050 inflation comparisons"; }
    function GetVersion() { return 1; }
    function GetDate() { return "2026-10-30"; }
    function CreateInstance() { return "InflationCheck"; }
    function GetShortName() { return "INFL"; }
    function GetAPIVersion() { return "15"; }
}
RegisterGS(InflationCheck());
