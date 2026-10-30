# Restricciones de timing de asic_top (PnR y signoff).
#
# Parte del SDC generico de LibreLane (librelane/scripts/base.sdc) y lee las
# mismas variables del flujo (CLOCK_PERIOD, IO_DELAY_CONSTRAINT, driving cell,
# carga de salida, incertidumbre, transicion y derating), asi un barrido con
# `-c CLOCK_PERIOD=...` sigue funcionando sin tocar este archivo.
#
# Unica diferencia con el generico: rst_ni no se trata como entrada de datos.
# Es un reset asincrono; pochoco_soc lo pasa por un sincronizador de 2 FF, asi
# que solo su liberacion importa y esa ya queda alineada con clk_i. La red
# interna de reset (salida del sincronizador -> pines de clear) si se analiza,
# como camino reg->reg con chequeos de recovery/removal.

# Reloj
create_clock [get_ports clk_i] -name clk_i -period $::env(CLOCK_PERIOD)
set clk [get_clocks clk_i]

set_clock_uncertainty $::env(CLOCK_UNCERTAINTY_CONSTRAINT) $clk
set_clock_transition  $::env(CLOCK_TRANSITION_CONSTRAINT)  $clk

# Antes de CTS LibreLane pide reloj ideal; despues, el arbol real (propagado)
if { [info exists ::env(OPENLANE_SDC_IDEAL_CLOCKS)] && $::env(OPENLANE_SDC_IDEAL_CLOCKS) } {
    unset_propagated_clock [all_clocks]
} else {
    set_propagated_clock [all_clocks]
}

# Entradas y salidas de datos: retardo de IO_DELAY_CONSTRAINT % del periodo
set io_delay    [expr {$::env(CLOCK_PERIOD) * $::env(IO_DELAY_CONSTRAINT) / 100.0}]
set data_inputs [get_ports {btn_i[*] spi_sclk_i spi_mosi_i spi_cs_ni}]
set rst_input   [get_ports rst_ni]

set_input_delay  $io_delay -clock $clk $data_inputs
set_output_delay $io_delay -clock $clk [all_outputs]

# Reset asincrono: sin input delay y fuera del analisis de timing
set_false_path -from $rst_input

# Driving cells y carga de salida
set drv     [split $::env(SYNTH_DRIVING_CELL) "/"]
set clk_drv [split $::env(SYNTH_CLK_DRIVING_CELL) "/"]
set_driving_cell -lib_cell [lindex $drv 0]     -pin [lindex $drv 1]     $data_inputs
set_driving_cell -lib_cell [lindex $drv 0]     -pin [lindex $drv 1]     $rst_input
set_driving_cell -lib_cell [lindex $clk_drv 0] -pin [lindex $clk_drv 1] [get_ports clk_i]
set_load [expr {$::env(OUTPUT_CAP_LOAD) / 1000.0}] [all_outputs]

# Limites de diseno
set_max_fanout $::env(MAX_FANOUT_CONSTRAINT) [current_design]
if { [info exists ::env(MAX_TRANSITION_CONSTRAINT)] } {
    set_max_transition $::env(MAX_TRANSITION_CONSTRAINT) [current_design]
}
if { [info exists ::env(MAX_CAPACITANCE_CONSTRAINT)] } {
    set_max_capacitance $::env(MAX_CAPACITANCE_CONSTRAINT) [current_design]
}

# Variacion on-chip
set_timing_derate -early [expr {1 - $::env(TIME_DERATING_CONSTRAINT) / 100.0}]
set_timing_derate -late  [expr {1 + $::env(TIME_DERATING_CONSTRAINT) / 100.0}]
