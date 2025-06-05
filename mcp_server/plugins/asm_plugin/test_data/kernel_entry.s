# Linux Kernel Entry Point (AT&T Syntax)
# Simplified example of kernel initialization

.section .text.head
.globl _start
.globl startup_64

.code64
.type _start, @function
_start:
startup_64:
    # Clear BSS section
    xorl %eax, %eax
    movq $_bss_start, %rdi
    movq $_bss_end, %rcx
    subq %rdi, %rcx
    shrq $3, %rcx
    rep stosq

    # Set up initial stack
    movq $init_thread_union+THREAD_SIZE-8, %rsp
    
    # Clear EFLAGS
    pushq $0
    popfq

    # Jump to C code
    call x86_64_start_kernel
    
    # Should never reach here
    hlt
    jmp .

.type early_idt_handler, @function
early_idt_handler:
    # Early interrupt handler
    cld
    pushq %rax
    pushq %rcx
    pushq %rdx
    pushq %rsi
    pushq %rdi
    pushq %r8
    pushq %r9
    pushq %r10
    pushq %r11
    
    # Handle interrupt
    movq %rsp, %rdi
    call early_fixup_exception
    
    popq %r11
    popq %r10
    popq %r9
    popq %r8
    popq %rdi
    popq %rsi
    popq %rdx
    popq %rcx
    popq %rax
    iretq

.section .data
.align 16
.globl boot_gdt
boot_gdt:
    .quad 0x0000000000000000    # null descriptor
    .quad 0x00af9a000000ffff    # kernel code segment
    .quad 0x00cf92000000ffff    # kernel data segment

.globl boot_gdt_descr
boot_gdt_descr:
    .word boot_gdt_end - boot_gdt - 1
    .quad boot_gdt
boot_gdt_end:

.section .bss
.align PAGE_SIZE
.globl empty_zero_page
empty_zero_page:
    .skip PAGE_SIZE

.comm init_thread_union, THREAD_SIZE, THREAD_SIZE