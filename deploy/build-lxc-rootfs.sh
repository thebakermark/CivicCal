#!/usr/bin/env bash
# Build a Debian 13 LXC root filesystem archive. This does not contact Proxmox.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this build script as root in an isolated build environment." >&2
  exit 2
fi
if ! command -v debootstrap >/dev/null 2>&1; then
  echo "debootstrap is required on the build machine." >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-${REPO_ROOT}/dist}"
WORK_DIR="$(mktemp -d)"
ROOTFS="${WORK_DIR}/rootfs"
trap 'rm -rf "${WORK_DIR}"' EXIT
mkdir -p "${OUTPUT_DIR}" "${ROOTFS}"

debootstrap --variant=minbase \
  --include=python3,python3-minimal,tzdata,ca-certificates,systemd,systemd-sysv,sqlite3 \
  trixie "${ROOTFS}" https://deb.debian.org/debian

install -d -m 0755 "${ROOTFS}/opt/civiccal/app/scripts"
cp -a "${REPO_ROOT}/scripts/." "${ROOTFS}/opt/civiccal/app/scripts/"
install -d -m 0755 "${ROOTFS}/etc/systemd/system" "${ROOTFS}/etc/civiccal"
install -m 0644 "${REPO_ROOT}/deploy/systemd/civiccal-sqlite-api.service" \
  "${ROOTFS}/etc/systemd/system/civiccal-sqlite-api.service"
install -m 0640 "${REPO_ROOT}/deploy/civiccal-sqlite.env.example" \
  "${ROOTFS}/etc/civiccal/civiccal-sqlite.env"

chroot "${ROOTFS}" groupadd --system civiccal
chroot "${ROOTFS}" useradd --system --gid civiccal --home-dir /nonexistent \
  --no-create-home --shell /usr/sbin/nologin civiccal
install -d -m 0750 "${ROOTFS}/srv/civiccal/data"
chroot "${ROOTFS}" chown root:civiccal /srv/civiccal/data
chroot "${ROOTFS}" chmod 0750 /srv/civiccal/data
chroot "${ROOTFS}" chown -R root:root /opt/civiccal
chroot "${ROOTFS}" chmod -R go-w /opt/civiccal
chroot "${ROOTFS}" chown root:civiccal /etc/civiccal/civiccal-sqlite.env
printf 'civiccal\n' > "${ROOTFS}/etc/hostname"
touch "${ROOTFS}/etc/machine-id"
chmod 0444 "${ROOTFS}/etc/machine-id"

ARCHIVE="${OUTPUT_DIR}/civiccal-debian13-rootfs.tar.gz"
tar --numeric-owner --xattrs --acls -C "${ROOTFS}" -czf "${ARCHIVE}" .
(
  cd "${OUTPUT_DIR}"
  sha256sum "$(basename "${ARCHIVE}")" > SHA256SUMS
)
echo "Built ${ARCHIVE}"
echo "The API service is installed but disabled; no database is provisioned."
