# Maintainer: irrld <teknoweb219@gmail.com>

pkgname=shitfuckzones-git
_pkgname=shitfuckzones
pkgver=r1.1e6e2a2
pkgrel=1
pkgdesc="FancyZones-style window snapping with configurable layouts for KDE Plasma 6"
arch=('any')
url="https://github.com/irrld/shitfuckzones"
license=('MIT')
depends=(
    'kwin'
    'python'
    'python-pyqt6'
    'python-dbus'
    'python-gobject'
    'python-evdev'
    'kconfig'
    'qt6-tools'
    'acl'
)
makedepends=('git')
provides=("$_pkgname")
conflicts=("$_pkgname")
install="$_pkgname.install"
source=("$_pkgname::git+$url.git")
sha256sums=('SKIP')

pkgver() {
    cd "$_pkgname"
    printf "r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

package() {
    cd "$_pkgname"

    # Source tree
    install -d "$pkgdir/usr/share/$_pkgname/contents/code"
    install -Dm644 config.json       "$pkgdir/usr/share/$_pkgname/config.json"
    install -Dm644 metadata.json     "$pkgdir/usr/share/$_pkgname/metadata.json"
    install -Dm644 contents/code/main.js "$pkgdir/usr/share/$_pkgname/contents/code/main.js"
    install -Dm755 daemon.py         "$pkgdir/usr/share/$_pkgname/daemon.py"
    install -Dm755 install.sh        "$pkgdir/usr/share/$_pkgname/install.sh"

    # User-facing entrypoints
    install -d "$pkgdir/usr/bin"
    ln -s "/usr/share/$_pkgname/install.sh" "$pkgdir/usr/bin/$_pkgname"
    cat > "$pkgdir/usr/bin/$_pkgname-daemon" <<'EOF'
#!/bin/sh
exec python3 /usr/share/shitfuckzones/daemon.py "$@"
EOF
    chmod 755 "$pkgdir/usr/bin/$_pkgname-daemon"

    # Udev rule — grants uaccess to /dev/input/event* for the active seat user
    install -Dm644 udev/99-$_pkgname.rules \
        "$pkgdir/usr/lib/udev/rules.d/99-$_pkgname.rules"

    # Docs
    install -Dm644 README.md "$pkgdir/usr/share/doc/$_pkgname/README.md"
}

# vim:set ts=4 sw=4 et:
