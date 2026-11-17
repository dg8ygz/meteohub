# Experimental OpenSSL symbol bridge

**Investigation only. Not installed by `install-pi.py`, not approved for production.**

This experiment lets the reviewed original Meteohub 5.1e ARMHF executables keep
their bytes and `OPENSSL_1.0.0` references while forwarding 17 public functions
to the distribution's `libcrypto.so.3`. It contains no manufacturer binaries,
activation data or cryptographic implementation. See the
[investigation and installer gaps](../../docs/unmodified-runtime-investigation.md).
The metadata-only [reviewed-imports.json](reviewed-imports.json) records the six
original hashes, dependencies and Crypto imports. It is an audit record, not
an enforced installer allowlist.

`bridge.c` exports exactly the symbols in `exports.map`. Explicit
`OPENSSL_3.0.0` references select the modern implementation rather than
recursively calling the wrapper. The SONAME is `libcrypto.so.1.0.0`.

The reviewed executables also name `libssl.so.1.0.0` in their dependencies but
import no TLS functions. `ssl-needed.c` therefore creates an empty dependency
placeholder with that SONAME. **It implements no TLS.** A caller requiring an
unsupported SSL symbol must fail; do not add fake success stubs.

This is not a general OpenSSL 1 ABI replacement. Structures, macros, provider
policies and behavior have changed across major versions. A successful load or
these function tests does not establish compatibility of every application
path. In particular, direct accesses to old structure layouts, dynamically
looked-up symbols and complete CGI workflows remain outside this acceptance.
OpenSSL documents these migration issues in its
[migration guide](https://docs.openssl.org/3.0/man7/migration_guide/).

## Host tests

On a separate Debian development machine with a C compiler, make, Python 3,
binutils, OpenSSL 3 development headers and the `openssl` command:

```sh
make test
```

The test checks all 17 old-version exports and modern-version imports, MD5's
known `abc` result, binary Base64 round trips, invalid PEM rejection, RSA object
ownership, and successful/failed PKCS#1 signature-block recovery. Keys are
freshly generated temporary **test** keys and removed afterwards. They have no
connection to Meteohub activation. Real ELF consumers verify the legacy symbol
version requirement rather than merely resolving unversioned functions.

`arm-functional.c` is the shared C functional probe; despite its name it also
runs in the host test. Assertions must be enabled. The link step can warn that
the old and new crypto SONAMEs coexist: this is intentional, and the symbol
version checks and execution test the forwarding.

## Cross build and ARM probe

The Makefile accepts `CC`, `CPPFLAGS`, `LDFLAGS` and `BUILD`. For example, with a
properly provisioned ARMHF sysroot and cross compiler:

```sh
make BUILD=build/armhf \
  CC="arm-linux-gnueabihf-gcc --sysroot=$ARM_SYSROOT" \
  CPPFLAGS="-I$ARM_SYSROOT/usr/include/arm-linux-gnueabihf" \
  LDFLAGS="-L$ARM_SYSROOT/usr/lib/arm-linux-gnueabihf"

arm-linux-gnueabihf-gcc --sysroot="$ARM_SYSROOT" \
  -Wall -Wextra -Werror -Wno-deprecated-declarations \
  -I"$ARM_SYSROOT/usr/include/arm-linux-gnueabihf" \
  arm-functional.c -o build/armhf/functional \
  -Lbuild/armhf -L"$ARM_SYSROOT/usr/lib/arm-linux-gnueabihf" \
  -Wl,-rpath-link,"$ARM_SYSROOT/usr/lib/arm-linux-gnueabihf" \
  -Wl,--no-as-needed -l:libssl.so.1.0.0 -l:libcrypto.so.1.0.0 -lcrypto
```

Generate a disposable test input in a private temporary directory:

```sh
umask 077
fixture=$(mktemp -d)
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$fixture/key.pem"
openssl pkey -in "$fixture/key.pem" -pubout -out "$fixture/public.pem"
printf '%s' 'bridge-test-only-not-a-license' > "$fixture/payload"
openssl pkeyutl -sign -inkey "$fixture/key.pem" -pkeyopt rsa_padding_mode:pkcs1 \
  -in "$fixture/payload" -out "$fixture/signature"

qemu-arm -L "$ARM_SYSROOT" -E LD_BIND_NOW=1 \
  -E "LD_LIBRARY_PATH=$PWD/build/armhf:$ARM_SYSROOT/usr/lib/arm-linux-gnueabihf:$ARM_SYSROOT/lib/arm-linux-gnueabihf" \
  build/armhf/functional "$fixture/public.pem" "$fixture/signature"
rm -rf -- "$fixture"
```

This command runs our test probe, not a vendor program. Before executing vendor
code, construct a separate network-isolated, unprivileged, read-only test root
with only reviewed libraries and fixtures. Do not run vendor installers or give
the test access to host configuration, devices, keys or station connections.
The investigation used such a disposable chroot plus mount/network namespaces.

For loader traces invoke the original ELF through QEMU with guest
`-E LD_TRACE_LOADED_OBJECTS=1`. Do not invoke the ARM loader as the emulated
main program: in our test that caused a mapping collision with the CGI's large
BSS, also with the existing patched control. Executing the actual ELF resolved
that test-harness issue.

## Integration gates

- Audit hashes, dependencies and versioned imports for each allowed executable.
  Unreviewed versions, extra imports and any TLS requirements must stop staging.
- Keep libraries private to the application; never install these legacy SONAMEs
  into system library directories or change global `ldconfig`/`LD_PRELOAD`.
- Test on a separate native ARM Pi with a fresh, unactivated configuration:
  CGI, collection, evaluation, restart, checkpoint and restoration separately.
- Verify original program hashes again after staging and tests.
- Keep manufacturer downloads and credentials out of source, release images,
  build caches and public test attachments. User license acceptance and any
  activation remain the user's own process.

These gates are requirements for future integration, **not implemented installer
features**. There is deliberately no `make install` target.
