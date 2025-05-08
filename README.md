# PicorePlayer-ES9018K2M
Alsa driver for ES9018K2M dac in Picoreplayer

This is alsa driver for ES9018K2M  which implements the h/w volume control control of iir/fir filters  etc. They can be controlled using tools such as alsamixer and amixer. The original code is from: https://github.com/VinnyLorrin/Rpi-ES9018K2M-DAC.git.The driver module is compiled using the PIcoreplaye (PCP) kernel module tool: https://github.com/piCorePlayer/pCP-Kernels.git Follow the instructions to generate the module and create the extension.  This has been tested on pcp10, kernel 6.6.67.

There is a cgi script (es9018k2m.cgi) and config file (es9018k2m.conf) so that the controls can be done in PCP webui. Copy these files to tce dir, and update the bootlocal.sh to do a symbolic link to them in the approriate directories. The driver (ES9018K2M.c)is just a codec driver,  the machine driver is that of simple audio card which takes in a regular  I2S audio card. This can be seen in the .dts file to generate device tree overlay.
