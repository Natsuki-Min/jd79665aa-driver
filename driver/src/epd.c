/* JD79665 sequence ported from krstc/openepaperlinkforCN,
 * commit 42bd21471b5d3a6df07fd5ff9639fb88b5bcdc11:
 * tag_fw/src/epd_driver/jd79665.cpp, epdSetup(),
 * epdWriteDisplayDataPhysicalFrame(), drawNoWait(), powerOff().
 * Cross-checked against refdoc/BLE_EPD_DISPLAY/EPD_3in98g.cpp and
 * panyihang/3.98Inch-ESP32C3-EPD, commit
 * 779eab27ba8b914e097fec530d1e1d601265fdcc, main/epd_panel.c.
 * Only the exposed digital interface is controlled; no EPD_BS/HV GPIOs.
 */
#include "epd.h"

#include <inttypes.h>
#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"

#define EPD_RESET_TIMEOUT_MS 3000u
#define EPD_OPERATION_TIMEOUT_MS 120000u

/* Count edges in IRQ context, print only in foreground. This also catches
 * BUSY pulses shorter than the 1 ms foreground polling interval.
 * Aligned 32-bit reads/writes are atomic on RP2040; each counter has one writer.
 */
static volatile uint32_t busy_falls;
static volatile uint32_t busy_rises;
static volatile uint32_t busy_fall_us;
static volatile uint32_t busy_rise_us;
static uint32_t monitor_falls;
static uint32_t monitor_rises;
static uint32_t monitor_start_us;
static bool monitor_initial_low;
static const char *busy_stage = "READY";

static void busy_irq(uint gpio, uint32_t events)
{
    if (gpio != EPD_PIN_BUSY) return;
    if (events & GPIO_IRQ_EDGE_FALL) {
        busy_fall_us = time_us_32();
        ++busy_falls;
    }
    if (events & GPIO_IRQ_EDGE_RISE) {
        busy_rise_us = time_us_32();
        ++busy_rises;
    }
}

int epd_busy_level(void)
{
    return gpio_get(EPD_PIN_BUSY);
}

epd_busy_edges_t epd_busy_edges(void)
{
    epd_busy_edges_t result;
    /* Read counters again if an edge interrupted the snapshot. Called only
     * from foreground; IRQ timestamps already exist for native refresh. */
    do {
        result.falls=busy_falls;result.rises=busy_rises;
        result.fall_us=busy_fall_us;result.rise_us=busy_rise_us;
    }while(result.falls!=busy_falls||result.rises!=busy_rises);
    return result;
}

static void monitor_begin(const char *stage)
{
    busy_stage = stage;
    monitor_start_us = time_us_32();
    monitor_falls = busy_falls;
    monitor_rises = busy_rises;
    monitor_initial_low = epd_busy_level() == 0;
    printf("BUSY [%s] before operation: %d (LOW=busy, HIGH=ready)\n",
           stage, epd_busy_level());
}

