@ Embedded System Example - STM32F4 LED Blink
@ This demonstrates typical embedded ARM assembly patterns

.syntax unified
.cpu cortex-m4
.fpu softvfp
.thumb

@ Vector Table
.section .isr_vector,"a",%progbits
.type g_pfnVectors, %object
.size g_pfnVectors, .-g_pfnVectors

g_pfnVectors:
    .word _estack
    .word Reset_Handler
    .word NMI_Handler
    .word HardFault_Handler
    .word MemManage_Handler
    .word BusFault_Handler
    .word UsageFault_Handler

@ Reset Handler
.section .text.Reset_Handler
.weak Reset_Handler
.type Reset_Handler, %function
Reset_Handler:
    @ Set stack pointer
    ldr sp, =_estack
    
    @ Copy data section from flash to RAM
    movs r1, #0
    b LoopCopyDataInit

CopyDataInit:
    ldr r3, =_sidata
    ldr r3, [r3, r1]
    str r3, [r0, r1]
    adds r1, r1, #4

LoopCopyDataInit:
    ldr r0, =_sdata
    ldr r3, =_edata
    adds r2, r0, r1
    cmp r2, r3
    bcc CopyDataInit
    
    @ Zero fill the bss segment
    ldr r2, =_sbss
    b LoopFillZerobss

FillZerobss:
    movs r3, #0
    str r3, [r2], #4

LoopFillZerobss:
    ldr r3, = _ebss
    cmp r2, r3
    bcc FillZerobss
    
    @ Call system initialization
    bl SystemInit
    
    @ Call main
    bl main
    bx lr

.size Reset_Handler, .-Reset_Handler

@ GPIO Configuration for LED
.section .text.GPIO_Init
.global GPIO_Init
.type GPIO_Init, %function
GPIO_Init:
    push {r4-r7, lr}
    
    @ Enable GPIOD clock (LED on PD12)
    ldr r0, =0x40023830     @ RCC_AHB1ENR
    ldr r1, [r0]
    orr r1, r1, #0x08       @ Enable GPIOD
    str r1, [r0]
    
    @ Configure PD12 as output
    ldr r0, =0x40020C00     @ GPIOD base
    ldr r1, [r0]            @ MODER
    bic r1, r1, #(3 << 24)  @ Clear mode bits for PD12
    orr r1, r1, #(1 << 24)  @ Set as output
    str r1, [r0]
    
    pop {r4-r7, pc}

@ LED Control Functions
.section .text.LED_On
.global LED_On
.type LED_On, %function
LED_On:
    ldr r0, =0x40020C14     @ GPIOD_ODR
    ldr r1, [r0]
    orr r1, r1, #(1 << 12)  @ Set PD12
    str r1, [r0]
    bx lr

.section .text.LED_Off
.global LED_Off
.type LED_Off, %function
LED_Off:
    ldr r0, =0x40020C14     @ GPIOD_ODR
    ldr r1, [r0]
    bic r1, r1, #(1 << 12)  @ Clear PD12
    str r1, [r0]
    bx lr

@ Simple delay function
.section .text.delay
.global delay
.type delay, %function
delay:
    @ r0 contains delay count
    subs r0, r0, #1
    bne delay
    bx lr

@ Main program
.section .text.main
.global main
.type main, %function
main:
    push {r4-r7, lr}
    
    @ Initialize GPIO
    bl GPIO_Init
    
main_loop:
    @ Turn LED on
    bl LED_On
    
    @ Delay
    ldr r0, =0x100000
    bl delay
    
    @ Turn LED off
    bl LED_Off
    
    @ Delay
    ldr r0, =0x100000
    bl delay
    
    @ Repeat
    b main_loop
    
    pop {r4-r7, pc}

@ Default interrupt handlers
.section .text.Default_Handler,"ax",%progbits
Default_Handler:
Infinite_Loop:
    b Infinite_Loop
.size Default_Handler, .-Default_Handler

@ Weak aliases for interrupt handlers
.weak NMI_Handler
.thumb_set NMI_Handler,Default_Handler

.weak HardFault_Handler
.thumb_set HardFault_Handler,Default_Handler

.weak MemManage_Handler
.thumb_set MemManage_Handler,Default_Handler

.weak BusFault_Handler
.thumb_set BusFault_Handler,Default_Handler

.weak UsageFault_Handler
.thumb_set UsageFault_Handler,Default_Handler

@ Data section
.section .data
led_state:
    .byte 0

.section .rodata
led_pattern:
    .word 0x55AA55AA
    .word 0xFFFF0000