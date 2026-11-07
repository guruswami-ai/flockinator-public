#pragma once
// HTTP response authentication, independent of the unchanged v1 request MAC.
// No platform dependencies, allocation, wall clock, or shared pending state.
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace flock_response {
constexpr char VersionHeader[] = "X-Flock-Response-Version";
constexpr char ChallengeHeader[] = "X-Flock-Response-Challenge";
constexpr char SignatureHeader[] = "X-Flock-Response-Signature";
constexpr char EmptyHash[] = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
constexpr size_t BodyLimit = 128 * 1024;
constexpr size_t PathLimit = 256;
constexpr int64_t MaxAgeMs = 10000;

template<size_t N> inline bool copy(char (&out)[N], const char* in) {
    if (!in) return false;
    size_t n = strnlen(in, N);
    if (n == N) return false;
    memcpy(out, in, n + 1); return true;
}
inline bool hex(const char* in, size_t n) {
    if (!in || strnlen(in, n + 1) != n) return false;
    for (size_t i = 0; i < n; ++i)
        if (!((in[i] >= '0' && in[i] <= '9') || (in[i] >= 'a' && in[i] <= 'f'))) return false;
    return true;
}
inline bool mac(const char* in) {
    if (!in || strnlen(in, 18) != 17) return false;
    for (size_t i = 0; i < 17; ++i) {
        char c = in[i];
        if (i % 3 == 2 ? c != ':' : !((c >= '0' && c <= '9') || (c >= 'A' && c <= 'F') || (c >= 'a' && c <= 'f'))) return false;
    }
    return true;
}
inline bool counter(const char* in) {
    size_t n = in ? strnlen(in, 11) : 0;
    if (!n || n > 10 || in[0] == '0') return false;
    uint64_t value = 0;
    for (size_t i = 0; i < n; ++i) {
        if (in[i] < '0' || in[i] > '9') return false;
        value = value * 10 + unsigned(in[i] - '0');
    }
    return value <= UINT32_MAX;
}
struct Binding {
    char challenge[33]{}, node[18]{}, method[5]{}, path[PathLimit + 1]{};
    char request_hash[65]{}, nonce[33]{}, count[11]{}, request_signature[65]{};
};
inline bool valid(const Binding& b) {
    if (strnlen(b.method, sizeof(b.method)) == sizeof(b.method) ||
        strnlen(b.nonce, sizeof(b.nonce)) == sizeof(b.nonce) ||
        strnlen(b.count, sizeof(b.count)) == sizeof(b.count) ||
        strnlen(b.request_signature, sizeof(b.request_signature)) == sizeof(b.request_signature)) return false;
    if (!hex(b.challenge, 32) || !mac(b.node) ||
        (strcmp(b.method, "GET") && strcmp(b.method, "POST")) || !hex(b.request_hash, 64)) return false;
    size_t n = strnlen(b.path, sizeof(b.path));
    if (!n || n > PathLimit || b.path[0] != '/') return false;
    for (size_t i = 0; i < n; ++i) if (b.path[i] < '!' || b.path[i] > '~') return false;
    if (!strcmp(b.path, "/v1/challenge"))
        return !strcmp(b.method, "GET") && !strcmp(b.request_hash, EmptyHash) &&
               !strcmp(b.nonce, "-") && !strcmp(b.count, "0") && !strcmp(b.request_signature, "-");
    return hex(b.nonce, 32) && counter(b.count) && hex(b.request_signature, 64);
}
inline bool bind(Binding& b, const char* challenge, const char* node, const char* method,
                 const char* path, const char* request_hash, const char* nonce = "-",
                 const char* count = "0", const char* signature = "-") {
    b = {};
    return copy(b.challenge, challenge) && copy(b.node, node) && copy(b.method, method) &&
           copy(b.path, path) && copy(b.request_hash, request_hash) && copy(b.nonce, nonce) &&
           copy(b.count, count) && copy(b.request_signature, signature) && valid(b);
}
// Output includes all fields in a fixed order, separated by LF, without a final LF.
inline bool canonical(const Binding& b, int status, const char* body_hash, char (&out)[768], size_t& size) {
    size = 0;
    if (!valid(b) || status < 100 || status > 599 || !hex(body_hash, 64)) return false;
    int n = snprintf(out, sizeof(out), "flock-management-response-v1\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%d\n%s",
        b.challenge, b.node, b.method, b.path, b.request_hash, b.nonce, b.count, b.request_signature, status, body_hash);
    if (n < 0 || size_t(n) >= sizeof(out)) return false;
    size = size_t(n); return true;
}
// Backend returns lowercase hex HMAC-SHA256, or false on any crypto failure.
using Hmac = bool (*)(const uint8_t key[32], const char* bytes, size_t size, char out[65]);
inline bool sign(const Binding& b, int status, const char* body_hash, const uint8_t key[32], Hmac hmac, char out[65]) {
    char bytes[768]; size_t size;
    return canonical(b, status, body_hash, bytes, size) && hmac(key, bytes, size, out) && hex(out, 64);
}
struct Pending {
    Binding request{};
    int64_t started_ms = 0;
    bool waiting = true;
};
inline bool verify(Pending& pending, int64_t now_ms, const char* version, const char* signature,
                   int status, const char* body_hash, const uint8_t key[32], Hmac hmac) {
    bool waiting = pending.waiting;
    pending.waiting = false; // Exactly one attempt, including failures.
    if (!waiting || pending.started_ms < 0 || now_ms < pending.started_ms || now_ms - pending.started_ms > MaxAgeMs ||
        !version || strcmp(version, "1") || !hex(signature, 64)) return false;
    char expected[65];
    if (!sign(pending.request, status, body_hash, key, hmac, expected)) return false;
    uint8_t diff = 0;
    for (size_t i = 0; i < 64; ++i) diff |= uint8_t(expected[i] ^ signature[i]);
    return diff == 0;
}
} // namespace flock_response
