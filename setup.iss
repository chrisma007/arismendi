
[Setup]
; Identificador único para esta aplicación. ¡No lo cambies si quieres que las actualizaciones reemplacen a la versión anterior!
AppId={{5D0E81C0-333B-4C67-B029-A71B120FDE1D}
AppName=Sistema Escolar Nexus
AppVersion=6.6
AppPublisher=Nexus Academic Solutions
AppPublisherURL=https://github.com/RagnarokManifests
AppSupportURL=https://github.com/RagnarokManifests
AppUpdatesURL=https://github.com/RagnarokManifests/msp2.0
; Se instala en AppData/Local para que no pida permisos de Administrador
DefaultDirName={localappdata}\NexusAcademic
DefaultGroupName=Sistema Escolar Nexus
DisableProgramGroupPage=yes
; Directorio de salida del instalador
OutputDir=Output
OutputBaseFilename=Instalar_Nexus_v6.6
SetupIconFile=logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Sistema_Escolar_Nexus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Sistema Escolar Nexus"; Filename: "{app}\Sistema_Escolar_Nexus.exe"
Name: "{autodesktop}\Sistema Escolar Nexus"; Filename: "{app}\Sistema_Escolar_Nexus.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Sistema_Escolar_Nexus.exe"; Description: "{cm:LaunchProgram,Sistema Escolar Nexus}"; Flags: nowait postinstall
