# [SOLO SIMULACION -- NO usar para la Go Board fisica]
# Copia de game.s con las constantes de tiempo (3s y 1 decima) cambiadas a
# valores chicos, para que una partida completa de 10 rondas se pueda
# simular en unos pocos miles de ciclos en vez de ~750 millones. Usado por
# sim/tb_game_smoke.v. Si game.s cambia de logica de control (no solo las
# dos constantes de tiempo marcadas [TEST] mas abajo), hay que volver a
# generar este archivo a mano con el mismo reemplazo.
#
# Copyright 2026 Universidad de los Andes.
# Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
# you may not use this file except in compliance with the License.
# SPDX-License-Identifier: SHL-0.51
#
# Course: Arquitectura de Computadores (2026)
# Proyecto 2 - Juego de reflejos sobre Pochoco SoC
#
# Secuencia por ronda (enunciado):
#   1. Prender los 4 LEDs durante >= 3 segundos.
#   2. Elegir un LED objetivo pseudoaleatorio y encender solo ese.
#   3. La medicion de tiempo arranca en el mismo instante logico en que
#      arranca la ronda (antes del paso 1, no cuando se prende el objetivo).
#   4. Esperar un boton; si coincide con el objetivo, termina la ronda.
#   5. Mostrar el tiempo de respuesta en decimas de segundo (decimal real).
#   6. Repetir hasta completar diez respuestas correctas.
#   7. Mostrar el promedio de las diez rondas, misma unidad.
#   8. Boton incorrecto: indicar error y reiniciar SOLO la ronda actual
#      (correct_count/sum_decimas ya acumulados se conservan).
#
# Reloj de la Go Board: 25 MHz (mismo oscilador de Proyecto 1, ver
# proyecto1/constraints/go-board.pcf). Conversion ciclos -> tiempo:
#   3 segundos       = 75,000,000 ciclos
#   1 decima de seg  =  2,500,000 ciclos
#
# Generacion pseudoaleatoria: espino_alu.v tiene los shifts deshabilitados
# (ejecutan como ADD), asi que en vez de un LFSR clasico se mezcla un estado
# persistente con el contador de ciclos usando solo add/xor, y se elige 1 de
# 4 con "andi x,x,3" (no hace falta shift porque 4 es potencia de 2). Esto
# es exactamente lo que permite el enunciado: "una semilla tomada del
# contador de ciclos y operaciones de assembly", perceptiblemente
# pseudoaleatorio porque cada ronda se re-siembra con el tiempo de reaccion
# humano de la ronda anterior.
#
# Sin instruccion de division ni multiplicacion en esta ALU: los cocientes
# (decimas de segundo, promedio, digitos decimales) se calculan por resta
# repetida, y el nibble alto del registro de 7 segmentos se arma por suma
# repetida de 16 (equivalente a "decenas << 4" sin usar shift).
#
# Mapa de memoria usado (offsets desde 0x8000_0000, ver pochoco_periph.v):
#   0x00  digitos 7-seg (escritura; decodificados a hex por hex2seg)
#   0x04  LEDs (escritura, 4 bits)
#   0x08  botones (solo lectura, 4 bits; se asume boton i <-> LED i)
#   0x0C  contador de ciclos (lectura = valor actual; escritura = recarga)
#
# Registros usados en todo el programa (sin llamadas anidadas ni pila):
#   s0 = base de perifericos (0x8000_0000), fijo
#   s1 = estado persistente del generador pseudoaleatorio
#   a0 = correct_count (0..10)
#   a1 = sum_decimas (acumulador para el promedio)
#   a2 = cyc_start de la ronda actual
#   a3 = target_led (indice 0..3)
#   a4 = mascara one-hot del LED objetivo
#   a5, t0, t1, t2, ra = scratch de uso libre entre fases

.section .text
.global _start

_start:
    lui  s0, 0x80000        # s0 = 0x80000000 (base de perifericos)

    lw   s1, 12(s0)         # semilla inicial del PRNG = contador de ciclos al boot
    addi a0, x0, 0          # correct_count = 0
    addi a1, x0, 0          # sum_decimas = 0

round_start:
    sw   x0, 0(s0)          # limpia el display al empezar/reiniciar la ronda

    # Paso 3: la medicion de tiempo arranca AQUI (mismo instante logico en
    # que arranca la ronda), antes de prender los 4 LEDs.
    lw   a2, 12(s0)         # a2 = cyc_start

    # Paso 1: los 4 LEDs encendidos durante >= 3 segundos.
    addi t0, x0, 15
    sw   t0, 4(s0)          # LEDs = 1111

    addi t1, x0, 50          # [TEST] valor chico en vez de 75,000,000 para simular rapido

