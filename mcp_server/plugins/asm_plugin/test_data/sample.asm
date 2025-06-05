; Sample Assembly file demonstrating various syntax styles
; This file tests the generic assembly plugin capabilities

.model small
.stack 100h

; Data segment with various data types
.data
    message     db 'Hello, World!', 13, 10, '$'
    buffer      db 256 dup(?)
    counter     dw 0
    pointers    dd 10 dup(0)
    
; Constants and equates
MAX_SIZE    equ 1024
BUFFER_LEN  = 256

; Structure definition
Point struc
    x   dw ?
    y   dw ?
Point ends

; Code segment
.code
    ; External procedures
    extern printf:proc
    extern malloc:proc
    
    ; Public symbols
    public main
    public calculate_sum

; Main entry point
main proc
    mov ax, @data
    mov ds, ax
    
    ; Display message
    lea dx, message
    mov ah, 09h
    int 21h
    
    ; Call our calculation
    call calculate_sum
    
    ; Exit program
    mov ax, 4C00h
    int 21h
main endp

; Calculate sum of array elements
; Input: BX = array pointer, CX = count
; Output: AX = sum
calculate_sum proc near
    push bx
    push cx
    xor ax, ax          ; Clear sum
    
sum_loop:
    add ax, [bx]        ; Add current element
    add bx, 2           ; Move to next word
    loop sum_loop       ; Decrement CX and loop
    
    pop cx
    pop bx
    ret
calculate_sum endp

; Macro definition
PRINT_CHAR macro char
    push ax
    mov al, char
    mov ah, 0Eh
    int 10h
    pop ax
endm

; Another procedure using the macro
display_char proc
    PRINT_CHAR 'A'
    ret
display_char endp

; NASM-style section and macro
%macro SAVE_REGS 0
    push ax
    push bx
    push cx
    push dx
%endmacro

; GAS-style section
.section .text
.global _start
_start:
    movl $1, %eax       # System call number
    movl $0, %ebx       # Exit status
    int $0x80           # Call kernel

; FASM-style procedure
proc strlen, string
    push edi
    mov edi, [string]
    xor eax, eax
    cld
    repne scasb
    not eax
    dec eax
    pop edi
    ret
endp

end main