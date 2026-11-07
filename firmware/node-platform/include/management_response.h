#pragma once
// Included by maintenance.cpp after key/identity declarations. A context belongs
// to one HTTP request; it never refers to a global "last request" or counter.
#include "management/response_auth.h"

static bool response_hmac(const uint8_t* secret, const char* bytes, size_t size, char out[65]) {
    uint8_t digest[32];
    if (mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), secret, 32,
                       reinterpret_cast<const uint8_t*>(bytes), size, digest) != 0) return false;
    hex(digest, 32, out); return true;
}
class ManagementResponse {
    httpd_req_t* req;
    flock_response::Binding binding{};
    uint8_t response_key[32]{};
    bool requested = false, valid = true;
    template<size_t N> bool header(const char* name, char (&out)[N]) {
        size_t n = httpd_req_get_hdr_value_len(req, name);
        return n > 0 && n < N && httpd_req_get_hdr_value_str(req, name, out, N) == ESP_OK;
    }
public:
    explicit ManagementResponse(httpd_req_t* request) : req(request) {
        requested = httpd_req_get_hdr_value_len(req, flock_response::VersionHeader) ||
                    httpd_req_get_hdr_value_len(req, flock_response::ChallengeHeader);
        if (!requested) return; // Legacy request clients remain supported.
        char version[2], challenge[33], hash[65], nonce[33], count[11], signature[65];
        xSemaphoreTake(guard, portMAX_DELAY);
        valid = has_key;
        if (valid) memcpy(response_key, key, sizeof(response_key));
        xSemaphoreGive(guard);
        valid = valid && header(flock_response::VersionHeader, version) && !strcmp(version, "1") &&
                header(flock_response::ChallengeHeader, challenge);
        if (!valid) return;
        const char* method = req->method == HTTP_GET ? "GET" : req->method == HTTP_POST ? "POST" : "";
        if (!strcmp(req->uri, "/v1/challenge")) {
            valid = req->content_len == 0 && flock_response::bind(binding, challenge, board, method,
                        req->uri, flock_response::EmptyHash);
        } else {
            valid = header("X-Flock-SHA256", hash) && header("X-Flock-Nonce", nonce) &&
                    header("X-Flock-Counter", count) && header("X-Flock-Signature", signature) &&
                    flock_response::bind(binding, challenge, board, method, req->uri, hash, nonce, count, signature);
        }
    }
    bool acceptable() const { return valid; }
    esp_err_t send(const char* bytes, size_t size, int status = 200, const char* type = "application/json") {
        if (!valid || size > flock_response::BodyLimit) return ESP_FAIL;
        const char* status_line = status == 200 ? "200 OK" : status == 400 ? "400 Bad Request" :
            status == 401 ? "401 Unauthorized" : status == 404 ? "404 Not Found" :
            status == 409 ? "409 Conflict" : status == 500 ? "500 Internal Server Error" :
            status == 503 ? "503 Service Unavailable" : nullptr;
        if (!status_line) return ESP_FAIL;
        char signature[65];
        if (requested) {
            uint8_t digest[32]; char hash[65];
            if (mbedtls_sha256(reinterpret_cast<const uint8_t*>(bytes), size, digest, 0) != 0) return ESP_FAIL;
            hex(digest, 32, hash);
            if (!flock_response::sign(binding, status, hash, response_key, response_hmac, signature) ||
                httpd_resp_set_hdr(req, flock_response::VersionHeader, "1") != ESP_OK ||
                httpd_resp_set_hdr(req, flock_response::SignatureHeader, signature) != ESP_OK) return ESP_FAIL;
        }
        if (httpd_resp_set_status(req, status_line) != ESP_OK || httpd_resp_set_type(req, type) != ESP_OK) return ESP_FAIL;
        // Header buffers remain alive until the synchronous send has completed.
        return httpd_resp_send(req, bytes, size);
    }
    esp_err_t answer(const char* text, int status = 200) { return send(text, strlen(text), status); }
    esp_err_t error(int status, const char* text) { return send(text, strlen(text), status, "text/html"); }
    esp_err_t unavailable() { return answer("{\"error\":\"busy_or_timeout\"}", 503); }
};
