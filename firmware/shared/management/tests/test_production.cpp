// Production function bodies are copied verbatim at build time by run_native.py.
// Only ESP transport, clocks, RNG and PSA's API boundary are host substitutes.
// All hashes and MACs use the real portable Mbed TLS implementation.
#include "controller_json.h"
#include "management/response_auth.h"
#include "mbedtls/md.h"
#include "mbedtls/sha256.h"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <map>
#include <strings.h>
#include <vector>

static unsigned checks = 0;
static void require(bool ok, const char* what) {
    ++checks;
    if (!ok) { fprintf(stderr, "FAIL: %s\n", what); exit(1); }
}
using esp_err_t = int;
constexpr int ESP_OK = 0, ESP_FAIL = -1, HTTP_GET = 0, HTTP_POST = 1, HTTP_METHOD_POST = 1;
constexpr int HTTP_EVENT_ON_HEADER = 1, HTTP_EVENT_ON_DATA = 2, HTTP_EVENT_ERROR = 3, HTTP_EVENT_ON_FINISH = 4;
static int64_t fake_ms = 100;
static uint64_t random_serial = 0;
static void esp_fill_random(void* data, size_t size) {
    // Deterministic unique test randomness only; production uses ESP's RNG.
    auto* out = static_cast<uint8_t*>(data);
    ++random_serial;
    for (size_t i = 0; i < size; ++i) out[i] = uint8_t((random_serial >> ((i % 8) * 8)) ^ (i * 19));
}
struct WireResponse { int status = 200; string body; std::vector<std::pair<string,string>> headers; };
struct httpd_req_t {
    int method = HTTP_GET;
    const char* uri = nullptr;
    size_t content_len = 0;
    std::map<string,string> headers;
    WireResponse response;
};
static size_t httpd_req_get_hdr_value_len(httpd_req_t* req, const char* name) {
    auto it = req->headers.find(name); return it == req->headers.end() ? 0 : it->second.size();
}
static int httpd_req_get_hdr_value_str(httpd_req_t* req, const char* name, char* out, size_t cap) {
    auto it = req->headers.find(name);
    if (it == req->headers.end() || it->second.size() >= cap) return ESP_FAIL;
    memcpy(out, it->second.c_str(), it->second.size() + 1); return ESP_OK;
}
static int httpd_resp_set_hdr(httpd_req_t* req, const char* name, const char* value) {
    req->response.headers.emplace_back(name, value); return ESP_OK;
}
static int httpd_resp_set_status(httpd_req_t* req, const char* status) { req->response.status = atoi(status); return ESP_OK; }
static int httpd_resp_set_type(httpd_req_t*, const char*) { return ESP_OK; }
static int httpd_resp_send(httpd_req_t* req, const char* body, size_t size) { req->response.body.assign(body, size); return ESP_OK; }
constexpr int portMAX_DELAY = 0;
static void xSemaphoreTake(int, int) {}
static void xSemaphoreGive(int) {}

namespace node {
static uint8_t key[32];
static bool has_key = true;
static char board[18] = "00:11:22:33:44:55", nonce[33] = "000102030405060708090a0b0c0d0e0f", key_id[17] = "0123456789abcdef";
static uint32_t counter = 0;
static int guard = 0;
static char snapshot[8192];
#include "node.inc"
}

