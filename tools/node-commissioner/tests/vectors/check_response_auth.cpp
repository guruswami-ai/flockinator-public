// Cross-implementation check of the golden vectors against the authoritative firmware
// header firmware/shared/management/response_auth.h, using OpenSSL as the HMAC backend.
// Reads tab-separated lines on stdin (text fields hex-encoded UTF-8 so tabs and newlines survive):
//   name key_hex challenge node method path request_hash nonce count request_signature status body_hex signature
// Writes one line per case:
//   name INVALID                                         (bind()/valid() rejected the binding)
//   name VALID canonical_hex signature verify_given verify_replay verify_tampered_status verify_tampered_body
// Built and driven by tests/test_response_auth_cxx.py; no sockets, devices or firmware.
#include "response_auth.h"
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/sha.h>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static const char* HEX = "0123456789abcdef";

static bool hmac_backend(const uint8_t key[32], const char* bytes, size_t size, char out[65]) {
    unsigned char digest[32]; unsigned int n = 0;
    if (!HMAC(EVP_sha256(), key, 32, reinterpret_cast<const unsigned char*>(bytes), size, digest, &n) || n != 32) return false;
    for (int i = 0; i < 32; ++i) { out[2 * i] = HEX[digest[i] >> 4]; out[2 * i + 1] = HEX[digest[i] & 15]; }
    out[64] = 0; return true;
}

static bool unhex(const std::string& in, std::vector<uint8_t>& out) {
    if (in.size() % 2) return false;
    out.clear();
    for (size_t i = 0; i < in.size(); i += 2) {
        auto digit = [](char c) { return c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1; };
        int hi = digit(in[i]), lo = digit(in[i + 1]);
        if (hi < 0 || lo < 0) return false;
        out.push_back(uint8_t(hi * 16 + lo));
    }
    return true;
}

static std::string tohex(const uint8_t* bytes, size_t n) {
    std::string out;
    for (size_t i = 0; i < n; ++i) { out += HEX[bytes[i] >> 4]; out += HEX[bytes[i] & 15]; }
    return out;
}

int main() {
    std::string line;
    while (std::getline(std::cin, line)) {
        std::vector<std::string> f; std::string field; std::istringstream in(line);
        while (std::getline(in, field, '\t')) f.push_back(field);
        if (f.size() != 13) { std::cout << (f.empty() ? "?" : f[0]) << "\tBADLINE\n"; continue; }
        std::vector<uint8_t> key, body; std::string text[13]; bool decoded = unhex(f[1], key) && key.size() == 32 && unhex(f[11], body);
        for (int i : {2, 3, 4, 5, 6, 7, 8, 9, 12}) {
            std::vector<uint8_t> raw; decoded = decoded && unhex(f[i], raw);
            text[i].assign(raw.begin(), raw.end());
        }
        if (!decoded) { std::cout << f[0] << "\tBADLINE\n"; continue; }
        flock_response::Binding b;
        if (!flock_response::bind(b, text[2].c_str(), text[3].c_str(), text[4].c_str(), text[5].c_str(), text[6].c_str(), text[7].c_str(), text[8].c_str(), text[9].c_str())) {
            std::cout << f[0] << "\tINVALID\n"; continue;
        }
        int status = std::stoi(f[10]);
        uint8_t digest[32]; SHA256(body.data(), body.size(), digest);
        std::string body_hash = tohex(digest, 32);
        char canonical[768]; size_t size = 0; char signature[65];
        if (!flock_response::canonical(b, status, body_hash.c_str(), canonical, size) ||
            !flock_response::sign(b, status, body_hash.c_str(), key.data(), hmac_backend, signature)) {
            std::cout << f[0] << "\tINVALID\n"; continue;
        }
        flock_response::Pending pending{b, 0, true};
        const char* expected = text[12].c_str();
        bool given = flock_response::verify(pending, 0, "1", expected, status, body_hash.c_str(), key.data(), hmac_backend);
        bool replay = flock_response::verify(pending, 0, "1", expected, status, body_hash.c_str(), key.data(), hmac_backend);
        flock_response::Pending other{b, 0, true};
        bool tampered_status = flock_response::verify(other, 0, "1", expected, status == 599 ? 598 : status + 1, body_hash.c_str(), key.data(), hmac_backend);
        std::string altered = body_hash; altered[0] = altered[0] == 'a' ? 'b' : 'a';
        flock_response::Pending third{b, 0, true};
        bool tampered_body = flock_response::verify(third, 0, "1", expected, status, altered.c_str(), key.data(), hmac_backend);
        std::cout << f[0] << "\tVALID\t" << tohex(reinterpret_cast<const uint8_t*>(canonical), size) << "\t" << signature << "\t"
                  << given << "\t" << replay << "\t" << tampered_status << "\t" << tampered_body << "\n";
    }
    return 0;
}
