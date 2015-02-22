#pragma OPENCL EXTENSION cl_khr_global_int32_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_local_int32_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_global_int32_extended_atomics : enable
#pragma OPENCL EXTENSION cl_khr_local_int32_extended_atomics : enable
#pragma OPENCL EXTENSION cl_khr_int64_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_int64_base_atomics : enable

unsigned int constant IS_INHIBITORY = 1<<0;
unsigned int constant IS_SPIKED = 1<<1;
unsigned int constant IS_DEAD = 1<<2;
unsigned int constant IS_TRANSMITTER = 1<<3;
unsigned int constant IS_RECEIVER = 1<<4;

__kernel void test_kernel(__global int * res, __const unsigned int num) {
    int i = get_global_id(0);
    if(i == 0){res[i] = IS_INHIBITORY;}
    if(i == 1){res[i] = IS_SPIKED;}
    if(i == 2){res[i] = IS_DEAD;}
    if(i == 3){res[i] = IS_TRANSMITTER;}
    if(i == 4){res[i] = IS_RECEIVER;}
    atomic_add(&res[5], 1);
    if(i == 6){res[i] = 3 & IS_INHIBITORY;}
    if(i == 7){res[i] = 3 & IS_SPIKED;}
    if(i == 8){res[i] = 3 & IS_DEAD;}
    if(i == 9){res[i] = num;}
}

// for each neuron
__kernel void tick_neurons(
    /* domain */
    __const {{ types.tick | to_c_type }}            d_ticks,
    /* layers */
    __global {{ types.threshold | to_c_type }}      * l_threshold,
    __global {{ types.threshold | to_c_type }}      * l_relaxation,
    __global {{ types.tick | to_c_type }}           * l_total_spikes,
    /* neurons */
    __global {{ types.neuron_level | to_c_type }}   * n_level,
    __global {{ types.neuron_flags | to_c_type }}   * n_flags,
    __global {{ types.tick | to_c_type }}           * n_spike_tick,
    __global {{ types.medium_address | to_c_type }} * n_layer
) {
    int neuron_address = get_global_id(0);
    // get layer
    int layer_address = n_layer[neuron_address];
    // stop if neuron is dead
    if(n_flags[neuron_address] & IS_DEAD){
        return;
    }
    // remove spiked flag
    n_flags[neuron_address] &= ~IS_SPIKED;
    // if this is reseiver neuron - stop
    if(n_flags[neuron_address] & IS_RECEIVER){
        return;
    }
    // is spiked
    if(n_level[neuron_address] >= l_threshold[layer_address]){
        // set neuron spiked flag
        n_flags[neuron_address] |= IS_SPIKED;
        atomic_add(&l_total_spikes[layer_address], 1);
        // reset neuron.level (or decrease it by layer.threshold, I don't know
        // which one is better)
        n_level[neuron_address] = 0;
        // store neurons last tick for better training
        n_spike_tick[neuron_address] = d_ticks;
    }
    // just relax
    else if(n_level[neuron_address] > 0){
        n_level[neuron_address] -= l_relaxation[layer_address];
        if(n_level[neuron_address] < 0){
            n_level[neuron_address] = 0;
        }
    }
}
__kernel void tick_sinapses() {
    int i = get_global_id(0);
}