// A small PSA ABI shim; it delegates every production crypto call to Mbed TLS.
using psa_key_attributes_t = int;
struct psa_key_id_t { uint8_t bytes[32]; };
constexpr int PSA_KEY_ATTRIBUTES_INIT = 0, PSA_KEY_TYPE_HMAC = 1, PSA_KEY_USAGE_SIGN_MESSAGE = 2, PSA_ALG_SHA_256 = 3, PSA_SUCCESS = 0;
static int PSA_ALG_HMAC(int x) { return x; }
static void psa_set_key_type(int*, int) {}
static void psa_set_key_usage_flags(int*, int) {}
static void psa_set_key_algorithm(int*, int) {}
static bool crypto_failure = false;
static int psa_import_key(int*, const uint8_t* key, size_t size, psa_key_id_t* id) {
    if (size != 32 || crypto_failure) return -1;
    memcpy(id->bytes, key, 32); return PSA_SUCCESS;
}
static int psa_mac_compute(psa_key_id_t id, int, const uint8_t* data, size_t size, uint8_t* out, size_t cap, size_t* actual) {
    if (cap < 32 || crypto_failure) return -1;
    *actual = 32; return mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), id.bytes, 32, data, size, out);
}
static void psa_destroy_key(psa_key_id_t) {}
static int psa_hash_compute(int, const uint8_t* data, size_t size, uint8_t* out, size_t cap, size_t* actual) {
    if (cap < 32 || crypto_failure) return -1;
    *actual = 32; return mbedtls_sha256(data, size, out, 0);
}
struct esp_http_client_event_t { int event_id; void* user_data; const char* header_key; const char* header_value; void* data; int data_len; };
struct esp_http_client_config_t {
    const char* url = nullptr;
    int timeout_ms = 0;
    esp_err_t (*event_handler)(esp_http_client_event_t*) = nullptr;
    void* user_data = nullptr;
    bool disable_auto_redirect = false;
    int buffer_size = 0, buffer_size_tx = 0;
};
struct HttpClient {
    esp_http_client_config_t cfg;
    string url, body;
    int method = HTTP_GET, status = 0;
    std::map<string,string> headers;
    bool complete = true;
};
static std::function<void(httpd_req_t&)> before_node, after_node;
static std::function<void(HttpClient&)> after_events;
static bool transport_error = false, incomplete = false, missing_finish = false, setup_error = false;
static int calls = 0;
static std::vector<string> client_challenges;
static HttpClient* esp_http_client_init(const esp_http_client_config_t* cfg) {
    auto* c = new HttpClient; c->cfg = *cfg; c->url = cfg->url; return c;
}
static int esp_http_client_set_method(HttpClient* c, int method) { c->method = method; return ESP_OK; }
static int esp_http_client_set_post_field(HttpClient* c, const char* bytes, size_t size) { c->body.assign(bytes, size); return ESP_OK; }
static int esp_http_client_set_header(HttpClient* c, const char* name, const char* value) {
    c->headers[name] = value; return setup_error ? ESP_FAIL : ESP_OK;
}
static int esp_http_client_perform(HttpClient* c) {
    ++calls;
    string uri = c->url.substr(c->url.find('/', 7));
    httpd_req_t req;
    req.uri = uri.c_str(); req.method = c->method; req.headers = c->headers; req.content_len = c->body.size();
    client_challenges.push_back(req.headers.at(flock_response::ChallengeHeader));
    if (before_node) before_node(req);
    int result;
    if (!strcmp(req.uri, "/v1/challenge")) result = node::challenge(&req);
    else if (!strcmp(req.uri, "/v1/status")) result = node::protected_status(&req);
    else {
        node::ManagementResponse response(&req);
        // Fixture for arbitrary binary journal payload; the actual response
        // serializer/signing adapter is production code.
        result = response.send(c->body.data(), c->body.size());
    }
    if (result != ESP_OK) return result;
    if (after_node) after_node(req);
    c->status = req.response.status; c->complete = !incomplete;
    for (auto& h : req.response.headers) {
        esp_http_client_event_t e{HTTP_EVENT_ON_HEADER, c->cfg.user_data, h.first.c_str(), h.second.c_str(), nullptr, 0};
        c->cfg.event_handler(&e); // Deliberately ignore callback error: receiver must latch failures.
    }
    for (size_t start = 0; start < req.response.body.size(); start += 701) {
        size_t length = std::min(size_t(701), req.response.body.size() - start);
        esp_http_client_event_t e{HTTP_EVENT_ON_DATA, c->cfg.user_data, nullptr, nullptr, &req.response.body[start], int(length)};
        c->cfg.event_handler(&e);
    }
    if (!missing_finish) {
        esp_http_client_event_t e{HTTP_EVENT_ON_FINISH, c->cfg.user_data, nullptr, nullptr, nullptr, 0}; c->cfg.event_handler(&e);
    }
    if (after_events) after_events(*c);
    return transport_error ? ESP_FAIL : ESP_OK;
}
static int esp_http_client_get_status_code(HttpClient* c) { return c->status; }
static bool esp_http_client_is_complete_data_received(HttpClient* c) { return c->complete; }
static void esp_http_client_cleanup(HttpClient* c) { delete c; }

namespace monitor {
struct Panel { char mac[18], ip[16]; uint8_t key[32]; };
struct Health { int64_t at; bool live; unsigned uptime,ram; char version[17]; };
static Panel panels[16];
static Health health[16];
static bool ready = true;
static int mutex = 0;
struct Guard { explicit Guard(int) {} };
static int64_t ms() { return fake_ms; }
static string name(int) { return "A1"; }
string sha256hex(const string&);
bool signed_panel(int,const char*,const char*,const string&,string&);
#include "monitor.inc"
}

