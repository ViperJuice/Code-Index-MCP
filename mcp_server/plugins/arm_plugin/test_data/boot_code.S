/* ARM Boot Code Example
 * Demonstrates typical bootloader patterns
 * Compatible with ARMv7-A architecture
 */

.section .boot, "ax"
.arm
.align 4

/* Boot entry point */
.global _start
_start:
    /* Disable interrupts */
    cpsid if
    
    /* Set up exception vectors */
    ldr r0, =exception_vectors
    mcr p15, 0, r0, c12, c0, 0   /* Write VBAR */
    
    /* Initialize stack pointers for different modes */
    msr cpsr_c, #0xD1   /* FIQ mode */
    ldr sp, =fiq_stack_top
    
    msr cpsr_c, #0xD2   /* IRQ mode */
    ldr sp, =irq_stack_top
    
    msr cpsr_c, #0xD7   /* Abort mode */
    ldr sp, =abort_stack_top
    
    msr cpsr_c, #0xDB   /* Undefined mode */
    ldr sp, =undef_stack_top
    
    msr cpsr_c, #0xDF   /* System mode */
    ldr sp, =sys_stack_top
    
    msr cpsr_c, #0xD3   /* Supervisor mode */
    ldr sp, =svc_stack_top
    
    /* Enable VFP/NEON if available */
    mrc p15, 0, r0, c1, c0, 2
    orr r0, r0, #(0xF << 20)     /* Enable CP10 and CP11 */
    mcr p15, 0, r0, c1, c0, 2
    isb
    
    vmrs r0, fpexc
    orr r0, r0, #(1 << 30)       /* Enable VFP */
    vmsr fpexc, r0
    
    /* Clear BSS */
    ldr r0, =__bss_start
    ldr r1, =__bss_end
    mov r2, #0
.Lclear_bss:
    cmp r0, r1
    strlt r2, [r0], #4
    blt .Lclear_bss
    
    /* Initialize memory controller */
    bl memory_init
    
    /* Copy data from ROM to RAM */
    ldr r0, =__data_start_rom
    ldr r1, =__data_start
    ldr r2, =__data_end
.Lcopy_data:
    cmp r1, r2
    ldrlt r3, [r0], #4
    strlt r3, [r1], #4
    blt .Lcopy_data
    
    /* Set up MMU */
    bl mmu_init
    
    /* Enable caches */
    mrc p15, 0, r0, c1, c0, 0
    orr r0, r0, #(1 << 12)       /* I-cache enable */
    orr r0, r0, #(1 << 2)        /* D-cache enable */
    orr r0, r0, #(1 << 0)        /* MMU enable */
    mcr p15, 0, r0, c1, c0, 0
    isb
    
    /* Initialize hardware */
    bl hardware_init
    
    /* Call C main */
    bl main
    
    /* Should never reach here */
.Lhang:
    wfi
    b .Lhang

/* Exception vector table */
.align 5
exception_vectors:
    ldr pc, reset_addr
    ldr pc, undefined_addr
    ldr pc, swi_addr
    ldr pc, prefetch_addr
    ldr pc, abort_addr
    nop                          /* Reserved */
    ldr pc, irq_addr
    ldr pc, fiq_addr

reset_addr:     .word reset_handler
undefined_addr: .word undefined_handler
swi_addr:       .word swi_handler
prefetch_addr:  .word prefetch_handler
abort_addr:     .word abort_handler
irq_addr:       .word irq_handler
fiq_addr:       .word fiq_handler

/* Reset handler */
reset_handler:
    b _start

/* Undefined instruction handler */
undefined_handler:
    stmfd sp!, {r0-r12, lr}
    
    /* Save SPSR */
    mrs r0, spsr
    push {r0}
    
    /* Get fault address */
    sub r0, lr, #4
    
    /* Call C handler */
    bl handle_undefined_instruction
    
    /* Restore SPSR */
    pop {r0}
    msr spsr_cxsf, r0
    
    ldmfd sp!, {r0-r12, pc}^

