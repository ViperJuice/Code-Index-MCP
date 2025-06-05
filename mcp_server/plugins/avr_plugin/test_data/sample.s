; AVR Assembly Sample - LED blink with timer interrupt
; For ATmega328P (Arduino Uno)

.include "m328pdef.inc"

; I/O Register definitions
.equ LED_PORT = PORTB
.equ LED_DDR = DDRB
.equ LED_PIN = 5        ; Arduino pin 13 = PB5

; Timer constants
.equ TIMER_PRESCALER = 1024
.equ TIMER_COUNT = 156  ; For ~10Hz at 16MHz

; Register aliases
.def temp = r16
.def counter = r17
.def status_save = r18

; Interrupt vectors
.org 0x0000
    rjmp RESET          ; Reset vector
.org 0x0002
    rjmp INT0_handler   ; External interrupt 0
.org 0x0020
    rjmp TIMER0_OVF_handler ; Timer0 overflow

; Data segment
.dseg
blink_count:    .byte 1
delay_counter:  .word 1

; Code segment
.cseg
.org 0x0034            ; Start after interrupt vectors

RESET:
    ; Initialize stack pointer
    ldi temp, HIGH(RAMEND)
    out SPH, temp
    ldi temp, LOW(RAMEND)
    out SPL, temp
    
    ; Initialize LED pin as output
    sbi LED_DDR, LED_PIN
    
    ; Initialize timer
    rcall init_timer0
    
    ; Enable global interrupts
    sei
    
    ; Jump to main loop
    rjmp main

; Initialize Timer0 for overflow interrupt
init_timer0:
    ; Set prescaler to 1024
    ldi temp, (1<<CS02)|(1<<CS00)
    out TCCR0B, temp
    
    ; Enable Timer0 overflow interrupt
    ldi temp, (1<<TOIE0)
    sts TIMSK0, temp
    
    ; Initialize counter
    ldi temp, 256 - TIMER_COUNT
    out TCNT0, temp
    
    ret

; Main program loop
main:
    ; Main loop can do other tasks
    nop
    nop
    rjmp main

; Timer0 overflow interrupt handler
TIMER0_OVF_handler:
    ; Save status register
    in status_save, SREG
    
    ; Reload timer
    ldi temp, 256 - TIMER_COUNT
    out TCNT0, temp
    
    ; Toggle LED
    sbic PINB, LED_PIN
    rjmp led_off
    sbi LED_PORT, LED_PIN
    rjmp timer_done
led_off:
    cbi LED_PORT, LED_PIN
    
timer_done:
    ; Increment blink counter
    lds counter, blink_count
    inc counter
    sts blink_count, counter
    
    ; Restore status register
    out SREG, status_save
    reti

; External interrupt 0 handler
INT0_handler:
    ; Save status register
    in status_save, SREG
    
    ; Reset blink counter
    clr counter
    sts blink_count, counter
    
    ; Restore status register
    out SREG, status_save
    reti

; Utility macro for delay
.macro delay_ms
    ldi r24, low(@0)
    ldi r25, high(@0)
    rcall delay_routine
.endm

; Delay routine
delay_routine:
    ; Simple busy-wait delay
    push r24
    push r25
delay_loop:
    sbiw r24, 1         ; 2 cycles
    brne delay_loop     ; 2 cycles if true
    pop r25
    pop r24
    ret

; EEPROM data
.eseg
.org 0x0000
config_byte:    .db 0xFF
device_id:      .dw 0x1234