void epd_spi_init(void)
{
    /* Preload output latches HIGH before enabling drivers: no CS/RST glitch. */
    const uint outputs[] = {EPD_PIN_CS, EPD_PIN_DC, EPD_PIN_RST};
    for (size_t i = 0; i < sizeof(outputs) / sizeof(outputs[0]); ++i) {
        gpio_init(outputs[i]);
        gpio_put(outputs[i], 1);
        gpio_set_dir(outputs[i], GPIO_OUT);
    }
    gpio_init(EPD_PIN_BUSY);
    gpio_set_dir(EPD_PIN_BUSY, GPIO_IN);
    gpio_disable_pulls(EPD_PIN_BUSY); /* Do not disguise a stuck/floating BUSY. */
    gpio_set_irq_enabled_with_callback(EPD_PIN_BUSY,
        GPIO_IRQ_EDGE_FALL | GPIO_IRQ_EDGE_RISE, true, busy_irq);

    spi_init(spi0, EPD_SPI_HZ);
    spi_set_format(spi0, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
    gpio_set_function(EPD_PIN_CLK, GPIO_FUNC_SPI);
    gpio_set_function(EPD_PIN_DIN, GPIO_FUNC_SPI);
    /* GP5 stays SIO/manual CS; no MISO and no peripheral-driven CS. */
}

static bool spi_payload(const uint8_t *data, size_t length)
{
    if (length == 0) return true;
    if (data == NULL) return false;
    bool ok = true;
#if EPD_CS_PER_BYTE
    for (size_t i = 0; i < length; ++i) {
        gpio_put(EPD_PIN_CS, 0);
        sleep_us(1);
        int sent = spi_write_blocking(spi0, data + i, 1);
        gpio_put(EPD_PIN_CS, 1);
        sleep_us(1);
        if (sent != 1) { ok = false; break; }
    }
#else
    gpio_put(EPD_PIN_CS, 0);
    sleep_us(1);
    /* Pico SDK drains the TX FIFO and waits for SPI idle before returning,
     * so CS cannot rise before the final bit. No 16-bit length truncation.
     */
    ok = spi_write_blocking(spi0, data, length) == (int)length;
    gpio_put(EPD_PIN_CS, 1);
    sleep_us(1);
#endif
    if (!ok) printf("ERROR: SPI short write, requested %u bytes\n", (unsigned)length);
    return ok;
}

bool epd_cmd(uint8_t command)
{
    gpio_put(EPD_PIN_DC, 0);
    bool ok = spi_payload(&command, 1);
    gpio_put(EPD_PIN_DC, 1);
    return ok;
}

bool epd_data(const uint8_t *data, size_t length)
{
    gpio_put(EPD_PIN_DC, 1);
    return spi_payload(data, length);
}

static bool cmd_data(uint8_t command, const uint8_t *data, size_t length)
{
    return epd_cmd(command) && epd_data(data, length);
}

bool epd_wait_ready(uint32_t timeout_ms)
{
    const uint64_t start = time_us_64();
    const uint64_t timeout_us = (uint64_t)timeout_ms * 1000u;
    uint32_t logged_falls = monitor_falls;
    uint32_t logged_rises = monitor_rises;
    uint64_t next_progress_us = 5000000u;
    printf("BUSY [%s] wait start=%d, timeout=%" PRIu32 " ms\n",
           busy_stage, epd_busy_level(), timeout_ms);

    while (true) {
        uint64_t elapsed = time_us_64() - start;
        uint32_t falls = busy_falls;
        uint32_t rises = busy_rises;
        if (falls != logged_falls) {
            printf("BUSY [%s] -> LOW, last edge at +%" PRIu32 " us, falls=%" PRIu32 "\n",
                   busy_stage, (uint32_t)(busy_fall_us - monitor_start_us),
                   falls - monitor_falls);
            logged_falls = falls;
        }
        if (rises != logged_rises) {
            printf("BUSY [%s] -> HIGH, last edge at +%" PRIu32 " us, rises=%" PRIu32 "\n",
                   busy_stage, (uint32_t)(busy_rise_us - monitor_start_us),
                   rises - monitor_rises);
            logged_rises = rises;
        }
        /* The reference has a 1 ms post-command settle. Observe for at least
         * 10 ms here so a still-HIGH input cannot bypass a delayed BUSY edge.
         * A ready-only wait cannot prove that the controller saw a command.
         */
        if (epd_busy_level() == 1 && elapsed >= 10000u && elapsed <= timeout_us) {
            printf("BUSY [%s] ready, wait=%" PRIu64 " ms\n", busy_stage, elapsed / 1000u);
            if (!monitor_initial_low && falls == monitor_falls) {
                printf("WARN [%s]: no BUSY LOW observed; HIGH alone does not confirm panel response\n",
                       busy_stage);
            }
            return true;
        }
        if (elapsed >= timeout_us) {
            printf("ERROR [%s]: BUSY TIMEOUT, level=%d, wait=%" PRIu64 " ms\n",
                   busy_stage, epd_busy_level(), elapsed / 1000u);
            return false;
        }
        if (elapsed >= next_progress_us) {
            printf("BUSY [%s] level=%d, waiting %" PRIu64 " ms\n",
                   busy_stage, epd_busy_level(), elapsed / 1000u);
            next_progress_us += 5000000u;
        }
        sleep_ms(1);
    }
}

bool epd_reset(void)
{
    puts("RESET");
    monitor_begin("RESET");
    gpio_put(EPD_PIN_RST, 1);
    sleep_ms(20);
    gpio_put(EPD_PIN_RST, 0);
    sleep_ms(2);
    gpio_put(EPD_PIN_RST, 1);
    sleep_ms(20);
    printf("BUSY after reset = %d\n", epd_busy_level());
    if (!epd_wait_ready(EPD_RESET_TIMEOUT_MS)) return false;
    sleep_ms(30);
    return true;
}

bool epd_init(void)
{
    if (!epd_reset()) return false;
    puts("INIT REGISTERS");
    static const struct {
        uint8_t command;
        uint8_t length;
        uint8_t data[6];
    } init[] = {
        {0xAA, 6, {0x49, 0x55, 0x20, 0x08, 0x09, 0x18}},
        {0x01, 1, {0x3F}},
        {0x00, 2, {0x4B, 0x69}},
        {0x05, 4, {0x40, 0x1F, 0x1F, 0x2C}},
        {0x08, 4, {0x6F, 0x1F, 0x1F, 0x22}},
        {0x06, 4, {0x6F, 0x1F, 0x14, 0x14}},
        {0x03, 4, {0x00, 0x54, 0x00, 0x44}},
        {0x60, 2, {0x02, 0x00}},
        {0x30, 1, {0x08}},
        {0x50, 1, {0x3F}},
        {0x61, 4, {EPD_FRAME_WIDTH >> 8, EPD_FRAME_WIDTH & 0xFF,
                     EPD_FRAME_HEIGHT >> 8, EPD_FRAME_HEIGHT & 0xFF}},
        {0x65, 4, {0x10, 0x00, 0x20, 0x00}},
        {0xE3, 1, {0x2F}},
        {0x84, 1, {0x01}},
    };
    for (size_t i = 0; i < sizeof(init) / sizeof(init[0]); ++i) {
        printf("  0x%02X :", init[i].command);
        for (uint8_t j = 0; j < init[i].length; ++j) printf(" %02X", init[i].data[j]);
        putchar('\n');
        if (!cmd_data(init[i].command, init[i].data, init[i].length)) return false;
    }
    return true;
}

static bool full_window(void)
{
    const uint16_t xe = EPD_FRAME_WIDTH - 1u;
    const uint16_t ye = EPD_FRAME_HEIGHT - 1u;
    const uint8_t window[] = {0, 0, xe >> 8, xe & 0xFF,
                             0, 0, ye >> 8, ye & 0xFF, 1};
    return cmd_data(0x83, window, sizeof(window));
}

/* R83 uses a mirrored X coordinate when SHL=0:
 *   actual RAM x = 800 - encoded_x - width
 * so encoded_x = 800 - (visible_x + 32) - width.
 */
static bool visible_window(uint16_t x, uint16_t y, uint16_t w, uint16_t h)
{
    if (w == 0 || h == 0 || (w & 3u) != 0) return false;
    if (w > EPD_VISIBLE_WIDTH || h > EPD_VISIBLE_HEIGHT) return false;
    if (x > EPD_VISIBLE_WIDTH - w || y > EPD_VISIBLE_HEIGHT - h) return false;
    const uint16_t physical_x = (uint16_t)(x + EPD_FRAME_X_OFFSET);
    const uint16_t encoded_x = (uint16_t)(EPD_FRAME_WIDTH - physical_x - w);
    const uint16_t encoded_xe = (uint16_t)(encoded_x + w - 1u);
    const uint16_t ye = (uint16_t)(y + h - 1u);
    const uint8_t window[] = {encoded_x >> 8, encoded_x & 0xFF,
                             encoded_xe >> 8, encoded_xe & 0xFF,
                             y >> 8, y & 0xFF, ye >> 8, ye & 0xFF, 1};
    return cmd_data(0x83, window, sizeof(window));
}

bool epd_partial_update(uint16_t x, uint16_t y, uint16_t w, uint16_t h,
                        const uint8_t *data, size_t length)
{
    puts("PARTIAL UPDATE");
    const size_t expected = (size_t)w * h / 4u;
    if (data == NULL || length != expected || !visible_window(x, y, w, h)) {
        printf("ERROR: partial payload must be %u bytes, w%%4=0, inside 768x552\n",
               (unsigned)expected);
        return false;
    }
    if (!epd_cmd(0x10) || !epd_data(data, length)) return false;
    if (!visible_window(x, y, w, h)) return false;
    monitor_begin("PARTIAL REFRESH");
    const uint8_t zero = 0;
    return cmd_data(0x12, &zero, 1) && epd_wait_ready(EPD_OPERATION_TIMEOUT_MS);
}

bool epd_power_on(void)
{
    puts("POWER ON");
    monitor_begin("POWER ON");
    return epd_cmd(0x04) && epd_wait_ready(EPD_OPERATION_TIMEOUT_MS);
}

bool epd_write_frame(const uint8_t *frame, size_t length)
{
    puts("WRITE FRAME");
    if (frame == NULL || length != EPD_FRAME_BYTES) {
        printf("ERROR: frame must contain exactly %u bytes\n", (unsigned)EPD_FRAME_BYTES);
        return false;
    }
    if (!full_window() || !epd_cmd(0x10)) return false;
    uint64_t start = time_us_64();
    if (!epd_data(frame, length)) return false;
    printf("bytes sent = %u, rows=%u, bytes/row=%u, duration=%" PRIu64 " ms\n",
           (unsigned)length, (unsigned)EPD_FRAME_HEIGHT, (unsigned)EPD_ROW_BYTES,
           (time_us_64() - start) / 1000u);
    return true;
}

bool epd_refresh(void)
{
    puts("REFRESH");
    if (!full_window()) return false;
    monitor_begin("REFRESH");
    const uint8_t zero = 0;
    return cmd_data(0x12, &zero, 1) && epd_wait_ready(EPD_OPERATION_TIMEOUT_MS);
}

bool epd_power_off(void)
{
    puts("POWER OFF");
    monitor_begin("POWER OFF");
    const uint8_t zero = 0;
    return cmd_data(0x02, &zero, 1) && epd_wait_ready(EPD_OPERATION_TIMEOUT_MS);
}
