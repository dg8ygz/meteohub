/* Reviewed binaries have DT_NEEDED libssl.so.1.0.0 but import no SSL symbols.
 * This object intentionally supplies NO SSL functions. Unsupported callers
 * must fail symbol resolution; it is not an old TLS implementation.
 */
