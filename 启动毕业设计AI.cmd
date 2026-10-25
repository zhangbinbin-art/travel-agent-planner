@echo off
rem ============================================================
rem  Graduation-project dedicated opencode instance launcher
rem ------------------------------------------------------------
rem  - Runs opencode with this folder as the project (%~dp0).
rem  - Uses a PRIVATE session database (OPENCODE_DB) so this
rem    instance's conversations stay fully independent from any
rem    other opencode instance. No shared chat history.
rem  - Config / agents / skills are inherited from the user-level
rem    opencode config, so every skill is available here too.
rem  - ASCII-only file on purpose (no non-ASCII literals).
rem ============================================================
setlocal

rem Private database for THIS instance (kept next to the launcher).
set "OPENCODE_DB=%~dp0.opencode-data\opencode.db"
if not exist "%~dp0.opencode-data" mkdir "%~dp0.opencode-data" >nul 2>&1

rem Launch the TUI in this folder and RESUME the last conversation (-c).
rem   "%~dp0." avoids a trailing-backslash-quote issue.
rem   To start a fresh session instead: press Ctrl+X then N inside the TUI.
rem   To pick another session: press Ctrl+O (recent) or Ctrl+X then L (all).
"C:\Users\zbb\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe" -c "%~dp0."

endlocal
