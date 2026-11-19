/* RAM stops 8 bytes short of 32 KB: the bootloader double-tap flag lives at the top and the stack start must be 8-byte aligned. */
/* Adafruit Feather M0 (SAMD21G18): the UF2 bootloader owns the first 8 KB of flash. */
MEMORY
{
  FLASH (rx) : ORIGIN = 0x00002000, LENGTH = 0x00040000 - 0x2000
  RAM (xrw)  : ORIGIN = 0x20000000, LENGTH = 0x00008000 - 8
}
