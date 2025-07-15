#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%

; --- Start Python script when AHK starts (terminal window persists) ---
pythonExe := "python"
pythonScript := A_ScriptDir . "\open-whisper.py"
Run, %pythonExe% "%pythonScript%",, Hide, pythonPID

OnExit, ClosePython

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