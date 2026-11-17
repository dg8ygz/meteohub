/* Cross-architecture probe. Inputs are a freshly generated TEST public key and
 * a PKCS#1 v1.5 signature block for "bridge-test-only-not-a-license".
 * No activation keys or manufacturer data are used.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <openssl/bio.h>
#include <openssl/evp.h>
#include <openssl/md5.h>
#include <openssl/pem.h>
#include <openssl/rsa.h>

#ifdef NDEBUG
#error "This probe requires assertions; do not build with NDEBUG"
#endif

static size_t load(const char *name, unsigned char *buf, size_t cap) {
    FILE *f = fopen(name, "rb");
    assert(f); size_t n = fread(buf, 1, cap, f);
    assert(n && n < cap && !ferror(f)); fclose(f); return n;
}
int main(int argc, char **argv) {
    assert(argc == 3);
    unsigned char out[4096], keybuf[4096], signature[4096], digest[16];
    static const unsigned char expected[16] = {
        0x90,0x01,0x50,0x98,0x3c,0xd2,0x4f,0xb0,
        0xd6,0x96,0x3f,0x7d,0x28,0xe1,0x7f,0x72};
    assert(MD5((const unsigned char *)"abc",3,digest));
    assert(!memcmp(digest,expected,16));
    BIO *sink = BIO_new(BIO_s_mem()), *b = BIO_new(BIO_f_base64());
    assert(sink && b); BIO_set_flags(b,BIO_FLAGS_BASE64_NO_NL);
    assert(BIO_push(b,sink)==b && BIO_write(b,"abc",3)==3);
    assert(BIO_ctrl(b,BIO_CTRL_FLUSH,0,NULL)==1);
    assert(BIO_read(sink,out,sizeof(out))==4 && !memcmp(out,"YWJj",4));
    BIO_free_all(b);
    BIO *source = BIO_new_mem_buf("YWJj",4); b = BIO_new(BIO_f_base64());
    assert(source && b); BIO_set_flags(b,BIO_FLAGS_BASE64_NO_NL);
    assert(BIO_push(b,source)==b);
    assert(BIO_read(b,out,sizeof(out))==3 && !memcmp(out,"abc",3));
    BIO_free_all(b);
    source = BIO_new_mem_buf("not a key",9); assert(source);
    assert(!PEM_read_bio_PUBKEY(source,NULL,NULL,NULL)); assert(BIO_free(source)==1);
    RSA *rsa = RSA_new(); assert(rsa); RSA_free(rsa);
    size_t n = load(argv[1],keybuf,sizeof(keybuf));
    source = BIO_new_mem_buf(keybuf,(int)n); assert(source);
    EVP_PKEY *key = PEM_read_bio_PUBKEY(source,NULL,NULL,NULL); assert(key);
    rsa = EVP_PKEY_get1_RSA(key); assert(rsa);
    EVP_PKEY_free(key); BIO_free(source);
    n = load(argv[2],signature,sizeof(signature));
    const char *message = "bridge-test-only-not-a-license";
    int recovered = RSA_public_decrypt((int)n,signature,out,rsa,RSA_PKCS1_PADDING);
    assert(recovered==(int)strlen(message) && !memcmp(out,message,(size_t)recovered));
    memset(signature,0,n);
    assert(RSA_public_decrypt((int)n,signature,out,rsa,RSA_PKCS1_PADDING)<=0);
    RSA_free(rsa);
    puts("PASS: 17 legacy-version imports, MD5, BIO/Base64, PEM and RSA positive/negative cases");
    return 0;
}
