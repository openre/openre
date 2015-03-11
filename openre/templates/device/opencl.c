#pragma OPENCL EXTENSION cl_khr_global_int32_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_local_int32_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_global_int32_extended_atomics : enable
#pragma OPENCL EXTENSION cl_khr_local_int32_extended_atomics : enable
#pragma OPENCL EXTENSION cl_khr_int64_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_int64_base_atomics : enable

/* openre.data_types.types */
{{ types.neuron_flags | to_c_type }} constant IS_INHIBITORY = 1<<0;
{{ types.neuron_flags | to_c_type }} constant IS_SPIKED = 1<<1;
{{ types.neuron_flags | to_c_type }} constant IS_DEAD = 1<<2;
{{ types.neuron_flags | to_c_type }} constant IS_TRANSMITTER = 1<<3;
{{ types.neuron_flags | to_c_type }} constant IS_RECEIVER = 1<<4;
{{ types.neuron_flags | to_c_type }} constant IS_INFINITE_ERROR = 1<<5;
/* openre.data_types.null */
{{ types.address | to_c_type }} constant NULL_ADDRESS = {{ null }};

__kernel void test_kernel(__global unsigned int * res, __const unsigned int num) {
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
    if(i == 10){res[i] = NULL_ADDRESS;}
    if(i == 11){res[i] = IS_INFINITE_ERROR;}
}

// for each neuron
__kernel void tick_neurons(
    /* domain */
    __const {{ types.tick | to_c_type }}            d_ticks,
    /* layers */
    __global {{ types.threshold | to_c_type }}      * l_threshold,
    __global {{ types.threshold | to_c_type }}      * l_relaxation,
    __global {{ types.tick | to_c_type }}           * l_total_spikes,
    __global {{ types.vitality | to_c_type }}       * l_spike_cost,
    __global {{ types.vitality | to_c_type }}       * l_max_vitality,
    /* neurons */
    __global {{ types.neuron_level | to_c_type }}   * n_level,
    __global {{ types.neuron_flags | to_c_type }}   * n_flags,
    __global {{ types.tick | to_c_type }}           * n_spike_tick,
    __global {{ types.medium_address | to_c_type }} * n_layer,
    __global {{ types.vitality | to_c_type }}       * n_vitality
) {
    {{ types.address | to_c_type }} neuron_address = get_global_id(0);
    // get layer
    {{ types.address | to_c_type }} layer_address = n_layer[neuron_address];
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
        if(n_vitality[neuron_address] > l_spike_cost[layer_address]){
            n_vitality[neuron_address] -= l_spike_cost[layer_address];
            // set neuron spiked flag
            n_flags[neuron_address] |= IS_SPIKED;
            atomic_add(&l_total_spikes[layer_address], 1);
            // reset neuron.level (or decrease it by layer.threshold, I don't know
            // which one is better)
            n_level[neuron_address] = 0;
            // store neurons last tick for better training
            n_spike_tick[neuron_address] = d_ticks;
        }
        else{
            // neurons vitality is exhausted so it dies
            n_flags[neuron_address] |= IS_DEAD;
            n_vitality[neuron_address] = l_max_vitality[layer_address];
            n_level[neuron_address] = 0;
        }
    }
    // just relax
    else if(n_level[neuron_address] >= 0){
        n_level[neuron_address] -= l_relaxation[layer_address];
    }
    if(n_level[neuron_address] < 0){
        n_level[neuron_address] = 0;
    }
    if(n_vitality[neuron_address] < l_max_vitality[layer_address]){
        n_vitality[neuron_address] += 1;
    }
}
__kernel void tick_sinapses(
    /* domain */
    __const {{ types.threshold | to_c_type }}       d_learn_threshold,
    __const {{ types.threshold | to_c_type }}       d_forget_threshold,
    /* neurons */
    __global {{ types.neuron_level | to_c_type }}   * n_level,
    __global {{ types.neuron_flags | to_c_type }}   * n_flags,
    __global {{ types.tick | to_c_type }}           * n_spike_tick,
    /* sinapses */
    __global {{ types.sinapse_level | to_c_type }}  * s_level,
    __global {{ types.address | to_c_type }}        * s_pre,
    __global {{ types.address | to_c_type }}        * s_post,
    /* pre-neuron - sinapse index */
    __global {{ types.address | to_c_type }}        * pre_key,
    __global {{ types.address | to_c_type }}        * pre_value,
    /* post-neuron - sinapse index */
    __global {{ types.address | to_c_type }}        * post_key,
    __global {{ types.address | to_c_type }}        * post_value
) {
    {{ types.address | to_c_type }} neuron_address = get_global_id(0);
    /*
     *  pre-neuron -> pre-sinapse -> neuron -> post-sinapse -> post-neuron
     *  pre_key - sinapses index, for neuron in sinapse.pre
     *  post_key - sinapses index, for neuron in sinapse.post
     *  post-sinapse address = pre_key[neuron address]
     *  pre-sinapse address = post_key[neuron address]
     * */
    {{ types.address | to_c_type }} post_sinapse_address = pre_key[neuron_address];
    {{ types.address | to_c_type }} post_neuron_address = NULL_ADDRESS;
    {{ types.address | to_c_type }} pre_sinapse_address = post_key[neuron_address];
    {{ types.address | to_c_type }} pre_neuron_address = NULL_ADDRESS;
    int not_infinite = 0;
    // stop if neuron is dead or not spiked
    if(
        n_flags[neuron_address] & IS_DEAD
        || !(n_flags[neuron_address] & IS_SPIKED)
    ){
        return;
    }
    // for each post-sinapses
    not_infinite = 1000000;
    while(post_sinapse_address != NULL_ADDRESS && not_infinite){
        not_infinite--; /* TODO: send error to host if infinite loop */
        post_neuron_address = s_post[post_sinapse_address];
        // sinapse is dead
        if(s_level[post_sinapse_address] == 0){
            continue;
        }
        // post-neuron is dead - kill sinapse
        if(n_flags[post_neuron_address] & IS_DEAD){
            s_level[post_sinapse_address] = 0;
            continue;
        }
        // is spiked - change post neuron level
        n_level[post_neuron_address] +=
            n_flags[neuron_address] & IS_INHIBITORY
            ? -s_level[post_sinapse_address] : s_level[post_sinapse_address];
        // post-sinapse learning
        // next sinapse
        post_sinapse_address = pre_value[post_sinapse_address];
    }
    // for each pre-sinapses
    not_infinite = 1000000;
    while(pre_sinapse_address != NULL_ADDRESS && not_infinite){
        not_infinite--; /* TODO: send error to host if infinite loop */
        pre_neuron_address = s_pre[pre_sinapse_address];
        // sinapse is dead
        if(s_level[pre_sinapse_address] == 0){
            continue;
        }
        // pre-neuron is dead - kill sinapse
        if(n_flags[pre_neuron_address] & IS_DEAD){
            s_level[pre_sinapse_address] = 0;
            continue;
        }
        // pre-sinapse learning
        // next pre-sinapse
        pre_sinapse_address = post_value[pre_sinapse_address];
    }
}

