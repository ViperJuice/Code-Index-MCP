# Interrupt Handler Implementation
# AT&T syntax with C preprocessor

#include <asm/segment.h>
#include <asm/irqflags.h>

.section .text

# Macro for interrupt handler stub
.macro INTERRUPT_HANDLER vector
.globl interrupt_handler_\vector
.type interrupt_handler_\vector, @function
interrupt_handler_\vector:
    pushq $0            # Error code placeholder
    pushq $\vector      # Interrupt vector
    jmp common_interrupt_handler
.endm

# Generate interrupt handlers
INTERRUPT_HANDLER 0x00  # Divide by zero
INTERRUPT_HANDLER 0x01  # Debug
INTERRUPT_HANDLER 0x02  # NMI
INTERRUPT_HANDLER 0x03  # Breakpoint
INTERRUPT_HANDLER 0x04  # Overflow
INTERRUPT_HANDLER 0x05  # Bound range exceeded

# Page fault handler (has error code)
.globl page_fault_handler
.type page_fault_handler, @function
page_fault_handler:
    # Error code already pushed by CPU
    pushq $0x0E         # Page fault vector
    jmp common_interrupt_handler

# Common interrupt handler
.type common_interrupt_handler, @function
common_interrupt_handler:
    # Save all registers
    pushq %rax
    pushq %rbx
    pushq %rcx
    pushq %rdx
    pushq %rsi
    pushq %rdi
    pushq %rbp
    pushq %r8
    pushq %r9
    pushq %r10
    pushq %r11
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    
    # Save segment registers
    movq %ds, %rax
    pushq %rax
    movq %es, %rax
    pushq %rax
    movq %fs, %rax
    pushq %rax
    movq %gs, %rax
    pushq %rax
    
    # Load kernel segments
    movq $__KERNEL_DS, %rax
    movq %rax, %ds
    movq %rax, %es
    
    # Call C handler
    movq %rsp, %rdi     # Pass stack pointer as argument
    call do_interrupt
    
    # Restore segment registers
    popq %rax
    movq %rax, %gs
    popq %rax
    movq %rax, %fs
    popq %rax
    movq %rax, %es
    popq %rax
    movq %rax, %ds
    
    # Restore general registers
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %r11
    popq %r10
    popq %r9
    popq %r8
    popq %rbp
    popq %rdi
    popq %rsi
    popq %rdx
    popq %rcx
    popq %rbx
    popq %rax
    
    # Remove vector and error code
    addq $16, %rsp
    
    iretq

# System call entry point
.globl system_call_entry
.type system_call_entry, @function
system_call_entry:
    # Save user stack
    swapgs
    movq %rsp, %gs:0    # Save user RSP
    movq %gs:8, %rsp    # Load kernel RSP
    
    # Build pt_regs on stack
    pushq $__USER_DS
    pushq %gs:0         # User RSP
    pushq %r11          # User RFLAGS
    pushq $__USER_CS
    pushq %rcx          # User RIP
    
    # Save registers
    pushq %rax
    pushq %rdi
    pushq %rsi
    pushq %rdx
    pushq %r10          # Instead of RCX
    pushq %r8
    pushq %r9
    pushq %rbx
    pushq %rbp
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    
    # Call system call handler
    movq %rax, %rdi     # System call number
    movq %rsp, %rsi     # pt_regs pointer
    call do_syscall
    
    # Restore registers
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbp
    popq %rbx
    popq %r9
    popq %r8
    popq %r10
    popq %rdx
    popq %rsi
    popq %rdi
    
    # Skip RAX (return value)
    addq $8, %rsp
    
    # Return to userspace
    swapgs
    sysretq

.section .data
.align 16
interrupt_count:
    .quad 0

.section .rodata
int_msg:
    .asciz "Interrupt %d occurred\n"