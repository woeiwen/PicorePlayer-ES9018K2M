#!/bin/sh
# put other system startup commands here
modprobe i2c_dev

sudo mount --bind /etc/sysconfig/tcedir/alsa_mixer.cgi  /tmp/tcloop/pcp-10.0.0-www/var/www/cgi-bin/alsa_mixer.cgi
ln -s  /etc/sysconfig/tcedir/es9018k2m.cgi /var/www/cgi-bin/es9018k2m.cgi
ln -s  /etc/sysconfig/tcedir/es9018k2m.conf /usr/local/share/pcp/cards/es9018k2m.conf

#cp /etc/sysconfig/tcedir/es9018k2m.conf /usr/local/share/pcp/cards
#cp /etc/sysconfig/tcedir/es9018k2m.cgi /var/www/cgi-bin

GREEN="$(echo -e '\033[1;32m')"

echo
echo "${GREEN}Running bootlocal.sh..."
#pCPstart------
/usr/local/etc/init.d/pcp_startup.sh 2>&1 | tee -a /var/log/pcp_boot.log
#pCPstop------
