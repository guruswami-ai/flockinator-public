#pragma once
#include "../../shared/recon/font.h"
#include "../../shared/recon/model.h"
#include "pixel_ui.h"
#include <cstdio>
namespace recon {
constexpr uint16_t rgb(unsigned x) {
  return ((x >> 8) & 0xf800) | ((x >> 5) & 0x07e0) | ((x >> 3) & 0x001f);
}
constexpr auto bg = rgb(0x06110d), ink = rgb(0xc4f6a4), dim = rgb(0x759d70),
               accent = rgb(0x92f5ad), warn = rgb(0xffd17b),
               conflict = rgb(0xff9fc8), red = rgb(0xff3030),
               blue = rgb(0x4488ff);
struct Painter {
  node::Frame &f;
  void pixel(float x, float y, uint16_t c) {
    int xx = std::lround(x), yy = std::lround(y);
    if (xx >= 0 && xx < 64 && yy >= 0 && yy < 64)
      f.pixel(xx, yy, c);
  }
  void rect(int x, int y, int w, int h, uint16_t c) {
    for (int yy = y; yy < y + h; yy++)
      for (int xx = x; xx < x + w; xx++)
        pixel(xx, yy, c);
  }
  void line(float ax, float ay, float bx, float by, uint16_t c) {
    int x = std::lround(ax), y = std::lround(ay), x1 = std::lround(bx),
        y1 = std::lround(by), dx = std::abs(x1 - x), sx = x < x1 ? 1 : -1,
        dy = -std::abs(y1 - y), sy = y < y1 ? 1 : -1, err = dx + dy;
    for (;;) {
      pixel(x, y, c);
      if (x == x1 && y == y1)
        break;
      int e = 2 * err;
      if (e >= dy) {
        err += dy;
        x += sx;
      }
      if (e <= dx) {
        err += dx;
        y += sy;
      }
    }
  }
  void text(int x, int y, const char *s, uint16_t c) {
    for (; *s; s++, x += 4) {
      auto b = glyph(*s);
      for (int yy = 0; yy < 5; yy++)
        for (int xx = 0; xx < 3; xx++)
          if (b & (1 << (14 - yy * 3 - xx)))
            pixel(x + xx, y + yy, c);
    }
  }
  void corners(int x, int y, int r, uint16_t c, bool dashed = false) {
    if (dashed) {
      for (int k = -r; k <= r; k += 3) {
        pixel(x + k, y - r, c);
        pixel(x + k, y + r, c);
        pixel(x - r, y + k, c);
        pixel(x + r, y + k, c);
      }
      return;
    }
    for (int sx : {-1, 1})
      for (int sy : {-1, 1}) {
        line(x + sx * r, y + sy * r, x + sx * (r - 3), y + sy * r, c);
        line(x + sx * r, y + sy * r, x + sx * r, y + sy * (r - 3), c);
      }
  }
  void square(int x, int y, int r, uint16_t c) {
    line(x - r, y - r, x + r, y - r, c);
    line(x + r, y - r, x + r, y + r, c);
    line(x + r, y + r, x - r, y + r, c);
    line(x - r, y + r, x - r, y - r, c);
  }
};
inline bool pulse(float age) {
  return age >= 0 && (age < .25f || (age >= .375f && age < .625f));
}
inline void label(int index, char *out) {
  out[0] = 'A' + index % 4;
  out[1] = '1' + index / 4;
  out[2] = 0;
}
inline void render(node::Frame &f, node::Frame &scratch, const Scene &s,
                   int index, const node::Frame* background=nullptr, float worldHeading=0, float worldPitch=0, float worldRoll=0, float worldAltitude=0) {
  Painter p{f};
  f.clear(bg);
  const auto &v = motions[s.variation % 10];
  const auto &m = motions[s.camera % 10];
  auto state = s.state;
  float phase = s.phase, mp = visual(state, phase);
  char id[3], str[32], peer[3];
  label(index, id);
  label(s.peer % 16, peer);
  bool approach = state == MARK && phase < 10;
  auto border = [&]() {
    if (approach || (s.direction && pulse(s.commAge))) {
      uint16_t c = approach           ? warn
                   : s.direction == 1 ? rgb(0xff8a24)
                                      : rgb(0x32ed70);
      p.line(0, 0, 63, 0, c);
      p.line(0, 63, 63, 63, c);
      p.line(0, 1, 0, 62, c);
      p.line(63, 1, 63, 62, c);
    }
  };
  if (state == BLANK) {
    f.clear();
    return;
  }
  if (state == READY) {
    p.text(2, 1, id, ink);
    p.text(50, 1, "SIM", accent);
    p.text(18, 24, "READY", accent);
    p.text(10, 36, "REMOTE START", dim);
    return;
  }
  if (state == APPROVED || state == ORDERS) {
    f.clear();
    if (state == APPROVED) {
      if (int(phase * 2) % 2 == 0) {
        p.text(18, 24, "MISSION", accent);
        p.text(16, 33, "APPROVED", accent);
      }
    } else {
      p.text(2, 1, id, ink);
      p.text(50, 1, "SIM", accent);
      p.text(20, 13, "ORDERS", accent);
      p.text(18, 25,
             s.goal == 2   ? "RECOVER"
             : s.goal == 1 ? "COMPARE"
                           : "SURVEY",
             ink);
      p.text(12, 34, "SHARE DATA", ink);
      p.text(12, 43, "KEEP CLEAR", ink);
      snprintf(str, sizeof(str), "MISSION %02lu",
               (unsigned long)(s.cycle % 100));
      p.text(12, 58, str, dim);
    }
    return;
  }
  // MARK holds the marked-site view past the ETA countdown (rescue hold,
  // TARGET CONFIRMED): no blank gap, no static feed-lost. CRASH keeps the
  // honest-failure static branch below.
  if (state == CRASH && phase >= 3) {
    constexpr uint16_t shades[] = {rgb(0x101315), rgb(0x22272a), rgb(0x343a3d),
                                   rgb(0x4b5357), rgb(0x697175)};
    for (int y = 0; y < 64; y++)
      for (int x = 0; x < 64; x++)
        p.pixel(x, y,
                shades[mix((x + y * 64 + 1) ^
                           uint32_t(int(phase * 8) + 1) * 0x45d9f3bu ^
                           uint32_t(index + 1) * 0x27d4eb2du ^
                           uint32_t(s.variation + 1) * 0x85ebca6bu) %
                       5]);
    p.rect(0, 0, 64, 8, bg);
    p.text(2, 1, id, ink);
    p.text(50, 1, "SIM", accent);
    p.rect(8, 25, 48, 11, 0);
    p.text(10, 28, "SIGNAL LOST", rgb(0xe1e8e9));
    p.rect(0, 50, 64, 14, bg);
    p.text(2, 52, name(state), warn);
    p.text(2, 58, "FEED LOST", dim);
    border();
    return;
  }
  int battery = state == EMPTY    ? std::max(0, 5 - int(phase * 2))
                : state == CHARGE ? std::min(5, 1 + int(phase / 1.5))
                : state == R2B    ? 3
                : state == LAND   ? 1
                                  : 5;
  if (state == CHARGE || state == STANDBY) {
    p.text(2, 1, id, ink);
    p.text(50, 1, "SIM", accent);
    p.line(1, 7, 62, 7, dim);
    p.corners(32, 27, 18 + s.variation % 5, dim);
    p.line(24, 20, 24, 34, accent);
    p.line(40, 20, 40, 34, accent);
    p.line(24, 27, 40, 27, accent);
    p.rect(18, 42, 27, 6, dim);
    p.rect(19, 43, 25, 4, bg);
    p.rect(19, 43, battery * 5, 4,
           state == CHARGE && int(phase * 2) % 2 == 0 ? ink : accent);
    p.rect(45, 44, 2, 2, dim);
    p.text(2, 52, name(state), ink);
    snprintf(str, sizeof(str), "BAT %d", battery * 20);
    if (s.friendly) {
      char source[3];
      label(s.source, source);
      snprintf(str, sizeof(str), "FRIEND %s", source);
    } else if (state == STANDBY)
      strcpy(str, "RESERVE");
    else if (battery == 5)
      strcpy(str, "READY");
    p.text(2, 58, str, s.friendly ? blue : dim);
    snprintf(str, sizeof(str), "PAD %02d", s.variation + 1);
    p.text(18, 10, str, dim);
    border();
    return;
  }
  float cameraElapsed = state == NOLINK  ? 0
                        : state == CRASH ? std::min(phase, v.rollTime)
                        : state == EMPTY ? std::min(phase, 3.f)
                                         : phase;
  float visualTime =
            reversible(state) ? s.motion : s.motion - phase + cameraElapsed,
        t = visualTime + index * 1.71f + m.offset;
  int heading =
      int(std::round(
          mod(82 + index * 13 +
                  (m.bank * t + m.sway * (1 - std::cos(t * .32f * m.rate)) /
                                    (.32f * m.rate)) *
                      50,
              360))) %
      360;
  if(background) heading=int(std::lround(mod(worldHeading,360)))%360;
  float launch = state == LAND ? 1 - smooth(phase / 6) : s.launch;
  float at = state == TAKEOFF ? 6 + index * 1.71f + m.offset
             : state == MARK || state == LAND
                 ? s.motion - phase + index * 1.71f + m.offset
                 : t;
  float bank = (m.bank + std::sin(at * .32f * m.rate) * m.sway) * launch,
        airPitch = m.pitch + std::sin(at * .43f * m.rate) * m.heave,
        pitch = state == TAKEOFF || state == LAND
                    ? -32 + (airPitch + 32) * launch
                    : airPitch;
  if(background){bank=worldRoll*Pi/180;pitch=42*std::tan(std::max(-60.f,worldPitch)*Pi/180);}
  float cs = std::cos(bank), sn = std::sin(bank);
  bool observations = s.observations && state != TAKEOFF && state != DEPLOY;
  if(background){for(int y=8;y<50;y++)for(int x=0;x<64;x++)p.pixel(x,y,background->pixels[y*64+x]);}
  else for (int y = 8; y < 50; y++)
    for (int x = 0; x < 64; x++) {
      float dx = x - 31.5f, dy = y - 28.5f, u = dx * cs + dy * sn,
            w = -dx * sn + dy * cs - pitch;
      int c = 0;
      if (w > 0) {
        c = 1;
        if (w > 5) {
          float depth = 110 / w,
                wx = u * depth / 3.5f + index * 9 + s.camera * 13,
                wz = depth * 10 - t * m.speed * 5, gx = mod(wx, 30),
                gz = mod(wz, 28);
          int h =
              int(mod(std::floor(wx / 30) * 7 + std::floor(wz / 28) * 11, 5));
          if (h > 1 && gx > 5 && gx < 23 && gz > 5 && gz < 21)
            c = 2;
        }
      }
      if (std::abs(w) < .55)
        c = 3;
      const uint16_t night[] = {bg, rgb(0x102b20), rgb(0x3a5945), accent},
                     day[] = {rgb(0x607b8a), rgb(0x454e37), rgb(0x827557),
                              rgb(0xafc9ce)};
      uint16_t color = night[c];
      if (s.sensor == WH || s.sensor == BH) {
        const int heats[] = {28, 64, 104, 155};
        int h = heats[c];
        if (observations && w > 3) {
          float hx = 20 + std::sin(t * .2f + s.variation) * 7,
                hy = 38 + std::cos(t * .3f) * 3,
                d = std::hypot((x - hx) / 1.3f, y - hy);
          if (d < 5)
            h = std::lround(235 - d * 15);
        }
        if (s.sensor == BH)
          h = 255 - h;
        color = rgb(h * 0x010101u);
      } else if (s.sensor == CAM)
        color = day[c];
      p.pixel(x, y, color);
    }
  auto ax = [&](float u, float w) { return 31.5f + u * cs - (w + pitch) * sn; };
  auto ay = [&](float u, float w) { return 28.5f + u * sn + (w + pitch) * cs; };
  for (int w : {-8, 8})
    for (int side : {-1, 1})
      if (w < 0)
        p.line(ax(side * 8, w), ay(side * 8, w), ax(side * 14, w),
               ay(side * 14, w), dim);
      else
        for (int u = 8; u <= 14; u += 3)
          p.pixel(ax(side * u, w), ay(side * u, w), dim);
  if (observations && (state == SCAN || state == LOITER || state == SEEN ||
                       state == CHECK || state == DOUBT)) {
    uint16_t contrast = s.sensor == BH    ? rgb(0x080808)
                        : s.sensor == CAM ? rgb(0xf2e6b8)
                        : s.sensor == WH  ? rgb(0xf4f4f4)
                                          : ink;
    for (int d = 0; d < 3; d++) {
      float u = -14 + d * 13 + std::sin(t * .25f + index + d) * 3,
            w = 8 + mod(d * 5 + t * .6f, 11), x = ax(u, w), y = ay(u, w);
      if (x >= 5 && x <= 58 && y >= 12 && y <= 47) {
        p.pixel(x, y, contrast);
        if (d == 1)
          p.pixel(x + 1, y, contrast);
      }
    }
  }
  int gap = state == SCAN || state == LOST
                ? 5 + std::lround((std::sin(t * 1.8f) + 1) * 2)
            : state == EVENT ? std::max(2, 7 - int(mp * 4))
                              : 5;
  uint16_t cross =
      state == DOUBT || state == EVENT || state == LOST ? warn : ink;
  p.line(28 - gap, 30, 32 - gap, 30, cross);
  p.line(32 + gap, 30, 36 + gap, 30, cross);
  p.line(32, 26 - gap, 32, 30 - gap, cross);
  p.line(32, 30 + gap, 32, 34 + gap, cross);
  p.pixel(32, 30, ink);
  if (state == SCAN) {
    int sweep = 9 + int(mod(t * (4 + v.speed * 2), 40));
    if (s.variation % 2)
      for (int y = 12; y < 46; y += 3)
        p.pixel(sweep + 6, y, dim);
    else
      for (int x = 8; x < 57; x += 3)
        p.pixel(x, sweep, dim);
  }
  if (state == SEEN || state == SHARE || state == CHECK || state == DOUBT ||
      state == EVENT || state == MARK || state == TARGET) {
    bool centred = state == MARK || state == EVENT;
    int bx = centred
                 ? 32
                 : 32 + std::lround(std::sin(t * .55f * v.rate + index) * v.tx),
        by =
            centred ? 30 : 31 + std::lround(std::cos(t * .42f * v.rate) * v.ty);
    float zoom = state == MARK
                     ? 1 + (v.zoomMax - 1) *
                               std::pow(std::min(phase, 10.f) / 10, v.zoomPower)
                     : 1;
    int size = std::lround(3 * zoom),
        radius = state == EVENT ? std::max(5, 11 - int(mp * 4))
                                 : std::min(18, int(std::lround(7 * zoom)));
    p.rect(bx - size / 2, by - size / 2, size, size, ink);
    if (state == EVENT || state == MARK || state == TARGET)
      p.square(bx, by, radius, state == TARGET ? red : accent);
    else
      p.corners(bx, by, radius, state == CHECK ? warn : accent);
    if (state == CHECK)
      p.text(51, 12, "?", warn);
    if (state == DOUBT) {
      p.corners(s.variation % 2 ? 47 : 15,
                19 + std::lround(std::sin(t * .5f) * v.ty), 5, conflict, true);
      p.text(48, 12, "?", conflict);
    }
  }
  if (state >= ALERT && state <= YIELD) {
    int bx = 31 + std::lround(std::sin(t * .5f * v.rate) * v.tx * .45f),
        by = 30 + std::lround(std::cos(t * .4f) * v.ty * .5f);
    auto c = state == YIELD ? dim : warn;
    p.corners(bx, by, 6, c, state == CLAIM || state == YIELD);
    p.rect(bx - 1, by - 1, 3, 3, c);
    p.rect(2, 10, 12, 7, bg);
    p.text(3, 11, "P1", c);
    if (state == PRIORITY) {
      p.corners(51, 40, 4, dim, true);
      p.rect(48, 11, 13, 7, bg);
      p.text(49, 12, "P2", dim);
      p.line(15, 13, 21, 13, warn);
      p.line(19, 11, 21, 13, warn);
      p.line(19, 15, 21, 13, warn);
    }
    if (state == ALERT)
      p.corners(bx, by, 8 + int(mod(mp, 1) * 6), warn, true);
    if (state == CLAIM)
      p.corners(bx, by, 9 + std::lround(std::sin(mp * 4)), conflict, true);
    if (state == ASSIGN) {
      p.line(bx - 3, by, bx, by + 3, accent);
      p.line(bx, by + 3, bx + 5, by - 3, accent);
    }
    if (state == YIELD)
      p.line(bx - 4, by - 4, bx + 4, by + 4, dim);
  }
  if (state == LOST) {
    float travel = std::min(mp, 2.f) * (16 + v.speed * 4);
    int x = 32 + std::lround(std::cos(v.exit) * travel),
        y = 30 + std::lround(std::sin(v.exit) * travel);
    if (mp < 2) {
      p.rect(x - 1, y - 1, 3, 3, ink);
      p.corners(x, y, 5, warn, true);
    } else
      p.corners(std::max(7, std::min(56, x)), std::max(14, std::min(43, y)), 5,
                dim, true);
  }
  if (state == LOITER) {
    const int grid[][2] = {{16, 18}, {48, 18}, {48, 26}, {16, 26}, {16, 34},
                           {48, 34}, {48, 42}, {16, 42}, {16, 18}},
              orbit[][2] = {{21, 18}, {43, 18}, {49, 29}, {43, 41},
                            {21, 41}, {15, 29}, {21, 18}};
    auto path = s.variation % 2 ? grid : orbit;
    int n = s.variation % 2 ? 9 : 7;
    for (int k = 1; k < n; k++)
      p.line(path[k - 1][0], path[k - 1][1], path[k][0], path[k][1], dim);
    float q = mod(phase, 8) / 8 * (n - 1), frac = q - int(q);
    int k = q;
    p.rect(std::lround(path[k][0] + (path[k + 1][0] - path[k][0]) * frac) - 1,
           std::lround(path[k][1] + (path[k + 1][1] - path[k][1]) * frac) - 1,
           3, 3, ink);
  }
  if (state == R2B || state == LAND) {
    int y = state == LAND ? 33 : 29;
    p.line(24, y, 32, y - 7, accent);
    p.line(32, y - 7, 40, y, accent);
    p.line(26, y, 26, y + 9, accent);
    p.line(38, y, 38, y + 9, accent);
    p.line(26, y + 9, 38, y + 9, accent);
    if (state == R2B) {
      int shift = int(phase * 2) % 5;
      p.line(30, 43 - shift, 32, 41 - shift, ink);
      p.line(32, 41 - shift, 34, 43 - shift, ink);
    }
  }
  if (s.friendly && state != CRASH && state != EMPTY && state != NOLINK &&
      state != MARK) {
    p.square(20, 28, 5, blue);
    p.rect(2, 42, 40, 8, bg);
    char source[3];
    label(s.source, source);
    snprintf(str, sizeof(str), "FRIEND %s", source);
    p.text(3, 44, str, blue);
  }
  if (state == CRASH && !background) {
    scratch = f;
    float roll = v.roll * Pi * std::min(phase / v.rollTime, 1.f),
          c = std::cos(roll), ss = std::sin(roll);
    for (int y = 8; y < 50; y++)
      for (int x = 0; x < 64; x++) {
        float dx = x - 31.5f, dy = y - 28.5f;
        int sx = std::lround(31.5f + dx * c + dy * ss),
            sy = std::lround(28.5f - dx * ss + dy * c);
        p.pixel(x, y,
                sx < 0 || sx > 63 || sy < 8 || sy > 49
                    ? bg
                    : scratch.pixels[sy * 64 + sx]);
      }
  }
  if (state == EMPTY) {
    float factor = 1 - std::min(phase / 3, 1.f) * .8f;
    for (int y = 8; y < 50; y++)
      for (int x = 0; x < 64; x++) {
        auto c = f.pixels[y * 64 + x];
        p.pixel(x, y,
                (uint16_t(((c >> 11) & 31) * factor) << 11) |
                    (uint16_t(((c >> 5) & 63) * factor) << 5) |
                    uint16_t((c & 31) * factor));
      }
  }
  if (state == NOLINK) {
    p.rect(14, 25, 36, 9, bg);
    p.text(18, 27, "NO LINK", warn);
  }
  p.rect(0, 0, 64, 8, bg);
  p.text(2, 1, id, ink);
  p.text(12, 1, "N", dim);
  p.text(25, 1, sensor_name(s.sensor), dim);
  snprintf(str, sizeof(str), "%03d", heading);
  p.text(38, 1, str, dim);
  p.text(50, 1, "SIM", accent);
  p.line(1, 7, 62, 7, dim);
  constexpr int dirs[][2] = {{0, -1}, {-1, -1}, {-1, 0}, {-1, 1},
                             {0, 1},  {1, 1},   {1, 0},  {1, -1}};
  auto d = dirs[int(std::lround(heading / 45.f)) % 8];
  int dx = d[0], dy = d[1];
  bool card = dx == 0 || dy == 0;
  p.line(20 - dx * 2, 3 - dy * 2, 20 + dx * 2, 3 + dy * 2, ink);
  p.line(20 + (card ? -dy * 2 : dx - dy), 3 + (card ? dx * 2 : dy + dx),
         20 + dx * 2, 3 + dy * 2, ink);
  p.line(20 + (card ? dy * 2 : dx + dy), 3 + (card ? -dx * 2 : dy - dx),
         20 + dx * 2, 3 + dy * 2, ink);
  p.rect(0, 50, 64, 14, bg);
  p.line(1, 50, 62, 50, dim);
  p.text(2, 52, name(state),
         state == DOUBT ? conflict
         : state == CHECK || state == EVENT || state == LOST ||
                 state == CRASH || state == EMPTY || state == NOLINK
             ? warn
             : ink);
  p.rect(52, 52, 9, 5, battery ? dim : warn);
  p.rect(53, 53, 7, 3, bg);
  p.rect(53, 53, battery, 3, accent);
  p.rect(61, 53, 1, 3, battery ? dim : warn);
  snprintf(str, sizeof(str), "ALT %d",
           int(std::lround(background?worldAltitude:(40 + index % 5 * 3) * launch)));
  const char *detail = str;
  switch (state) {
  case DEPLOY:
    detail = "FORM UP";
    break;
  case LOITER:
    detail = s.variation % 2 ? "GRID" : "ORBIT";
    break;
  case R2B:
    detail = "HOME";
    break;
  case HOLD:
    detail = "HQ WAIT";
    break;
  case SHARE:
    detail = "REPORT";
    break;
  case CHECK:
    detail = "VERIFY";
    break;
  case DOUBT:
    detail = "2 CLAIMS";
    break;
  case FRIEND:
    detail = "WARN ALL";
    break;
  case TARGET:
    detail = "CONFIRMED";
    break;
  case EVENT:
    detail = "SIM EVENT";
    break;
  case LOST:
    detail = "SEARCH";
    break;
  case MARK:
    // Rescue-team arrival countdown, then hold the marked-site view.
    if (phase < 10)
      snprintf(str, sizeof(str), "ETA 00:%02d",
               std::max(0, int(std::ceil(10 - phase))));
    else
      detail = "TARGET CONFIRMED";
    break;
  case CRASH:
    detail = "FEED HELD";
    break;
  case EMPTY:
    snprintf(str, sizeof(str), "BAT %d", battery * 20);
    break;
  case NOLINK:
    snprintf(str, sizeof(str), "AGE %dS", int(phase));
    break;
  case ALERT:
    detail = "BEACON P1";
    break;
  case PRIORITY:
    detail = "P1 FIRST";
    break;
  case CLAIM:
    detail = "CLAIM P1";
    break;
  case ASSIGN:
  case YIELD: {
    char owner[3];
    label(s.owner, owner);
    snprintf(str, sizeof(str), "OWNER %s", owner);
    break;
  }
  default:
    break;
  }
  if (!approach && s.direction && s.commAge >= 0 && s.commAge < .625) {
    snprintf(str, sizeof(str), "%s %s", s.direction == 1 ? "TX" : "RX",
             s.peer == 255 ? "ALL" : peer);
    detail = str;
  }
  p.text(2, 58, detail, dim);
  border();
}
} // namespace recon
