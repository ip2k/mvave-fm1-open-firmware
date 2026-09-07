cmake_minimum_required(VERSION 3.13)

# Requires PICO_SDK_PATH in the environment (pico-sdk 2.x). See ../README.md.
if(NOT DEFINED ENV{PICO_SDK_PATH})
  message(FATAL_ERROR "PICO_SDK_PATH is not set; point it at a pico-sdk checkout")
endif()
set(PICO_BOARD pico CACHE STRING "Board type")
include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(usb_key_dongle C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(usb_key_dongle main.c)
pico_generate_pio_header(usb_key_dongle ${CMAKE_CURRENT_LIST_DIR}/usb_key.pio)
target_include_directories(usb_key_dongle PRIVATE ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(usb_key_dongle pico_stdlib hardware_pio hardware_clocks)

pico_enable_stdio_usb(usb_key_dongle 1)
pico_enable_stdio_uart(usb_key_dongle 0)
pico_add_extra_outputs(usb_key_dongle)
