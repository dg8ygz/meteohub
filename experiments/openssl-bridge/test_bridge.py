#!/usr/bin/env python3
"""Host-architecture functional/version tests; NOT a Meteohub or ARM acceptance."""
import ctypes as c
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

EXPECTED = set('MD5 BIO_ctrl BIO_f_base64 BIO_free BIO_free_all BIO_new BIO_new_mem_buf BIO_push BIO_read BIO_s_mem BIO_set_flags BIO_write EVP_PKEY_free EVP_PKEY_get1_RSA PEM_read_bio_PUBKEY RSA_new RSA_public_decrypt'.split())

def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs)

def main():
    build = Path(sys.argv[1]).resolve(strict=True)
    bridge = c.CDLL(str(build/'libcrypto.so.1.0.0'))
    modern = c.CDLL('libcrypto.so.3')
    loader = c.CDLL(None)
    loader.dlvsym.argtypes = [c.c_void_p, c.c_char_p, c.c_char_p]
    loader.dlvsym.restype = c.c_void_p
    def function(name, result, *args):
        addr = loader.dlvsym(bridge._handle, name.encode(), b'OPENSSL_1.0.0')
        new = loader.dlvsym(modern._handle, name.encode(), b'OPENSSL_3.0.0')
        assert addr and new and addr != new, name
        return c.CFUNCTYPE(result, *args)(addr)
    ptr, integer = c.c_void_p, c.c_int
    md5 = function('MD5', ptr, ptr, c.c_size_t, ptr)
    ctrl = function('BIO_ctrl', c.c_long, ptr, integer, c.c_long, ptr)
    base64 = function('BIO_f_base64', ptr)
    free = function('BIO_free', integer, ptr)
    free_all = function('BIO_free_all', None, ptr)
    new = function('BIO_new', ptr, ptr)
    mem_buf = function('BIO_new_mem_buf', ptr, ptr, integer)
    push = function('BIO_push', ptr, ptr, ptr)
    read = function('BIO_read', integer, ptr, ptr, integer)
    memory = function('BIO_s_mem', ptr)
    flags = function('BIO_set_flags', None, ptr, integer)
    write = function('BIO_write', integer, ptr, ptr, integer)
    key_free = function('EVP_PKEY_free', None, ptr)
    rsa_get = function('EVP_PKEY_get1_RSA', ptr, ptr)
    pem = function('PEM_read_bio_PUBKEY', ptr, ptr, ptr, ptr, ptr)
    rsa_new = function('RSA_new', ptr)
    decrypt = function('RSA_public_decrypt', integer, integer, ptr, ptr, ptr, integer)
    modern.RSA_free.argtypes = [ptr]
    modern.RSA_free.restype = None
    digest = c.create_string_buffer(16)
    assert md5(b'abc', 3, digest)
    assert digest.raw.hex() == '900150983cd24fb0d6963f7d28e17f72'
    plain = b'\x00Meteohub bridge test\xff'
    import base64 as b64
    expected = b64.b64encode(plain)
    sink = new(memory()); encoder = new(base64())
    assert sink and encoder
    flags(encoder, 0x100)  # BIO_FLAGS_BASE64_NO_NL
    assert push(encoder, sink) == encoder
    assert write(encoder, plain, len(plain)) == len(plain)
    assert ctrl(encoder, 11, 0, None) == 1  # BIO_CTRL_FLUSH
    buf = c.create_string_buffer(1024)
    count = read(sink, buf, len(buf))
    assert buf.raw[:count] == expected
    free_all(encoder)
    source = mem_buf(expected, len(expected)); decoder = new(base64())
    assert source and decoder
    flags(decoder, 0x100); assert push(decoder, source) == decoder
    count = read(decoder, buf, len(buf))
    assert buf.raw[:count] == plain
    free_all(decoder)
    invalid = b'not a public key'
    source = mem_buf(invalid, len(invalid))
    assert not pem(source, None, None, None)
    assert free(source) == 1
    rsa = rsa_new(); assert rsa; modern.RSA_free(rsa)
    with tempfile.TemporaryDirectory(prefix='meteohub-bridge-test-') as tmp:
        tmp = Path(tmp)
        subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(tmp/'key.pem')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        public = subprocess.check_output(['openssl','pkey','-in',str(tmp/'key.pem'),'-pubout'])
        (tmp/'public.pem').write_bytes(public)
        (tmp/'payload').write_bytes(b'bridge-test-only-not-a-license')
        subprocess.run(['openssl','pkeyutl','-sign','-inkey',str(tmp/'key.pem'),'-pkeyopt','rsa_padding_mode:pkcs1','-in',str(tmp/'payload'),'-out',str(tmp/'signature')],check=True)
        source = mem_buf(public, len(public)); key = pem(source, None, None, None)
        assert key; rsa = rsa_get(key); assert rsa
        key_free(key); free(source)  # get1 must retain a usable independent RSA reference
        signature = (tmp/'signature').read_bytes()
        count = decrypt(len(signature), signature, buf, rsa, 1)
        assert buf.raw[:count] == (tmp/'payload').read_bytes()
        assert decrypt(len(signature), bytes(len(signature)), buf, rsa, 1) <= 0
        modern.RSA_free(rsa)
        # A real ELF consumer is linked against the old SONAME and old version.
        source = tmp/'consumer.c'
        source.write_text('#include <openssl/md5.h>\nint main(void) { unsigned char d[16]; return MD5((const unsigned char *)"abc",3,d)==0 || d[0]!=0x90; }\n')
        command = shlex.split(os.environ.get('CC','cc'))
        subprocess.run(command+['-Wno-deprecated-declarations',str(source),'-o',str(tmp/'consumer'),'-L'+str(build),'-Wl,-rpath,'+str(build),'-Wl,--no-as-needed','-l:libssl.so.1.0.0','-l:libcrypto.so.1.0.0'],check=True)
        symbols = run('readelf','--dyn-syms','--wide',str(tmp/'consumer'))
        assert 'MD5@OPENSSL_1.0.0' in symbols
        subprocess.run([str(tmp/'consumer')],env={**os.environ,'LD_BIND_NOW':'1'},check=True)
        # The same complete C probe is also used for the isolated ARM test.
        probe = tmp/'functional'
        subprocess.run(command+['-Wall','-Wextra','-Werror','-Wno-deprecated-declarations',
            str(Path(__file__).with_name('arm-functional.c')),'-o',str(probe),
            '-L'+str(build),'-Wl,-rpath,'+str(build),'-Wl,--no-as-needed',
            '-l:libssl.so.1.0.0','-l:libcrypto.so.1.0.0','-lcrypto'],check=True)
        symbols = run('readelf','--dyn-syms','--wide',str(probe))
        assert set(re.findall(r'\b(\w+)@OPENSSL_1\.0\.0',symbols)) == EXPECTED
        subprocess.run([str(probe),str(tmp/'public.pem'),str(tmp/'signature')],
                       env={**os.environ,'LD_BIND_NOW':'1'},check=True)
    symbols = run('readelf','--dyn-syms','--wide',str(build/'libcrypto.so.1.0.0'))
    exported = set(re.findall(r'\b(\w+)@@OPENSSL_1\.0\.0',symbols))
    assert exported == EXPECTED, exported ^ EXPECTED
    assert set(re.findall(r'\b(\w+)@OPENSSL_3\.0\.0',symbols)) == EXPECTED
    ssl = c.CDLL(str(build/'libssl.so.1.0.0'))
    try:
        ssl.SSL_new
    except AttributeError:
        pass
    else:
        raise AssertionError('SSL placeholder unexpectedly implements TLS')
    print(json.dumps({'passed':True,'forwarded_symbols':len(EXPECTED),'checks':['versioned ELF consumer','MD5 known answer','binary base64 encode/decode','PEM valid/invalid','RSA ownership','RSA valid/invalid signature block','no TLS exports'],'scope':'host architecture only; no production or vendor application acceptance'},indent=2))

if __name__ == '__main__':
    main()
