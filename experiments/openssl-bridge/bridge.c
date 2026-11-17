/* Experimental, narrowly scoped ELF symbol-version bridge for reviewed imports.
 * No cryptography is implemented here. Every operation goes to libcrypto.so.3.
 * Not a general OpenSSL 1.0 ABI replacement; not installed by install-pi.py.
 * Explicit version references avoid resolving a forwarded call back to itself.
 */
#include <openssl/bio.h>
#include <openssl/evp.h>
#include <openssl/md5.h>
#include <openssl/pem.h>
#include <openssl/rsa.h>

#define MODERN(name) \
    extern __typeof__(name) modern_##name; \
    __asm__(".symver modern_" #name "," #name "@OPENSSL_3.0.0")
#define VALUE(ret, name, args, call) \
    MODERN(name); ret name args { return modern_##name call; }
#define NOTHING(name, args, call) \
    MODERN(name); void name args { modern_##name call; }

VALUE(unsigned char *, MD5,
      (const unsigned char *data, size_t count, unsigned char *digest),
      (data, count, digest))
VALUE(long, BIO_ctrl, (BIO *b, int command, long argument, void *pointer),
      (b, command, argument, pointer))
VALUE(const BIO_METHOD *, BIO_f_base64, (void), ())
VALUE(int, BIO_free, (BIO *b), (b))
NOTHING(BIO_free_all, (BIO *b), (b))
VALUE(BIO *, BIO_new, (const BIO_METHOD *method), (method))
VALUE(BIO *, BIO_new_mem_buf, (const void *buffer, int length), (buffer, length))
VALUE(BIO *, BIO_push, (BIO *b, BIO *append), (b, append))
VALUE(int, BIO_read, (BIO *b, void *data, int length), (b, data, length))
VALUE(const BIO_METHOD *, BIO_s_mem, (void), ())
NOTHING(BIO_set_flags, (BIO *b, int flags), (b, flags))
VALUE(int, BIO_write, (BIO *b, const void *data, int length), (b, data, length))
NOTHING(EVP_PKEY_free, (EVP_PKEY *key), (key))
VALUE(RSA *, EVP_PKEY_get1_RSA, (EVP_PKEY *key), (key))
VALUE(EVP_PKEY *, PEM_read_bio_PUBKEY,
      (BIO *b, EVP_PKEY **key, pem_password_cb *callback, void *user),
      (b, key, callback, user))
VALUE(RSA *, RSA_new, (void), ())
VALUE(int, RSA_public_decrypt,
      (int length, const unsigned char *from, unsigned char *to, RSA *rsa, int padding),
      (length, from, to, rsa, padding))
