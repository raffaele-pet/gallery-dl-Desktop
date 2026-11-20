#ifndef AppVersion
  #define AppVersion "1.0.1"
#endif
#define AppGuid "{197D0908-84FC-4C46-896A-B4522809A5E6}"

[Setup]
AppId={{#AppGuid}
AppName=gallery-dl Desktop
AppVersion={#AppVersion}
AppPublisher=raffaele-pet
AppPublisherURL=https://github.com/raffaele-pet/gallery-dl-Desktop
DefaultDirName={localappdata}\Programs\gallery-dl Desktop
DefaultGroupName=gallery-dl Desktop
UsePreviousAppDir=yes
DisableDirPage=auto
AlwaysShowDirOnReadyPage=yes
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
MinVersion=10.0
ChangesEnvironment=yes
SetupLogging=yes
SetupIconFile=..\assets\gallery-dl-icon.ico
UninstallDisplayIcon={app}\assets\gallery-dl-icon.ico
OutputDir=..\dist
OutputBaseFilename=gallery-dl-Desktop-Setup
WizardStyle=modern
Compression=lzma2
SolidCompression=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Files]
Source: "..\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\network.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\maintenance.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app_update.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\gallery_worker.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\engine.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\INSTALL.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\RUN.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\RUN_DEBUG.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\gallery-dl-icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\gallery-dl-icon.png"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\gallery-dl Desktop"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\RUN.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\gallery-dl-icon.ico"
Name: "{userdesktop}\gallery-dl Desktop"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\RUN.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\gallery-dl-icon.ico"; Tasks: desktopicon

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\RUN.vbs"""; WorkingDir: "{app}"; Description: "Launch gallery-dl Desktop"; Flags: nowait postinstall skipifsilent

[InstallDelete]
Type: files; Name: "{app}\assets\gallery-dl-logo.png"

[UninstallDelete]
Type: files; Name: "{app}\.installed-release"
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppGuid}_is1';
  DependencySteps = 5;

var
  InstalledDir, InstalledVersion: String;
  LegacySource: String;
  DependencyPage: TOutputProgressWizardPage;
  ShowDependencies: Boolean;
  DependencyStage: String;
  DependencyError: String;

function ExistingApplication(const Dir: String): Boolean;
var
  Root: String;
begin
  Root := AddBackslash(Dir);
  Result := (Dir <> '') and FileExists(Root + 'app.py') and FileExists(Root + 'gallery_worker.py') and
    FileExists(Root + 'engine.py') and FileExists(Root + 'RUN.vbs');
end;

function IsGitCheckout(const Dir: String): Boolean;
var
  GitPath: String;
begin
  GitPath := AddBackslash(Dir) + '.git';
  Result := DirExists(GitPath) or FileExists(GitPath);
end;

function LegacyShortcutDirectory(const FileName: String): String;
var
  Shell, Link: Variant;
  Path: String;
begin
  Path := AddBackslash(ExpandConstant('{userdesktop}')) + FileName;
  if not FileExists(Path) then
    exit;
  try
    Shell := CreateOleObject('WScript.Shell');
    Link := Shell.CreateShortcut(Path);
    Result := Link.WorkingDirectory;
    if not ExistingApplication(Result) then
      Result := '';
  except
    Log('Could not read the previous gallery-dl Desktop shortcut.');
  end;
end;

procedure InitializeWizard;
var
  Previous: String;
begin
  RegQueryStringValue(HKCU, UninstallKey, 'InstallLocation', InstalledDir);
  RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', InstalledVersion);
  if ExistingApplication(InstalledDir) then
  begin
    if not FileExists(AddBackslash(InstalledDir) + '.installed-release') then
    begin
      Previous := GetPreviousData('LegacySource', '');
      if ExistingApplication(Previous) then
        LegacySource := Previous;
    end;
  end
  else
  begin
    InstalledVersion := '';
    Previous := LegacyShortcutDirectory('gallery-dl Desktop.lnk');
    if Previous = '' then
      Previous := LegacyShortcutDirectory('Gallery-DL.lnk');
    if Previous <> '' then
    begin
      if IsGitCheckout(Previous) then
        LegacySource := Previous
      else if CompareText(WizardDirValue, ExpandConstant('{localappdata}\Programs\gallery-dl Desktop')) = 0 then
        WizardForm.DirEdit.Text := Previous;
    end;
  end;
  DependencyPage := CreateOutputProgressPage(
    'Preparing dependencies', 'Setup is preparing the tools used by gallery-dl Desktop.');
end;

procedure RegisterPreviousData(PreviousDataKey: Integer);
begin
  SetPreviousData(PreviousDataKey, 'LegacySource', LegacySource);
end;

function UpdatingExistingInstallation: Boolean;
begin
  Result := ExistingApplication(WizardDirValue) and not IsGitCheckout(WizardDirValue);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ManagedDir: String;
begin
  Result := True;
  if (CurPageID <> wpSelectDir) or not IsGitCheckout(WizardDirValue) then
    exit;
  if not ExistingApplication(WizardDirValue) then
  begin
    MsgBox('Choose an installation folder outside the Git checkout.', mbError, MB_OK);
    Result := False;
    exit;
  end;
  LegacySource := WizardDirValue;
  ManagedDir := ExpandConstant('{localappdata}\Programs\gallery-dl Desktop');
  if IsGitCheckout(ManagedDir) then
    ManagedDir := ManagedDir + ' App';
  WizardForm.DirEdit.Text := ManagedDir;
  MsgBox('Setup can reuse the settings from this repository. Review the separate installation folder and click Next.',
    mbInformation, MB_OK);
  Result := False;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if IsGitCheckout(WizardDirValue) then
    Result := 'Choose a separate installation folder. A Git checkout cannot be overwritten by Setup.';
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpReady) and UpdatingExistingInstallation then
  begin
    WizardForm.PageNameLabel.Caption := 'Ready to update';
    WizardForm.PageDescriptionLabel.Caption :=
      'Setup will update gallery-dl Desktop in its current folder.';
    WizardForm.ReadyLabel.Caption := 'Click Update to continue, or click Back to review your settings.';
    WizardForm.NextButton.Caption := '&Update';
    if (InstalledVersion <> '') and
      (CompareText(AddBackslash(WizardDirValue), AddBackslash(InstalledDir)) = 0) then
      WizardForm.ReadyMemo.Lines.Insert(0,
        'Installed version: ' + InstalledVersion + '   |   Setup version: {#AppVersion}');
  end
  else if (CurPageID = wpReady) and (LegacySource <> '') then
  begin
    WizardForm.ReadyMemo.Lines.Insert(0, 'Reuse settings and browser session from: ' + LegacySource);
  end;
end;

procedure RegisterExtraCloseApplicationsResources;
begin
  if UpdatingExistingInstallation then
    RegisterExtraCloseApplicationsResource(False, AddBackslash(WizardDirValue) + '.venv\Scripts\pythonw.exe');
  if LegacySource <> '' then
    RegisterExtraCloseApplicationsResource(False, AddBackslash(LegacySource) + '.venv\Scripts\pythonw.exe');
end;

procedure ImportLegacySettings;
var
  Source, Target, Staging: String;
  ExitCode: Integer;
begin
  if LegacySource = '' then
    exit;
  Source := AddBackslash(LegacySource);
  Target := AddBackslash(ExpandConstant('{app}'));
  if FileExists(Source + '.gallery-dl-gui.json') and not FileExists(Target + '.gallery-dl-gui.json') then
    if not FileCopy(Source + '.gallery-dl-gui.json', Target + '.gallery-dl-gui.json', True) then
      RaiseException('Could not copy the settings from the previous installation.');
  if DirExists(Source + '.browser-profile') and not DirExists(Target + '.browser-profile') then
  begin
    if ShowDependencies then
      DependencyPage.SetText('Copying the existing browser session...', '');
    Staging := Target + '.browser-profile.importing';
    if not ExecAndLogOutput(ExpandConstant('{sys}\robocopy.exe'),
      AddQuotes(Source + '.browser-profile') + ' ' + AddQuotes(Staging) +
      ' /E /XJ /R:1 /W:1 /NFL /NDL /NJH /NJS /NP', Target, SW_HIDE,
      ewWaitUntilTerminated, ExitCode, nil) then
      RaiseException('Could not start the browser session import.');
    if (ExitCode >= 8) or not RenameFile(Staging, Target + '.browser-profile') then
      RaiseException('Could not copy the browser session. Close the app and its browser window, then run Setup again.');
  end;
end;

procedure ShowDependencyOutput(const Line: String; const Error, FirstLine: Boolean);
var
  S: String;
  Step: Integer;
begin
  S := Trim(Line);
  if S = '' then
    exit;
  Log('Dependency setup: ' + S);

  if (Pos('[ERROR]', S) = 1) or (Pos('ERROR:', S) = 1) then
    DependencyError := S;
  if not ShowDependencies then
    exit;

  if (Copy(S, 1, 1) = '[') and (Copy(S, 3, 4) = '/6] ') then
  begin
    Step := StrToIntDef(Copy(S, 2, 1), 0);
    if (Step >= 1) and (Step <= DependencySteps) then
    begin
      DependencyStage := Format('Step %d of %d - %s', [Step, DependencySteps, Copy(S, 7, Length(S))]);
      DependencyPage.SetText(DependencyStage, '');
      DependencyPage.SetProgress(Step - 1, DependencySteps);
    end;
  end
  else if (Pos('[INSTALL]', S) = 1) or (Pos('[REPAIR]', S) = 1) then
    DependencyPage.SetText(DependencyStage, Copy(S, Pos(']', S) + 2, Length(S)))
  else if Pos('Collecting ', S) = 1 then
    DependencyPage.SetText(DependencyStage, 'Checking Python packages...')
  else if Pos('Downloading ', S) = 1 then
    DependencyPage.SetText(DependencyStage, 'Downloading packages...')
  else if Pos('Installing collected packages:', S) = 1 then
    DependencyPage.SetText(DependencyStage, 'Installing Python packages...');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ExitCode: Integer;
  Failure: String;
begin
  if CurStep <> ssPostInstall then
    exit;
  ShowDependencies := WizardForm.Visible;
  if ShowDependencies then
  begin
    DependencyPage.SetText('Checking prerequisites...', '');
    DependencyPage.SetProgress(0, DependencySteps);
    DependencyPage.Show;
  end;
  try
    ImportLegacySettings;
    if not ExecAndLogOutput(ExpandConstant('{cmd}'), '/D /C INSTALL.bat --setup', ExpandConstant('{app}'),
      SW_HIDE, ewWaitUntilTerminated, ExitCode, @ShowDependencyOutput) then
      Failure := 'Could not start dependency setup. Error code: ' + IntToStr(ExitCode)
    else if ExitCode <> 0 then
    begin
      Failure := 'Dependency setup failed. Error code: ' + IntToStr(ExitCode);
      if DependencyError <> '' then
        Failure := Failure + #13#10 + DependencyError;
    end;

    if Failure <> '' then
      RaiseException(Failure + #13#10#13#10 + 'Setup log: ' + ExpandConstant('{log}'));
    if not SaveStringToFile(ExpandConstant('{app}\.installed-release'), '{#AppVersion}', False) then
      RaiseException('Could not record the installed version.');
    if ShowDependencies then
      DependencyPage.SetProgress(DependencySteps, DependencySteps);
  finally
    if ShowDependencies then
      DependencyPage.Hide;
  end;
end;
