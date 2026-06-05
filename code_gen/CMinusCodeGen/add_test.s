# Código MIPS generado por cgen.py para C-
# Archivo fuente compilado a: add_test.s

.data
_newline: .asciiz "\n"

.text
.globl main
    j    main

suma:
    subu $sp, $sp, 20
    sw   $ra, 16($sp)
    sw   $fp, 12($sp)
    addu $fp, $sp, 16
    sw   $a0, -12($fp)   # param a
    sw   $a1, -16($fp)   # param b

    lw   $v0, -12($fp)  # local a
    subu $sp, $sp, 4
    sw   $v0, 0($sp)
    lw   $v0, -16($fp)  # local b
    lw   $t0, 0($sp)
    addu $sp, $sp, 4
    move $t1, $v0
    add  $v0, $t0, $t1
    j    suma_exit
suma_exit:
    lw   $ra, 16($sp)
    lw   $fp, 12($sp)
    addu $sp, $sp, 20
    jr   $ra

main:
    subu $sp, $sp, 36
    sw   $ra, 32($sp)
    sw   $fp, 28($sp)
    addu $fp, $sp, 32

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
    jal  suma
    move $t0, $v0
    sw   $t0, -32($fp)  # local result
    move $v0, $t0
    lw   $v0, -32($fp)  # local result
    move $a0, $v0
    li   $v0, 1
    syscall               # print_int
    la   $a0, _newline
    li   $v0, 4
    syscall               # print newline
main_exit:
    lw   $ra, 32($sp)
    lw   $fp, 28($sp)
    addu $sp, $sp, 36
    li   $v0, 10
    syscall               # exit

