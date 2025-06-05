; System Call Wrapper Functions
; NASM syntax for Linux x86_64

section .text

global sys_write
global sys_read
global sys_open
global sys_close
global sys_exit

; Macro for system call wrapper
%macro SYSCALL_WRAPPER 2
    global %1
    %1:
        mov rax, %2     ; System call number
        syscall
        ret
%endmacro

; ssize_t sys_write(int fd, const void *buf, size_t count)
sys_write:
    mov rax, 1          ; __NR_write
    syscall
    ret

; ssize_t sys_read(int fd, void *buf, size_t count)
sys_read:
    mov rax, 0          ; __NR_read
    syscall
    ret

; int sys_open(const char *pathname, int flags, mode_t mode)
sys_open:
    mov rax, 2          ; __NR_open
    syscall
    ret

; int sys_close(int fd)
sys_close:
    mov rax, 3          ; __NR_close
    syscall
    ret

; void sys_exit(int status)
sys_exit:
    mov rax, 60         ; __NR_exit
    syscall
    ; No return

; Advanced system calls with error handling
global safe_mmap
safe_mmap:
    ; void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset)
    push rbp
    mov rbp, rsp
    
    ; Move 6th argument from stack to r9
    mov r9, [rbp + 16]  ; offset
    
    mov rax, 9          ; __NR_mmap
    syscall
    
    ; Check for error
    cmp rax, -4096
    ja .error
    
    leave
    ret
    
.error:
    ; Convert to errno
    neg rax
    mov [errno], eax
    mov rax, -1
    leave
    ret

section .data
    errno: dd 0

section .rodata
    ; System call numbers for reference
    SYS_READ    equ 0
    SYS_WRITE   equ 1
    SYS_OPEN    equ 2
    SYS_CLOSE   equ 3
    SYS_MMAP    equ 9
    SYS_EXIT    equ 60