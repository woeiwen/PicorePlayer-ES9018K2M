# ES9018K2M DAC Driver Makefile
KERNEL_SRC = /lib/modules/$(KVER)/build
BUILD_DIR = $(shell pwd)
DTC = $(KERNEL_SRC)/scripts/dtc/dtc
VERBOSE = 0

# Module definitions
obj-m := es9018k2m.o


all: modules dtbo

modules:
	$(MAKE) -C $(KERNEL_SRC) M=$(BUILD_DIR) KBUILD_VERBOSE=$(VERBOSE) modules

dtbo: es9018k2m.dtbo

es9018k2m.dtbo: es9018k2m.dts
	$(DTC) -@ -I dts -O dtb -o $@ $<

clean:
	$(MAKE) -C $(KERNEL_SRC) M=$(BUILD_DIR) clean
	rm -f *.dtbo *.mod.c *.mod.o *.o *.ko *.symvers *.order

modules_install:
	cp es9018k2m.ko /lib/modules/$(KVER)/kernel/sound/soc/codecs/
	depmod -a

install: modules_install dtbo_install

dtbo_install: es9018k2m.dtbo
	cp es9018k2m.dtbo /mnt/mmcblk0p1/overlays/

remove:
	rmmod es9018k2m 2>/dev/null || true

.PHONY: all modules dtbo clean modules_install install dtbo_install remove
