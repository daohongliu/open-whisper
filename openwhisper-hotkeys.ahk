#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%

; --- Start Python script when AHK starts (terminal window persists) ---
pythonExe := A_ScriptDir . "\venv\Scripts\python.exe"
pythonScript := A_ScriptDir . "\open-whisper.py"

; Check if virtual environment Python exists
IfNotExist, %pythonExe%
{
    MsgBox, 16, Error, Virtual environment Python not found!`n`nPlease make sure you've set up the environment:`n1. python -m venv venv`n2. venv\Scripts\activate`n3. pip install -r requirements.txt
    ExitApp
}

Run, "%pythonExe%" "%pythonScript%",, Hide, pythonPID

OnExit, ClosePython

; Test connection after a delay
SetTimer, TestConnection, 3000

; Windows+Alt+Space: Hold to record, release to stop (suppressed)
#!Space::
    HttpPost("http://127.0.0.1:17800/start_recording")
    KeyWait, Space
    HttpPost("http://127.0.0.1:17800/stop_recording")
    ; Release modifiers to prevent browser from seeing them
    SendInput, {LWin up}{RWin up}{Alt up}
return

; Ctrl+Alt+V: Replay last transcription (suppressed)
^!v::
    HttpPost("http://127.0.0.1:17800/replay")
    SendInput, {Ctrl up}{Alt up}
return

; Ctrl+Alt+Q: Gracefully shutdown the Flask server and exit (suppressed)
^!q::
    HttpPost("http://127.0.0.1:17800/shutdown")
    Sleep, 500
    ExitApp
return

HttpPost(url) {
    whr := ComObjCreate("WinHttp.WinHttpRequest.5.1")
    whr.Open("POST", url, false)
    whr.SetRequestHeader("Content-Type", "application/json")
    whr.Send("{}")
    return whr.ResponseText
}

ClosePython:
    ; Gracefully shutdown Flask server instead of force-killing
    HttpPost("http://127.0.0.1:17800/shutdown")
    Sleep, 500
    if (pythonPID) {
        Process, Close, %pythonPID%
    }
    ExitApp
return 

TestConnection:
    SetTimer, TestConnection, Off
    try {
        whr := ComObjCreate("WinHttp.WinHttpRequest.5.1")
        whr.Open("GET", "http://127.0.0.1:17800/start_recording", false)
        whr.Send()
        status := whr.Status
    } catch e {
        MsgBox, 48, Warning, Could not connect to Python server.`n`nMake sure all dependencies are installed in the virtual environment.`nCheck the Python script for errors.
    }
return