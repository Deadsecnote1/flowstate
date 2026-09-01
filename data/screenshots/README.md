# Screenshots for Flathub / AppStream

Flathub **requires** screenshots. Add PNG files here, then push to GitHub.

## Required files

| File | Content |
|------|---------|
| `tasks.png` | Tasks tab (default screenshot) |
| `planner.png` | Planner tab |
| `clock.png` | Clock / timer tab |

Recommended size: **1280×720** or larger (16:9).

## Capture on Linux

```bash
flowstate
# Switch to each tab, then:
gnome-screenshot -w -f tasks.png
# Move files into this folder and rename
```

Or use your desktop screenshot tool.

## After adding images

1. Commit and push to GitHub (`main` branch if metainfo URLs use `/main/`).
2. Verify URLs load in browser:
   - https://raw.githubusercontent.com/Deadsecnote1/flowstate/main/data/screenshots/tasks.png
3. Validate metainfo:
   ```bash
   appstreamcli validate --no-net data/io.github.Deadsecnote1.Flowstate.metainfo.xml
   ```

Then follow [FLATHUB.md](../../FLATHUB.md).
