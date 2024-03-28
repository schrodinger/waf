SECTIONS
{
  . = 0x20000;
  .text : { *(.text) }
  . = 0x986754;
  .data : { *(.data) }
  .bss : { *(.bss) }
}
