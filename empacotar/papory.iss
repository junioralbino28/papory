; Instalador do Papory (Inno Setup 6). Monta a partir da pasta do PyInstaller:
;   iscc /DVersao=0.1.0 empacotar\papory.iss      ->  empacotar\saida\Papory-Setup-0.1.0.exe
; Instala só para o usuário (sem administrador). Os dados da pessoa (%APPDATA%\Papory) ficam ao desinstalar.

#ifndef Versao
  #define Versao "0.1.0"
#endif

[Setup]
AppId={{61CBFE1F-EE4F-4231-8EC6-5CCCE47CF3EB}
AppName=Papory
AppVersion={#Versao}
AppVerName=Papory {#Versao}
AppPublisher=Papory
AppPublisherURL=https://github.com/junioralbino28/papory
AppSupportURL=https://github.com/junioralbino28/papory/issues
DefaultDirName={localappdata}\Programs\Papory
DefaultGroupName=Papory
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=saida
OutputBaseFilename=Papory-Setup-{#Versao}
SetupIconFile=..\marca\papory.ico
UninstallDisplayIcon={app}\Papory.exe
UninstallDisplayName=Papory
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar atalho na Área de Trabalho"
Name: "iniciar"; Description: "Abrir o Papory junto com o Windows"; Flags: unchecked

[Files]
Source: "dist\Papory\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Papory"; Filename: "{app}\Papory.exe"
Name: "{userdesktop}\Papory"; Filename: "{app}\Papory.exe"; Tasks: atalho

[Registry]
; mesmo nome e formato que papory/plataforma/windows.py usa (a opção nas Configurações liga e desliga isto)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Papory"; ValueData: """{app}\Papory.exe"" --escondido"; Tasks: iniciar; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Papory.exe"; Description: "Abrir o Papory agora"; Flags: nowait postinstall skipifsilent
; instalação silenciosa = atualização feita pelo próprio Papory: ele fechou para trocar os arquivos, então reabre
Filename: "{app}\Papory.exe"; Flags: nowait skipifnotsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
