CC ?= cc
BUILD ?= build
CFLAGS ?= -O2 -Wall -Wextra -Werror -Wno-deprecated-declarations
HARDEN = -Wl,-z,relro,-z,now,-z,noexecstack

.PHONY: all test clean
all: $(BUILD)/libcrypto.so.1.0.0 $(BUILD)/libssl.so.1.0.0

$(BUILD):
	mkdir -p $@

$(BUILD)/libcrypto.so.1.0.0: bridge.c exports.map | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -fPIC -shared $(LDFLAGS) $(HARDEN) -Wl,-z,defs -Wl,-soname,libcrypto.so.1.0.0 -Wl,--version-script=exports.map -o $@ bridge.c -lcrypto

$(BUILD)/libssl.so.1.0.0: ssl-needed.c | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -fPIC -shared $(LDFLAGS) $(HARDEN) -Wl,-z,defs -Wl,-soname,libssl.so.1.0.0 -o $@ $<

test: all
	python3 test_bridge.py $(BUILD)

clean:
	rm -rf -- $(BUILD)
