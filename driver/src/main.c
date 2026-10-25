/*
 * Minimal SE0398NZ07A1 / JD79665AA demo.
 *
 * Wiring (RP2040 Pico):
 *   DIN=GP3  CLK=GP2  CS=GP5  DC=GP6  RST=GP7  BUSY=GP8
 *
 * This is the known-good factory full-refresh path only. It draws four
 * vertical bands (black / white / yellow / red) once at boot. Type 'r' in
 * the USB serial console to repeat, 's' to print status.
 *
 * Do not use this file to program MTP/OTP. It only sends normal display
 * commands and always powers off after a completed refresh.
 */
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "epd.h"

/* One physical framebuffer: 800 x 600, 2 bits per pixel. */
static uint8_t framebuffer[EPD_FRAME_BYTES];
_Static_assert(sizeof(framebuffer) == EPD_FRAME_CAPACITY, "framebuffer size");

static void set_visible_pixel(unsigned x, unsigned y, uint8_t color)
{
    x += EPD_FRAME_X_OFFSET;
    const size_t index = (size_t)y * EPD_ROW_BYTES + x / 4u;
    const unsigned shift = 6u - 2u * (x & 3u);
    framebuffer[index] = (uint8_t)((framebuffer[index] & ~(3u << shift)) |
                                   ((color & 3u) << shift));
}

static void make_test_pattern(void)
{
    memset(framebuffer, EPD_PACKED_WHITE, sizeof(framebuffer));
    for (unsigned y = 0; y < EPD_VISIBLE_HEIGHT; ++y) {
        for (unsigned x = 0; x < EPD_VISIBLE_WIDTH; ++x) {
            uint8_t color = (uint8_t)(x / (EPD_VISIBLE_WIDTH / 4u));
            if (x < 4u || x >= EPD_VISIBLE_WIDTH - 4u ||
                y < 4u || y >= EPD_VISIBLE_HEIGHT - 4u) color = EPD_BLACK;
            /* Asymmetric marks catch row flips and an off-by-one origin. */
            if (x >= 16u && x < 48u && y >= 16u && y < 32u) color = EPD_WHITE;
            if (x >= 720u && x < 752u && y >= 520u && y < 536u) color = EPD_BLACK;
            set_visible_pixel(x, y, color);
        }
    }
}

static bool run_once(void)
{
    if (epd_init()) {
        make_test_pattern();
        if (epd_power_on() &&
            epd_write_frame(framebuffer, sizeof(framebuffer)) &&
            epd_refresh() && epd_power_off()) {
            return true;
        }
    }
    puts("ERROR: attempting power-off and reset after a failed stage");
    (void)epd_power_off();
    (void)epd_reset();
    return false;
}

int main(void)
{
    /* Set CS/DC/RST high before USB init can block. */
    epd_spi_init();
    const int initial_busy = epd_busy_level();
    stdio_init_all();

    puts("BOOT: RP2040 / JD79665AA / SE0398NZ07A1");
    printf("initial BUSY=%d (0=busy, 1=ready)\n", initial_busy);
    printf("SPI0 mode0 MSB-first: DIN=GP3 CLK=GP2 CS=GP5 DC=GP6 RST=GP7 BUSY=GP8\n");
    printf("SPI requested=%u Hz actual=%u Hz\n",
           (unsigned)EPD_SPI_HZ, (unsigned)spi_get_baudrate(spi0));
    printf("physical=%ux%u, visible=%ux%u at (%u,0)\n",
           (unsigned)EPD_FRAME_WIDTH, (unsigned)EPD_FRAME_HEIGHT,
           (unsigned)EPD_VISIBLE_WIDTH, (unsigned)EPD_VISIBLE_HEIGHT,
           (unsigned)EPD_FRAME_X_OFFSET);
    sleep_ms(500);

    bool ok = run_once();
    puts(ok ? "DONE: inspect the panel and the BUSY log"
            : "FAILED: read the stage above");
    puts("Commands: r=repeat, s=status");

    while (true) {
        const int ch = getchar_timeout_us(10000);
        if (ch == 'r' || ch == 'R') {
            ok = run_once();
            puts(ok ? "DONE: inspect the panel and the BUSY log" : "FAILED");
        } else if (ch == 's' || ch == 'S') {
            printf("status=%s BUSY=%d (0=busy, 1=ready)\n",
                   ok ? "DONE" : "FAILED", epd_busy_level());
        }
        tight_loop_contents();
    }
}
