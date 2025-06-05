; Data Structure Definitions
; Include file for assembly programs

; Process Control Block
struc PCB
    .pid:       resd 1      ; Process ID
    .ppid:      resd 1      ; Parent process ID
    .state:     resb 1      ; Process state
    .priority:  resb 1      ; Process priority
    .padding:   resb 2      ; Alignment padding
    .esp:       resq 1      ; Stack pointer
    .eip:       resq 1      ; Instruction pointer
    .cr3:       resq 1      ; Page directory base
    .name:      resb 16     ; Process name
    .size:
endstruc

; Interrupt Descriptor Table Entry
struc IDT_ENTRY
    .offset_low:    resw 1
    .selector:      resw 1
    .ist:           resb 1
    .type_attr:     resb 1
    .offset_mid:    resw 1
    .offset_high:   resd 1
    .reserved:      resd 1
    .size:
endstruc

; Global Descriptor Table Entry
struc GDT_ENTRY
    .limit_low:     resw 1
    .base_low:      resw 1
    .base_mid:      resb 1
    .access:        resb 1
    .granularity:   resb 1
    .base_high:     resb 1
    .size:
endstruc

; Memory allocation block
struc MEM_BLOCK
    .size:          resq 1      ; Block size
    .next:          resq 1      ; Next block pointer
    .prev:          resq 1      ; Previous block pointer
    .free:          resb 1      ; Free flag
    .padding:       resb 7      ; Alignment
    .size:
endstruc

; Constants
KERNEL_CS   equ 0x08
KERNEL_DS   equ 0x10
USER_CS     equ 0x18 | 3
USER_DS     equ 0x20 | 3

; Page flags
PAGE_PRESENT    equ 0x001
PAGE_RW         equ 0x002
PAGE_USER       equ 0x004
PAGE_SIZE_4MB   equ 0x080

; Process states
PROC_RUNNING    equ 0
PROC_READY      equ 1
PROC_BLOCKED    equ 2
PROC_ZOMBIE     equ 3

; Useful macros
%macro PUSH_ALL 0
    push rax
    push rbx
    push rcx
    push rdx
    push rsi
    push rdi
    push rbp
    push r8
    push r9
    push r10
    push r11
    push r12
    push r13
    push r14
    push r15
%endmacro

%macro POP_ALL 0
    pop r15
    pop r14
    pop r13
    pop r12
    pop r11
    pop r10
    pop r9
    pop r8
    pop rbp
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rbx
    pop rax
%endmacro