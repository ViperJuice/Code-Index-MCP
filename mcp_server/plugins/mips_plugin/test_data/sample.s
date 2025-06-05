# MIPS Assembly Sample - Basic arithmetic and syscall example
# Demonstrates functions, data declarations, and system calls

.data
    prompt:     .asciiz "Enter a number: "
    result_msg: .asciiz "Result: "
    newline:    .asciiz "\n"
    buffer:     .space 20
    number1:    .word 42
    number2:    .word 17
    
    # Constants
    MAX_VALUE = 100
    MIN_VALUE = 0

.text
.globl main

main:
    # Print prompt
    li $v0, 4               # syscall for print string
    la $a0, prompt
    syscall
    
    # Read integer
    li $v0, 5               # syscall for read integer
    syscall
    move $t0, $v0           # store input in $t0
    
    # Load values from memory
    lw $t1, number1
    lw $t2, number2
    
    # Call add function
    move $a0, $t0
    move $a1, $t1
    jal add_numbers
    move $t3, $v0           # store result
    
    # Call multiply function
    move $a0, $t3
    move $a1, $t2
    jal multiply_numbers
    move $t4, $v0           # store final result
    
    # Print result message
    li $v0, 4
    la $a0, result_msg
    syscall
    
    # Print result
    li $v0, 1               # syscall for print integer
    move $a0, $t4
    syscall
    
    # Print newline
    li $v0, 4
    la $a0, newline
    syscall
    
    # Exit program
    li $v0, 10              # syscall for exit
    syscall

# Function: add_numbers
# Arguments: $a0, $a1 - numbers to add
# Returns: $v0 - sum
add_numbers:
    add $v0, $a0, $a1
    jr $ra

# Function: multiply_numbers
# Arguments: $a0, $a1 - numbers to multiply
# Returns: $v0 - product
multiply_numbers:
    mul $v0, $a0, $a1
    jr $ra

# Macro example
.macro print_int %value
    li $v0, 1
    move $a0, %value
    syscall
.endm

# System call wrapper for file operations
open_file_syscall:
    li $v0, 13              # open file syscall
    syscall
    jr $ra

read_file_syscall:
    li $v0, 14              # read file syscall
    syscall
    jr $ra

close_file_syscall:
    li $v0, 16              # close file syscall
    syscall
    jr $ra