/* SWI handler */
swi_handler:
    stmfd sp!, {r0-r12, lr}
    
    /* Get SWI number */
    ldr r0, [lr, #-4]
    bic r0, r0, #0xFF000000
    
    /* Call appropriate system call */
    bl handle_syscall
    
    ldmfd sp!, {r0-r12, pc}^

/* IRQ handler */
irq_handler:
    sub lr, lr, #4
    stmfd sp!, {r0-r12, lr}
    
    /* Acknowledge interrupt */
    bl interrupt_acknowledge
    
    /* Handle interrupt */
    bl interrupt_handler
    
    ldmfd sp!, {r0-r12, pc}^

/* Memory initialization */
memory_init:
    push {r4-r11, lr}
    
    /* Configure SDRAM controller */
    ldr r0, =0x10000000          /* SDRAM controller base */
    
    /* Timing configuration */
    ldr r1, =0x00000032
    str r1, [r0, #0x04]          /* CAS latency, etc. */
    
    /* Size configuration */
    ldr r1, =0x00001000          /* 256MB */
    str r1, [r0, #0x08]
    
    /* Enable controller */
    ldr r1, =0x00000001
    str r1, [r0, #0x00]
    
    /* Wait for initialization */
    mov r2, #0x1000
.Lmem_wait:
    subs r2, r2, #1
    bne .Lmem_wait
    
    pop {r4-r11, pc}

/* MMU initialization */
mmu_init:
    push {r4-r11, lr}
    
    /* Create translation table */
    ldr r0, =translation_table
    
    /* Identity map first 1MB for boot code */
    mov r1, #0x00000000
    orr r1, r1, #0x00000C02      /* Cacheable, bufferable */
    str r1, [r0]
    
    /* Map SDRAM (0x20000000 physical -> 0x20000000 virtual) */
    mov r2, #512                  /* 512 entries for 512MB */
    ldr r1, =0x20000000
    orr r1, r1, #0x00000C02
    add r0, r0, #0x800            /* Offset in table */
.Lmmu_sdram:
    str r1, [r0], #4
    add r1, r1, #0x00100000      /* Next 1MB */
    subs r2, r2, #1
    bne .Lmmu_sdram
    
    /* Map peripherals (uncached) */
    ldr r0, =translation_table
    ldr r1, =0x40000000
    orr r1, r1, #0x00000C12      /* Device memory */
    str r1, [r0, #0x1000]
    
    /* Set translation table base */
    ldr r0, =translation_table
    mcr p15, 0, r0, c2, c0, 0
    
    /* Set domain access */
    mvn r0, #0
    mcr p15, 0, r0, c3, c0, 0
    
    pop {r4-r11, pc}

/* Hardware initialization */
hardware_init:
    push {r4-r11, lr}
    
    /* Initialize UART for debug output */
    ldr r0, =0x40001000          /* UART base */
    
    /* Set baud rate */
    mov r1, #115200
    bl uart_set_baudrate
    
    /* Enable UART */
    mov r1, #0x03                /* TX and RX enable */
    str r1, [r0, #0x0C]
    
    /* Print boot message */
    adr r0, boot_message
    bl uart_print_string
    
    pop {r4-r11, pc}

/* UART functions */
uart_print_string:
    push {r4, lr}
    mov r4, r0
.Luart_loop:
    ldrb r0, [r4], #1
    cmp r0, #0
    beq .Luart_done
    bl uart_putc
    b .Luart_loop
.Luart_done:
    pop {r4, pc}

uart_putc:
    ldr r1, =0x40001000          /* UART base */
.Luart_wait:
    ldr r2, [r1, #0x18]          /* Status register */
    tst r2, #0x20                /* TX FIFO full? */
    bne .Luart_wait
    strb r0, [r1, #0x00]         /* Data register */
    bx lr

/* Data section */
.section .data
.align 4

boot_message:
    .asciz "ARM Bootloader v1.0\r\n"

/* BSS section */
.section .bss
.align 4

/* Stack areas */
.space 0x1000
fiq_stack_top:
.space 0x1000
irq_stack_top:
.space 0x1000
abort_stack_top:
.space 0x1000
undef_stack_top:
.space 0x1000
sys_stack_top:
.space 0x2000
svc_stack_top:

/* MMU translation table (16KB) */
.align 14
translation_table:
    .space 0x4000