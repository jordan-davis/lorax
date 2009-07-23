# pylorax/images.py

import sys
import os
import commands
import re
import datetime
import fnmatch

import actions
import actions.base
from config import Template

from utils.fileutils import cp, mv, rm, touch, edit, replace
from utils.ldd import LDD
from utils.genmodinfo import genmodinfo


class InitRD(object):
    def __init__(self, config, yum):
        self.conf = config
        self.yum = yum

        # get supported actions
        supported_actions = actions.getActions()

        vars = { 'instroot': self.conf.treedir,
                 'initrd': self.conf.initrddir,
                 'libdir': self.conf.libdir,
                 'buildarch': self.conf.buildarch,
                 'confdir' : self.conf.confdir,
                 'datadir': self.conf.datadir }

        initrd_template = (os.path.join(self.conf.confdir, 'templates',
                                        'initrd.%s' % self.conf.buildarch))
        self.template = Template()
        self.template.preparse(initrd_template)
        self.template.parse(supported_actions, vars)

        self._actions = []

    def getPackages(self):
        packages = []
        for action in filter(lambda action: action.install, self.template.actions):
            m = re.match(r'%s(.*)' % self.conf.treedir, action.install)
            if m:
                packages.append(m.group(1))

        return packages

    def getDeps(self):
        libroots = []
        libroots.append(os.path.join(self.conf.treedir, self.conf.libdir))
        libroots.append(os.path.join(self.conf.treedir, 'usr', self.conf.libdir))
        # on 64 bit systems, add also normal lib directories
        if self.conf.libdir.endswith('64'):
            libroots.append(os.path.join(self.conf.treedir, self.conf.libdir[:-2]))
            libroots.append(os.path.join(self.conf.treedir, 'usr', self.conf.libdir[:-2]))

        ldd = LDD(libroots)
        for action in filter(lambda action: hasattr(action, 'getDeps'), self.template.actions):
            ldd.getDeps(action.getDeps)

        # resolve symlinks
        ldd.getLinks()

        # add dependencies to actions
        for dep in ldd.deps:
            kwargs = {}
            kwargs['src'] = dep
            kwargs['dst'] = re.sub(r'%s(?P<file>.*)' % self.conf.treedir,
                                   '%s\g<file>' % self.conf.initrddir,
                                   dep)

            new_action = actions.base.Copy(**kwargs)
            self._actions.append(new_action)

    def processActions(self):
        if os.path.isdir(self.conf.initrddir):
            rm(self.conf.initrddir)
        os.makedirs(self.conf.initrddir)

        for action in self.template.actions + self._actions:
            action.execute()

    def getModules(self):
        modlist = os.path.join(self.conf.treedir, 'usr', 'lib', 'anaconda-runtime', 'modlist')
        modinfo = os.path.join(self.conf.tempdir, 'modinfo')
        genmodinfo(os.path.join(self.conf.treedir, 'lib', 'modules', self.conf.kernelver), modinfo)

        modfiles = []
        modfiles.append(os.path.join(self.conf.confdir, 'modules', 'modules'))
        modfiles.append(os.path.join(self.conf.confdir, 'modules', self.conf.buildarch, 'modules'))

        modules = set()
        for file in modfiles:
            if os.path.isfile(file):
                f = open(file, 'r')
                lines = f.readlines()
                f.close()

                for line in lines:
                    line = line.strip()
                    line, sep, comment = line.partition('#')
                    if line.startswith('-'):
                        modules.discard(line[1:])
                    elif line.startswith('='):
                        cmd = '%s --modinfo-file %s %s' % (modlist, modinfo, line[1:])
                        output = commands.getoutput(cmd)
                        for module in output.splitlines():
                            modules.add(module)
                    else:
                        modules.add(line)

        # resolve deps
        depfile = os.path.join(self.conf.treedir, 'lib', 'modules', self.conf.kernelver, 'modules.dep')
        f = open(depfile, 'r')
        lines = f.readlines()
        f.close()

        changed = True
        while changed:
            for line in lines:
                changed = False
                line = line.strip()
                m = re.match(r'^.*/(?P<name>.*)\.ko:(?P<deps>.*)$', line)
                modname = m.group('name')
                if modname in modules:
                    for dep in m.group('deps').split():
                        m = re.match(r'^.*/(?P<name>.*)\.ko$', dep)
                        if m.group('name') not in modules:
                            changed = True
                            print('Adding module dependency %s' % m.group('name'))
                            modules.add(m.group('name'))

        srcdir = os.path.join(self.conf.treedir, 'lib', 'modules')
        dstdir = os.path.join(self.conf.initrddir, 'lib', 'modules')
        cp(os.path.join(srcdir, '*'), dstdir)

        for root, dirs, files in os.walk(dstdir):
            for file in files:
                name, ext = os.path.splitext(file)
                if ext == '.ko' and name not in modules:
                    print('Removing %s module' % name)
                    rm(os.path.join(root, file))

        # copy firmware
        srcdir = os.path.join(self.conf.treedir, 'lib', 'firmware')
        dstdir = os.path.join(self.conf.initrddir, 'lib', 'firmware')
        
        fw = ( ('ipw2100', 'ipw2100*'),
               ('ipw2200', 'ipw2200*'),
               ('iwl3945', 'iwlwifi-3945*'),
               ('iwl4965', 'iwlwifi-4965*'),
               ('atmel', 'atmel_*.bin'),
               ('zd1211rw', 'zd1211'),
               ('qla2xxx', 'ql*') )

        for module, file in fw:
            if module in modules:
                print('Copying %s firmware' % module)
                cp(os.path.join(srcdir, file), dstdir)

        # create modinfo
        dst = os.path.join(self.conf.initrddir, 'lib', 'modules', 'module-info')
        cmd = '%s --modinfo-file %s --ignore-missing --modinfo %s > %s' % \
              (modlist, modinfo, ' '.join(list(modules)), dst)
        commands.getoutput(cmd)

        # compress modules
        cmd = 'find -H %s -type f -name *.ko -exec gzip -9 {} \\;' % \
              os.path.join(self.conf.initrddir, 'lib', 'modules')
        commands.getoutput(cmd)

        # run depmod
        cmd = '/sbin/depmod -a -F %s -b %s %s' % \
              (os.path.join(self.conf.treedir, 'boot', 'System.map-%s' % self.conf.kernelver),
               self.conf.initrddir, self.conf.kernelver)
        commands.getoutput(cmd)

        # remove leftovers
        rm(os.path.join(self.conf.initrddir, 'lib', 'modules', self.conf.kernelver, 'modules.*map'))
        rm(os.path.join(self.conf.initrddir, 'lib', 'modules', self.conf.kernelver, 'source'))
        rm(os.path.join(self.conf.initrddir, 'lib', 'modules', self.conf.kernelver, 'build'))

    def create(self, dst):
        # create the productfile
        text = '%s\n' % self.conf.imageuuid
        text = text + '%s\n' % self.conf.product
        text = text + '%s\n' % self.conf.version
        text = text + '%s\n' % self.conf.bugurl
        edit(os.path.join(self.conf.initrddir, '.buildstamp'), text)

        # get modules
        self.getModules()

        # create the initrd
        err, output = commands.getstatusoutput('find %s | cpio --quiet -c -o | gzip -9 > %s' %
                                               (self.conf.initrddir, dst))

    def cleanUp(self):
        rm(self.conf.initrddir)


