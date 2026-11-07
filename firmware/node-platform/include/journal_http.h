#pragma once
// Included by maintenance.cpp after its authenticated-request helpers.
#include <sys/stat.h>
#include <unistd.h>
#include <cerrno>
#include "esp_heap_caps.h"

namespace journal {
constexpr size_t Limit = 128 * 1024;
struct StorageLease { ~StorageLease(){ maintenance_release_storage(); } };

static bool hash_file(const char* path, const char* expected, size_t bytes) {
    FILE* file = fopen(path,"rb");
    if (!file) return false;
    mbedtls_sha256_context hash;
    mbedtls_sha256_init(&hash); mbedtls_sha256_starts(&hash,0);
    uint8_t chunk[1024], digest[32]; size_t count=0, n;
    while (count<=bytes && (n=fread(chunk,1,sizeof(chunk),file))>0) {
        count+=n; mbedtls_sha256_update(&hash,chunk,n);
    }
    bool ok=!ferror(file) && count==bytes;
    fclose(file); mbedtls_sha256_finish(&hash,digest); mbedtls_sha256_free(&hash);
    char actual[65]; hex(digest,32,actual);
    return ok && !strcmp(expected,actual);
}

static esp_err_t handle(httpd_req_t* req) {
    ManagementResponse response(req); if(!response.acceptable()) return ESP_FAIL;
    char signed_hash[65];
    xSemaphoreTake(guard,portMAX_DELAY);
    bool auth=authenticate(req,signed_hash);
    xSemaphoreGive(guard);
    if (!auth) return response.error(401,"Authentication failed");
    bool read=!strcmp(req->uri,"/v1/journal/read");
    size_t size=req->content_len;
    if (!size || size>Limit || (read && size!=64))
        return response.error(400,"Invalid journal length");
    auto* body=static_cast<uint8_t*>(heap_caps_malloc(size+1,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if (!body) return response.unavailable();
    struct Buffer { void* p; ~Buffer(){free(p);} } cleanup{body};
    for (size_t got=0;got<size;) {
        int n=httpd_req_recv(req,reinterpret_cast<char*>(body+got),size-got);
        if (n<=0) return ESP_FAIL;
        got+=n;
    }
    body[size]=0;
    uint8_t digest[32]; char actual[65];
    mbedtls_sha256(body,size,digest,0); hex(digest,32,actual);
    if (strcmp(actual,signed_hash))
        return response.error(400,"Digest mismatch");
    const char* key=read?reinterpret_cast<char*>(body):signed_hash;
    if (read && !unhex(key,digest,32))
        return response.error(400,"Invalid journal ID");
    if (!maintenance_claim_storage()) return response.unavailable();
    StorageLease lease;
    char path[96]; snprintf(path,sizeof(path),"/sd/JOURNALS/%s.jsonl",key);
    if (read) {
        struct stat entry{};
        if (stat(path,&entry)!=0) return response.error(404,"Unknown journal");
        if (entry.st_size<=0 || entry.st_size>Limit) return response.unavailable();
        FILE* f=fopen(path,"rb");
        if (!f) return response.unavailable();
        // Sign and send the same bounded snapshot; no hash/read race on the SD.
        size_t length=static_cast<size_t>(entry.st_size);
        auto* data=static_cast<char*>(heap_caps_malloc(length,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
        if (!data) { fclose(f); return response.unavailable(); }
        Buffer content{data};
        bool complete=fread(data,1,length,f)==length && fgetc(f)==EOF && !ferror(f);
        fclose(f);
        if (!complete) return response.unavailable();
        return response.send(data,length,200,"application/x-ndjson");
    }
    if (mkdir("/sd/JOURNALS",0700)!=0 && errno!=EEXIST) return response.unavailable();
    struct stat existing{};
    if (stat(path,&existing)==0) {
        if (!hash_file(path,key,size)) return response.unavailable();
    } else {
        if (errno!=ENOENT) return response.unavailable();
        const char* temp="/sd/JOURNALS/PENDING.TMP";
        FILE* f=fopen(temp,"wb");
        if (!f) return response.unavailable();
        bool ok=fwrite(body,1,size,f)==size;
        if (fclose(f)!=0) ok=false;
        // Reopen the card file before publishing; a retry can verify an existing file.
        if (!ok || !hash_file(temp,key,size) || rename(temp,path)!=0) {
            unlink(temp); return response.unavailable();
        }
    }
    char reply[120]; snprintf(reply,sizeof(reply),"{\"ok\":true,\"sha256\":\"%s\",\"bytes\":%u}",key,unsigned(size));
    return response.answer(reply);
}
}
