# AVR Assembly Plugin Agent Instructions

## Overview
This plugin provides support for AVR Assembly language files (.s, .S, .avr) using regex-based parsing since Tree-sitter doesn't support AVR assembly. Designed for AVR 8-bit microcontrollers like ATmega328P (Arduino Uno).

## Key Features
1. **Symbol Detection**:
   - Functions and labels (ending with `:`)
   - Interrupt vectors and handlers
   - Data definitions (.byte, .word, .dw, .db, .ds)
   - I/O register definitions (.equ)
   - Register aliases (.def)
   - Macros (.macro)

2. **Section Awareness**:
   - Tracks current section (.text, .data, .bss, .eeprom)
   - EEPROM-specific data handling
   - Interrupt vector recognition at specific addresses

3. **AVR-Specific Support**:
   - Built-in knowledge of AVR registers (r0-r31, X, Y, Z, SP)
   - Common I/O register definitions (PORTB, DDRB, TIMSK0, etc.)
   - Interrupt vector mapping (RESET, INT0, TIMER0_OVF, etc.)
   - Register pointer pairs (X=r27:r26, Y=r29:r28, Z=r31:r30)

## Implementation Notes
- No Tree-sitter support - uses regex patterns exclusively
- Recognizes AVR-specific conventions and interrupt handling
- Tracks .org directives for interrupt vector definitions
- Supports common AVR microcontroller families

## Testing
Use the test data in `test_data/sample.s` which demonstrates:
- Interrupt vector table setup
- Timer configuration and ISR
- I/O register usage
- Macros and delays
- EEPROM data section

## Agent Guidelines
- AVR assembly is case-insensitive but conventions use lowercase
- Interrupt vectors are at fixed addresses (e.g., 0x0000 for RESET)
- Register names can be numeric (r16) or aliases (temp)
- I/O registers are memory-mapped and accessed via in/out or lds/sts
- Stack must be initialized before using interrupts or calls