#include "maintenance.h"
#include "maintenance_gate.h"
#include "storage.h"
#include "audio.h"
#include "display.h"
#include "node_link.h"
#include "esp_http_server.h"
#include "esp_ota_ops.h"
#include "esp_app_desc.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_system.h"
#include "mbedtls/md.h"
#include "mbedtls/sha256.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include <atomic>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>
static uint8_t key[32]{};
static bool has_key=false,server_ok=false;
static char board[18]{},nonce[33]{},key_id[17]{};
static uint32_t counter=0;
static httpd_handle_t server;
static SemaphoreHandle_t guard;
static char snapshot[8192]="{}";
static node::MaintenanceGate resource;
struct Command { uint32_t id; int op; int64_t expires; char body[512]{}; };
struct Reply { uint32_t id; bool ok; };
static QueueHandle_t commands,replies;
static void hex(const uint8_t* bytes,size_t n,char* out) { for(size_t i=0;i<n;i++) snprintf(out+2*i,3,"%02x",bytes[i]); }
static bool unhex(const char* s,uint8_t* out,size_t n) {
    if(strlen(s)!=n*2) return false;
    for(size_t i=0;i<n;i++) { unsigned value=0; for(int j=0;j<2;j++) { char c=s[2*i+j]; int d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1; if(d<0) return false; value=value*16+d; } out[i]=value; } return true;
}
static bool same(const uint8_t* a,const uint8_t* b,size_t n) { uint8_t diff=0; for(size_t i=0;i<n;i++) diff|=a[i]^b[i]; return diff==0; }
static void refresh_identity() { uint8_t raw[16],digest[32]; esp_fill_random(raw,16); hex(raw,16,nonce); mbedtls_sha256(key,32,digest,0); hex(digest,8,key_id); counter=0; }
#include "management_response.h"
static bool authenticate(httpd_req_t* req,char expected_hash[65]) {
    char signature[65],received_nonce[33],target[18],count[11]; uint8_t supplied[32],actual[32],digest[32];
    if(!has_key || httpd_req_get_hdr_value_str(req,"X-Flock-Signature",signature,sizeof(signature))!=ESP_OK ||
       httpd_req_get_hdr_value_str(req,"X-Flock-Nonce",received_nonce,sizeof(received_nonce))!=ESP_OK ||
       httpd_req_get_hdr_value_str(req,"X-Flock-Target",target,sizeof(target))!=ESP_OK ||
       httpd_req_get_hdr_value_str(req,"X-Flock-Counter",count,sizeof(count))!=ESP_OK ||
       httpd_req_get_hdr_value_str(req,"X-Flock-SHA256",expected_hash,65)!=ESP_OK) return false;
    if(strcmp(target,board) || strcmp(received_nonce,nonce) || !unhex(signature,supplied,32) || !unhex(expected_hash,digest,32)) return false;
    char* end; unsigned long n=strtoul(count,&end,10);
    char canonical_count[11]; snprintf(canonical_count,sizeof(canonical_count),"%lu",n);
    if(*end || strcmp(count,canonical_count) || n!=uint64_t(counter)+1 || n>UINT32_MAX) return false;
    const char* method=req->method==HTTP_GET?"GET":"POST";
    std::string message=std::string("v1\n")+nonce+"\n"+count+"\n"+board+"\n"+method+"\n"+req->uri+"\n"+expected_hash;
    if(mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),key,32,reinterpret_cast<const uint8_t*>(message.data()),message.size(),actual)!=0 || !same(actual,supplied,32)) return false;
    counter=n; return true; // Consume before executing, including failed requests.
}
static esp_err_t challenge(httpd_req_t* req) {
    ManagementResponse response(req); if(!response.acceptable()) return ESP_FAIL;
    xSemaphoreTake(guard,portMAX_DELAY);
    char out[256]; snprintf(out,sizeof(out),"{\"v\":1,\"base_mac\":\"%s\",\"nonce\":\"%s\",\"next_counter\":%lu,\"key_id\":\"%s\",\"configured\":%s}",board,nonce,static_cast<unsigned long>(counter+1),key_id,has_key?"true":"false");
    xSemaphoreGive(guard); return response.answer(out);
}
static esp_err_t protected_status(httpd_req_t* req) {
    ManagementResponse response(req); if(!response.acceptable()) return ESP_FAIL;
    xSemaphoreTake(guard,portMAX_DELAY); char hash[65]; bool ok=authenticate(req,hash);
    const char* empty="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    if(!ok || strcmp(hash,empty) || req->content_len) { xSemaphoreGive(guard); return response.error(401,"Authentication failed"); }
    char* copy=strdup(snapshot); xSemaphoreGive(guard);
    if(!copy) return response.error(500,"No memory");
    auto result=response.answer(copy); free(copy); return result;
}
static esp_err_t control(httpd_req_t* req) {
    ManagementResponse response(req); if(!response.acceptable()) return ESP_FAIL;
    char expected[65],body[512]{}; xSemaphoreTake(guard,portMAX_DELAY); bool ok=authenticate(req,expected); uint32_t id=counter; xSemaphoreGive(guard);
    if(!ok) return response.error(401,"Authentication failed");
    if(req->content_len<1 || req->content_len>=sizeof(body)) return response.error(400,"Invalid command length");
    size_t got=0; while(got<req->content_len) { int n=httpd_req_recv(req,body+got,req->content_len-got); if(n<=0) return ESP_FAIL; got+=n; }
    uint8_t digest[32]; char actual[65]; mbedtls_sha256(reinterpret_cast<uint8_t*>(body),got,digest,0); hex(digest,32,actual);
    if(strcmp(actual,expected)) return response.error(400,"Invalid digest");
    if(body[0]=='{') {
        auto* command=cJSON_ParseWithLength(body,got);
        auto text=[&](const char* name){auto* value=cJSON_GetObjectItemCaseSensitive(command,name);return cJSON_IsString(value)?value->valuestring:"";};
        const char* action=text("op");
        if(!strncmp(action,"display_",8)||!strncmp(action,"mission_",8)){
            Command queued{};queued.id=id;queued.op=3;queued.expires=esp_timer_get_time()+3000000;memcpy(queued.body,body,got);cJSON_Delete(command);
            if(xQueueSend(commands,&queued,0)!=pdTRUE)return response.unavailable();
            Reply reply{};int64_t deadline=esp_timer_get_time()+3500000;
            while(esp_timer_get_time()<deadline){if(xQueueReceive(replies,&reply,pdMS_TO_TICKS(100))&&reply.id==id)return response.answer(reply.ok?"{\"ok\":true}":"{\"ok\":false,\"error\":\"invalid_display_command\"}");}
            return response.unavailable();
        }
        int sdop=!strcmp(action,"sd_prepare")?1:!strcmp(action,"sd_format_quick")?2:!strcmp(action,"sd_format_full")?3:0;
        uint32_t job=0;const char* error=sdop?storage_request(sdop,text("card_id"),text("token"),job):"invalid_sd_operation";
        cJSON_Delete(command);
        char out[160];
        if(error){snprintf(out,sizeof(out),"{\"ok\":false,\"error\":\"%s\"}",error);}
        else snprintf(out,sizeof(out),"{\"ok\":true,\"job\":%lu}",(unsigned long)job);
        return response.answer(out,error?409:200);
    }
    int op=!strcmp(body,"tone")?1:!strcmp(body,"next_page")?2:0;
    if(strcmp(actual,expected) || !op) return response.error(400,"Invalid command or digest");
    Command c{id,op,esp_timer_get_time()+3000000};
    if(xQueueSend(commands,&c,0)!=pdTRUE) return response.unavailable();
    Reply r{}; int64_t deadline=esp_timer_get_time()+3500000;
    while(esp_timer_get_time()<deadline) { if(xQueueReceive(replies,&r,pdMS_TO_TICKS(100)) && r.id==id) return response.answer(r.ok?"{\"ok\":true}":"{\"ok\":false}"); }
    return response.unavailable();
}
#ifdef FLOCK_MISSION_JOURNAL
#include "journal_http.h"
#endif
static esp_err_t update(httpd_req_t* req) {
    ManagementResponse response(req); if(!response.acceptable()) return ESP_FAIL;
    char expected[65]; xSemaphoreTake(guard,portMAX_DELAY); bool authenticated=authenticate(req,expected); xSemaphoreGive(guard);
    if(!authenticated) return response.error(401,"Authentication failed");
    auto* slot=esp_ota_get_next_update_partition(nullptr);
    if(!slot || req->content_len<288 || req->content_len>slot->size) return response.error(400,"Image does not fit");
    if(!maintenance_claim_update()) return response.unavailable();
    esp_ota_handle_t ota=0; esp_err_t e=esp_ota_begin(slot,req->content_len,&ota);
    mbedtls_sha256_context hash; mbedtls_sha256_init(&hash); mbedtls_sha256_starts(&hash,0);
    uint8_t buffer[2048]; size_t received=0;
    while(e==ESP_OK && received<req->content_len) {
        size_t wanted=std::min(sizeof(buffer),req->content_len-received);
        int n=httpd_req_recv(req,reinterpret_cast<char*>(buffer),wanted);
        if(n<=0) { e=ESP_ERR_TIMEOUT; break; }
        mbedtls_sha256_update(&hash,buffer,n); e=esp_ota_write(ota,buffer,n); received+=n;
    }
    uint8_t digest[32]; char actual[65]; mbedtls_sha256_finish(&hash,digest); mbedtls_sha256_free(&hash); hex(digest,32,actual);
    if(e==ESP_OK && strcmp(actual,expected)) e=ESP_ERR_INVALID_CRC;
    if(e==ESP_OK) { e=esp_ota_end(ota); ota=0; }
    if(e==ESP_OK) {
        esp_app_desc_t app{};
        e=esp_ota_get_partition_description(slot,&app);
        if(e==ESP_OK && strncmp(app.project_name,esp_app_get_description()->project_name,sizeof(app.project_name))) e=ESP_ERR_INVALID_ARG;
    }
    if(e==ESP_OK) e=esp_ota_set_boot_partition(slot);
    if(ota) esp_ota_abort(ota);
    if(e!=ESP_OK) { maintenance_release_update(); return response.error(400,"Image rejected; running slot retained"); }
    response.answer("{\"ok\":true,\"rebooting\":true}"); vTaskDelay(pdMS_TO_TICKS(250)); esp_restart(); return ESP_OK;
}
void maintenance_init(const char* mac) {
    strncpy(board,mac,sizeof(board)-1); guard=xSemaphoreCreateMutex(); commands=xQueueCreate(4,sizeof(Command)); replies=xQueueCreate(4,sizeof(Reply));
    if(!guard || !commands || !replies) return;
    nvs_handle_t nvs; if(nvs_open_from_partition("identity","maintenance",NVS_READONLY,&nvs)==ESP_OK) { size_t len=32; has_key=nvs_get_blob(nvs,"key",key,&len)==ESP_OK && len==32; nvs_close(nvs); }
    refresh_identity(); httpd_config_t cfg=HTTPD_DEFAULT_CONFIG(); cfg.stack_size=8192; cfg.recv_wait_timeout=5; cfg.send_wait_timeout=5;
    if(httpd_start(&server,&cfg)!=ESP_OK) return;
    httpd_uri_t handlers[]={ {.uri="/v1/challenge",.method=HTTP_GET,.handler=challenge,.user_ctx=nullptr}, {.uri="/v1/status",.method=HTTP_GET,.handler=protected_status,.user_ctx=nullptr}, {.uri="/v1/control",.method=HTTP_POST,.handler=control,.user_ctx=nullptr}, {.uri="/v1/update",.method=HTTP_POST,.handler=update,.user_ctx=nullptr} };
    server_ok=true;
#ifdef FLOCK_MISSION_JOURNAL
    for(const char* path:{"/v1/journal","/v1/journal/read"}) {
        httpd_uri_t endpoint{.uri=path,.method=HTTP_POST,.handler=journal::handle,.user_ctx=nullptr};
        if(httpd_register_uri_handler(server,&endpoint)!=ESP_OK) server_ok=false;
    }
#endif
    for(auto& h:handlers) if(httpd_register_uri_handler(server,&h)!=ESP_OK) server_ok=false;
}
bool maintenance_set_key(const char* value) {
    uint8_t candidate[32]; if(!guard || !unhex(value,candidate,32)) return false;
    xSemaphoreTake(guard,portMAX_DELAY);
    bool ok=false; nvs_handle_t nvs;
    if(has_key) ok=same(candidate,key,32);
    else if(nvs_open_from_partition("identity","maintenance",NVS_READWRITE,&nvs)==ESP_OK) {
        ok=nvs_set_blob(nvs,"key",candidate,32)==ESP_OK && nvs_commit(nvs)==ESP_OK; nvs_close(nvs);
        if(ok) { memcpy(key,candidate,32); has_key=true; refresh_identity(); }
    }
    memset(candidate,0,32); xSemaphoreGive(guard); return ok;
}
void maintenance_json(cJSON* root) {
    auto* j=cJSON_AddObjectToObject(root,"maintenance");
    if(guard) xSemaphoreTake(guard,portMAX_DELAY);
    cJSON_AddBoolToObject(j,"server_ready",server_ok); cJSON_AddBoolToObject(j,"key_provisioned",has_key); cJSON_AddStringToObject(j,"key_id",has_key?key_id:"");
    cJSON_AddStringToObject(j,"ota_acceptance","PENDING");
    if(guard) xSemaphoreGive(guard);
}
void maintenance_publish(cJSON* status) { node_link_publish(status); if(!guard) return; char* json=cJSON_PrintUnformatted(status); if(!json) return; xSemaphoreTake(guard,portMAX_DELAY); if(strlen(json)<sizeof(snapshot)) strcpy(snapshot,json); xSemaphoreGive(guard); free(json); }
void maintenance_tick() { if(!commands) return; Command c{}; if(xQueueReceive(commands,&c,0)) { bool ok=false; if(esp_timer_get_time()<c.expires) { if(c.op==1) ok=audio_tone(); else if(c.op==2) { display_next_page(); ok=true; } else if(c.op==3) {auto* req=cJSON_Parse(c.body);ok=req&&!display_command(req);cJSON_Delete(req);} } Reply r{c.id,ok}; xQueueSend(replies,&r,0); } }
bool maintenance_busy() { return resource.owner==node::MaintenanceOwner::Ota; }

bool maintenance_ready() { return server_ok; }
bool maintenance_copy_key(uint8_t out[32]) {
    if(!guard) return false;
    xSemaphoreTake(guard,portMAX_DELAY);
    bool ready=has_key;
    if(ready) memcpy(out,key,32);
    xSemaphoreGive(guard);
    return ready;
}
bool maintenance_claim_update() { return resource.claim(node::MaintenanceOwner::Ota); }
void maintenance_release_update() { resource.release(node::MaintenanceOwner::Ota); }
bool maintenance_claim_storage() { return resource.claim(node::MaintenanceOwner::Storage); }
void maintenance_release_storage() { resource.release(node::MaintenanceOwner::Storage); }
bool maintenance_storage_busy() { return resource.owner==node::MaintenanceOwner::Storage; }
