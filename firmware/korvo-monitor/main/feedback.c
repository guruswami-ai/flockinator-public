#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>
#include "bsp/audio.h"
#include "bsp/sdcard.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "feedback.h"
#include "sdkconfig.h"

typedef struct {int state; const char *name; const uint8_t *start,*end;} sample_t;
#if CONFIG_KORVO_EMBED_SPEECH
#define SAMPLE(name) extern const uint8_t name##_start[] asm("_binary_" #name "_pcm_start"); extern const uint8_t name##_end[] asm("_binary_" #name "_pcm_end")
SAMPLE(takeoff); SAMPLE(seen); SAMPLE(friend); SAMPLE(target); SAMPLE(engage);
SAMPLE(assign); SAMPLE(share); SAMPLE(rtb); SAMPLE(crash); SAMPLE(kill);
#define ENTRY(state,name) {state,#name,name##_start,name##_end}
#else
#define ENTRY(state,name) {state,#name,NULL,NULL}
#endif
static const sample_t samples[]={ENTRY(27,takeoff),ENTRY(2,seen),ENTRY(22,friend),ENTRY(23,target),ENTRY(6,engage),ENTRY(15,assign),ENTRY(3,share),ENTRY(18,rtb),ENTRY(9,crash),ENTRY(8,kill)};
typedef struct {int volume,frequency,state;} tone_t;
static QueueHandle_t tones;
static esp_codec_dev_handle_t speaker;
static int16_t pcm[4800];
static bool card_ready;

static void prepare_card(void)
{
    bsp_sdcard_config_t config=BSP_SDCARD_DEFAULT_CONFIG();
    config.format_if_mount_failed=false;
    esp_err_t result=bsp_sdcard_mount(&config,NULL);
    if(result!=ESP_OK) {ESP_LOGW("feedback","SD unavailable (%s); tones remain available",esp_err_to_name(result));return;}
    if((mkdir("/sdcard/flockinator",0775) && errno!=EEXIST) || (mkdir("/sdcard/flockinator/audio",0775) && errno!=EEXIST)) {
        ESP_LOGW("feedback","Cannot create audio folder; tones remain available");return;
    }
    card_ready=true;
#if CONFIG_KORVO_EMBED_SPEECH
    for(unsigned i=0;i<sizeof(samples)/sizeof(samples[0]);i++) {
        char path[96];snprintf(path,sizeof(path),"/sdcard/flockinator/audio/%s.pcm",samples[i].name);
        struct stat existing;
        if(stat(path,&existing)==0) continue;
        if(errno!=ENOENT) {ESP_LOGW("feedback","Cannot inspect %s",samples[i].name);continue;}
        char temporary[112];snprintf(temporary,sizeof(temporary),"%s.tmp",path);
        int fd=open(temporary,O_WRONLY|O_CREAT|O_EXCL,0644);
        if(fd<0) {ESP_LOGW("feedback","Cannot create staging file for %s",samples[i].name);continue;}
        const uint8_t *p=samples[i].start; size_t remaining=(uintptr_t)samples[i].end-(uintptr_t)p; bool ok=true;
        while(remaining) {ssize_t written=write(fd,p,remaining>4096?4096:remaining);if(written<=0){ok=false;break;} p+=written;remaining-=written;}
        if(fsync(fd)!=0)ok=false;
        if(close(fd)!=0)ok=false;
        /* Only this firmware mounts the card; preserve an existing destination. */
        if(ok && stat(path,&existing)==0) ok=false;
        if(ok && errno!=ENOENT) ok=false;
        if(ok && rename(temporary,path)!=0)ok=false;
        if(!ok){unlink(temporary);ESP_LOGW("feedback","Could not save %s",samples[i].name);}
        else ESP_LOGI("feedback","SD sample ready: %s",samples[i].name);
    }
#endif
}
static bool play_sample(int state)
{
    if(!card_ready) return false;
    const sample_t *sample=NULL;
    for(unsigned i=0;i<sizeof(samples)/sizeof(samples[0]);i++) if(samples[i].state==state)sample=&samples[i];
    if(!sample) return false;
    char path[96];snprintf(path,sizeof(path),"/sdcard/flockinator/audio/%s.pcm",sample->name);
    FILE *file=fopen(path,"rb");if(!file)return false;
    struct stat st;
    if(fstat(fileno(file),&st)!=0 || st.st_size<2 || st.st_size>96000 || st.st_size%2) {fclose(file);return false;}
    int16_t input[256];bool ok=true;size_t count;
    while((count=fread(input,sizeof(int16_t),256,file))>0) {
        for(size_t i=0;i<count;i++)for(int j=0;j<3;j++){pcm[6*i+2*j]=input[i];pcm[6*i+2*j+1]=input[i];}
        if(esp_codec_dev_write(speaker,pcm,count*6*sizeof(int16_t))!=ESP_CODEC_DEV_OK){ok=false;break;}
        if(uxQueueMessagesWaiting(tones)>0) break;
    }
    if(ferror(file))ok=false;
    fclose(file);
    ESP_LOGI("feedback","speech=%s result=%s",sample->name,ok?"ok":"error");
    return ok;
}
static void audio_task(void *unused)
{
    (void)unused;tone_t tone;
    while(xQueueReceive(tones,&tone,portMAX_DELAY)==pdTRUE) {
        int result=esp_codec_dev_set_out_vol(speaker,tone.volume);
        if(result==ESP_CODEC_DEV_OK && tone.volume && !play_sample(tone.state)) {
            for(int i=0;i<2400;i++) {float envelope=sinf(3.14159265f*i/2399);int16_t sample=(int16_t)(4000*envelope*sinf(6.2831853f*tone.frequency*i/48000));pcm[2*i]=sample;pcm[2*i+1]=sample;}
            result=esp_codec_dev_write(speaker,pcm,sizeof(pcm));
        }
        ESP_LOGI("feedback","volume=%d tone=%d result=%d",tone.volume,tone.frequency,result);
    }
}
bool feedback_init(void)
{
    speaker=bsp_audio_codec_speaker_init();if(!speaker)return false;
    esp_codec_dev_sample_info_t format={.sample_rate=48000,.channel=2,.bits_per_sample=16};
    if(esp_codec_dev_open(speaker,&format)!=ESP_CODEC_DEV_OK || esp_codec_dev_set_out_vol(speaker,0)!=ESP_CODEC_DEV_OK)return false;
    tones=xQueueCreate(1,sizeof(tone_t));if(!tones)return false;
    prepare_card();
    if(xTaskCreate(audio_task,"ui_audio",4096,NULL,3,NULL)!=pdPASS){vQueueDelete(tones);tones=NULL;return false;}
    ESP_LOGI("feedback","speaker ready; SD speech %s; microphone not opened",card_ready?"available":"unavailable");return true;
}
static void enqueue(int volume,int frequency,int state)
{
    if(!tones)return;
    tone_t tone={.volume=volume<0?0:volume>100?100:volume,.frequency=frequency,.state=state};
    xQueueOverwrite(tones,&tone);
}
void feedback_play(int volume,int frequency){enqueue(volume,frequency,-1);}
void feedback_event(int volume,int frequency,int state){enqueue(volume,frequency,state);}