static void reset() {
    before_node = {}; after_node = {}; after_events = {};
    transport_error = incomplete = missing_finish = setup_error = crypto_failure = false;
    fake_ms = 100; calls = 0; client_challenges.clear();
    node::counter = 0; node::has_key = true;
    strcpy(node::board, "00:11:22:33:44:55");
    strcpy(node::snapshot, "{\"label\":\"A1\",\"base_mac\":\"00:11:22:33:44:55\",\"type\":\"status\",\"uptime_ms\":123000,\"free_internal\":102400,\"firmware\":\"test-only\"}");
    for (size_t i = 0; i < 32; ++i) node::key[i] = monitor::panels[0].key[i] = uint8_t(i);
    strcpy(monitor::panels[0].mac, node::board); strcpy(monitor::panels[0].ip, "192.0.2.1");
    monitor::ready = true; monitor::health[0] = {};
}
static bool status() { Json result; return monitor::status(0, result); }
static void rejected(const char* label) {
    monitor::health[0].live = true;
    require(!status(), label); require(!monitor::health[0].live, "error never leaves health live");
}
static bool operation(const httpd_req_t& req) { return strcmp(req.uri, "/v1/challenge") != 0; }
static void production_cases() {
    reset(); require(status(), "legitimate production node status accepted");
    require(monitor::health[0].live && monitor::health[0].uptime == 123, "only authenticated status updates health");
    require(client_challenges.size() == 2 && client_challenges[0] != client_challenges[1], "bootstrap and operation challenges are fresh");
    require(node::counter == 1, "original v1 request authentication and counter consumption retained");

    reset(); after_node = [](auto& req) { req.response.headers.clear(); }; rejected("legacy unsigned device rejected");
    reset(); after_node = [](auto& req) { if (operation(req)) req.response.headers.clear(); }; rejected("unsigned fabricated operation rejected");
    reset(); after_node = [](auto& req) { if (operation(req)) req.response.body += " "; }; rejected("exact body alteration rejected");
    reset(); after_node = [](auto& req) { if (operation(req)) req.response.status = 503; }; rejected("status alteration rejected");
    reset(); before_node = [](auto& req) { if (operation(req)) strcpy(node::board,"00:11:22:33:44:56"); }; rejected("wrong node identity rejected");
    reset(); before_node = [](auto& req) { if (operation(req)) req.uri = "/v1/control"; }; rejected("crossed path rejected");
    reset(); before_node = [](auto& req) { if (operation(req)) req.method = HTTP_POST; }; rejected("changed method rejected");
    reset(); before_node = [](auto& req) { req.headers[flock_response::ChallengeHeader][0] ^= 1; }; rejected("client challenge alteration rejected");
    reset(); before_node = [](auto& req) { if (operation(req)) req.headers["X-Flock-SHA256"] = string(64,'0'); }; rejected("request hash alteration rejected");
    reset(); before_node = [](auto& req) { if (operation(req)) req.headers["X-Flock-Counter"] = "2"; }; rejected("request counter alteration rejected");
    reset(); before_node = [](auto& req) { if (operation(req)) req.headers["X-Flock-Signature"][0] ^= 1; }; rejected("request signature alteration rejected");
    reset(); after_node = [](auto& req) { req.response.headers[0].second = "2"; }; rejected("unknown response version rejected");
    reset(); after_node = [](auto& req) { req.response.headers.emplace_back("x-flock-response-version","1"); }; rejected("duplicate case-insensitive version rejected");
    reset(); after_node = [](auto& req) { req.response.headers.push_back(req.response.headers[1]); }; rejected("duplicate signature rejected");
    reset(); after_node = [](auto& req) { req.response.headers[1].second += "0"; }; rejected("overlong signature rejected");
    reset(); after_node = [](auto& req) { req.response.body.assign(flock_response::BodyLimit+1, 'x'); }; rejected("overflow latched even if transport ignores callback error");
    reset(); transport_error = true; rejected("transport error rejected");
    reset(); incomplete = true; rejected("truncated HTTP framing rejected");
    reset(); missing_finish = true; rejected("missing completion event rejected");
    reset(); setup_error = true; rejected("failed request header setup rejected"); require(calls == 0,"no send after setup failure");
    reset(); after_events = [](auto&) { fake_ms += flock_response::MaxAgeMs + 1; }; rejected("monotonic expiry rejected");
    reset(); after_events = [](auto& c) {
        esp_http_client_event_t e{HTTP_EVENT_ERROR,c.cfg.user_data,nullptr,nullptr,nullptr,0}; c.cfg.event_handler(&e);
    }; rejected("event error latched even with perform success");
    reset(); after_events = [](auto& c) {
        char byte='x';esp_http_client_event_t e{HTTP_EVENT_ON_DATA,c.cfg.user_data,nullptr,nullptr,&byte,-1};c.cfg.event_handler(&e);
    }; rejected("invalid callback length rejected");
    reset(); crypto_failure = true; rejected("crypto failure rejected");

    // An authentic error is still not a successful operation. Flipping its
    // status to 200 must also fail because numeric status is covered by the MAC.
    for (bool flip : {false,true}) {
        reset(); before_node = [](auto& req) { if (operation(req)) node::counter += 1; };
        after_node = [flip](auto& req) { if (operation(req)) { require(req.response.status==401,"production sender signs auth errors"); if(flip)req.response.status=200; } };
        rejected(flip ? "signed error promoted to 200 rejected" : "signed HTTP error cannot mark live");
    }
    reset(); strcpy(node::snapshot,"{\"label\":{},\"type\":\"status\"}"); rejected("signed malformed status fails without exception");
    reset(); before_node = [](auto&) { node::has_key = false; }; rejected("unconfigured node cannot claim authenticated response");

    reset(); string out = "stale"; monitor::ready = false;
    require(!monitor::signed_panel(0,"GET","/v1/status","",out) && out.empty(), "failure clears stale reply");
    reset(); after_node = [](auto& req) { if (operation(req)) req.response.headers.clear(); };out="stale";
    require(!monitor::signed_panel(0,"GET","/v1/status","",out) && out.empty(), "rejected bytes never escape signed_panel");

    reset(); string binary(flock_response::BodyLimit,'\0'); for(size_t i=0;i<binary.size();++i)binary[i]=char(i);
    require(monitor::signed_panel(0,"POST","/v1/journal/read",binary,out) && out==binary,"bounded binary response preserves NULs and exact limit");
}

