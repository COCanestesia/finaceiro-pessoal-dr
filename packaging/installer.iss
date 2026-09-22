#define MyAppName "Financeiro Pessoal do Dr."
#define MyAppVersion "1.0.0"
#define MyAppExeName "FinanceiroPessoalDr.exe"

[Setup]
AppId={{B9FC7C42-7D67-4FD1-BD98-8B56917641D1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=COC
DefaultDirName={localappdata}\Programs\Financeiro Pessoal do Dr
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=FinanceiroPessoalDr-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\FinanceiroPessoalDr\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
