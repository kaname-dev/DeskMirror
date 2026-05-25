#!/usr/bin/env bash
# devkitPro + 3DS toolchain setup for MSYS2 (run from MSYS2 UCRT64 or MINGW64 shell)
set -euo pipefail

DEVKITPRO_WIN="${DEVKITPRO_WIN:-/c/devkitPro}"
PACMAN_CONF="/etc/pacman.conf"
KEY_ID="BC26F752D25B92CE272E0F44F7FD5492264BB9D0"

echo "==> devkitPro setup (target: ${DEVKITPRO_WIN})"

if ! grep -q '\[dkp-libs\]' "$PACMAN_CONF" 2>/dev/null; then
  echo "==> Adding devkitPro repositories to pacman.conf"
  cat >> "$PACMAN_CONF" <<'EOF'

[dkp-libs]
Server = https://pkg.devkitpro.org/packages
SigLevel = Required

[dkp-windows]
Server = https://pkg.devkitpro.org/packages/windows/$arch/
SigLevel = Required
EOF
fi

echo "==> Importing devkitPro signing key"
pacman-key --init 2>/dev/null || true
pacman-key --recv-keys "$KEY_ID" --keyserver keyserver.ubuntu.com || \
  pacman-key --recv-keys "$KEY_ID" --keyserver keys.openpgp.org || true
pacman-key --lsign-key "$KEY_ID" 2>/dev/null || true

echo "==> Installing devkitpro-keyring"
pacman -U --noconfirm https://pkg.devkitpro.org/devkitpro-keyring.pkg.tar.zst
pacman-key --populate devkitpro 2>/dev/null || true

echo "==> Updating package databases"
pacman -Sy --noconfirm

echo "==> Installing build utilities"
pacman -S --needed --noconfirm make

echo "==> Installing 3DS development group (devkitARM, libctru, citro3d, ...)"
pacman -S --needed --noconfirm 3ds-dev devkit-env dkp-toolchain-vars

echo "==> Setting DEVKITPRO path for Windows"
mkdir -p "$(cygpath -u "$DEVKITPRO_WIN")" 2>/dev/null || mkdir -p "$DEVKITPRO_WIN"

if [[ ! -f /etc/profile.d/devkit-env.sh ]]; then
  echo "Warning: devkit-env may not be installed correctly."
fi

echo ""
echo "devkitPro 3DS toolchain installed."
echo "Open a new MSYS2 shell and run: source /etc/profile.d/devkit-env.sh"
echo "Verify with: arm-none-eabi-gcc --version"
