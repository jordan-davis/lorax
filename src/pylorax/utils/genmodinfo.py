import sys
import os
import commands

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pylorax')


def genmodinfo(path, output):
    mods = {}
    for root, dirs, files in os.walk(path):
        for file in files:
            mods[file] = os.path.join(root, file)

    modules = { 'scsi_hostadapter': ['block'], 'eth': ['networking'] }
    blacklist = ('floppy', 'scsi_mod', 'libiscsi')

    list = {}
    for modtype in modules:
        list[modtype] = {}
        for file in modules[modtype]:
            try:
                filename = os.path.join(path, 'modules.%s' % file)
                f = open(filename, 'r')
            except IOError:
                logger.error('cannot open file %s', filename)
                continue
            else:
                lines = f.readlines()
                f.close()

            for line in lines:
                line = line.strip()
                if line in mods:
                    modname, ext = os.path.splitext(line)
                    if modname in blacklist:
                        logger.info('skipping %s', modname)
                        continue

                    outtext = commands.getoutput('modinfo -F description %s' % mods[line])
                    desc = outtext.split('\n')[0]
                    desc = desc.strip()

                    # XXX why we need to do this?
                    desc = desc[:65]

                    if not desc:
                        desc = '%s driver' % modname
                        modinfo = '%s\n\t%s\n\t"%s"\n' % (modname, modtype, desc)
                        list[modtype][modname] = modinfo

    f = open(output, 'a')
    f.write('Version 0\n')
    for type in list:
        modlist = list[type].keys()
        modlist.sort()
        for m in modlist:
            f.write('%s\n' %list[type][m])
    f.close()