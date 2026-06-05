# Código MIPS generado por cgen.py para C-
# Archivo fuente compilado a: file.s

.data
_newline: .asciiz "\n"

.text
.globl main
    j    main

gcd:
    subu $sp, $sp, 20
    sw   $ra, 16($sp)
    sw   $fp, 12($sp)
    addu $fp, $sp, 16
    sw   $a0, -12($fp)   # param u
    sw   $a1, -16($fp)   # param v

    lw   $v0, -16($fp)  # local v
    subu $sp, $sp, 4
    sw   $v0, 0($sp)
    li   $v0, 0
    lw   $t0, 0($sp)
    addu $sp, $sp, 4
    move $t1, $v0
    seq  $v0, $t0, $t1
    beq  $v0, $zero, else1
    lw   $v0, -12($fp)  # local u
    j    gcd_exit
    j    endif2
else1:
    lw   $v0, -16($fp)  # local v
    subu $sp, $sp, 4
    sw   $v0, 0($sp)
    lw   $v0, -12($fp)  # local u
    subu $sp, $sp, 4
    sw   $v0, 0($sp)
    lw   $v0, -12($fp)  # local u
    subu $sp, $sp, 4
    sw   $v0, 0($sp)
    lw   $v0, -16($fp)  # local v
    lw   $t0, 0($sp)
    addu $sp, $sp, 4
    move $t1, $v0
    div  $t0, $t1
    mflo $v0
    subu $sp, $sp, 4
    sw   $v0, 0($sp)
    lw   $v0, -16($fp)  # local v
    lw   $t0, 0($sp)
    addu $sp, $sp, 4
    move $t1, $v0
    mul  $v0, $t0, $t1
    lw   $t0, 0($sp)
    addu $sp, $sp, 4
    move $t1, $v0
    sub  $v0, $t0, $t1
    subu $sp, $sp, 4
    sw   $v0, 0($sp)
    lw   $a1, 0($sp)
    addu $sp, $sp, 4
    lw   $a0, 0($sp)
    addu $sp, $sp, 4
    jal  gcd
    j    gcd_exit
endif2:
gcd_exit:
    lw   $ra, 16($sp)
    lw   $fp, 12($sp)
    addu $sp, $sp, 20
    jr   $ra

main:
    subu $sp, $sp, 32
    sw   $ra, 28($sp)
    sw   $fp, 24($sp)
    addu $fp, $sp, 28

    li   $v0, 5
    syscall               # read_int → $v0
    move $t0, $v0
    sw   $t0, -24($fp)  # local x
    move $v0, $t0
    li   $v0, 5
    syscall               # read_int → $v0
    move $t0, $v0
    sw   $t0, -28($fp)  # local y
    move $v0, $t0
    lw   $v0, -24($fp)  # local x
    subu $sp, $sp, 4
    sw   $v0, 0($sp)
    lw   $v0, -28($fp)  # local y
    subu $sp, $sp, 4
    sw   $v0, 0($sp)
    lw   $a1, 0($sp)
    addu $sp, $sp, 4
    lw   $a0, 0($sp)
    addu $sp, $sp, 4
    jal  gcd
    move $a0, $v0
    li   $v0, 1
    syscall               # print_int
    la   $a0, _newline
    li   $v0, 4
    syscall               # print newline
main_exit:
    lw   $ra, 28($sp)
    lw   $fp, 24($sp)
    addu $sp, $sp, 32
    li   $v0, 10
    syscall               # exit