static void replay_and_concurrency() {
    reset(); WireResponse old_challenge, old_status;
    after_node = [&](auto& req) { (operation(req)?old_status:old_challenge) = req.response; };
    require(status(),"capture authentic exchange");
    after_node = [&](auto& req) { req.response = operation(req)?old_status:old_challenge; };
    int before = calls; rejected("captured exchange with maliciously replayed server challenge rejected");
    require(calls == before + 1,"replayed challenge stopped before operation request");

    // Even if a peer emits the same server nonce/counter again, a captured
    // operation response cannot match the new client-generated challenge.
    node::counter = 0; after_node = [&](auto& req) { if(operation(req))req.response=old_status; };
    rejected("old operation rejected with identical server nonce and counter");

    reset();
    auto make_req=[](char challenge_char) {
        httpd_req_t req;req.uri="/v1/challenge";
        req.headers[flock_response::VersionHeader]="1";
        req.headers[flock_response::ChallengeHeader]=string(32,challenge_char);return req;
    };
    auto a=make_req('a'),b=make_req('b');
    node::ManagementResponse a_response(&a),b_response(&b);
    require(b_response.answer("same") == ESP_OK && a_response.answer("same") == ESP_OK,"interleaved sender contexts operate independently");
    flock_response::Binding ab,bb;
    require(flock_response::bind(ab,string(32,'a').c_str(),node::board,"GET","/v1/challenge",flock_response::EmptyHash),"bind A");
    require(flock_response::bind(bb,string(32,'b').c_str(),node::board,"GET","/v1/challenge",flock_response::EmptyHash),"bind B");
    string hash=monitor::sha256hex("same");
    flock_response::Pending ap{ab,100,true},bp{bb,100,true};
    require(!flock_response::verify(ap,101,"1",b.response.headers[1].second.c_str(),200,hash.c_str(),node::key,node::response_hmac),"crossed concurrent response B rejected by A");
    require(!flock_response::verify(bp,101,"1",a.response.headers[1].second.c_str(),200,hash.c_str(),node::key,node::response_hmac),"crossed concurrent response A rejected by B");
    ap={ab,100,true};bp={bb,100,true};
    require(flock_response::verify(ap,101,"1",a.response.headers[1].second.c_str(),200,hash.c_str(),node::key,node::response_hmac),"A accepts its own response");
    require(flock_response::verify(bp,101,"1",b.response.headers[1].second.c_str(),200,hash.c_str(),node::key,node::response_hmac),"B accepts its own response");
    require(!flock_response::verify(ap,102,"1",a.response.headers[1].second.c_str(),200,hash.c_str(),node::key,node::response_hmac),"response cannot be accepted twice");

    reset(); // Legacy request authentication remains usable, without a response-auth claim.
    httpd_req_t req;req.uri="/v1/status";
    string message=string("v1\n")+node::nonce+"\n1\n"+node::board+"\nGET\n/v1/status\n"+flock_response::EmptyHash;
    req.headers={{"X-Flock-Nonce",node::nonce},{"X-Flock-Counter","1"},{"X-Flock-Target",node::board},
                 {"X-Flock-SHA256",flock_response::EmptyHash},{"X-Flock-Signature",monitor::sign(node::key,message)}};
    require(node::protected_status(&req)==ESP_OK&&req.response.status==200,"legacy signed request remains valid");
    require(req.response.headers.empty(),"legacy request makes no response-auth claim");
    require(node::protected_status(&req)==ESP_OK&&req.response.status==401,"legacy request replay remains rejected");
}

int main() {
    production_cases(); replay_and_concurrency();
    printf("PASS: %u compiled production HTTP checks (in-process transport, real Mbed TLS)\n",checks);
}
