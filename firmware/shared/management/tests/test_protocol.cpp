#include "../response_auth.h"
#include "mbedtls/md.h"
#include "mbedtls/sha256.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <string>

namespace response = flock_response;
static unsigned checks = 0;
static const uint8_t Key[32] = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
};
static constexpr char Challenge[] = "00112233445566778899aabbccddeeff";
static constexpr char Node[] = "02:11:22:33:44:55";
static constexpr char Nonce[] = "fedcba98765432100123456789abcdef";
static constexpr char RequestHash[] = "cb9872ce4fcf983a6238ca63a5f437cdb7f974a4d9bab08eaa1b0977625a702e";
static constexpr char RequestSignature[] = "f7a8fb1f246f373a37315540b98f9f1bd0fa275910e7460de030bd0401cc6b94";
static constexpr char BodyHash[] = "e5f1eb4d806641698a35efe20e098efd20d7d57a9b90ee69079d5bb650920726";
static constexpr char Signature[] = "8f3b8f032da4bb37dbc655d208f434cb2ba12c5ecc3eae5d0ee3c50119ed3297";

static void require(bool result, const char* description) {
    ++checks;
    if (!result) { std::fprintf(stderr, "FAIL: %s\n", description); std::exit(1); }
}
static void encode(const uint8_t* bytes, size_t size, char* out) {
    const char* digits = "0123456789abcdef";
    for (size_t i = 0; i < size; ++i) {
        out[i * 2] = digits[bytes[i] >> 4]; out[i * 2 + 1] = digits[bytes[i] & 15];
    }
    out[size * 2] = 0;
}
static bool hmac(const uint8_t key[32], const char* bytes, size_t size, char out[65]) {
    uint8_t digest[32];
    if (mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), key, 32,
                       reinterpret_cast<const uint8_t*>(bytes), size, digest)) return false;
    encode(digest, sizeof(digest), out); return true;
}
static void hash(const std::string& body, char out[65]) {
    uint8_t digest[32];
    require(mbedtls_sha256(reinterpret_cast<const uint8_t*>(body.data()), body.size(), digest, 0) == 0,
            "real SHA-256 succeeds");
    encode(digest, sizeof(digest), out);
}
static bool failed_hmac(const uint8_t[32], const char*, size_t, char[65]) { return false; }
static bool invalid_hmac(const uint8_t[32], const char*, size_t, char out[65]) {
    std::memset(out, 'z', 64); out[64] = 0; return true;
}
static response::Binding fixture() {
    response::Binding binding;
    require(response::bind(binding, Challenge, Node, "POST", "/v1/control", RequestHash,
                           Nonce, "42", RequestSignature), "bind valid protected request");
    return binding;
}
static response::Pending pending(const response::Binding& binding, int64_t started = 1000) {
    response::Pending p; p.request = binding; p.started_ms = started; return p;
}
static bool accepts(const response::Binding& binding, const char* signature = Signature,
                    int status = 200, const char* body_hash = BodyHash) {
    auto p = pending(binding);
    return response::verify(p, 1100, "1", signature, status, body_hash, Key, hmac);
}
static void known_vector() {
    // Independent Python stdlib fixture, calculated with:
    // key=bytes(range(32)); rh=sha256(b'{"op":"tone"}').hexdigest()
    // rs=hmac.new(key, '\n'.join(['v1',nonce,'42',node,'POST','/v1/control',rh]).encode(),sha256).hexdigest()
    // bh=sha256(b'{"ok":true}\n').hexdigest()
    // hmac.new(key, '\n'.join(['flock-management-response-v1',challenge,node,
    //     'POST','/v1/control',rh,nonce,'42',rs,'200',bh]).encode(),sha256).hexdigest()
    const char expected[] =
        "flock-management-response-v1\n00112233445566778899aabbccddeeff\n"
        "02:11:22:33:44:55\nPOST\n/v1/control\n"
        "cb9872ce4fcf983a6238ca63a5f437cdb7f974a4d9bab08eaa1b0977625a702e\n"
        "fedcba98765432100123456789abcdef\n42\n"
        "f7a8fb1f246f373a37315540b98f9f1bd0fa275910e7460de030bd0401cc6b94\n200\n"
        "e5f1eb4d806641698a35efe20e098efd20d7d57a9b90ee69079d5bb650920726";
    auto binding = fixture(); char bytes[768], actual[65]; size_t size = 0;
    require(response::canonical(binding, 200, BodyHash, bytes, size), "canonical fixture builds");
    require(size == 331 && size == sizeof(expected) - 1 && !std::memcmp(bytes, expected, size),
            "canonical bytes match independent fixture without final LF");
    hash("{\"op\":\"tone\"}", actual); require(!std::strcmp(actual, RequestHash), "request hash vector");
    hash("{\"ok\":true}\n", actual); require(!std::strcmp(actual, BodyHash), "response hash vector");
    require(response::sign(binding, 200, BodyHash, Key, hmac, actual), "production signer succeeds");
    require(!std::strcmp(actual, Signature), "response HMAC matches independent Python fixture");
    require(accepts(binding), "legitimate protected reply accepted");
    require(!accepts(binding, RequestSignature), "request MAC cannot be reflected as response MAC");

    response::Binding challenge;
    require(response::bind(challenge, Challenge, Node, "GET", "/v1/challenge", response::EmptyHash),
            "challenge endpoint sentinel binding accepted");
    require(response::sign(challenge, 200, BodyHash, Key, hmac, actual), "challenge reply signed");
    require(accepts(challenge, actual), "legitimate challenge reply verified");
    require(!accepts(binding, actual), "challenge reply cannot authenticate protected endpoint");
}
static void tampering() {
    auto original = fixture();
    // Every character of every bound request field must affect verification.
    char* fields[] = {original.challenge, original.node, original.method, original.path,
                      original.request_hash, original.nonce, original.count, original.request_signature};
    for (char* field : fields) {
        size_t length = std::strlen(field);
        for (size_t i = 0; i < length; ++i) {
            char saved = field[i]; field[i] = saved == '0' ? '1' : '0';
            require(!accepts(original), "single-character binding mutation rejected");
            field[i] = saved;
        }
    }
    std::strcpy(original.method, "GET");
    require(!accepts(original), "different valid HTTP method rejected");
    std::strcpy(original.method, "POST");
    char changed[65];
    for (size_t i = 0; i < 64; ++i) {
        std::strcpy(changed, Signature); changed[i] = changed[i] == '0' ? '1' : '0';
        require(!accepts(original, changed), "every response signature nibble is authenticated");
        std::strcpy(changed, BodyHash); changed[i] = changed[i] == '0' ? '1' : '0';
        require(!accepts(original, Signature, 200, changed), "every response digest nibble is authenticated");
    }
    for (int status = 100; status <= 599; ++status)
        if (status != 200) require(!accepts(original, Signature, status), "HTTP status alteration rejected");
    hash("{\"ok\":true}", changed);
    require(!accepts(original, Signature, 200, changed), "even trailing newline body alteration rejected");
    std::string binary_body = "{\"ok\":true}\n"; binary_body.append("\0suffix", 7);
    hash(binary_body, changed);
    require(!accepts(original, Signature, 200, changed), "body hashing includes NUL and following bytes");
    require(!accepts(original, nullptr), "missing signature rejected");
    require(!accepts(original, ""), "unsigned response rejected");
    for (const char* version : {static_cast<const char*>(nullptr), "", "0", "2", "01", "1\n"}) {
        auto p = pending(original);
        require(!response::verify(p, 1100, version, Signature, 200, BodyHash, Key, hmac),
                "missing or noncanonical response version rejected");
        require(!p.waiting, "version failure consumes pending attempt");
    }
    uint8_t wrong_key[32]; std::memcpy(wrong_key, Key, 32); wrong_key[31] ^= 1;
    auto p = pending(original);
    require(!response::verify(p, 1100, "1", Signature, 200, BodyHash, wrong_key, hmac), "wrong key rejected");
    p = pending(original);
    require(!response::verify(p, 1100, "1", Signature, 200, BodyHash, Key, failed_hmac), "crypto failure rejected");
    p = pending(original);
    require(!response::verify(p, 1100, "1", Signature, 200, BodyHash, Key, invalid_hmac), "malformed crypto output rejected");
}
static void replay_and_time() {
    auto binding = fixture(); auto p = pending(binding);
    require(response::verify(p, 1100, "1", Signature, 200, BodyHash, Key, hmac), "first reply accepted");
    require(!response::verify(p, 1100, "1", Signature, 200, BodyHash, Key, hmac), "same pending reply replay rejected");
    p = pending(binding);
    require(!response::verify(p, 1100, "1", "", 200, BodyHash, Key, hmac), "bad first attempt rejected");
    require(!response::verify(p, 1100, "1", Signature, 200, BodyHash, Key, hmac), "failure also consumes attempt");

    auto fresh = binding; fresh.challenge[0] = 'f';
    require(!accepts(fresh), "captured reply rejected despite replayed server nonce and counter");
    char fresh_signature[65];
    require(response::sign(fresh, 200, BodyHash, Key, hmac, fresh_signature), "fresh client request signed");
    auto one = pending(binding), two = pending(fresh);
    require(!response::verify(one, 1100, "1", fresh_signature, 200, BodyHash, Key, hmac), "concurrent response two cannot satisfy one");
    require(!response::verify(two, 1100, "1", Signature, 200, BodyHash, Key, hmac), "concurrent response one cannot satisfy two");
    one = pending(binding); two = pending(fresh);
    require(response::verify(two, 1100, "1", fresh_signature, 200, BodyHash, Key, hmac), "independent concurrent state two accepts own reply");
    require(response::verify(one, 1100, "1", Signature, 200, BodyHash, Key, hmac), "independent concurrent state one accepts own reply");

    p = pending(binding);
    require(response::verify(p, 1000 + response::MaxAgeMs, "1", Signature, 200, BodyHash, Key, hmac), "deadline boundary accepted");
    p = pending(binding);
    require(!response::verify(p, 1001 + response::MaxAgeMs, "1", Signature, 200, BodyHash, Key, hmac), "expired reply rejected");
    for (int64_t now : {int64_t(-1), int64_t(999), std::numeric_limits<int64_t>::max()}) {
        p = pending(binding);
        require(!response::verify(p, now, "1", Signature, 200, BodyHash, Key, hmac), "invalid or excessive elapsed time rejected");
    }
    for (int64_t start : {int64_t(-1), std::numeric_limits<int64_t>::min()}) {
        p = pending(binding, start);
        require(!response::verify(p, 0, "1", Signature, 200, BodyHash, Key, hmac), "negative start rejected without subtraction overflow");
        p = pending(binding, start);
        require(!response::verify(p, std::numeric_limits<int64_t>::max(), "1", Signature, 200, BodyHash, Key, hmac),
                "opposite signed clock extremes rejected without overflow");
    }
    p = pending(binding, std::numeric_limits<int64_t>::max() - 1);
    require(response::verify(p, std::numeric_limits<int64_t>::max(), "1", Signature, 200, BodyHash, Key, hmac),
            "large valid monotonic timestamps accepted");
}
static void bounds_and_injection() {
    response::Binding binding;
    std::string path(response::PathLimit, 'a'); path[0] = '/';
    require(response::bind(binding, Challenge, Node, "POST", path.c_str(), RequestHash, Nonce, "4294967295", RequestSignature),
            "maximum path and uint32 counter bind");
    char bytes[768]; size_t size = 0;
    require(response::canonical(binding, 599, BodyHash, bytes, size) && size < sizeof(bytes) && bytes[size] == 0,
            "maximum canonical message fits bounded output");
    char signature[65];
    require(response::sign(binding, 599, BodyHash, Key, hmac, signature) && accepts(binding, signature, 599),
            "maximum bounded binding signs and verifies");
    path.push_back('a');
    require(!response::bind(binding, Challenge, Node, "POST", path.c_str(), RequestHash, Nonce, "42", RequestSignature),
            "oversize path rejected rather than truncated");
    std::string long_challenge(33, 'a'), long_node(18, 'a'), long_method(5, 'a');
    std::string long_hash(65, 'a'), long_nonce(33, 'a'), long_count(11, '1'), long_signature(65, 'a');
    const char* fields[] = {Challenge, Node, "POST", "/v1/control", RequestHash, Nonce, "42", RequestSignature};
    const char* oversized[] = {long_challenge.c_str(), long_node.c_str(), long_method.c_str(), path.c_str(),
                               long_hash.c_str(), long_nonce.c_str(), long_count.c_str(), long_signature.c_str()};
    auto bind_fields = [&]() {
        return response::bind(binding, fields[0], fields[1], fields[2], fields[3], fields[4], fields[5], fields[6], fields[7]);
    };
    for (size_t i = 0; i < 8; ++i) {
        const char* saved = fields[i];
        fields[i] = nullptr; require(!bind_fields(), "null binding field rejected");
        fields[i] = oversized[i]; require(!bind_fields(), "oversized field rejected");
        fields[i] = ""; require(!bind_fields(), "empty field rejected");
        std::string injected = saved; injected[0] = '\n'; fields[i] = injected.c_str();
        require(!bind_fields(), "LF canonical field injection rejected");
        injected[0] = '\r'; require(!bind_fields(), "CR canonical field injection rejected");
        fields[i] = saved;
    }
    for (const char* invalid : {"0", "00", "01", "-1", "+1", " 1", "1 ", "1\n", "4294967296", "9999999999", "10000000000"})
        require(!response::counter(invalid), "noncanonical or overflowing request counter rejected");
    require(response::counter("1") && response::counter("4294967295"), "request counter endpoints valid");
    for (const char* invalid : {"v1/status", "/v1/ status", "/v1/\tstatus", "/v1/\nstatus", "/v1/\rstatus", "/v1/\x7fstatus", "/v1/\x80status"})
        require(!response::bind(binding, Challenge, Node, "GET", invalid, RequestHash, Nonce, "42", RequestSignature),
                "non-ASCII or whitespace path rejected");
    require(!response::bind(binding, Challenge, Node, "GET", "/v1/challenge", RequestHash), "challenge requires empty request digest");
    require(!response::bind(binding, Challenge, Node, "POST", "/v1/challenge", response::EmptyHash), "challenge requires GET");
    require(!response::bind(binding, Challenge, Node, "GET", "/v1/challenge", response::EmptyHash, Nonce), "challenge requires explicit sentinel nonce");
    require(!response::bind(binding, Challenge, Node, "GET", "/v1/status", response::EmptyHash), "protected endpoint rejects challenge sentinels");
    binding = fixture();
    for (int status : {0, 99, 600, -1, std::numeric_limits<int>::max()}) {
        size = 123;
        require(!response::canonical(binding, status, BodyHash, bytes, size) && size == 0, "invalid HTTP status rejected with empty length");
    }
    for (const char* invalid : {static_cast<const char*>(nullptr), "", "ABCDEF", long_hash.c_str()})
        require(!response::canonical(binding, 200, invalid, bytes, size), "malformed body digest rejected");
    std::string uppercase = BodyHash; uppercase[0] = 'E';
    require(!response::canonical(binding, 200, uppercase.c_str(), bytes, size), "noncanonical uppercase digest rejected");
    response::Binding unterminated;
    auto* raw = reinterpret_cast<unsigned char*>(&unterminated);
    for (size_t i = 0; i < sizeof(unterminated); ++i) raw[i] = 'a';
    require(!response::valid(unterminated), "unterminated fixed fields rejected");
    struct Field { char* bytes; size_t size; } fixed[] = {
        {binding.challenge, sizeof(binding.challenge)}, {binding.node, sizeof(binding.node)},
        {binding.method, sizeof(binding.method)}, {binding.path, sizeof(binding.path)},
        {binding.request_hash, sizeof(binding.request_hash)}, {binding.nonce, sizeof(binding.nonce)},
        {binding.count, sizeof(binding.count)}, {binding.request_signature, sizeof(binding.request_signature)}
    };
    for (const auto& field : fixed) {
        binding = fixture();
        std::memset(field.bytes, 'a', field.size);
        require(!response::valid(binding), "each individually unterminated field rejected");
    }
}
int main() {
    known_vector(); tampering(); replay_and_time(); bounds_and_injection();
    std::printf("PASS: %u management response protocol checks (real portable Mbed TLS)\n", checks);
}
