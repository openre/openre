{% extends "device/base.c" %}

{% block code %}
// Add level from data to neuron.level
__kernel void tick_numpy_input_data_uint8(
    __global unsigned char * np_data,
    __global {{ types.neuron_level | to_c_type }}   * n_level
) {
    {{ types.address | to_c_type }} index = get_global_id(0);
    n_level[index] += np_data[index];
}

{% endblock %}
