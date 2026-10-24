#define AppName "Lockstep"
#define AppVersion "0.2.1"
#define AppPublisher "Lockstep"

[Setup]
AppId={{B592E854-DB7D-4D0A-93B5-1AAEFBF5C37A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\Lockstep
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\build\installer
OutputBaseFilename=Lockstep-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\lockstep.exe

[Files]
Source: "..\src-tauri\target\release\lockstep.exe"; DestDir: "{app}"; Flags: ignoreversion
#if FileExists("..\build\sidecar\lockstep-agent.exe")
Source: "..\build\sidecar\lockstep-agent.exe"; DestDir: "{app}\resources\agent"; Flags: ignoreversion
#endif

[Icons]
Name: "{autoprograms}\Lockstep"; Filename: "{app}\lockstep.exe"
Name: "{autodesktop}\Lockstep"; Filename: "{app}\lockstep.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

[Run]
Filename: "{app}\lockstep.exe"; Description: "Lockstep starten"; Flags: postinstall nowait skipifsilent
