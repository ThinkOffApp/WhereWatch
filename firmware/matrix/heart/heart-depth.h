// ThinkOff heart centre-distance map, 8x8 row-major top-left first. 0 = core, 1..3 rings outwards, 4 = background.
// colour = HEART_PALETTE[(THINKOFF_HEART_DIST[i] + phase) % 5]; step phase down every ~120 ms for an outward wave.
static const uint8_t THINKOFF_HEART_DIST[64] = {
  4, 3, 3, 4, 4, 3, 3, 4,
  3, 2, 2, 3, 3, 2, 2, 3,
  3, 2, 1, 0, 0, 1, 2, 3,
  3, 2, 1, 1, 1, 1, 2, 3,
  4, 3, 2, 1, 1, 2, 3, 4,
  4, 4, 3, 2, 2, 3, 4, 4,
  4, 4, 4, 3, 3, 4, 4, 4,
  4, 4, 4, 4, 4, 4, 4, 4,
};
static const uint32_t HEART_PALETTE[5] = { 0x74D42C, 0xFFC400, 0xFF00E5, 0xFF8DE6, 0x1A0A2E };  // core first, background last
