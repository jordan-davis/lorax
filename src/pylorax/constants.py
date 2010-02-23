#
# constants.py
#
# Copyright (C) 2009  Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Red Hat Author(s):  Martin Gracik <mgracik@redhat.com>
#

from os.path import join as pjoin


class LoraxConstants(object):

    ROOT_UID = 0

    ANACONDA_PACKAGE = "anaconda"
    ANACONDA_RUNTIME = "usr/lib/anaconda-runtime"
    ANACONDA_BOOTDIR = "usr/lib/anaconda-runtime/boot"
    ANACONDA_LOADERDIR = "usr/lib/anaconda-runtime/loader"

    BOOTDIR = "boot"
    BOOTDIR_IA64 = "boot/efi/EFI/redhat"

    EFIDIR = "boot/efi/EFI/redhat"
    SPLASH = "boot/grub/splash.xpm.gz"

    VESASPLASH = pjoin(ANACONDA_RUNTIME, "syslinux-vesa-splash.jpg")
    SYSLINUXSPLASH = pjoin(ANACONDA_BOOTDIR, "syslinux-splash.jpg")
    SPLASHTOOLS = pjoin(ANACONDA_RUNTIME, "splashtools.sh")
    SPLASHLSS = pjoin(ANACONDA_BOOTDIR, "splash.lss")
    VESAMENU = "usr/share/syslinux/vesamenu.c32"

    MODDIR = "lib/modules"
    FWDIR = "lib/firmware"

    MODDEPFILE = "modules.dep"
    MODULEINFO = "module-info"
    MODLIST = "usr/lib/anaconda-runtime/modlist"

    LOCALEDIR = "usr/lib/locale"
    LOCALES = "usr/share/locale"
    LANGTABLE = "usr/lib/anaconda/lang-table"

    ISOLINUXBIN = "usr/share/syslinux/isolinux.bin"
    SYSLINUXCFG = "usr/lib/anaconda-runtime/boot/syslinux.cfg"

    LDSOCONF = "etc/ld.so.conf"
    MANCONF = "etc/man.config"


class LoraxCommands(dict):

    def __init__(self):
        self["MODINFO"] = "/sbin/modinfo"
        self["DEPMOD"] = "/sbin/depmod"
        self["LOCALEDEF"] = "/usr/bin/localedef"
        self["MKDOSFS"] = "/sbin/mkdosfs"
        self["MKSQUASHFS"] = "/sbin/mksquashfs"
        self["MKISOFS"] = "/usr/bin/mkisofs"
        self["ISOHYBRID"] = "/usr/bin/isohybrid"
        self["LOSETUP"] = "/sbin/losetup"
        self["DMSETUP"] = "/sbin/dmsetup"
        self["AWK"] = "/usr/bin/awk"
        self["MOUNT"] = "/bin/mount"
        self["UMOUNT"] = "/bin/umount"
        self["LDCONFIG"] = "/sbin/ldconfig"
        self["PARTED"] = "/sbin/parted"

    def __getattr__(self, attr):
        return self[attr]