/* GPL-2.0-only. */
class HubCheck extends GSInfo {
    function GetAuthor() { return "Future Logistics"; }
    function GetName() { return "HubCheck"; }
    function GetDescription() { return "Distribution hub construction and live loading bays"; }
    function GetVersion() { return 1; }
    function GetDate() { return "2026-10-26"; }
    function CreateInstance() { return "HubCheck"; }
    function GetShortName() { return "HUBC"; }
    function GetAPIVersion() { return "15"; }
}
RegisterGS(HubCheck());
