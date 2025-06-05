// AArch64 (64-bit ARM) Example
// Demonstrates modern ARM64 assembly features

.arch armv8-a
.text

// Function to calculate factorial
// Input: x0 = n
// Output: x0 = n!
.global factorial
.type factorial, %function
factorial:
    // Save frame pointer and link register
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    
    // Base case: if n <= 1, return 1
    cmp x0, #1
    b.le .Lfactorial_base
    
    // Recursive case: n * factorial(n-1)
    mov x19, x0                 // Save n in x19
    sub x0, x0, #1             // x0 = n - 1
    bl factorial               // Call factorial(n-1)
    mul x0, x0, x19            // x0 = (n-1)! * n
    
    // Restore and return
    ldp x29, x30, [sp], #16
    ret
    
.Lfactorial_base:
    mov x0, #1
    ldp x29, x30, [sp], #16
    ret

// String length function using SIMD
.global strlen_simd
.type strlen_simd, %function
strlen_simd:
    // x0 = string pointer
    mov x1, x0                  // Save original pointer
    
    // Align to 16-byte boundary
    and x2, x0, #15            // Get alignment offset
    bic x0, x0, #15            // Align down to 16 bytes
    
    // Load first vector
    ld1 {v0.16b}, [x0], #16
    
    // Create mask for bytes before string start
    dup v1.16b, #0xFF
    lsl x2, x2, #3
    neg x2, x2
    ushl v1.2d, v1.2d, v2.2d
    
    // Check for null bytes
    cmeq v2.16b, v0.16b, #0
    and v2.16b, v2.16b, v1.16b
    
    // Check if any null byte found
    umaxv b3, v2.16b
    fmov w2, s3
    cbnz w2, .Lstrlen_found
    
.Lstrlen_loop:
    ld1 {v0.16b}, [x0], #16
    cmeq v2.16b, v0.16b, #0
    umaxv b3, v2.16b
    fmov w2, s3
    cbz w2, .Lstrlen_loop
    
.Lstrlen_found:
    // Find exact position of null byte
    sub x0, x0, #16
    mov x2, #0
.Lstrlen_find_exact:
    ldrb w3, [x0, x2]
    cbz w3, .Lstrlen_done
    add x2, x2, #1
    b .Lstrlen_find_exact
    
.Lstrlen_done:
    add x0, x0, x2
    sub x0, x0, x1
    ret

// Memory copy optimized for AArch64
.global memcpy_opt
.type memcpy_opt, %function
memcpy_opt:
    // x0 = destination
    // x1 = source
    // x2 = size
    
    mov x3, x0                  // Save destination for return
    
    // Copy 64 bytes at a time
    cmp x2, #64
    b.lt .Lmemcpy_small
    
.Lmemcpy_64:
    ldp q0, q1, [x1], #32
    ldp q2, q3, [x1], #32
    stp q0, q1, [x0], #32
    stp q2, q3, [x0], #32
    sub x2, x2, #64
    cmp x2, #64
    b.ge .Lmemcpy_64
    
.Lmemcpy_small:
    // Copy remaining bytes
    cbz x2, .Lmemcpy_done
    
.Lmemcpy_byte:
    ldrb w4, [x1], #1
    strb w4, [x0], #1
    subs x2, x2, #1
    b.ne .Lmemcpy_byte
    
.Lmemcpy_done:
    mov x0, x3                  // Return destination
    ret

// Atomic operations example
.global atomic_add
.type atomic_add, %function
atomic_add:
    // x0 = pointer to atomic variable
    // x1 = value to add
    
.Latomic_retry:
    ldaxr x2, [x0]              // Load exclusive with acquire
    add x2, x2, x1              // Add value
    stlxr w3, x2, [x0]          // Store exclusive with release
    cbnz w3, .Latomic_retry     // Retry if exclusive access failed
    
    mov x0, x2                  // Return new value
    ret

// Cryptographic acceleration example (SHA256)
.global sha256_transform_block
.type sha256_transform_block, %function
sha256_transform_block:
    // x0 = state (8 words)
    // x1 = input block (16 words)
    
    // Load initial hash values
    ld1 {v0.4s, v1.4s}, [x0]
    
    // Load message schedule
    ld1 {v4.4s-v7.4s}, [x1], #64
    
    // Rounds 0-3
    mov v2.16b, v0.16b
    mov v3.16b, v1.16b
    sha256h q0, q1, v4.4s
    sha256h2 q1, q2, v4.4s
    sha256su0 v4.4s, v5.4s
    sha256su1 v4.4s, v6.4s, v7.4s
    
    // ... (more rounds abbreviated)
    
    // Store updated hash
    st1 {v0.4s, v1.4s}, [x0]
    ret

// Exception handling example
.global exception_handler
.type exception_handler, %function
exception_handler:
    // Save all registers
    stp x0, x1, [sp, #-16]!
    stp x2, x3, [sp, #-16]!
    stp x4, x5, [sp, #-16]!
    stp x6, x7, [sp, #-16]!
    stp x8, x9, [sp, #-16]!
    stp x10, x11, [sp, #-16]!
    stp x12, x13, [sp, #-16]!
    stp x14, x15, [sp, #-16]!
    stp x16, x17, [sp, #-16]!
    stp x18, x19, [sp, #-16]!
    stp x20, x21, [sp, #-16]!
    stp x22, x23, [sp, #-16]!
    stp x24, x25, [sp, #-16]!
    stp x26, x27, [sp, #-16]!
    stp x28, x29, [sp, #-16]!
    str x30, [sp, #-8]!
    
    // Get exception syndrome
    mrs x0, esr_el1
    mrs x1, elr_el1
    mrs x2, spsr_el1
    
    // Call C handler
    bl handle_exception
    
    // Restore registers
    ldr x30, [sp], #8
    ldp x28, x29, [sp], #16
    ldp x26, x27, [sp], #16
    ldp x24, x25, [sp], #16
    ldp x22, x23, [sp], #16
    ldp x20, x21, [sp], #16
    ldp x18, x19, [sp], #16
    ldp x16, x17, [sp], #16
    ldp x14, x15, [sp], #16
    ldp x12, x13, [sp], #16
    ldp x10, x11, [sp], #16
    ldp x8, x9, [sp], #16
    ldp x6, x7, [sp], #16
    ldp x4, x5, [sp], #16
    ldp x2, x3, [sp], #16
    ldp x0, x1, [sp], #16
    
    eret

// System register access
.global read_system_register
.type read_system_register, %function
read_system_register:
    // Example: Read CPU ID
    mrs x0, midr_el1
    ret

// Macro definition example
.macro SAVE_CONTEXT
    stp x29, x30, [sp, #-16]!
    mov x29, sp
.endm

.macro RESTORE_CONTEXT
    mov sp, x29
    ldp x29, x30, [sp], #16
.endm

// Using the macros
.global optimized_function
.type optimized_function, %function
optimized_function:
    SAVE_CONTEXT
    
    // Function body
    mov x0, #42
    
    RESTORE_CONTEXT
    ret

// Data section with alignment
.section .data
.align 4
counter:
    .quad 0

.align 16
simd_constants:
    .float 1.0, 2.0, 3.0, 4.0
    .float 5.0, 6.0, 7.0, 8.0

.section .rodata
error_message:
    .asciz "Error occurred at address: 0x%016lx\n"