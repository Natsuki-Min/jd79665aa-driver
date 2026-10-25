#ifndef EPD_H
#define EPD_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifndef EPD_SPI_HZ
#define EPD_SPI_HZ 1000000
#endif
#ifndef EPD_PHYS_800X600
#define EPD_PHYS_800X600 1
#endif
#ifndef EPD_X_OFFSET
#define EPD_X_OFFSET 32
#endif
#ifndef EPD_LINEAR_ROWS
#define EPD_LINEAR_ROWS 1
#endif
#ifndef EPD_CS_PER_BYTE
#define EPD_CS_PER_BYTE 0
#endif

#if (EPD_PHYS_800X600 != 0 && EPD_PHYS_800X600 != 1) || \
    (EPD_LINEAR_ROWS != 0 && EPD_LINEAR_ROWS != 1) || \
    (EPD_CS_PER_BYTE != 0 && EPD_CS_PER_BYTE != 1)
#error "EPD mode switches must be numeric 0 or 1"
#endif

#define EPD_PIN_DIN  3u
#define EPD_PIN_CLK  2u
#define EPD_PIN_CS   5u
#define EPD_PIN_DC   6u
#define EPD_PIN_RST  7u
#define EPD_PIN_BUSY 8u

#define EPD_VISIBLE_WIDTH  768u
#define EPD_VISIBLE_HEIGHT 552u
#if EPD_PHYS_800X600
#define EPD_FRAME_WIDTH  800u
#define EPD_FRAME_HEIGHT 600u
#define EPD_FRAME_X_OFFSET EPD_X_OFFSET
#else
#define EPD_FRAME_WIDTH  EPD_VISIBLE_WIDTH
#define EPD_FRAME_HEIGHT EPD_VISIBLE_HEIGHT
#define EPD_FRAME_X_OFFSET 0u
#endif
#define EPD_ROW_BYTES (EPD_FRAME_WIDTH / 4u)
#define EPD_FRAME_BYTES (EPD_ROW_BYTES * EPD_FRAME_HEIGHT)
#define EPD_FRAME_CAPACITY 120000u

#define EPD_BLACK  0u
#define EPD_WHITE  1u
#define EPD_YELLOW 2u
#define EPD_RED    3u
#define EPD_PACKED_WHITE 0x55u

_Static_assert(EPD_SPI_HZ > 0, "SPI clock must be positive");
_Static_assert(EPD_FRAME_X_OFFSET >= 0 &&
               EPD_FRAME_X_OFFSET + EPD_VISIBLE_WIDTH <= EPD_FRAME_WIDTH,
               "Visible region must fit inside physical frame");
_Static_assert(EPD_FRAME_BYTES <= EPD_FRAME_CAPACITY, "Framebuffer capacity exceeded");

void epd_spi_init(void);
int epd_busy_level(void);
typedef struct { uint32_t falls,rises,fall_us,rise_us; } epd_busy_edges_t;
epd_busy_edges_t epd_busy_edges(void);
bool epd_reset(void);
bool epd_wait_ready(uint32_t timeout_ms);
bool epd_cmd(uint8_t command);
bool epd_data(const uint8_t *data, size_t length);
bool epd_init(void); /* Hardware reset followed by register programming. */
bool epd_power_on(void);
bool epd_write_frame(const uint8_t *frame, size_t length);
bool epd_refresh(void);
/* Optional: drive one visible rectangle. x/y are visible coordinates, w must
 * be a multiple of 4, payload is row-major w*h/4 bytes. This still uses the
 * factory full-refresh waveform, so it takes the same ~15 s. */
bool epd_partial_update(uint16_t x, uint16_t y, uint16_t w, uint16_t h,
                        const uint8_t *data, size_t length);
bool epd_power_off(void);

#endif
