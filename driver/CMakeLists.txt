cmake_minimum_required(VERSION 3.17)

set(PICO_BOARD pico CACHE STRING "Pico board")
include(pico_sdk_import.cmake)
project(se0398nz07a1_bringup C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()
pico_sdk_init()

add_executable(epd_bringup
    src/main.c
    src/epd.c
)
target_include_directories(epd_bringup PRIVATE src)
target_link_libraries(epd_bringup PRIVATE pico_stdlib hardware_spi)
target_compile_options(epd_bringup PRIVATE -Wall -Wextra -Werror)
target_compile_definitions(epd_bringup PRIVATE
    EPD_SPI_HZ=1000000
    EPD_PHYS_800X600=1
    EPD_X_OFFSET=32
    EPD_LINEAR_ROWS=1
    EPD_CS_PER_BYTE=0
    PICO_STDIO_USB_CONNECT_WAIT_TIMEOUT_MS=3000
    PICO_STDIO_USB_STDOUT_TIMEOUT_US=10000)

pico_enable_stdio_usb(epd_bringup 1)
pico_enable_stdio_uart(epd_bringup 0)
pico_set_program_name(epd_bringup "SE0398NZ07A1 bring-up")
pico_set_program_version(epd_bringup "1.0")
pico_add_extra_outputs(epd_bringup)
