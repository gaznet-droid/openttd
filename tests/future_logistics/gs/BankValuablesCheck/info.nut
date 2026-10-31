/* GPL-2.0-only. Regression script for temperate Bank Valuables production. */
class BankValuablesCheck extends GSInfo {
    function GetAuthor() { return "Future Logistics"; }
    function GetName() { return "BankValuablesCheck"; }
    function GetDescription() { return "Builds a temperate Bank and reports Valuables production"; }
    function GetVersion() { return 1; }
    function GetDate() { return "2026-10-30"; }
    function CreateInstance() { return "BankValuablesCheck"; }
    function GetShortName() { return "BNKV"; }
    function GetAPIVersion() { return "15"; }
}
RegisterGS(BankValuablesCheck());
