---
name: plymouth-theme
description: Use when modifying, deploying, or testing Plymouth splash themes. Covers the full workflow: source editing, asset generation, copying to installed theme dir, rebuilding initramfs, verification, and testing.
---

# Plymouth Theme Update

## Source layout
```
/root/aur/PlymouthTheme-Cat/   # git repo (artemis branch)
  cat/
    cat.script                  # script plugin entry point
    cat.plymouth                # theme descriptor (ModuleName=script, ImageDir=assets/)
    gen-assets.py               # PNG generator (cap_left, cap_right, body, bullet, frames)
    assets/                     # ImageDir — all .png files
      cap_left.png
      cap_right.png
      body.png
      bullet.png
      frame-*.png
```

Installed at:
```
/usr/share/plymouth/themes/cat/
```

## Workflow

### 1. Edit source
Edit files in the repo (`/root/aur/PlymouthTheme-Cat/cat/`). Do NOT edit the installed copy directly — it will be overwritten by the cp step below.

### 2. Regenerate assets (if PNGs change)
```bash
cd /root/aur/PlymouthTheme-Cat/cat && python gen-assets.py
```

### 3. Deploy to installed theme directory
```bash
cp /root/aur/PlymouthTheme-Cat/cat/cat.script     /usr/share/plymouth/themes/cat/cat.script
cp /root/aur/PlymouthTheme-Cat/cat/cat.plymouth   /usr/share/plymouth/themes/cat/cat.plymouth
# If assets changed:
cp /root/aur/PlymouthTheme-Cat/cat/assets/*.png    /usr/share/plymouth/themes/cat/assets/
```

### 4. Rebuild initramfs
```bash
mkinitcpio -P
```
(Note: on this system mkinitcpio hooks are used; both `linux` and `linux-lts` kernels will be rebuilt.)

### 5. (Optional) Verify initramfs contents
```bash
lsinitramfs /boot/initramfs-linux.img | grep -E 'cat\.(script|plymouth)|assets/'
```

### 6. Reboot to test
```bash
reboot
```

After reboot, observed behavior:
- **Dialog hidden** until first keystroke on LUKS prompt
- **Dialog stays visible** through wrong-password retries
- **Dialog disappears** on successful unlock (normal display)

## Plymouth script API notes
- `Sprite(image)` — creates visible sprite at (0,0), default opacity 1
- `Sprite.SetOpacity(v)` — 0 = invisible, 1 = fully opaque
- `Sprite.SetPosition(x, y, z)` — z-order (higher = on top)
- `Image.Scale(w, h)` — returns scaled copy of image
- `SetDisplayPasswordFunction(cb)` — cb receives `(text, bulletCount)`
- `SetDisplayNormalFunction(cb)` — called when password mode ends
- All sprites should be created at init with `SetOpacity(0)` and shown only when needed

## Dialog geometry
```
CAP_W = 26          # cap_left / cap_right width
DIALOG_H = 50       # total dialog height
PADDING = 30        # horizontal padding in body
BULLET_SPACING = 40 # center-to-center distance between bullets
```

Minimum body width fits 8 bullets:
```
min_body_w = 8 * bullet_w + 7 * (BULLET_SPACING - bullet_w) + PADDING
```
(expand when bulletCount > 8)