wait_3s:
    lw   t2, 12(s0)
    sub  t2, t2, a2         # t2 = ciclos transcurridos desde cyc_start
    blt  t2, t1, wait_3s

    # Paso 2: elegir el LED objetivo pseudoaleatorio.
    add  s1, s1, t2         # mezcla el jitter humano de la espera de 3s
    xori s1, s1, 1783       # constante de mezcla (evita simetrias del xor)
    add  s1, s1, a2         # mezcla tambien el instante de inicio de ronda
    andi a3, s1, 3          # a3 = indice 0..3 del LED objetivo

    addi a4, x0, 1          # target 0 -> mascara 0001
    beq  a3, x0, target_ready
    addi a4, x0, 2          # target 1 -> mascara 0010
    addi t0, x0, 1
    beq  a3, t0, target_ready
    addi a4, x0, 4          # target 2 -> mascara 0100
    addi t0, x0, 2
    beq  a3, t0, target_ready
    addi a4, x0, 8          # unico caso restante (target 3) -> mascara 1000
target_ready:
    sw   a4, 4(s0)          # enciende SOLO el LED objetivo

    # El jugador debe soltar cualquier boton que haya quedado apretado de
    # la ronda anterior antes de que una pulsacion nueva cuente.
wait_release:
    lw   t0, 8(s0)
    bne  t0, x0, wait_release

    # Paso 4: esperar una pulsacion.
wait_button:
    lw   t0, 8(s0)
    beq  t0, x0, wait_button

    lw   t1, 12(s0)
    sub  t1, t1, a2          # t1 = ciclos de reaccion (tiempo de respuesta)

    bne  t0, a4, wrong_button

    # Correcto: decimas de segundo = t1 / 2,500,000 (resta repetida).
    addi t2, x0, 8           # [TEST] valor chico en vez de 2,500,000 para simular rapido
    addi a5, x0, 0
response_div:
    blt  t1, t2, response_div_done
    sub  t1, t1, t2
    addi a5, a5, 1
    jal  x0, response_div
response_div_done:
    add  a1, a1, a5          # sum_decimas += decimas de esta ronda
    addi a0, a0, 1           # correct_count += 1

    jal  ra, show_decimal    # muestra a5 (decimas) en decimal

    addi t0, x0, 10
    beq  a0, t0, all_rounds_done
    jal  x0, round_start

wrong_button:
    # Paso 8: boton incorrecto -> indicar error y reiniciar SOLO la ronda.
    sw   x0, 4(s0)            # apaga los LEDs
    addi t0, x0, 238          # 0xEE: hex2seg muestra 'E' en ambos digitos
    sw   t0, 0(s0)

    addi t1, x0, 8            # [TEST] valor chico en vez de 2,500,000 para simular rapido
    addi t0, x0, 5            # pausa de error = 5 decimas (~0.5s) visibles
error_pause_outer:
    beq  t0, x0, error_pause_done
    lw   a2, 12(s0)
error_pause_inner:
    lw   t2, 12(s0)
    sub  t2, t2, a2
    blt  t2, t1, error_pause_inner
    addi t0, t0, -1
    jal  x0, error_pause_outer
error_pause_done:
    jal  x0, round_start      # reinicia SOLO esta ronda; a0/a1 no se tocan

all_rounds_done:
    # Paso 7: promedio = sum_decimas / 10 (resta repetida).
    addi t2, x0, 10
    addi a5, x0, 0
average_div:
    blt  a1, t2, average_div_done
    sub  a1, a1, t2
    addi a5, a5, 1
    jal  x0, average_div
average_div_done:
    jal  ra, show_decimal     # muestra el promedio en decimal

halt:
    jal  x0, halt              # la demo termina aqui (promedio queda en pantalla)

# show_decimal: muestra el valor en a5 (0..99, se recorta a 99) como dos
# digitos decimales reales en los 7-seg, reusando el decodificador hex2seg
# ya existente en pochoco_periph.v (nibble alto = decenas, nibble bajo =
# unidades). Sin division ni shift: decenas por resta repetida de 10, y el
# nibble alto por suma repetida de 16. Clobbers: t0, t1, t2, a5.
show_decimal:
    addi t0, x0, 10
    addi t1, x0, 0             # t1 = decenas
tens_div:
    blt  a5, t0, tens_div_done
    sub  a5, a5, t0
    addi t1, t1, 1
    jal  x0, tens_div
tens_div_done:
    addi t2, x0, 9
    blt  t1, t2, tens_in_range
    addi t1, x0, 9              # recorta a "99" si se pasa de dos digitos
    addi a5, x0, 9
tens_in_range:
    addi t0, x0, 0              # acumulador de decenas*16
    addi t2, x0, 0              # contador del bucle
mul16:
    beq  t2, t1, mul16_done
    addi t0, t0, 16
    addi t2, t2, 1
    jal  x0, mul16
mul16_done:
    add  t0, t0, a5             # t0 = decenas*16 + unidades
    sw   t0, 0(s0)
    jalr x0, 0(ra)
