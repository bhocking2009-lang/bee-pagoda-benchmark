; Bee Pagoda Benchmark — Inno Setup installer script
; Produces a standard Windows installer (.exe) for the PyInstaller bundle.
;
; Prerequisites:
;   1. Build the PyInstaller bundle first:
;        .\packaging\build-windows.ps1
;   2. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
;   3. Run:
;        iscc packaging\bee-pagoda-benchmark.iss
;
; Output: packaging\output\BeePageodaBenchmark-Setup-1.0.0.exe

#define AppName    "Bee Pagoda Benchmark"
#define AppVersion "1.0.0"
#define AppPublisher "Bee Pagoda"
#define AppURL     "https://github.com/bhocking2009-lang/bee-pagoda-benchmark"
#define AppExeName "bee-pagoda-benchmark.exe"
#define DistDir    "..\dist\bee-pagoda-benchmark"

[Setup]
AppId={{F3A4C8D2-6E91-4B5F-AA32-1D7E9F4C8B06}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=output
OutputBaseFilename=BeePageodaBenchmark-Setup-{#AppVersion}
SetupIconFile=bee-pagoda.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";         GroupDescription: "{cm:AdditionalIcons}"
Name: "startmenuicon";  Description: "Create Start Menu shortcut";     GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application bundle (PyInstaller output)
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Benchmark scripts
Source: "..\scripts\*";   DestDir: "{app}\scripts";   Flags: ignoreversion recursesubdirs
Source: "..\profiles\*";  DestDir: "{app}\profiles";  Flags: ignoreversion recursesubdirs
Source: "..\run_suite.ps1"; DestDir: "{app}";          Flags: ignoreversion

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\BeePagodaBenchmark"
