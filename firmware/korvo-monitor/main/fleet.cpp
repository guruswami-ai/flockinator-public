#include "fleet.h"
#include "controller.h"
#include "esp_http_client.h"
#include "esp_timer.h"
#include "esp_random.h"
#include "esp_mac.h"
#include "psa/crypto.h"
#include "../../shared/management/response_auth.h"
#include <arpa/inet.h>
#include <strings.h>
#include <ctime>
#include <atomic>
#include "mission_world.h"
namespace {
struct Panel {char mac[18],ip[16];uint8_t key[32];};
struct Mission {uint32_t id,revision;int scenario,goal,seconds;bool repeat,started;int64_t wall_start;uint16_t verified;};
Panel panels[16]{},stage[16]{};
uint16_t staged;
Mission mission{0,0,0,1,64,true,false,0,0};
struct Health{int64_t at;bool live;unsigned uptime,ram;char version[17];};
Health health[16]{};
SemaphoreHandle_t mutex;
nvs_handle_t ns;
std::atomic<bool> ready{false};
std::atomic<bool> network_ready{false};
bool busy=false;
int64_t origin_ms;
int64_t ms(){return esp_timer_get_time()/1000;}
int64_t wall(){timeval tv{};gettimeofday(&tv,nullptr);return int64_t(tv.tv_sec)*1000+tv.tv_usec/1000;}
string name(int i){return string(1,char('A'+i/4))+char('1'+i%4);}
string hex(const uint8_t* p,size_t n){const char* digits="0123456789abcdef";string s(n*2,'0');for(size_t i=0;i<n;i++){s[i*2]=digits[p[i]>>4];s[i*2+1]=digits[p[i]&15];}return s;}
string sign(const uint8_t* key,const string& text){
    psa_key_attributes_t attr=PSA_KEY_ATTRIBUTES_INIT;psa_key_id_t id;
    psa_set_key_type(&attr,PSA_KEY_TYPE_HMAC);psa_set_key_usage_flags(&attr,PSA_KEY_USAGE_SIGN_MESSAGE);
    psa_set_key_algorithm(&attr,PSA_ALG_HMAC(PSA_ALG_SHA_256));
    if(psa_import_key(&attr,key,32,&id)!=PSA_SUCCESS)return {};
    uint8_t out[32];size_t n=0;
    auto e=psa_mac_compute(id,PSA_ALG_HMAC(PSA_ALG_SHA_256),(const uint8_t*)text.data(),text.size(),out,32,&n);
    psa_destroy_key(id);return e==PSA_SUCCESS&&n==32?hex(out,n):string{};
}
bool response_hmac(const uint8_t* key,const char* bytes,size_t size,char out[65]){
    string signature=sign(key,string(bytes,size));
    if(!flock_response::hex(signature.c_str(),64))return false;
    memcpy(out,signature.c_str(),65);return true;
}
struct ReceivedResponse {
    string body;
    char version[2]{},signature[65]{};
    bool version_seen=false,signature_seen=false,failed=false,finished=false;
};
esp_err_t receive(esp_http_client_event_t* e){
    auto& r=*static_cast<ReceivedResponse*>(e->user_data);
    if(e->event_id==HTTP_EVENT_ON_HEADER){
        if(!e->header_key||!e->header_value)r.failed=true;
        else if(!strcasecmp(e->header_key,flock_response::VersionHeader)){
            if(r.version_seen||!flock_response::copy(r.version,e->header_value))r.failed=true;
            r.version_seen=true;
        }else if(!strcasecmp(e->header_key,flock_response::SignatureHeader)){
            if(r.signature_seen||!flock_response::copy(r.signature,e->header_value))r.failed=true;
            r.signature_seen=true;
        }
    }else if(e->event_id==HTTP_EVENT_ON_DATA){
        if(r.finished||e->data_len<0||size_t(e->data_len)>flock_response::BodyLimit-r.body.size()||(!e->data&&e->data_len))r.failed=true;
        if(!r.failed&&e->data_len)r.body.append(static_cast<const char*>(e->data),e->data_len);
    }else if(e->event_id==HTTP_EVENT_ERROR)r.failed=true;
    else if(e->event_id==HTTP_EVENT_ON_FINISH)r.finished=true;
    return r.failed?ESP_FAIL:ESP_OK;
}
bool fetch(const Panel& p,const char* path,const char* method,const string& bytes,const Json& headers,
           const flock_response::Binding& binding,string& reply){
    reply.clear();
    flock_response::Pending pending{binding,ms(),true};ReceivedResponse received;
    string url="http://"+string(p.ip)+path;esp_http_client_config_t cfg{};
    cfg.url=url.c_str();cfg.timeout_ms=1700;cfg.event_handler=receive;cfg.user_data=&received;
    cfg.disable_auto_redirect=true;cfg.buffer_size=2048;cfg.buffer_size_tx=1024;
    auto c=esp_http_client_init(&cfg);if(!c)return false;
    bool setup=true;
    if(!strcmp(method,"POST"))setup=esp_http_client_set_method(c,HTTP_METHOD_POST)==ESP_OK&&esp_http_client_set_post_field(c,bytes.data(),bytes.size())==ESP_OK;
    for(auto it=headers.begin();it!=headers.end();++it)
        if(esp_http_client_set_header(c,it.key().c_str(),it.value().get_ref<const string&>().c_str())!=ESP_OK)setup=false;
    if(esp_http_client_set_header(c,flock_response::VersionHeader,"1")!=ESP_OK||
       esp_http_client_set_header(c,flock_response::ChallengeHeader,binding.challenge)!=ESP_OK)setup=false;
    auto e=setup?esp_http_client_perform(c):ESP_FAIL;int status=esp_http_client_get_status_code(c);
    bool complete=esp_http_client_is_complete_data_received(c);
    esp_http_client_cleanup(c);
    if(e!=ESP_OK||!complete||received.failed||!received.finished||!received.version_seen||!received.signature_seen)return false;
    string digest=sha256hex(received.body);
    if(!flock_response::verify(pending,ms(),received.version,received.signature,status,digest.c_str(),p.key,response_hmac)||status!=200)return false;
    reply.swap(received.body);return true;
}
bool status(int i,Json& s){
    string data;bool ok=signed_panel(i,"GET","/v1/status","",data);
    if(ok){
        s=Json::parse(data,nullptr,false);
        ok=s.is_object()&&s.contains("label")&&s["label"]==name(i)&&s.contains("base_mac")&&s["base_mac"]==panels[i].mac&&
           s.contains("type")&&s["type"]=="status"&&s.contains("uptime_ms")&&natural(s["uptime_ms"],UINT64_MAX)&&
           s.contains("free_internal")&&natural(s["free_internal"],UINT32_MAX)&&s.contains("firmware")&&s["firmware"].is_string();
    }
    Health h{};h.at=ms();h.live=ok;
    if(ok){h.uptime=s.value("uptime_ms",uint64_t{})/1000;h.ram=s.value("free_internal",0u)/1024;snprintf(h.version,sizeof(h.version),"%s",s.value("firmware",string{}).c_str());}
    {Guard l(mutex);health[i]=h;}return ok;
}
void dispatch(Mission m,int64_t start){
    uint32_t runs[16]{};uint16_t sent=0,verified=0;
    for(int attempt=0;attempt<3&&sent!=0xffff;attempt++){
        for(int i=0;i<16;i++){
            if(sent&(1u<<i))continue;
            Json s;if(!status(i,s)||!s.contains("mission")||s["mission"].value("source",string{})!="scripted_simulation")continue;
            auto& reported=s["mission"];
            runs[i]=m.started?m.id:reported.value("run",0u);
            bool active=reported.value("running",false)||reported.value("waiting",false);
            // A lost acknowledgement can still mean the command took effect.
            // Read before retrying, retaining the original common start time.
            if((m.started&&reported.value("run",0u)==m.id&&active)||(!m.started&&!active)){
                sent|=1u<<i;continue;
            }
            int64_t delay=m.started?start-ms():0;if(delay<0||delay>60000)continue;
            Json cmd={{"op",m.started?"mission_start":"mission_stop"},{"run",runs[i]},{"seed",271828},{"scenario",m.scenario},{"goal",m.goal},{"seconds",m.seconds},{"repeat",m.repeat},{"delay_ms",delay}};
            string reply;if(!signed_panel(i,"POST","/v1/control",cmd.dump(),reply))continue;
            auto ack=Json::parse(reply,nullptr,false);if(ack.is_object()&&ack.value("ok",false))sent|=1u<<i;
        }
    }
    for(int pass=0;pass<3&&verified!=sent;pass++){
        vTaskDelay(pdMS_TO_TICKS(700));
        for(int i=0;i<16;i++)if(((sent&~verified)>>i)&1){
            Json s;if(!status(i,s)||!s.contains("mission"))continue;auto& r=s["mission"];
            if(r.value("run",0u)==runs[i]&&(r.value("running",false)||r.value("waiting",false))==m.started)verified|=1u<<i;
        }
    }
    Guard lock(mutex);mission.verified=verified;busy=false;nvs_set_blob(ns,"mission",&mission,sizeof(mission));nvs_commit(ns);
}
void worker(void*){
    int i=0,delivery=0;
    for(;;){
        if(!ready||!network_ready){vTaskDelay(pdMS_TO_TICKS(300));continue;}
        Mission m;bool work;int64_t start;
        {Guard l(mutex);work=busy;m=mission;start=origin_ms;}
        if(work){dispatch(m,start);continue;}
        Json s;status(i,s);
        i=(i+1)%16;
        // Refresh the complete fleet between SD transfers so a growing archive
        // cannot make healthy panels appear offline during delivery.
        if(i==0){deliver_next(delivery);delivery=(delivery+1)%16;}
        vTaskDelay(pdMS_TO_TICKS(180));
    }
}
}
string sha256hex(const string& bytes){uint8_t b[32];size_t n=0;if(psa_hash_compute(PSA_ALG_SHA_256,(const uint8_t*)bytes.data(),bytes.size(),b,32,&n)!=PSA_SUCCESS)return {};return hex(b,n);}
bool signed_panel(int i,const char* method,const char* path,const string& body,string& reply){
    reply.clear();
    if(!ready||i<0||i>=16)return false;
    const auto& p=panels[i];string raw;
    uint8_t random[16];esp_fill_random(random,sizeof(random));string client=hex(random,sizeof(random));
    flock_response::Binding binding;
    if(!flock_response::bind(binding,client.c_str(),p.mac,"GET","/v1/challenge",flock_response::EmptyHash)||
       !fetch(p,"/v1/challenge","GET","",Json::object(),binding,raw))return false;
    auto c=Json::parse(raw,nullptr,false);
    if(!c.is_object()||!c.contains("base_mac")||c["base_mac"]!=p.mac||!c.contains("configured")||c["configured"]!=true||
       !c.contains("v")||!natural(c["v"],1)||c["v"]!=1||!c.contains("next_counter")||
       !natural(c["next_counter"],UINT32_MAX)||c["next_counter"]==0||!c.contains("nonce")||!c["nonce"].is_string())return false;
    string nonce=c["nonce"];if(nonce.size()!=32||nonce.find_first_not_of("0123456789abcdef")!=string::npos)return false;
    string counter=c["next_counter"].dump(),digest=sha256hex(body);
    string msg="v1\n"+nonce+"\n"+counter+"\n"+p.mac+"\n"+method+"\n"+path+"\n"+digest;
    string sig=sign(p.key,msg);if(sig.empty())return false;
    Json headers={{"X-Flock-Nonce",nonce},{"X-Flock-Counter",counter},{"X-Flock-Target",p.mac},{"X-Flock-SHA256",digest},{"X-Flock-Signature",sig},{"Content-Type","application/octet-stream"}};
    esp_fill_random(random,sizeof(random));client=hex(random,sizeof(random));
    if(!flock_response::bind(binding,client.c_str(),p.mac,method,path,digest.c_str(),nonce.c_str(),counter.c_str(),sig.c_str()))return false;
    return fetch(p,path,method,body,headers,binding,reply);
}
bool fleet_init(nvs_handle_t handle){
    ns=handle;mutex=xSemaphoreCreateMutex();size_t sz=sizeof(panels);
    ready=nvs_get_blob(ns,"roster",panels,&sz)==ESP_OK&&sz==sizeof(panels);
    sz=sizeof(mission);Mission saved{};
    if(nvs_get_blob(ns,"mission",&saved,&sz)==ESP_OK&&sz==sizeof(saved)){mission=saved;origin_ms=ms()+(saved.wall_start-wall());}
    return xTaskCreate(worker,"fleet_io",16384,nullptr,2,nullptr)==pdPASS;
}
extern "C" bool standalone_ready(){return ready;}
extern "C" void standalone_network(bool connected){network_ready=connected;}
bool fleet_provision(const char* text){
    if(!mutex)return false;
    char target[18],label[3],ip[16],mac[18],key[65],extra;
    if(sscanf(text,"FK1 %17s %2s %15s %17s %64s%c",target,label,ip,mac,key,&extra)!=5)return false;
    uint8_t own[6];esp_read_mac(own,ESP_MAC_BASE);char wanted[18];
    snprintf(wanted,sizeof(wanted),"%02X:%02X:%02X:%02X:%02X:%02X",own[0],own[1],own[2],own[3],own[4],own[5]);
    in_addr addr;if(strcmp(wanted,target)||inet_aton(ip,&addr)!=1||strlen(label)!=2||label[0]<'A'||label[0]>'D'||label[1]<'1'||label[1]>'4'||strlen(mac)!=17||strlen(key)!=64||strspn(key,"0123456789abcdef")!=64)return false;
    int i=(label[0]-'A')*4+label[1]-'1';Panel& p=stage[i];
    strcpy(p.mac,mac);strcpy(p.ip,ip);for(int j=0;j<32;j++){unsigned b;sscanf(key+2*j,"%2x",&b);p.key[j]=b;}
    staged|=1u<<i;
    if(staged==0xffff){
        if(nvs_set_blob(ns,"roster",stage,sizeof(stage))!=ESP_OK||nvs_commit(ns)!=ESP_OK)return false;
        if(!ready){memcpy(panels,stage,sizeof(stage));ready=true;} // Re-provisioned rosters activate on reboot.
        memset(stage,0,sizeof(stage));staged=0;
    }
    return true;
}
bool fleet_command(const Json& v,string& err){
    if(!ready){err="Panel roster missing";return false;}
    if(!v.contains("start")||!v["start"].is_boolean()||!v.contains("repeat")||!v["repeat"].is_boolean()||
       !v.contains("seconds")||(v["seconds"]!=64&&v["seconds"]!=96)||!v.contains("scenario")||!natural(v["scenario"],2)||
       !v.contains("goal")||!natural(v["goal"],2)){err="Invalid mission parameters";return false;}
    if(v["start"]==true&&wall()<1700000000000LL){err="Clock pending. Start from the web controls or wait for network time.";return false;}
    Guard l(mutex);
    if(busy||!v.contains("previous")||v["previous"]!=mission.revision){err="Mission changed or a command is in progress";return false;}
    auto next=mission;next.started=v["start"];if(next.started)next.id=esp_random()|1u;
    next.seconds=v["seconds"];next.scenario=v["scenario"];next.goal=v["goal"];next.repeat=v["repeat"];next.revision++;next.verified=0;
    next.wall_start=wall()+60000;
    if(nvs_set_blob(ns,"mission",&next,sizeof(next))!=ESP_OK||nvs_commit(ns)!=ESP_OK){err="Cannot persist mission";return false;}
    mission=next;origin_ms=ms()+60000;busy=true;return true;
}
extern "C" bool standalone_touch(bool start,unsigned scenario,unsigned goal,unsigned seconds,bool repeat){
    unsigned prev;{Guard l(mutex);prev=mission.revision;}string err;
    return fleet_command({{"start",start},{"scenario",scenario},{"goal",goal},{"seconds",seconds},{"repeat",repeat},{"previous",prev}},err);
}
extern "C" void standalone_panel(int i,panel_view_t* out){
    *out={};if(!mutex||!ready)return;
    Mission m;Health h;int64_t start;{Guard l(mutex);m=mission;h=health[i];start=origin_ms;}
    out->known=h.at>0;out->live=h.live;out->uptime=h.uptime;out->ram=h.ram;out->age_ms=ms()-h.at;strcpy(out->version,h.version);
    int64_t elapsed=wall()>1700000000000LL?wall()-m.wall_start:ms()-start;
    recon::Runtime runtime;runtime.apply({m.id?m.id:1,271828,(uint16_t)m.seconds,(uint8_t)m.scenario,(uint8_t)m.goal,m.repeat},true,0,0);
    out->state=recon::READY;
    if(!m.started||wall()<1700000000000LL||elapsed<0||elapsed>=86400000||!runtime.active(elapsed))return;
    int index=i%4*4+i/4;auto scene=runtime.frame(elapsed,index);auto pose=mission_world::pose(index,(elapsed%((63+m.seconds)*1000))/1000.f,scene);
    out->state=scene.state;out->running=true;out->x=pose.position.x;out->y=pose.position.y;
}
Json fleet_snapshot(){
    Mission m;bool dispatching;int64_t start;{Guard l(mutex);m=mission;dispatching=busy;start=origin_ms;}
    auto elapsed=wall()>1700000000000LL?wall()-m.wall_start:ms()-start;Json nodes=Json::array(),result=Json::array();
    for(int i=0;i<16;i++){
        panel_view_t p;standalone_panel(i,&p);char frame[100];
        snprintf(frame,sizeof(frame),"F1 %d %d %s %u %u",i,p.live?1:0,p.live?p.version:"-",p.uptime,p.ram);
        nodes.push_back({{"label",name(i)},{"state",recon::name(p.state)},{"pose",{p.x,p.y,0,0}},{"health",p.known&&p.age_ms<20000?Json(frame):Json(nullptr)}});
        if(m.verified&(1u<<i))result.push_back(name(i));
    }
    return {{"status",!m.started?"Idle":wall()<1700000000000LL?"Waiting for clock":elapsed<0?"Starting":elapsed<(m.repeat?86400000:(63+m.seconds)*1000)?"Running":"Finished"},
            {"elapsed",std::max<int64_t>(0,elapsed)},{"starts_in_ms",m.started?std::max<int64_t>(0,-elapsed):0},{"busy",dispatching},{"prop",true},{"controller",true},{"nodes",nodes},
            {"mission",{{"run",m.id},{"request",m.revision},{"scenario",m.scenario},{"goal",m.goal},{"seconds",m.seconds},{"repeat",m.repeat},{"result",m.revision&&!dispatching?result:Json(nullptr)}}}};
}
