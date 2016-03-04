{% extends "device/base.c" %}
{% block code %}
{{ super() }}
__kernel void test_kernel(
        __global unsigned int * res,
        __const unsigned int num,
        __const unsigned int max_vitality
) {
    int i = get_global_id(0);
    unsigned int ui = 2;
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
    if(i == 11){res[i] = IS_STRENGTHENED;}
    if(i == 12){res[i] = -ui + 5;}
    if(i == 13){res[i] = 8 | (3 & IS_SPIKED);}
    if(i == 14){res[i] = 7 & ~IS_SPIKED;}
    if(i == 15){res[i] = max_vitality;}
}

// for each neuron
__kernel void tick_neurons(
    /* domain */
    __const {{ types.tick | to_c_type }}            d_ticks,
    /* layers */
    __global {{ types.threshold | to_c_type }}      * l_threshold,
    __global {{ types.threshold | to_c_type }}      * l_relaxation,
    __global {{ types.vitality | to_c_type }}       * l_spike_cost,
    __global {{ types.vitality | to_c_type }}       * l_max_vitality,
    /* neurons */
    __global {{ types.neuron_level | to_c_type }}   * n_level,
    __global {{ types.neuron_flags | to_c_type }}   * n_flags,
    __global {{ types.tick | to_c_type }}           * n_spike_tick,
    __global {{ types.medium_address | to_c_type }} * n_layer,
    __global {{ types.vitality | to_c_type }}       * n_vitality,
    __global {{ types.threshold | to_c_type }}       * n_threshold
) {
    {{ types.address | to_c_type }} neuron_address = get_global_id(0);
    // get layer
    {{ types.address | to_c_type }} layer_address = n_layer[neuron_address];
    // here we will store diff between now and last spike's tick
    {{ types.tick | to_c_type }} tick_diff = 0;
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
    if(n_level[neuron_address] >= n_threshold[neuron_address]){
        if(n_vitality[neuron_address] > l_spike_cost[layer_address]){
            n_vitality[neuron_address] -= l_spike_cost[layer_address];
            // set neuron spiked flag
            n_flags[neuron_address] |= IS_SPIKED;
            // decrease neuron's level by threshold. Its better than just zero
            // it, becouse we can better convert numbers to spikes
            n_level[neuron_address] -= n_threshold[neuron_address];
            {% if config.threshold_inc %}
            // higher threshold in case of high spikes rate
            tick_diff = d_ticks - n_spike_tick[neuron_address];
            if (tick_diff < 10
                && n_threshold[neuron_address] < {{ types.max(types.threshold) - config.threshold_inc}}
            ){
                n_threshold[neuron_address] += {{config.threshold_inc}} - tick_diff;
            }
            {% endif %}
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
    {% if config.threshold_dec %}
    tick_diff = d_ticks - n_spike_tick[neuron_address];
    if(tick_diff > 100
        && n_threshold[neuron_address] > {{config.threshold_dec}}
    ){
        n_threshold[neuron_address] -= {{config.threshold_dec}};
    }
    {% endif %}
    if(n_vitality[neuron_address] < l_max_vitality[layer_address]){
        n_vitality[neuron_address] += 1;
    }
}
__kernel void tick_synapses(
    /* domain */
    __const {{ types.synapse_level | to_c_type }}   d_learn_rate,
    __const {{ types.synapse_level | to_c_type }}   d_learn_threshold,
    __const {{ types.tick | to_c_type }}            d_spike_learn_threshold,
    __const {{ types.tick | to_c_type }}            d_spike_forget_threshold,
    /* neurons */
    __global {{ types.neuron_level | to_c_type }}   * n_level,
    __global {{ types.neuron_flags | to_c_type }}   * n_flags,
    __global {{ types.tick | to_c_type }}           * n_spike_tick,
    /* synapses */
    __global {{ types.synapse_level | to_c_type }}  * s_level,
    __global {{ types.address | to_c_type }}        * s_pre,
    __global {{ types.address | to_c_type }}        * s_post,
    __global {{ types.synapse_level | to_c_type }}  * s_learn,
    __global {{ types.synapse_flags | to_c_type }}  * s_flags,
    /* pre-neuron - synapse index */
    __global {{ types.address | to_c_type }}        * pre_key,
    __global {{ types.address | to_c_type }}        * pre_value,
    /* post-neuron - synapse index */
    __global {{ types.address | to_c_type }}        * post_key,
    __global {{ types.address | to_c_type }}        * post_value
) {
    {{ types.address | to_c_type }} neuron_address = get_global_id(0);
    /*
     *  pre-neuron -> pre-synapse -> neuron -> post-synapse -> post-neuron
     *  pre_key - synapses index, for neuron in synapse.pre
     *  post_key - synapses index, for neuron in synapse.post
     *  post-synapse address = pre_key[neuron address]
     *  pre-synapse address = post_key[neuron address]
     * */
    {{ types.address | to_c_type }} post_synapse_address = pre_key[neuron_address];
    {{ types.address | to_c_type }} post_neuron_address = NULL_ADDRESS;
    {{ types.address | to_c_type }} pre_synapse_address = post_key[neuron_address];
    {{ types.address | to_c_type }} pre_neuron_address = NULL_ADDRESS;
    int not_infinite = 0;
    // stop if neuron is dead or not spiked
    if(
        n_flags[neuron_address] & IS_DEAD
        || !(n_flags[neuron_address] & IS_SPIKED)
    ){
        return;
    }
    // for each post-synapses
    not_infinite = 1000000;
    while(post_synapse_address != NULL_ADDRESS && not_infinite){
        not_infinite--; /* TODO: send error to host if infinite loop */
        if(!not_infinite){
            // TODO: ignore next line only on NVIDIA devices
            // printf("Warning: infinite loop in post synapse while\n");
        }
        post_neuron_address = s_post[post_synapse_address];
        // synapse is dead
        if(s_level[post_synapse_address] == 0){
            post_synapse_address = pre_value[post_synapse_address];
            continue;
        }
        // post-neuron is dead - kill synapse
        if(n_flags[post_neuron_address] & IS_DEAD){
            s_level[post_synapse_address] = 0;
            post_synapse_address = pre_value[post_synapse_address];
            continue;
        }
        // is spiked - change post neuron level
        atomic_add(
            &n_level[post_neuron_address],
            n_flags[neuron_address] & IS_INHIBITORY
            ? -(s_level[post_synapse_address] + s_learn[post_synapse_address])
            : (s_level[post_synapse_address] + s_learn[post_synapse_address])
        );
        // post-synapse learning
        if(n_spike_tick[neuron_address] - n_spike_tick[post_neuron_address]
                < d_spike_learn_threshold){
            s_learn[post_synapse_address] += d_learn_rate;
            if(s_learn[post_synapse_address] > d_learn_threshold){
                if((s_flags[post_synapse_address] & IS_STRENGTHENED) == 0){
                    // set learned flag
                    s_flags[post_synapse_address] |= IS_STRENGTHENED;
                    // once increase synapse level
                    s_level[post_synapse_address] += d_learn_threshold;
                    s_learn[post_synapse_address] = 0;
                }
                else{
                    s_learn[post_synapse_address] = d_learn_threshold;
                }
            }
        }
        if (s_learn[post_synapse_address]){
            s_learn[post_synapse_address] -= 1;
        }
        // next synapse
        post_synapse_address = pre_value[post_synapse_address];
    }
    // for each pre-synapses
    not_infinite = 1000000;
    while(pre_synapse_address != NULL_ADDRESS && not_infinite){
        not_infinite--; /* TODO: send error to host if infinite loop */
        if(!not_infinite){
            // TODO: ignore next line only on NVIDIA devices
            // printf("Warning: infinite loop in pre synapse while\n");
        }
        pre_neuron_address = s_pre[pre_synapse_address];
        // synapse is dead
        if(s_level[pre_synapse_address] == 0){
            pre_synapse_address = post_value[pre_synapse_address];
            continue;
        }
        // pre-neuron is dead - kill synapse
        if(n_flags[pre_neuron_address] & IS_DEAD){
            s_level[pre_synapse_address] = 0;
            pre_synapse_address = post_value[pre_synapse_address];
            continue;
        }
        // pre-synapse learning
        if(n_spike_tick[neuron_address] - n_spike_tick[pre_neuron_address]
                < d_spike_learn_threshold){
            s_learn[pre_synapse_address] += d_learn_rate;
            if(s_learn[pre_synapse_address] > d_learn_threshold){
                if((s_flags[pre_synapse_address] & IS_STRENGTHENED) == 0){
                    // set learned flag
                    s_flags[pre_synapse_address] |= IS_STRENGTHENED;
                    // once increase synapse level
                    s_level[pre_synapse_address] += d_learn_threshold;
                    s_learn[pre_synapse_address] = 0;
                }
                else{
                    s_learn[pre_synapse_address] = d_learn_threshold;
                }
            }
        }
        if (s_learn[pre_synapse_address]){
            s_learn[pre_synapse_address] -= 1;
        }
        // next pre-synapse
        pre_synapse_address = post_value[pre_synapse_address];
    }
}

// fill layers stat buffer with zeros
__kernel void init_layers_stat(
    __global {{ types.stat | to_c_type }}           * l_stat
) {
    {{ types.address | to_c_type }} address = get_global_id(0);
    l_stat[address] = 0;
}

// fill layers_stat with data
__kernel void update_layers_stat(
    __const {{ types.tick | to_c_type }}            d_ticks,
    __const {{ types.address | to_c_type }}         d_stat_size,
    __const {{ types.address | to_c_type }}         d_stat_fields,
    /* layers */
    __global {{ types.stat | to_c_type }}           * l_stat,
    __global {{ types.vitality | to_c_type }}       * l_max_vitality,
    /* neurons */
    __global {{ types.neuron_flags | to_c_type }}   * n_flags,
    __global {{ types.tick | to_c_type }}           * n_spike_tick,
    __global {{ types.medium_address | to_c_type }} * n_layer,
    __global {{ types.vitality | to_c_type }}       * n_vitality
) {
    {{ types.address | to_c_type }} neuron_address = get_global_id(0);
    if(
        n_flags[neuron_address] & IS_RECEIVER
    ){
        return;
    }
    // get layer
    {{ types.address | to_c_type }} layer_address = n_layer[neuron_address];
    // start of the stat block for the layer with layer_address
    {{ types.address | to_c_type }} layer_stat_start
        = d_stat_fields * layer_address;
    // field 0 - count spikes between [d_ticks - d_stat_size + 1, d_ticks]
    if(
        (n_spike_tick[neuron_address] > d_ticks - d_stat_size
        && n_spike_tick[neuron_address] <= d_ticks)
    ){
        atom_add(
            &l_stat[
                /* start of the stat of the layer with layer_address */
                layer_stat_start
                /* start of the field */
                /* + 0 * d_stat_size */
            ],
            1
        );
    }
    // field 1 - get number of the dead neurons
    if(
        n_flags[neuron_address] & IS_DEAD
        && !(n_flags[neuron_address] & IS_RECEIVER)
    ){
        atom_add(
            &l_stat[
                /* start of the stat of the layer with layer_address */
                layer_stat_start
                /* start of the field */
                + 1/* * d_stat_size*/
            ],
            1
        );
    }
    // field 3 - get neurons tiredness
    // = sum(layer.max_vitality - neuron.vitality)
    if(
        l_max_vitality[layer_address] - n_vitality[neuron_address] > 0
    ){
        atom_add(
            &l_stat[
                /* start of the stat of the layer with layer_address */
                layer_stat_start
                /* start of the field */
                + 3/* * d_stat_size*/
            ],
            l_max_vitality[layer_address] - n_vitality[neuron_address]
        );
    }
}

// calc synapses stats
__kernel void update_synapses_stat(
    __global {{ types.stat | to_c_type }}           * d_stat,
    __global {{ types.synapse_level | to_c_type }}  * s_learn,
    __global {{ types.synapse_flags | to_c_type }}  * s_flags
) {
    {{ types.address | to_c_type }} synapse_address = get_global_id(0);
    // field 2 - count of the synapses with IS_STRENGTHENED flag

    if(
        s_flags[synapse_address] & IS_STRENGTHENED
    ){
        atom_add(&d_stat[2], 1);
    }
    // field 4 - synapse learn level
    if(
        s_learn[synapse_address]
    ){
        atom_add(&d_stat[4], s_learn[synapse_address]);
    }
}

// get spiked IS_TRANSMITTER neurons
__kernel void tick_transmitter_index(
    __global {{ types.address | to_c_type }}        * i_local_address,
    __global {{ types.neuron_flags | to_c_type }}   * i_is_spiked,
    __global {{ types.neuron_flags | to_c_type }}   * n_flags
) {
    {{ types.address | to_c_type }} index = get_global_id(0);
    {{ types.address | to_c_type }} neuron_address = i_local_address[index];
    if ((n_flags[neuron_address] & IS_SPIKED)
        && !(n_flags[neuron_address] & IS_DEAD)){
        i_is_spiked[index] = 1;
    }
    else{
        i_is_spiked[index] = 0;
    }
}

// set spiked IS_RECEIVER neurons
__kernel void tick_receiver_index(
    __global {{ types.address | to_c_type }}        * i_local_address,
    __global {{ types.neuron_flags | to_c_type }}   * i_is_spiked,
    __global {{ types.neuron_flags | to_c_type }}   * n_flags
) {
    {{ types.address | to_c_type }} index = get_global_id(0);
    {{ types.address | to_c_type }} neuron_address = i_local_address[index];
    // set IS_SPIKED flag only
    if(i_is_spiked[index]){
        n_flags[neuron_address] |= IS_SPIKED;
    }
    i_is_spiked[index] = 0;
}

{% for type_name in types.allowed_input_data_type_names %}
// Add level from np_data with type numpy.{{ type_name }} to neuron.level
__kernel void tick_numpy_input_data_{{ type_name }}(
    __global {{ type_name | to_c_type  }}         * np_data,
    __const {{ types.address | to_c_type }}         n_address,
    __global {{ types.neuron_level | to_c_type }} * n_level
) {
    {{ types.address | to_c_type }} index = get_global_id(0);
    n_level[index + n_address] += np_data[index];
}
{% endfor %}

{% for type_name in types.allowed_output_data_type_names %}
// Add level from np_data with type numpy.{{ type_name }} to neuron.level
__kernel void tick_numpy_output_data_{{ type_name }}(
    /* domain */
    __const {{ types.tick | to_c_type }}            d_ticks,
    /* output index */
    __global {{ types.address | to_c_type }}        * oi_address,
    __global {{ type_name | to_c_type  }}           * oi_data,
    __global {{ types.tick | to_c_type }}           * oi_tick,
    /* neuron */
    __global {{ types.neuron_flags | to_c_type }}   * n_flags
) {
    {{ types.address | to_c_type }} index = get_global_id(0);
    {{ types.address | to_c_type }} neuron_address = oi_address[index];
    {{ types.tick | to_c_type }} diff = 0;
    int threshold = 255; // FIXME: should be max of type_name
    if ((n_flags[neuron_address] & IS_SPIKED)
        && !(n_flags[neuron_address] & IS_DEAD)){
        diff = d_ticks - oi_tick[index] - 1;
        if(diff >= threshold){
            oi_data[index] = 1; /* was spike - let us notice that */
        }
        else{
            oi_data[index] = threshold - diff;
        }
        oi_tick[index] = d_ticks;
    }
    else{
        if(oi_data[index]){
            oi_data[index] -= 1; /* relax */
        }
    }
}
{% endfor %}

{% endblock %}