class Images(object):
    def __init__(self, config, yum):
        self.conf = config
        self.yum = yum

        # make imageuuid
        now = datetime.datetime.now()
        arch = os.uname()[4]    # XXX system arch, or build arch?
        imageuuid = '%s.%s' % (now.strftime('%Y%m%d%H%M'), arch)
        self.conf.addAttr('imageuuid')
        self.conf.set(imageuuid=imageuuid)

        self.initrd = InitRD(self.conf, self.yum)

        # XXX don't see this used anywhere... maybe in some other script, have to check...
        #syslinux = os.path.join(self.conf.treedir, 'usr', 'lib', 'syslinux', 'syslinux-nomtools')
        #if not os.path.isfile(syslinux):
        #    print('WARNING: %s does not exist' % syslinux)
        #    syslinux = os.path.join(self.conf.treedir, 'usr', 'bin', 'syslinux')
        #    if not os.path.isfile(syslinux):
        #        print('ERROR: %s does not exist' % syslinux)
        #        sys.exit(1)

    def run(self):
        bold = ('\033[1m', '\033[0m')

        print('%sInstalling needed packages%s' % bold)
        self.installPackages()

        print('%sCopying updates%s' % bold)
        self.copyUpdates()

        print('%sInitializing output directory%s' % bold)
        self.initOutputDirs()

        print('%sPopulating the isolinux directory%s' % bold)
        self.populateIsolinuxDir()

        # XXX a lot of other stuff needs to be done here
        pass

        print('%sDONE%s' % bold)

    def installPackages(self):
        # required packages
        self.yum.addPackages(['anaconda', 'anaconda-runtime', 'kernel', '*firmware*', 'syslinux'])

        # optional packages from confdir
        packages_files = []
        packages_files.append(os.path.join(self.conf.confdir, 'packages', 'packages'))
        packages_files.append(os.path.join(self.conf.confdir, 'packages', self.conf.buildarch,
                                           'packages'))

        packages = set()
        for pfile in packages_files:
            if os.path.isfile(pfile):
                f = open(pfile, 'r')
                for line in f.readlines():
                    line = line.strip()

                    if not line or line.startswith('#'):
                        continue

                    if line.startswith('-'):
                        packages.discard(line[1:])
                    else:
                        packages.add(line)

                f.close()

        self.yum.addPackages(list(packages))

        # packages required for initrd image
        packages = self.initrd.getPackages()
        self.yum.addPackages(packages)

        # install all packages
        self.yum.install()

    def copyUpdates(self):
        if self.conf.updates and os.path.isdir(self.conf.updates):
            cp(os.path.join(self.conf.updates, '*'), self.conf.treedir)
        self.conf.delAttr('updates')

    def initOutputDirs(self):
        # create the destination directories
        self.imgdir = os.path.join(self.conf.outdir, 'images')
        if os.path.exists(self.imgdir):
            rm(self.imgdir)
        os.makedirs(self.imgdir)

        self.pxedir = os.path.join(self.imgdir, 'pxeboot')
        os.makedirs(self.pxedir)

        # write the images/README
        src = os.path.join(self.conf.datadir, 'images', 'README')
        dst = os.path.join(self.imgdir, 'README')
        cp(src, dst)
        replace(dst, r'@PRODUCT@', self.conf.product)

        # write the images/pxeboot/README
        src = os.path.join(self.conf.datadir, 'images', 'pxeboot', 'README')
        dst = os.path.join(self.pxedir, 'README')
        cp(src, dst)
        replace(dst, r'@PRODUCT@', self.conf.product)

        # create the isolinux directory
        self.isodir = os.path.join(self.conf.outdir, 'isolinux')
        if os.path.exists(self.isodir):
            rm(self.isodir)
        os.makedirs(self.isodir)

    def populateIsolinuxDir(self):
        # set up some dir variables for further use
        anacondadir = os.path.join(self.conf.treedir, 'usr', 'lib', 'anaconda-runtime')
        bootdiskdir = os.path.join(anacondadir, 'boot')
        syslinuxdir = os.path.join(self.conf.treedir, 'usr', 'lib', 'syslinux')

        isolinuxbin = os.path.join(syslinuxdir, 'isolinux.bin')
        if os.path.isfile(isolinuxbin):
            # copy the isolinux.bin
            cp(isolinuxbin, self.isodir)

            # copy the syslinux.cfg to isolinux/isolinux.cfg
            isolinuxcfg = os.path.join(self.isodir, 'isolinux.cfg')
            cp(os.path.join(bootdiskdir, 'syslinux.cfg'), isolinuxcfg)

            # set the product and version in isolinux.cfg
            replace(isolinuxcfg, r'@PRODUCT@', self.conf.product)
            replace(isolinuxcfg, r'@VERSION@', self.conf.version)

            # copy the grub.conf
            cp(os.path.join(bootdiskdir, 'grub.conf'), self.isodir)

            # copy the vmlinuz
            self.conf.addAttr('kernelver')
            for file in os.listdir(os.path.join(self.conf.treedir, 'boot')):
                if fnmatch.fnmatch(file, 'vmlinuz-*'):
                    vmlinuz = os.path.join(self.conf.treedir, 'boot', file)
                    m = re.match(r'.*vmlinuz-(?P<ver>.*)', vmlinuz)
                    self.conf.set(kernelver=m.group('ver'))
                    cp(vmlinuz, os.path.join(self.isodir, 'vmlinuz'))
            
            # XXX do we want this here?
            # create the initrd.img
            print('Creating the initrd.img')
            self.initrd.getDeps()
            self.initrd.processActions()
            self.initrd.create(os.path.join(self.isodir, 'initrd.img'))
            #self.initrd.cleanUp()

            # copy the splash files
            vesasplash = os.path.join(anacondadir, 'syslinux-vesa-splash.jpg')
            if os.path.isfile(vesasplash):
                cp(vesasplash, os.path.join(self.isodir, 'splash.jpg'))
                vesamenu = os.path.join(syslinuxdir, 'vesamenu.c32')
                cp(vesamenu, self.isodir)
                replace(isolinuxcfg, r'default linux', r'default vesamenu.c32')
                replace(isolinuxcfg, r'prompt 1', r'#prompt 1')
            else:
                splashtools = os.path.join(anacondadir, 'splashtools.sh')
                splashlss = os.path.join(bootdiskdir, 'splash.lss')
                if os.path.isfile(splashtools):
                    cmd = '%s %s %s' % (splashtools,
                                        os.path.join(bootdiskdir, 'syslinux-splash.jpg'),
                                        splashlss)
                    os.system(cmd)
                if os.path.isfile(splashlss):
                    cp(splashlss, self.isodir)

            # copy the .msg files
            for file in os.listdir(bootdiskdir):
                if file.endswith('.msg'):
                    cp(os.path.join(bootdiskdir, file), self.isodir)
                    replace(os.path.join(self.isodir, file), r'@VERSION@', self.conf.version)

            # if present, copy the memtest
            cp(os.path.join(self.conf.treedir, 'boot', 'memtest*'),
               os.path.join(self.isodir, 'memtest'))
            if os.path.isfile(os.path.join(self.isodir, 'memtest')):
                text = "label memtest86\n"
                text = text + "  menu label ^Memory test\n"
                text = text + "  kernel memtest\n"
                text = text + "  append -\n"
                edit(isolinuxcfg, text, append=True)
        else:
            sys.stderr.write('No isolinux binary found, skipping isolinux creation\n')