INTRO
-----
livemedia-creator uses Anaconda, kickstart and Lorax to create bootable media
such as live iso's that use the same install path as a normal system install.

The general idea is to use virt-install to install into a disk image and then
use the disk image to create the bootable media.

livemedia-creator --help will describe all of the options available. At the
minimum you need:

--make-iso to create a final bootable .iso
--iso to specify the Anaconda install media to use with virt-install
--ks is the kickstart to use to install the system


QUICKSTART
----------
```bash
sudo livemedia-creator --make-iso \
--iso=/extra/iso/Fedora-16-x86_64-netinst.iso --ks=./fedora-livemedia.ks
```

If you are using the lorax git repo you can run it like so:

sudo PATH=./src/sbin/:$PATH PYTHONPATH=./src/ ./src/sbin/livemedia-creator \
--make-iso --iso=/extra/iso/Fedora-16-x86_64-netinst.iso \
--ks=./docs/fedora-livemedia.ks --lorax-templates=./share/

If you want to watch the install you can pass '--vnc vnc' and use a vnc
client to connect to localhost:0

This is usually a good idea when testing changes to the kickstart. It tries
to monitor the logs for fatal errors, but may not catch everything.


HOW IT WORKS
------------
The --make-* switches define the final output.

You then need to either pass --iso and --ks in order to create a disk image
using virt-install, or --disk-image to use a disk image from a previous run
to create the .iso

virt-install boots using the passed Anaconda installer iso and installs the
system based on the kickstart. The %post section of the kickstart is used to
customize the installed system in the same way that current spin-kickstarts
do.

livemedia-creator monitors the install process for problems by watching the
install logs. They are written to the current directory or to the base
directory specified by the --logfile command. You can also monitor the install
by passing --vnc vnc and using a vnc client. This is recommended when first
modifying a kickstart, since there are still places where Anaconda may get
stuck without the log monitor catching it.

The output from this process is a partitioned disk image. kpartx can be used
to mount and examine it when there is a problem with the install. It can also
be booted using kvm.

When creating an iso the disk image's / partition is copied into a formatted
disk image which is then used as the input to lorax for creation of the final
media.

The final image is created by lorax, using the templates in /usr/share/lorax/
or the directory specified by --lorax-templates

Currently the standard lorax templates are used to make a bootable iso, but
it should be possible to modify them to output other results. They are
written using the Mako template system which is very flexible.


KICKSTARTS
----------
Existing spin kickstarts can be used to create live media with a few changes.
Here are the steps I used to convert the XFCE spin.

1. Flatten the xfce kickstart using ksflatten
2. Add zerombr so you don't get the disk init dialog
3. Add clearpart --all
4. Add swap and biosboot partitions
5. bootloader target
6. Add shutdown to the kickstart
7. Add network --bootproto=dhcp --activate to activate the network
   This works for F16 builds but for F15 and before you need to pass
   something on the cmdline that activate the network, like sshd.

livemedia-creator --kernel-args="sshd"

8. Add a root password

rootpw rootme
network --bootproto=dhcp --activate
zerombr
clearpart --all
bootloader --location=mbr
part biosboot --size=1
part swap --size=512
shutdown

9. In the livesys script section of the %post remove the root password. This
   really depends on how the spin wants to work. You could add the live user
   that you create to the %wheel group so that sudo works if you wanted to.

passwd -d root > /dev/null

10. Remove /etc/fstab in %post, dracut handles mounting the rootfs

cat /dev/null > /dev/fstab

11. Don't delete initramfs files from /boot in %post
12. Have grub-efi, memtest86+ and syslinux in the package list

One drawback to using virt-install is that it pulls the packages from
the repo each time you run it. To speed things up you either need a local
mirror of the packages, or you can use a caching proxy. When using a proxy
you pass it to livemedia-creator like so:

--proxy=http://proxy.yourdomain.com:3128

You also need to use a specific mirror instead of mirrormanager so that the
packages will get cached, so your kickstart url would look like:

url --url="http://dl.fedoraproject.org/pub/fedora/linux/development/17/x86_64/os/"

You can also add an update repo, but don't name it updates. Add --proxy to
it as well.


ANACONDA IMAGE INSTALL
----------------------
You can create images without using virt-install by passing --no-virt on the
cmdline. This will use Anaconda's image install feature to handle the install.
There are a couple of things to keep in mind when doing this:

1. It will be most reliable when building images for the same release that the
   host is running. Because Anaconda has expectations about the system it is
   running under you may encounter strange bugs if you try to build newer or
   older releases.

2. Make sure selinux is set to permissive or disabled. It won't install
   correctly with selinux set to enforcing yet.

3. It may totally trash your host. So far I haven't had this happen, but the
   possibility exists that a bug in Anaconda could result in it operating on
   real devices. I recommend running it in a virt or on a system that you can
   afford to lose all data from.

The logs from anaconda will be placed in an ./anaconda/ directory in either
the current directory or in the directory used for --logfile

Example cmdline:

sudo livemedia-creator --make-iso --no-virt --ks=./fedora-livemedia.ks


AMI IMAGES
----------
Amazon EC2 images can be created by using the --make-ami switch and an appropriate
kickstart file. All of the work to customize the image is handled by the kickstart.
The example currently included was modified from the cloud-kickstarts version so
that it would work with livemedia-creator.

Example cmdline:
sudo livemedia-creator --make-ami --iso=/path/to/boot.iso --ks=./docs/fedora-livemedia-ec2.ks

This will produce an ami-root.img file in the working directory.

At this time I have not tested the image with EC2. Feedback would we welcome.


APPLIANCE CREATION ------------------ livemedia-creator can now replace
appliance-tools by using the --make-appliance switch. This will create the
partitioned disk image and an XML file that can be used with virt-image to
setup a virtual system.

The XML is generated using the Mako template from
/usr/share/lorax/appliance/virt-image.xml You can use a different template by
passing --app-template <template path>

Documentation on the Mako template system can be found here:
http://docs.makotemplates.org/en/latest/index.html

The name of the final output XML is appliance.xml, this can be changed with
--app-file <file path>

The following variables are passed to the template:
disks           A list of disk_info about each disk.
                Each entry has the following attributes:
    name           base name of the disk image file
    format         "raw"
    checksum_type  "sha256"
    checksum       sha256 checksum of the disk image
name            Name of appliance, from --app-name argument
arch            Architecture
memory          Memory in KB (from --ram)
vcpus           from --vcpus
networks        list of networks from the kickstart or []
title           from --title
project         from --project
releasever      from --releasever


DEBUGGING PROBLEMS
------------------
Cleaning up an aborted (ctrl-c) virt-install run (as root):
virsh list to show the name of the virt
virsh destroy <name>
virsh undefine <name>
umount /tmp/tmpXXXX
rm -rf /tmp/tmpXXXX
rm /tmp/diskXXXXX

The logs from the virt-install run are stored in virt-install.log,
logs from livemedia-creator are in livemedia.log and program.log

You can add --image-only to skip the .iso creation and examine the resulting
disk image. Or you can pass --keep-image to keep it around after lorax is
run.

Cleaning up aborted --no-virt installs can sometimes be accomplished by running
the anaconda-cleanup script.


HACKING
-------
Development on this will take place as part of the lorax project, and on the
anaconda-devel-list mailing list.

Feedback, enhancements and bugs are welcome.
You can use http://bugzilla.redhat.com to report bugs.

