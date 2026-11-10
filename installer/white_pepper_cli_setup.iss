; Inno Setup 6 Script for White Pepper Standalone CLI Engine
; Author: AceBurgundy <Samadriansabalo99@gmail.com>

#define MyAppName "White Pepper CLI Engine"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "AceBurgundy"
#define MyAppURL "https://github.com/AceBurgundy/white_pepper_scripts"
#define MyAppExeName "scan-cli.cmd"

[Setup]
AppId={{5C89F311-82A1-420E-B892-F16E87A5B9C2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\White Pepper CLI
DefaultGroupName=White Pepper CLI
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=WhitePepper-CLI-Setup-v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\installer\app_icon.ico
UninstallDisplayName={#MyAppName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "addtopath"; Description: "Add White Pepper CLI (bin/) to user PATH environment variable"; Flags: unchecked

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".git\*,.old.git*\,__pycache__\*,*.pyc,*.pyo,installer\output\*,scratch\*,test_output\*"

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}\bin'))

[Icons]
Name: "{group}\Command Prompt with White Pepper CLI"; Filename: "{cmd}"; Parameters: "/K set ""PATH={app}\bin;%PATH%"" & title White Pepper CLI"; IconFilename: "{app}\installer\app_icon.ico"
Name: "{group}\White Pepper CLI Documentation"; Filename: "{app}\documentation\index.html"; IconFilename: "{app}\installer\app_icon.ico"; Flags: createonlyiffileexists
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\white_pepper\__pycache__"
Type: filesandordirs; Name: "{app}\white_pepper\*\__pycache__"

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + UpperCase(Param) + ';', ';' + UpperCase(OrigPath) + ';') = 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  BinDir, OrigPath: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    BinDir := ExpandConstant('{app}\bin');
    if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
    begin
      StringChangeEx(OrigPath, ';' + BinDir, '', True);
      StringChangeEx(OrigPath, BinDir + ';', '', True);
      StringChangeEx(OrigPath, BinDir, '', True);
      RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath);
    end;
  end;
end;
