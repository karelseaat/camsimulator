# GrblSimulator

I built this to debug GRBL G-code without a machine attached—noSerial, no panic when you typo `G0 X1000`.

It’s a lightweight GUI simulator that runs GRBL’s state machine and visualizes motion in real time.

## What it does

- Renders X/Y/Z toolpath as you move or send G-code
- Interactive axis controls: drag the tool, set soft limits, tweak feed rate
- Tracks position, alarm states, and work coordinates live
- Parses GRBL commands (including `$`, `~`, `!`, etc.) and shows parser responses
- Reports machine status (`<Idle|WPos:...>`) exactly like the real thing

## Requirements

- Python 3.6+  
- No external dependencies (uses only stdlib: `tkinter`, `textwrap`, `re`)

## Install & run

```bash
git clone https://github.com/yourusername/GrblSimulator.git
cd GrblSimulator
python GrblSimulator.py
```

## Usage tips

- Drag the red square to manually jog the tool. Click the arrows to step by 1mm.
- Hit **Enter** in the command box to send G-code. The output panel shows GRBL’s response—including `$` settings and alarm codes.
- Set soft limits with the **Min/Max** fields. Exceed them and GRBL will alarm (you’ll see `Alarm:2` in output).
- Feed rate (F) is applied to all `G0`/`G1` moves—no interpolation, just linear scaling.

## Contributing

Bugs? Improvements? Hit the issues or PRs. I’ll mostly care about:
- Correct GRBL protocol behavior (look at grbl/grbl source)
- Keep it runnable on stock Python (no `pip install` required)

## License

MIT — see `LICENSE`.