# orb-terminal

An animated ASCII orb splash screen for your terminal. 3D-lit sphere with a blue/cyan color palette, a spin animation, and an explosion exit effect.

![orb-terminal demo](https://raw.githubusercontent.com/nicholasgasior/orb-terminal/main/demo.gif)

## Requirements

- Python 3.6+
- No external dependencies

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/orb-terminal.git
python orb-terminal/orb.py
```

Press any key to trigger the spin and explosion animation, then exit to your terminal. Press a second time during the animation to skip straight to the terminal.

## Options

| Flag | Description |
|------|-------------|
| `--name NAME` | Customize the welcome message (e.g. `--name Alice` → "Welcome to Alice's terminal") |
| `--panel` | Persistent panel mode — runs indefinitely, fills the terminal, resizes dynamically |
| `--splash` | Auto-exit after 3 seconds instead of waiting for a keypress |

## Shell Profile Integration

To run the orb every time you open a terminal, add this to your shell profile:

**Bash / Zsh** (`~/.bashrc` or `~/.zshrc`):
```bash
python /path/to/orb.py --name Alice
```

**PowerShell** (`$PROFILE`):
```powershell
python C:\path\to\orb.py --name Alice
```

## Windows Terminal — Side Panel Setup

You can run the orb as a persistent side panel alongside your shell using Windows Terminal's native pane splitting.

### 1. Add hidden profiles to `settings.json`

Open WT settings (`Ctrl+,`), click "Open JSON file", and add these two entries to the `profiles.list` array:

```json
{
    "commandline": "python C:\\path\\to\\orb.py --panel --name Alice",
    "hidden": true,
    "name": "Orb Panel"
},
{
    "closeOnExit": "always",
    "commandline": "python C:\\path\\to\\orb.py --name Alice",
    "hidden": true,
    "name": "Orb Splash"
}
```

### 2. Set your default profile's startup command

Find your default profile in `settings.json` and set the `commandline` to:

```
powershell -NoLogo -NoExit -Command "python C:\\path\\to\\orb.py --name Alice; Clear-Host; C:\\Users\\USERNAME\\AppData\\Local\\Microsoft\\WindowsApps\\wt.exe -w 0 split-pane -V -s 0.20 -p 'Orb Panel'; C:\\Users\\USERNAME\\AppData\\Local\\Microsoft\\WindowsApps\\wt.exe -w 0 move-focus left"
```

Replace `USERNAME` with your Windows username and update the path to `orb.py`.

This will:
1. Run the orb splash full-screen on startup
2. Split the terminal vertically, opening the orb in panel mode on the right (20% width)
3. Return focus to your main shell pane on the left

### Tip — find your `wt.exe` path

```powershell
Get-Item "$env:LOCALAPPDATA\Microsoft\WindowsApps\wt.exe"
```
