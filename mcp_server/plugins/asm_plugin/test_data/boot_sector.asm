; Simple Boot Sector Example
; This is a minimal bootloader that prints a message

[bits 16]               ; 16-bit real mode
[org 0x7c00]           ; BIOS loads boot sector at 0x7c00

global _start

_start:
    ; Set up segments
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7c00

    ; Print boot message
    mov si, boot_msg
    call print_string
    
    ; Halt system
    jmp $

; Print string function
; Input: SI = pointer to null-terminated string
print_string:
    push ax
    push si
.loop:
    lodsb                   ; Load byte from [SI] into AL
    test al, al             ; Check if null terminator
    jz .done
    mov ah, 0x0e            ; BIOS teletype function
    int 0x10                ; BIOS video interrupt
    jmp .loop
.done:
    pop si
    pop ax
    ret

; Boot sector data
boot_msg:   db "Booting...", 0x0d, 0x0a, 0

; Padding and boot signature
times 510-($-$$) db 0       ; Pad to 510 bytes
boot_signature: dw 0xaa55   ; Boot sector signature